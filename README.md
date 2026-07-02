# AI-Attend: Face Recognition Attendance System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com/)
[![InsightFace](https://img.shields.io/badge/InsightFace-buffalo__l-orange.svg)](https://github.com/deepinsight/insightface)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://www.postgresql.org/)

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Project Structure](#-project-structure)
- [Django Apps](#-django-apps)
- [Database Models](#-database-models)
- [AI Pipeline](#-ai-pipeline)
- [Anti-Spoofing / Liveness Detection](#-anti-spoofing--liveness-detection)
- [Role-Based Access](#-role-based-access)
- [URL Routes](#-url-routes)
- [Requirements](#-requirements)
- [Installation & Setup](#-installation--setup)
- [Running the Project](#-running-the-project)
- [Colab Notebooks](#-colab-notebooks)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Future Enhancements](#-future-enhancements)

---

## 🎯 Overview

**AI-Attend** is a full-stack web application for automated student attendance tracking using real-time face recognition. It is built on **Django 5.2**, backed by **PostgreSQL**, and powered by the **InsightFace `buffalo_l` model** (ArcFace-based) for accurate 512-D face embeddings. Live recognition frames are also passed through a **MiniFASNet anti-spoofing model** so printed photos / phone-screen replays are rejected before a match is even attempted.

The system follows a two-phase workflow:

1. **Enrollment** — An admin uses a webcam to capture multiple face frames per student. These are processed into a 512-D centroid embedding and stored in the database.
2. **Live Attendance** — A teacher starts a session for a specific **batch** (cohort). The webcam streams frames to the backend API, which runs a liveness check, then detects and recognizes faces in real time and automatically marks students present.

Teachers can also **manually override** attendance, **export session data as CSV**, and view historical sessions. Students can view their own attendance and **request corrections** for absences within a configurable time window. HODs have department-level oversight scoped to their own department. Admins manage all data, including batch intake, semester promotion, and student graduation.

---

## ✨ Key Features

| Feature | Details |
|--------|---------|
| 🔍 **Face Detection** | InsightFace `buffalo_l` — RetinaFace-based detector (`det_size=640×640`, `thresh=0.5`) |
| 🎭 **Face Recognition** | ArcFace 512-D L2-normalized embeddings, cosine similarity matching (`threshold=0.45`) |
| 🛡️ **Anti-Spoofing / Liveness** | MiniFASNet (V1 + V2) ONNX/PyTorch ensemble runs before every recognition attempt; rejects photos, screens, and masks |
| 📹 **Live Webcam API** | Browser streams base64 JPEG frames → Django JSON API → liveness check → recognition → marks attendance in DB |
| 👤 **Webcam Enrollment** | Admin captures ≥3 frames per student → centroid embedding stored as binary in PostgreSQL, with duplicate-face detection |
| 🎓 **Batch / Cohort Management** | Students belong to a `Batch` (department + intake year); sessions are scoped to one batch so parallel cohorts in the same semester don't collide |
| 🔢 **Auto Roll Numbers** | Roll number = `BatchCode + DeptRollCode + Sequence` (e.g. `260301`), generated automatically on student creation |
| 🔒 **Semester Locking** | Each batch can lock to a single semester; promoting or graduating a batch is a one-click admin action per batch |
| 🏫 **Role-Based Access** | Admin / HOD / Teacher / Student — each with scoped dashboards and permissions, enforced down to session/department/batch level |
| 📊 **Session Management** | Teachers start/end sessions per subject + batch; ACTIVE → COMPLETED with present/absent/late counts |
| ✏️ **Manual Override** | Teachers can manually mark any student in the session's cohort as PRESENT / ABSENT / LATE |
| 🔔 **In-App Notifications** | Students are notified when marked absent; teachers/HODs notified on new correction requests; students notified on approval/rejection |
| 📝 **Attendance Correction Requests** | Students can request a correction for an absence within a configurable window (default 48h); teachers/HODs approve or reject with a comment |
| 📥 **CSV Reports** | Role-scoped exports: student attendance summary, session-by-session detail, subject summary, and a student's own attendance — all filterable by date range, department, batch, subject |
| 🗄️ **PostgreSQL Backend** | All embeddings, sessions, attendance, notifications, and users stored in PostgreSQL |
| 🖥️ **Django Admin** | Full admin panel for managing all models |
| ⏱️ **Session Security** | Auto-logout after 30 minutes of inactivity via custom middleware |
| 📓 **Colab Notebooks** | Data preparation notebooks for face extraction and enrollment dataset building |

---

## 🏗️ System Architecture

```
Browser (Webcam)
       │
       │  base64 JPEG frames (POST /attendance/api/recognize/<session_id>/)
       ▼
┌─────────────────────────────────────────────┐
│              Django Web Server               │
│                                             │
│  ┌─────────────┐    ┌──────────────────┐   │
│  │  attendance │    │   enrollment     │   │
│  │   api.py    │    │   views.py       │   │
│  └──────┬──────┘    └────────┬─────────┘   │
│         │                    │             │
│         ▼                    ▼             │
│  ┌──────────────────────────────────────┐  │
│  │           AIService (Singleton)      │  │
│  │   web/ai_service.py                  │  │
│  │                                      │  │
│  │  detect_faces()   → InsightFace app  │  │
│  │  check_liveness()→ MiniFASNet (antispoof) │
│  │  get_embedding()  → 512-D ArcFace    │  │
│  │  recognize()      → cosine similarity│  │
│  │  compute_centroid()→ enrollment      │  │
│  │  load_gallery()   → DB → numpy arrays│  │
│  └──────┬───────────────────┬───────────┘  │
│         │                   │              │
│  ┌──────▼───────┐   ┌───────▼────────┐     │
│  │ InsightFace  │   │  MiniFASNetV1/V2│     │
│  │ buffalo_l    │   │  (antispoof/)   │     │
│  │ (CUDA / CPU) │   │  (CUDA / CPU)   │     │
│  └──────────────┘   └────────────────┘     │
└─────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────┐
│       PostgreSQL DB     │
│                         │
│  CustomUser             │
│  Department / Batch     │
│  Subject / SubjectTeacher│
│  Session (batch-scoped) │
│  Attendance             │
│  AttendanceCorrectionRequest │
│  Notification / NotificationPreference │
│  FaceEmbedding          │
└─────────────────────────┘
```

---

## 📁 Project Structure

```
AI-attend/
│
├── Colab Notebooks/                    # Jupyter notebooks for data preparation
│   ├── extract_faces_enrollment.ipynb  # Extract & align faces from videos for enrollment
│   └── face_extraction.ipynb           # General face extraction utilities
│
├── data/                                # Raw dataset directory (videos, images)
│
├── src/                                 # Standalone Python scripts / research code
│
└── web/                                 # Django project root
    ├── manage.py
    ├── ai_service.py                    # Thread-safe InsightFace + liveness singleton
    ├── liveness_service.py              # Standalone ONNX-based liveness scorer
    ├── fix_all.py                       # One-off dev script (bulk template/view patcher)
    ├── migrate_data.py                  # One-off legacy-data migration helper
    │
    ├── attendance_project/              # Django project settings
    │   ├── settings.py
    │   ├── urls.py
    │   ├── security.py                  # SessionTimeoutMiddleware (30-min auto logout)
    │   ├── error_views.py               # Custom 404 handler
    │   ├── wsgi.py
    │   └── asgi.py
    │
    ├── accounts/                        # User management app
    │   ├── models.py        (CustomUser — incl. batch, batch_sequence)
    │   ├── views.py          (login, logout, dashboard, profile, change password)
    │   ├── forms.py
    │   ├── urls.py
    │   ├── admin.py
    │   └── management/commands/
    │       ├── backfill_student_batches.py
    │       └── check_batch_migration_readiness.py
    │
    ├── academics/                       # Academic structure app
    │   ├── models.py        (Department, Batch, Subject, SubjectTeacher)
    │   ├── views.py         (CRUD for depts, batches, teachers, subjects, students)
    │   ├── lifecycle.py     (semester_management, promote_semester, graduate_students)
    │   ├── forms.py
    │   ├── urls.py
    │   └── admin.py
    │
    ├── attendance/                      # Attendance session app
    │   ├── models.py        (Session, Attendance, Notification,
    │   │                      AttendanceCorrectionRequest, NotificationPreference)
    │   ├── views.py         (session mgmt, HOD/student views, notifications, corrections)
    │   ├── api.py           (recognize_frame — liveness-gated recognition API)
    │   ├── reports.py       (reports_page, export_report_csv)
    │   ├── signals.py       (auto absence notifications, auto session-count updates)
    │   ├── urls.py
    │   ├── admin.py
    │   └── management/commands/
    │       └── backfill_session_batches.py
    │
    ├── enrollment/                       # Face enrollment app
    │   ├── models.py         (FaceEmbedding)
    │   ├── views.py          (enroll_page, enroll_process, enroll_delete)
    │   ├── urls.py
    │   └── admin.py
    │
    ├── antispoof/                        # MiniFASNet anti-spoofing package
    │   ├── anti_spoof_predict.py         # Model loading + inference
    │   ├── generate_patches.py           # Face-crop scaling for each model variant
    │   ├── utility.py                    # Model-name parsing helpers
    │   ├── model_lib/MiniFASNet.py       # V1 / V2 / V1SE / V2SE architectures
    │   ├── data_io/                      # Transform pipeline for training/inference
    │   └── resources/anti_spoof_models/  # .pth weights consumed by ai_service
    │
    ├── static/                           # CSS, JS, images
    ├── templates/                        # HTML templates (Bootstrap 5)
    └── media/                            # Uploaded media / face crops
```

---

## 🧩 Django Apps

### `accounts` — User Management

Extends Django's `AbstractUser` with a **role-based system** and batch/cohort membership:

```python
class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        ADMIN   = 'admin',   'Admin'
        HOD     = 'hod',     'HOD'
        TEACHER = 'teacher', 'Teacher'
        STUDENT = 'student', 'Student'

    role           = CharField(choices=Role.choices)
    full_name      = CharField(max_length=150)
    department     = ForeignKey('academics.Department')
    roll_no        = CharField(unique=True)          # Students only
    batch          = ForeignKey('academics.Batch')   # Students only — intake cohort
    batch_sequence = PositiveIntegerField()           # Students only — position within batch
    semester       = PositiveIntegerField()           # Students only (1–8)
    phone          = CharField()
```

`(batch, batch_sequence)` is enforced unique at the DB level so roll numbers can never collide within a batch.

**Management commands:**
- `backfill_student_batches [--apply] [--auto-set-department-roll-code]` — infers `batch`/`batch_sequence` for legacy students from their existing roll number (`YYDDSS` pattern).
- `check_batch_migration_readiness [--fail-on-issues]` — reports students missing batch data before a non-null migration is applied.

**URLs:**
| Route | View | Name |
|-------|------|------|
| `/accounts/login/` | `login_view` | `login` |
| `/accounts/logout/` | `logout_view` | `logout` |
| `/dashboard/` | `dashboard_view` | `dashboard` |
| `/profile/` | `profile_view` | `profile` |
| `/change-password/` | `change_password_view` | `change_password` |

---

### `academics` — Academic Structure & Lifecycle

Manages the academic hierarchy: Departments → Batches → Subjects → Subject-Teacher assignments, plus semester promotion/graduation.

**Models:**
- `Department` — name, code, `roll_code` (2-digit code used in roll numbers), HOD (FK to CustomUser), is_active
- `Batch` — department + intake `year`, 2-digit `code`, `semester_lock_enabled`, `locked_semester`, is_active. Unique per `(department, year)`.
- `Subject` — name, code, department, semester (1–8), credit_hours, is_active
- `SubjectTeacher` — links one teacher to one subject (one-to-one per subject)

**Roll number generation** (`_generate_roll_no`): `BatchCode + DepartmentRollCode + zero-padded Sequence`, e.g. batch `26`, dept `03`, sequence `01` → `260301`. Sequence numbers are allocated per `(batch, department)` and capped at 99.

**Semester lifecycle** (`lifecycle.py`):
- `semester_management` — dashboard showing student counts per department/batch/semester with promote/graduate actions.
- `promote_semester` — bumps all students in one batch from semester *N* to *N+1*; blocked if the target semester already has students, or if the batch is locked to a different semester.
- `graduate_students` — deactivates all Semester-8 students in a batch (data preserved, not deleted).

**URLs (Admin-only CRUD):**

| Route | Description |
|-------|-------------|
| `/academics/batches/` | List batches |
| `/academics/batches/create/` | Add batch |
| `/academics/departments/` | List departments |
| `/academics/departments/create/` | Add department |
| `/academics/departments/<pk>/edit/` | Edit department |
| `/academics/departments/<pk>/delete/` | Deactivate department |
| `/academics/teachers/` | List teachers |
| `/academics/teachers/create/` | Add teacher |
| `/academics/teachers/<pk>/edit/` | Edit teacher |
| `/academics/teachers/<pk>/delete/` | Deactivate teacher |
| `/academics/teachers/<pk>/promote-hod/` | Promote/demote HOD |
| `/academics/teachers/<pk>/reset-password/` | Reset teacher password |
| `/academics/subjects/` | List subjects |
| `/academics/subjects/create/` | Add subject |
| `/academics/subjects/<pk>/edit/` | Edit subject |
| `/academics/subjects/<pk>/delete/` | Deactivate subject |
| `/academics/students/` | List students |
| `/academics/students/create/` | Add student (auto roll number + batch resolution) |
| `/academics/students/<pk>/edit/` | Edit student |
| `/academics/students/<pk>/delete/` | Deactivate student |
| `/academics/students/<pk>/reset-password/` | Reset student password |
| `/academics/all-sessions/` | Admin view of all sessions (filterable by dept/batch) |
| `/academics/semesters/` | Semester management dashboard |
| `/academics/semesters/promote/` | Promote a batch's semester |
| `/academics/semesters/graduate/` | Graduate a batch's Semester-8 students |

---

### `attendance` — Session, Attendance, Notifications & Corrections

**Models:**

```python
class Session(models.Model):
    subject      = ForeignKey(Subject)
    teacher      = ForeignKey(CustomUser)
    department   = ForeignKey(Department)
    batch        = ForeignKey(Batch, null=True, blank=True)   # cohort scope
    semester     = PositiveIntegerField()
    date         = DateField()
    start_time   = TimeField()
    end_time     = TimeField()
    status       = CharField(choices=['ACTIVE', 'COMPLETED', 'CANCELLED'])
    total_present / total_absent / total_late = PositiveIntegerField()
    notification_sent = BooleanField(default=False)

class Attendance(models.Model):
    session     = ForeignKey(Session)
    student     = ForeignKey(CustomUser)
    status      = CharField(choices=['PRESENT', 'ABSENT', 'LATE'])
    time_marked = TimeField()
    confidence  = FloatField()   # Face recognition cosine similarity
    marked_by   = CharField(choices=['auto', 'manual'])

class AttendanceCorrectionRequest(models.Model):
    attendance        = OneToOneField(Attendance)
    student           = ForeignKey(CustomUser)
    teacher           = ForeignKey(CustomUser, null=True, blank=True)
    reason            = TextField()
    status            = CharField(choices=['pending', 'approved', 'rejected', 'withdrawn'])
    teacher_comment   = TextField(blank=True)
    corrected_status  = CharField(choices=Attendance.Status.choices, null=True)
    # One request per (attendance, student); must be submitted within
    # ATTENDANCE_REQUEST_WINDOW hours of session end (default 48h)

class Notification(models.Model):
    user                = ForeignKey(CustomUser)
    notification_type   = CharField(choices=['absent', 'request_submitted',
                                              'request_approved', 'request_rejected'])
    title, message      = CharField(), TextField()
    session, attendance, correction_request = ForeignKey(..., null=True)
    is_read, read_at    = BooleanField(), DateTimeField(null=True)

class NotificationPreference(models.Model):
    user = OneToOneField(CustomUser)
    notify_on_absence / notify_on_request_response / notify_on_request_received = BooleanField()
    email_on_absence / email_on_request_response = BooleanField()
    quiet_hours_enabled / quiet_hours_start / quiet_hours_end
```

`Session.batch` scopes a session (and therefore the student roster, mark-manual guard, and stats) to one cohort — this lets two batches share the same subject/semester without their sessions or attendance mixing. A signal (`signals.py`) automatically fires `send_absence_notifications()` when a session is saved as `COMPLETED`, and recalculates `total_present/late/absent` whenever an `Attendance` row is saved.

**URLs:**

| Route | Description | Role |
|-------|-------------|------|
| `/attendance/my-subjects/` | Teacher's assigned subjects (with batch-wise student counts) | Teacher/HOD |
| `/attendance/start-session/<subject_id>/` | Start a session for a chosen batch | Teacher/HOD |
| `/attendance/session/<session_id>/` | Live session view (webcam + roll) | Teacher/HOD |
| `/attendance/session/<session_id>/end/` | End session, auto-mark remaining as ABSENT | Teacher/HOD |
| `/attendance/session/<session_id>/mark/<student_id>/<status>/` | Manual mark (blocked if student isn't in the session's cohort) | Teacher/HOD |
| `/attendance/session/<session_id>/export/` | Export session CSV | Teacher/HOD/Admin |
| `/attendance/session-history/` | Past sessions, filterable by subject/batch | Teacher/HOD |
| `/attendance/my-attendance/` | Student's own records, scoped to their batch's sessions | Student |
| `/attendance/dept-overview/` | Department attendance summary | HOD |
| `/attendance/dept-students/` | Department student list, filterable by batch | HOD |
| `/attendance/reports/` | Reports landing page (role-scoped report cards) | All |
| `/attendance/reports/export/` | CSV export — `type=student_summary\|session_detail\|attendance\|my_attendance` | All (role-checked) |
| `/attendance/api/recognize/<session_id>/` | **Real-time liveness + face recognition API** | Teacher/HOD |
| `/attendance/api/notifications/` | List notifications (filter by type/unread) | All |
| `/attendance/api/notifications/<id>/read/` | Mark one notification read | All |
| `/attendance/api/notifications/read-all/` | Mark all notifications read | All |
| `/attendance/api/notifications/unread-count/` | Unread badge count | All |
| `/attendance/notifications/` | Full notifications page | All |
| `/attendance/session/<session_id>/detail/` | Session detail with correction-request UI | Student/Teacher/HOD/Admin |
| `/attendance/api/attendance/<id>/correction-form/` | Get correction-request window/status | Student |
| `/attendance/api/attendance/<id>/submit-correction/` | Submit a correction request | Student |
| `/attendance/api/correction-requests/my-requests/` | Student's own correction requests | Student |
| `/attendance/api/correction-requests/<id>/withdraw/` | Withdraw a pending request | Student |
| `/attendance/api/correction-requests/pending/` | Pending requests for teacher/HOD | Teacher/HOD |
| `/attendance/api/correction-requests/<id>/approve/` | Approve + set corrected status | Teacher/HOD |
| `/attendance/api/correction-requests/<id>/reject/` | Reject with a comment | Teacher/HOD |
| `/attendance/corrections/teacher/` | Correction requests inbox page | Teacher/HOD |
| `/attendance/corrections/my-requests/` | Student's correction requests page | Student |

#### Real-Time Recognition API (now liveness-gated)

`POST /attendance/api/recognize/<session_id>/`

**Request:**
```json
{
  "frame": "<base64_jpg_string>"
}
```

**Response:**
```json
{
  "faces_detected": 2,
  "recognized": [
    {"roll_no": "780322", "name": "Murari", "similarity": 0.87, "liveness": 0.96, "status": "MARKED"},
    {"roll_no": "780306", "name": "Arkrisha", "similarity": 0.82, "liveness": 0.91, "status": "ALREADY_MARKED"}
  ],
  "unknown": 0,
  "spoof_count": 1,
  "total_marked": 1,
  "total_students": 30
}
```

The API:
1. Verifies the requesting user owns the session (or is admin/HOD)
2. Decodes the base64 frame
3. Loads the gallery **filtered to only students in that session's department + semester + batch**
4. Detects faces using InsightFace
5. Runs each detected face through the **MiniFASNet anti-spoof ensemble** — faces that fail liveness are counted in `spoof_count` and skipped before any embedding work happens
6. Matches remaining (live) faces against the gallery (cosine similarity ≥ 0.45)
7. Creates an `Attendance` record with `marked_by='auto'` and stores the confidence + liveness score
8. Returns results to the browser for live UI updates

---

### `enrollment` — Face Enrollment

**Model:**

```python
class FaceEmbedding(models.Model):
    user           = OneToOneField(CustomUser)   # Student only
    embedding      = BinaryField()               # 512-D float32 (2048 bytes)
    embedding_dim  = PositiveIntegerField(default=512)
    num_samples    = PositiveIntegerField()       # Frames used
    intra_sim_mean = FloatField()                 # Quality: mean cosine similarity
    intra_sim_min  = FloatField()
    intra_sim_std  = FloatField()
    photo_path     = CharField()                  # Best face crop path
    is_active      = BooleanField(default=True)
```

**Quality Labels:**
- `Good` → `intra_sim_mean >= 0.7`
- `Fair` → `intra_sim_mean >= 0.5`
- `Poor` → `intra_sim_mean < 0.5`

**URLs:**

| Route | Description | Role |
|-------|-------------|------|
| `/enrollment/` | Webcam enrollment page | Admin |
| `/enrollment/process/` | Process captured frames API (rejects duplicate faces already enrolled under another roll number) | Admin |
| `/enrollment/delete/<student_id>/` | Delete student embedding | Admin |

**Enrollment Process:**
1. Admin selects a student from the list
2. Webcam captures ≥3 frames (single face only per frame)
3. Each frame → InsightFace detection → ArcFace 512-D embedding
4. New embeddings are checked against the existing gallery to catch a person accidentally enrolling under two roll numbers
5. Centroid is computed and L2-normalized
6. Stored as binary in `FaceEmbedding.embedding`, along with a reference photo crop

---

## 🗄️ Database Models

```
CustomUser (accounts)
    │
    ├── department → Department (academics)
    ├── batch → Batch (academics)                [students]
    │
    └── face_embedding → FaceEmbedding (enrollment)

Department (academics)
    ├── hod → CustomUser
    ├── batches → Batch[]
    ├── subjects → Subject[]
    └── sessions → Session[]

Batch (academics)
    ├── department → Department
    ├── students → CustomUser[]
    └── sessions → Session[]

Subject (academics)
    ├── department → Department
    └── teacher_assignments → SubjectTeacher[]

SubjectTeacher (academics)
    ├── teacher → CustomUser
    └── subject → Subject

Session (attendance)
    ├── subject → Subject
    ├── teacher → CustomUser
    ├── department → Department
    ├── batch → Batch
    ├── records → Attendance[]
    └── notifications → Notification[]

Attendance (attendance)
    ├── session → Session
    ├── student → CustomUser
    ├── correction_request → AttendanceCorrectionRequest (1:1)
    └── notifications → Notification[]

AttendanceCorrectionRequest (attendance)
    ├── attendance → Attendance (1:1)
    ├── student → CustomUser
    ├── teacher → CustomUser
    └── notifications → Notification[]

Notification (attendance)
    ├── user → CustomUser
    ├── session → Session
    ├── attendance → Attendance
    └── correction_request → AttendanceCorrectionRequest

NotificationPreference (attendance)
    └── user → CustomUser (1:1)

FaceEmbedding (enrollment)
    └── user → CustomUser
```

---

## 🤖 AI Pipeline

### `AIService` — Thread-Safe Singleton (`web/ai_service.py`)

The `AIService` class wraps InsightFace **and** the MiniFASNet anti-spoofing models. It is instantiated **once** at startup (lazy-loaded on first use) and uses a `threading.Lock` to be safe under concurrent Django requests.

```python
from ai_service import ai_service   # Global singleton

# Detect faces in a BGR frame
faces = ai_service.detect_faces(frame)          # → list of Face objects

# Anti-spoof check — run BEFORE embedding a face
is_real, liveness_score = ai_service.check_liveness(frame, face)
# → (bool, float in [0, 1]); fails open (True, 1.0) if the antispoof
#    models aren't installed, so recognition still works without them

# Get 512-D L2-normalized ArcFace embedding
emb = ai_service.get_embedding(face)            # → np.ndarray (512,) float32

# Compute centroid from multiple embeddings (enrollment)
result = ai_service.compute_centroid(embeddings)
# → {'centroid': np.ndarray, 'num_samples': int,
#    'intra_sim_mean': float, 'intra_sim_min': float, 'intra_sim_std': float}

# Match against gallery
match = ai_service.recognize(embedding, gallery, threshold=0.45)
# gallery format: {user_id: {'embedding': np.ndarray, 'roll_no': str, 'name': str}}
# → None | {'user_id': int, 'roll_no': str, 'name': str, 'similarity': float}

# Load / refresh all active embeddings from DB
gallery = ai_service.load_gallery()
ai_service.refresh_gallery()   # call after enroll/delete to bust the cache
```

**InsightFace Configuration:**
```python
FaceAnalysis(
    name='buffalo_l',
    providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
)
app.prepare(ctx_id=0, det_size=(640, 640), det_thresh=0.5)
```

---

## 🛡️ Anti-Spoofing / Liveness Detection

Located in `web/antispoof/` (a vendored MiniVision-style MiniFASNet implementation) plus `web/liveness_service.py` (a standalone ONNX-based scorer used as an alternate entry point).

- **Models:** `MiniFASNetV1` and `MiniFASNetV2` (with SE variants available) — small PyTorch CNNs trained to classify a face crop as real vs. spoof.
- **How it runs:** for each face detected in a frame, `AIService.check_liveness()` crops the face per-model, runs both `.pth` models found in `antispoof/resources/anti_spoof_models/`, sums their softmax outputs, and normalizes to a single `liveness_score` in `[0, 1]`.
- **Threshold:** `LIVENESS_THRESHOLD` in `settings.py` (default `0.85`). A face is accepted as real only if the score meets or exceeds this.
- **Fail-open by design:** if the model directory is missing or loading fails, `check_liveness()` returns `(True, 1.0)` so the attendance flow degrades gracefully instead of blocking every recognition.
- **`liveness_service.py`** offers a separate ONNX-runtime implementation (`ANTI_SPOOF_MODEL_PATH`, `.onnx`) with an additional OpenCV-based heuristic fallback (`ANTI_SPOOF_USE_HEURISTIC_FALLBACK`) for environments without the trained model — useful for local dev/testing.
- Spoofed frames are rejected **before** any embedding/recognition work runs, and are reported back to the frontend as `spoof_count` so the live session UI can show a "Spoof Blocked" toast.

---

## 👥 Role-Based Access

| Role | Permissions |
|------|------------|
| **Admin** | Full access: manage departments, batches, teachers, subjects, students; run semester promotion/graduation; enroll faces; view/export all sessions and reports |
| **HOD** | Department-scoped: view department sessions, students (filterable by batch), attendance overview, correction-request inbox for their department only |
| **Teacher** | Subject-scoped: start/end sessions per batch, live recognition, manual marks (guarded to the session's own cohort), export CSV, respond to correction requests they own |
| **Student** | Self-only, batch-scoped: view own attendance records, request/withdraw attendance corrections within the allowed window |

Each role gets a dedicated dashboard template:
- `dashboards/admin_dashboard.html`
- `dashboards/hod_dashboard.html`
- `dashboards/teacher_dashboard.html`
- `dashboards/student_dashboard.html`

Session security is enforced globally: `SessionTimeoutMiddleware` expires the session after 30 minutes of inactivity, and any unmatched URL renders the custom `404.html` page.

---

## 📋 Requirements

```
python>=3.8
django>=5.2
insightface>=0.7
opencv-python>=4.5
numpy>=1.19
torch                     # required by the antispoof MiniFASNet models
torchvision
onnxruntime               # used by liveness_service.py / ONNX antispoof path
psycopg2-binary            # PostgreSQL adapter
django-crispy-forms
crispy-bootstrap5
```

> **Note:** The InsightFace `buffalo_l` model will be automatically downloaded on first use. The MiniFASNet `.pth` weights must be placed under `web/antispoof/resources/anti_spoof_models/`; if omitted, liveness checks fail open and recognition proceeds without spoof detection.

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/10murari/AI-attend.git
cd AI-attend
```

### 2. Create and activate a virtual environment

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install django insightface opencv-python numpy torch torchvision onnxruntime \
            psycopg2-binary django-crispy-forms crispy-bootstrap5
```

### 4. Set up PostgreSQL

Create a PostgreSQL database and user matching the settings:

```sql
CREATE DATABASE attendance_system;
CREATE USER attendance_admin WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE attendance_system TO attendance_admin;
```

Update `web/attendance_project/settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'attendance_system',
        'USER': 'attendance_admin',
        'PASSWORD': 'your_password',   # ← Change this
        'HOST': 'localhost',
        'PORT': '5433',                # ← Change to 5432 if needed
    }
}
```

### 5. Run migrations

```bash
cd web
python manage.py migrate
```

### 6. Create a superuser (Admin)

```bash
python manage.py createsuperuser
```

Then go to `/admin/` and set the user's `role` to `admin`.

### 7. (Recommended) Backfill batch data for legacy students

If migrating from an older dataset with roll numbers but no `Batch` rows:

```bash
python manage.py check_batch_migration_readiness
python manage.py backfill_student_batches --apply --auto-set-department-roll-code
```

### 8. Pre-download InsightFace model (optional)

```python
import insightface
from insightface.app import FaceAnalysis
app = FaceAnalysis(name='buffalo_l')
app.prepare(ctx_id=0, det_size=(640, 640))
```

### 9. Place anti-spoof model weights (optional but recommended)

Copy the MiniFASNet `.pth` files into `web/antispoof/resources/anti_spoof_models/`. Without them, `ANTI_SPOOF_ENABLED` still works via the OpenCV heuristic fallback, but with reduced accuracy.

---

## 🚀 Running the Project

```bash
cd web
python manage.py runserver
```

The application will be available at **http://127.0.0.1:8000/**

**Default route:** `/` → redirects to `/dashboard/` → redirects to `/accounts/login/`

---

## 📓 Colab Notebooks

Located in `Colab Notebooks/`, these are used for **offline data preparation** before the web app is used:

| Notebook | Purpose |
|----------|---------|
| `face_extraction.ipynb` | Extract and align face images from raw video footage using InsightFace |
| `extract_faces_enrollment.ipynb` | Build an enrollment dataset — extract face images per student from phone/CCTV videos, organize into per-student folders |

These notebooks are useful when you have pre-recorded videos (phone videos, CCTV footage) and want to:
- Prepare a training/enrollment dataset offline
- Validate InsightFace detection quality before deploying the web system

---

## 🔧 Configuration

All configurable settings are in `web/attendance_project/settings.py`:

```python
# Face Recognition
RECOGNITION_THRESHOLD = 0.45    # Cosine similarity threshold for a match
INSIGHTFACE_MODEL     = 'buffalo_l'
DET_SIZE              = (640, 640)
DET_THRESH            = 0.5

# Anti-Spoofing / Liveness
ANTI_SPOOF_ENABLED               = True
ANTI_SPOOF_THRESHOLD             = 0.0525   # probability threshold (converted to logit space)
ANTI_SPOOF_MODEL_PATH            = PROJECT_ROOT / 'models' / 'best_model.onnx'
ANTI_SPOOF_INPUT_SIZE            = 128
ANTI_SPOOF_USE_HEURISTIC_FALLBACK = True    # Laplacian-variance fallback if no model
ANTI_SPOOF_UNCERTAIN_MARGIN      = 0.15
ANTI_SPOOF_MIN_FACE_SIZE         = 96
ANTI_SPOOF_CROP_MARGIN_RATIO     = 0.12
LIVENESS_THRESHOLD               = 0.85     # used by ai_service.check_liveness (MiniFASNet path)

# Enrollment Data
ENROLLMENT_DATA_DIR = PROJECT_ROOT / 'dataset' / 'enrollment'
FACES_DIR           = ENROLLMENT_DATA_DIR / 'faces_aligned'
GALLERY_DIR         = ENROLLMENT_DATA_DIR / 'gallery'

# Attendance / Notifications
ATTENDANCE_REQUEST_WINDOW       = 48     # hours a student has to request a correction
AUTO_SEND_ABSENCE_NOTIFICATIONS = True
NOTIFICATION_RETENTION_DAYS     = 30
NOTIFICATIONS_PER_PAGE          = 20

# Session Security
SESSION_COOKIE_AGE             = 1800    # 30 minutes
SESSION_SAVE_EVERY_REQUEST     = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Timezone
TIME_ZONE = 'Asia/Kathmandu'
```

---

## 🛠️ Troubleshooting

### GPU not detected / CUDA error
The `AIService` falls back to CPU automatically for both InsightFace and MiniFASNet:
```python
providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
```
To force CPU, restrict the providers list in `web/ai_service.py`.

### InsightFace model not found
Run the pre-download step (see Installation step 8) or ensure you have internet access on first run.

### Live faces getting rejected as spoof
Lower `LIVENESS_THRESHOLD` in `settings.py` (e.g. from `0.85` to `0.78`), improve lighting, and make sure the face isn't too small relative to `ANTI_SPOOF_MIN_FACE_SIZE`. Set `ANTI_SPOOF_DEBUG = True` to log raw model logits.

### Low recognition accuracy
Check enrollment quality in Django Admin → `FaceEmbedding`:
- `quality_label` should be **Good** (intra_sim_mean ≥ 0.7)
- Re-enroll students with `quality_label = Poor` under better lighting

### "Batch is locked to Semester X" errors when adding/editing a student
The student's batch already has `locked_semester` set from existing students. Either use the locked semester, or fix/clear the batch's existing student data first via Batch Management.

### Duplicate roll number / sequence collision on student creation
Two students in the same batch got assigned the same sequence concurrently. Retry — creation runs inside a `select_for_update()` transaction, so this should self-resolve; persistent collisions indicate a data integrity issue worth checking with `check_batch_migration_readiness`.

### PostgreSQL connection refused
- Verify PostgreSQL is running
- Check that `PORT` in `settings.py` matches your PostgreSQL installation (default is `5432`, not `5433`)

### "No face detected" during enrollment
- Ensure only **one face** is in frame during enrollment (multi-face frames are skipped)
- Improve lighting and camera angle
- Minimum **3 valid frames** required to compute a centroid

### Static files not loading
```bash
python manage.py collectstatic
```

---

## 🔮 Future Enhancements

- [ ] Real-time WebSocket-based frame streaming (Django Channels)
- [ ] Email/SMS notifications for low attendance (email hooks already exist as `NotificationPreference.email_on_*` flags but are not yet wired to a mail backend)
- [ ] Attendance report generation (PDF)
- [ ] Multi-camera support
- [ ] REST API with DRF for mobile app integration
- [ ] Fine-grained permission management
- [ ] Late threshold configuration per session
- [ ] Bulk student import via CSV

---

## 🙏 Acknowledgments

- [InsightFace](https://github.com/deepinsight/insightface) — `buffalo_l` model (RetinaFace + ArcFace)
- MiniVision **MiniFASNet** — anti-spoofing / liveness detection models
- [Django](https://www.djangoproject.com/) — Web framework
- [OpenCV](https://opencv.org/) — Image/video processing
- [Bootstrap 5](https://getbootstrap.com/) — Frontend UI

---

**Repository:** [10murari/AI-attend](https://github.com/10murari/AI-attend)
**Last Updated:** April 2026