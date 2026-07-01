"""Anti-spoof liveness service built from the ONNX MiniFAS source repo.

This implementation intentionally follows the source repository we inspected:
- 128x128 RGB face crops
- letterbox resize with reflection padding
- ONNX logits interpreted as [real, spoof]
- decision score = real_logit - spoof_logit
- configured threshold is treated as probability and converted to logit space
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from django.conf import settings

try:
    import onnxruntime as ort
except Exception:  # pragma: no cover
    ort = None

logger = logging.getLogger(__name__)


def _prob_to_logit(prob: float) -> float:
    prob = float(max(1e-6, min(1.0 - 1e-6, prob)))
    return float(np.log(prob / (1.0 - prob)))


def _preprocess_face_crop(image: np.ndarray, model_size: int) -> np.ndarray:
    """Resize with letterbox padding, normalize to [0,1], convert to CHW."""
    old_h, old_w = image.shape[:2]
    ratio = float(model_size) / max(old_h, old_w)
    scaled_h = int(old_h * ratio)
    scaled_w = int(old_w * ratio)

    interpolation = cv2.INTER_LANCZOS4 if ratio > 1.0 else cv2.INTER_AREA
    resized = cv2.resize(image, (scaled_w, scaled_h), interpolation=interpolation)

    pad_w = model_size - scaled_w
    pad_h = model_size - scaled_h
    top = pad_h // 2
    bottom = pad_h - top
    left = pad_w // 2
    right = pad_w - left

    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_REFLECT_101)
    rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return rgb.transpose(2, 0, 1)


class LivenessService:
    """Singleton anti-spoof service used by attendance."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._session = None
        self._input_name = None
        self._model_loaded = False
        self._load_lock = threading.Lock()

    def _resolve_model_path(self) -> Optional[Path]:
        model_path = Path(getattr(settings, "ANTI_SPOOF_MODEL_PATH", ""))
        return model_path if model_path.exists() else None

    def _extract_face_crop(self, frame: np.ndarray, face) -> Optional[np.ndarray]:
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox

        frame_h, frame_w = frame.shape[:2]
        margin_ratio = float(getattr(settings, "ANTI_SPOOF_CROP_MARGIN_RATIO", 0.12))
        dx = int((x2 - x1) * margin_ratio)
        dy = int((y2 - y1) * margin_ratio)

        x1 = max(0, x1 - dx)
        y1 = max(0, y1 - dy)
        x2 = min(frame_w, x2 + dx)
        y2 = min(frame_h, y2 + dy)

        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2]

    def _load_model(self) -> bool:
        if self._model_loaded:
            return self._session is not None

        with self._load_lock:
            if self._model_loaded:
                return self._session is not None

            model_path = self._resolve_model_path()
            if model_path is None:
                self._model_loaded = True
                return False

            try:
                if ort is not None and model_path.suffix.lower() == ".onnx":
                    sess_options = ort.SessionOptions()
                    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                    sess_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL

                    available = ort.get_available_providers()
                    preferred = ["CUDAExecutionProvider", "CPUExecutionProvider"]
                    providers = [provider for provider in preferred if provider in available]
                    if not providers:
                        providers = available

                    self._session = ort.InferenceSession(
                        str(model_path),
                        sess_options=sess_options,
                        providers=providers,
                    )
                    self._input_name = self._session.get_inputs()[0].name
                    logger.info(
                        "Loaded anti-spoof ONNX model via onnxruntime from %s (providers=%s)",
                        model_path,
                        providers,
                    )
                elif model_path.suffix.lower() == ".onnx":
                    self._session = cv2.dnn.readNetFromONNX(str(model_path))
                    self._input_name = None
                    logger.info("Loaded anti-spoof ONNX model via OpenCV DNN from %s", model_path)
                else:
                    logger.warning("Unsupported anti-spoof model format: %s", model_path)
                    self._session = None
            except Exception as exc:
                logger.exception("Failed to load anti-spoof model: %s", exc)
                self._session = None
                self._input_name = None

            self._model_loaded = True
            return self._session is not None

    def _infer_logits(self, crop: np.ndarray) -> Tuple[float, float, list]:
        model_size = int(getattr(settings, "ANTI_SPOOF_INPUT_SIZE", 128))
        if self._session is None:
            raise RuntimeError("Anti-spoof session is not loaded")

        if ort is not None and isinstance(self._session, ort.InferenceSession):
            inp = _preprocess_face_crop(crop, model_size)[None, :]
            output = self._session.run(None, {self._input_name: inp})[0]
        else:
            blob = cv2.dnn.blobFromImage(
                crop,
                scalefactor=1.0 / 255.0,
                size=(model_size, model_size),
                mean=(0, 0, 0),
                swapRB=True,
                crop=False,
            )
            self._session.setInput(blob)
            output = self._session.forward()

        output = np.squeeze(np.asarray(output, dtype=np.float32)).reshape(-1)
        if output.size < 2:
            raise RuntimeError(f"Unexpected anti-spoof output shape: {output.shape}")

        real_logit = float(output[0])
        spoof_logit = float(output[1])
        return real_logit, spoof_logit, output.tolist()

    def evaluate(self, frame: np.ndarray, face) -> dict:
        """Evaluate one detected face and return anti-spoof decision metadata."""
        if not getattr(settings, "ANTI_SPOOF_ENABLED", True):
            return {
                "is_live": True,
                "score": 0.0,
                "method": "disabled",
                "reason": "anti_spoof_disabled",
                "decision": "live",
            }

        crop = self._extract_face_crop(frame, face)
        if crop is None or crop.size == 0:
            return {
                "is_live": False,
                "score": 0.0,
                "method": "invalid_crop",
                "reason": "invalid_face_crop",
                "decision": "spoof",
            }

        threshold_prob = float(getattr(settings, "ANTI_SPOOF_THRESHOLD", 0.50))
        uncertain_margin = float(getattr(settings, "ANTI_SPOOF_UNCERTAIN_MARGIN", 0.15))
        threshold_logit = _prob_to_logit(threshold_prob)
        live_cutoff = _prob_to_logit(min(1.0 - 1e-6, threshold_prob + uncertain_margin))
        spoof_cutoff = _prob_to_logit(max(1e-6, threshold_prob - uncertain_margin))

        if self._load_model() and self._session is not None:
            try:
                real_logit, spoof_logit, raw_logits = self._infer_logits(crop)
                score = real_logit - spoof_logit

                if score >= live_cutoff:
                    decision = "live"
                    is_live = True
                elif score <= spoof_cutoff:
                    decision = "spoof"
                    is_live = False
                else:
                    decision = "uncertain"
                    is_live = False

                if getattr(settings, "ANTI_SPOOF_DEBUG", False):
                    logger.debug(
                        "anti-spoof logits=%s real=%.4f spoof=%.4f diff=%.4f threshold=%.4f live_cutoff=%.4f spoof_cutoff=%.4f decision=%s",
                        raw_logits,
                        real_logit,
                        spoof_logit,
                        score,
                        threshold_logit,
                        live_cutoff,
                        spoof_cutoff,
                        decision,
                    )

                return {
                    "is_live": is_live,
                    "score": round(float(score), 4),
                    "method": "onnx_model",
                    "reason": "model_score",
                    "decision": decision,
                    "real_logit": real_logit,
                    "spoof_logit": spoof_logit,
                    "raw_logits": raw_logits,
                }
            except Exception as exc:
                logger.exception("Anti-spoof ONNX inference failed: %s", exc)

        if getattr(settings, "ANTI_SPOOF_USE_HEURISTIC_FALLBACK", True):
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            h, w = gray.shape[:2]
            if min(h, w) < int(getattr(settings, "ANTI_SPOOF_MIN_FACE_SIZE", 96)):
                return {
                    "is_live": False,
                    "score": 0.0,
                    "method": "heuristic",
                    "reason": "face_too_small",
                    "decision": "spoof",
                }

            lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            score = float(np.clip((lap_var - 45.0) / 380.0, 0.0, 1.0))
            decision = "live" if score >= 0.60 else "spoof" if score <= 0.35 else "uncertain"
            return {
                "is_live": decision == "live",
                "score": round(score, 4),
                "method": "heuristic",
                "reason": "fallback",
                "decision": decision,
            }

        return {
            "is_live": False,
            "score": 0.0,
            "method": "no_model",
            "reason": "anti_spoof_model_unavailable",
            "decision": "spoof",
        }


liveness_service = LivenessService()
