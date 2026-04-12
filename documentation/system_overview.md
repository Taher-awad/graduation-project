# EduVR – Cortex AI Platform: System Overview

## Project Identity

| Field | Value |
|---|---|
| **Project Name** | EduVR – Cortex AI Platform |
| **Internal Codename** | Cortex |
| **Version** | 1.0 (Graduation Project) |
| **Stack** | Python FastAPI Microservices · React/TypeScript Frontend · PostgreSQL · MinIO · Redis · Nginx API Gateway · Celery · Blender (headless) · Docker |

---

## Problem Statement

Traditional education lacks immersive, interactive 3D environments for complex subject matter (anatomy, engineering, chemistry). EduVR provides a full-stack platform allowing teachers to upload, process, and share 3D models with students inside virtual-reality-ready rooms, with real-time status feedback during processing.

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Client (Browser / Unity VR)                                             │
│  React + TypeScript frontend (Vite, Tailwind, React Three Fiber)        │
└─────────────────┬────────────────────────────────────────────────────────┘
                  │ HTTP / SSE  (port 5173 → 8000)
┌─────────────────▼────────────────────────────────────────────────────────┐
│  API Gateway  (Nginx, port 8000)                                         │
│  Routes: /auth/ · /rooms/ · /assets/ · /notifications/                  │
│  Rate-limiting: 100 req/min per IP · CORS whitelist                      │
└──┬────────┬──────────┬──────────────┬───────────────────────────────────┘
   │        │          │              │
   ▼        ▼          ▼              ▼
 Auth     Rooms     Assets       Notifications
 :8000    :8000      :8000          :8000
 FastAPI  FastAPI    FastAPI        FastAPI (SSE)
   │        │          │              │
   └────────┴──────────┴──────────────┘
                        │
              ┌─────────┴──────────┐
              │   Shared Layer      │
              │  PostgreSQL (5432)  │
              │  Redis     (6379)  │
              │  MinIO     (9000)  │
              └─────────┬──────────┘
                        │
              ┌─────────▼──────────┐
              │  3D Worker Service  │
              │  Celery + Blender   │
              │  (Background tasks) │
              └────────────────────┘
```

---

## Services

### 1. `service-auth` (Authentication Service)
- **Framework**: FastAPI (Python)
- **Port**: 8000 (internal)
- **Responsibilities**:
  - User registration with role assignment (TEACHER / TA / STUDENT)
  - Password hashing via bcrypt
  - JWT token issuance (HS256, 15-minute expiry)
  - Seeds default users at startup (teacher: `taher`, student: `student1`)
- **Database**: PostgreSQL (shared schema)
- **Key files**: `auth.py`, `main.py`

### 2. `service-rooms` (Rooms Service)
- **Framework**: FastAPI (Python)
- **Port**: 8000 (internal)
- **Responsibilities**:
  - Create virtual classroom/lab rooms (Teacher/TA only)
  - List rooms owned/joined by the current user
  - Invite users to rooms (owner only)
  - Accept invitations to join a room
  - Update room online/offline status (owner only)
  - Delete rooms (owner only, cascades members)
- **Database**: PostgreSQL (shared schema)
- **Key files**: `rooms.py`, `main.py`

### 3. `service-assets` (Asset Management Service)
- **Framework**: FastAPI (Python)
- **Port**: 8000 (internal)
- **Responsibilities**:
  - Upload 3D models (GLB/GLTF/FBX/OBJ/BLEND/STL/ZIP), videos (MP4/MOV/AVI), slides (PDF/PPTX/PNG/JPG), images
  - Store raw files in MinIO object storage
  - Dispatch Celery background task for MODEL type assets
  - Generate presigned S3 URLs for downloads
  - List/get/delete user-owned assets
- **Storage**: MinIO (`assets` bucket)
- **Task Queue**: Redis + Celery
- **Key files**: `assets.py`, `main.py`

### 4. `service-notifications` (Real-Time Notifications)
- **Framework**: FastAPI (Python) + `sse-starlette`
- **Port**: 8000 (internal)
- **Responsibilities**:
  - Expose a Server-Sent Events (SSE) stream per user
  - Subscribe to Redis Pub/Sub channel `user_notifications:{client_id}`
  - Forward processing status events (PROCESSING, COMPLETED, FAILED) to the browser in real-time
- **Broker**: Redis Pub/Sub
- **Key files**: `main.py`

### 5. `service-3d-worker` (3D Processing Worker)
- **Framework**: Celery + Blender (headless `bpy`)
- **Concurrency**: 2 workers
- **Responsibilities**:
  - Dequeue `worker.process_asset` tasks from Redis
  - Download raw model from MinIO
  - Extract ZIP archives (including nested ZIPs)
  - Run Blender headlessly: import → normalize → validate → export GLB
  - Upload processed GLB to MinIO (`processed/` prefix)
  - Update asset status in PostgreSQL
  - Broadcast status events via Redis Pub/Sub → SSE notifications
- **Processing steps inside Blender**:
  1. Reset scene
  2. Import model (FBX, OBJ, STL, GLTF/GLB, BLEND)
  3. Normalize (scale to unit cube, center geometry, inject metadata, auto-smooth)
  4. Relink missing textures (disk scan)
  5. Auto-connect textures by name-similarity matching
  6. Fix transparency (vegetation → HASHED, glass → BLEND)
  7. Validate (NaN/Inf geometry, manifold check for sliceable, texture existence)
  8. Export as GLB with all modifiers applied
- **Key files**: `worker.py`, `process_model.py`, `celery_app.py`, `utils_worker.py`

### 6. `api-gateway` (Nginx Reverse Proxy)
- **Image**: Nginx
- **Port**: 8000 (public)
- **Responsibilities**:
  - Route `/auth/` → `service-auth`
  - Route `/rooms/` → `service-rooms`
  - Route `/assets/` → `service-assets` (max body 500MB)
  - Route `/notifications/` → `service-notifications` (buffering disabled for SSE)
  - Global rate limiting: 100 req/min, burst 20
  - CORS headers for `http://localhost:5173`

### 7. Frontend
- **Framework**: React 19 + TypeScript + Vite
- **Port**: 5173
- **Libraries**: React Three Fiber (3D viewer), TanStack Query, Framer Motion, Axios, React Router, Tailwind CSS, Lucide Icons
- **Pages**:
  - `/login` – JWT authentication
  - `/register` – Role-based user registration
  - `/` (Assets) – Upload, view, and manage 3D assets
  - `/rooms` – Create and manage virtual rooms, invite users

---

## Infrastructure Services

| Service | Image | Port(s) | Role |
|---|---|---|---|
| PostgreSQL | `postgres:15` | 5433→5432 | Primary relational database |
| Redis | `redis:7` | internal | Task queue broker + Pub/Sub |
| MinIO | `minio/minio` | 9000 (API), 9001 (Console) | S3-compatible object storage |

---

## Data Models

### User
| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `username` | String | Unique, indexed |
| `password_hash` | String | bcrypt |
| `role` | Enum | TEACHER / TA / STUDENT |

### Room
| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | String | Display name |
| `description` | String | Optional |
| `owner_id` | UUID | FK → users.id |
| `is_online` | Boolean | Live session flag |
| `max_participants` | Integer | Default 20 |
| `created_at` | DateTime | UTC |

### RoomMember
| Field | Type | Notes |
|---|---|---|
| `room_id` | UUID | PK + FK → rooms.id |
| `user_id` | UUID | PK + FK → users.id |
| `status` | Enum | INVITED / JOINED |
| `permissions` | JSON | `{can_slice, can_talk, can_interact}` |

### Asset
| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `owner_id` | UUID | FK → users.id |
| `filename` | String | Original filename |
| `asset_type` | Enum | MODEL / VIDEO / SLIDE / IMAGE |
| `is_sliceable` | Boolean | Manifold slicing flag |
| `status` | Enum | PENDING / PROCESSING / COMPLETED / FAILED |
| `original_path` | String | MinIO key e.g. `raw/{id}.fbx` |
| `processed_path` | String | MinIO key e.g. `processed/{id}.glb` |
| `metadata_json` | JSON | Processing metadata / errors |

---

## Security

| Mechanism | Detail |
|---|---|
| **Authentication** | JWT Bearer tokens (HS256, 15 min expiry) |
| **Password Storage** | bcrypt via `passlib` |
| **RBAC** | Role checked per endpoint (TEACHER/TA/STUDENT) |
| **Rate Limiting** | Nginx: 100 req/min per IP, burst 20 |
| **CORS** | Nginx whitelist (localhost:5173 in dev) |
| **File Validation** | Extension whitelist per asset type |
| **Asset Ownership** | All asset queries filter by `owner_id = current_user.id` |

---

## Environment Variables (`.env`)

| Variable | Used By | Example |
|---|---|---|
| `SECRET_KEY` | Auth, all services | `supersecretkey` |
| `DATABASE_URL` | All services | `postgresql://user:pw@db:5432/cortex` |
| `REDIS_URL` | Assets, Notifications, Worker | `redis://redis:6379/0` |
| `MINIO_ENDPOINT` | Assets, Worker | `http://minio:9000` |
| `MINIO_EXTERNAL_ENDPOINT` | Assets (presigned URLs) | `http://localhost:9000` |
| `MINIO_ACCESS_KEY` | Assets, Worker | `minioadmin` |
| `MINIO_SECRET_KEY` | Assets, Worker | `minioadmin` |
| `MINIO_BUCKET` | Assets, Worker | `assets` |
| `POSTGRES_USER` | DB | `cortex` |
| `POSTGRES_PASSWORD` | DB | `cortex` |
| `POSTGRES_DB` | DB | `cortex` |
| `MINIO_ROOT_USER` | MinIO | `minioadmin` |
| `MINIO_ROOT_PASSWORD` | MinIO | `minioadmin` |
