# EduVR – Cortex AI Platform: Architecture Reference

## Architecture Pattern

**Microservices** — Each service is an independent, containerized FastAPI application with its own concern. Services communicate indirectly through:
- **Shared PostgreSQL database** (same ORM models, separate logical ownership)
- **Redis** as a task broker (Celery async tasks) and pub/sub bus (real-time events)
- **MinIO** as shared S3-compatible object storage
- **Nginx API Gateway** as the single entry-point for all client requests

---

## Container Topology

```
                    ┌──────────────────────────┐
                    │    Frontend (React/Vite)  │
                    │       port 5173           │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────▼─────────────┐
                    │   Nginx API Gateway       │
                    │       port 8000           │
                    │  /auth/   →  service-auth │
                    │  /rooms/  →  service-rooms│
                    │  /assets/ →  service-assets│
                    │  /notifications/ → notifs │
                    └──┬──────┬──────┬──────┬──┘
                       │      │      │      │
           ┌───────────▼─┐ ┌──▼──┐ ┌▼────┐ ┌▼──────────────┐
           │ service-auth│ │rooms│ │assets│ │notifications  │
           │ FastAPI:8000│ │:8000│ │:8000 │ │FastAPI +SSE   │
           └─────────────┘ └─────┘ └──┬──┘ └───────────────┘
                  │           │        │              │
           ┌──────▼───────────▼──┐    │        ┌─────▼──────┐
           │   PostgreSQL :5432   │    │        │  Redis      │
           │  (shared schema)     │◄───┘        │  :6379      │
           └──────────────────────┘             └─────┬──────┘
                                                      │ pub/sub
                                          ┌───────────▼──────────┐
           ┌──────────────────────────┐   │  service-3d-worker   │
           │  MinIO Object Storage    │◄──│  Celery + Blender    │
           │  port 9000 (API)         │   │  concurrency: 2      │
           │  port 9001 (Console UI)  │   └──────────────────────┘
           └──────────────────────────┘
```

---

## Request Routing

| Client URL Pattern | Gateway Routes To | Service |
|---|---|---|
| `GET /auth/login` | `http://auth_service/auth/login` | service-auth |
| `POST /auth/register` | `http://auth_service/auth/register` | service-auth |
| `GET /rooms/` | `http://rooms_service/rooms/` | service-rooms |
| `POST /rooms/{id}/invite` | `http://rooms_service/rooms/{id}/invite` | service-rooms |
| `POST /assets/upload` | `http://assets_service/assets/upload` | service-assets |
| `GET /assets/` | `http://assets_service/assets/` | service-assets |
| `GET /notifications/stream/{id}` | `http://notifications_service/notifications/stream/{id}` | service-notifications |

---

## Authentication Flow

```
Client                      Gateway              Auth Service          Database
  │                           │                       │                   │
  ├──POST /auth/login ────────►│                       │                   │
  │                           ├──proxy──────────────►│                   │
  │                           │                       ├──query user──────►│
  │                           │                       │◄──user record─────┤
  │                           │                       ├──verify password   │
  │                           │                       ├──create JWT        │
  │◄──{token, role}───────────┤◄──{token, role}───────┤                   │
  │                           │                       │                   │
  ├──GET /rooms/ + Bearer ────►│                       │                   │
  │                           ├──proxy──────────────►rooms_service        │
  │                           │                       ├──decode JWT        │
  │                           │                       ├──query user──────►│
  │◄──[rooms array]───────────┤◄──[rooms]─────────────┤                   │
```

---

## 3D Asset Processing Pipeline

```
Client                   Assets Service         Redis           3D Worker           Blender           MinIO
  │                          │                    │                │                   │                 │
  ├─POST /assets/upload──────►│                    │                │                   │                 │
  │                          ├─upload raw file─────────────────────────────────────────────────────────►│
  │                          ├─insert DB (PENDING) │                │                   │                 │
  │                          ├─send_task───────────►│                │                   │                 │
  │◄─{id, PENDING}───────────┤                    │                │                   │                 │
  │                          │                    ├─dequeue────────►│                   │                 │
  │                          │                    │                ├─download raw───────────────────────►│
  │                          │                    │                │◄─file──────────────────────────────┤
  │                          │                    │                ├─run_blender────────►│                 │
  │                          │                    │                │   ├─import          │                 │
  │                          │                    │                │   ├─normalize       │                 │
  │                          │                    │                │   ├─relink textures │                 │
  │                          │                    │                │   ├─validate        │                 │
  │                          │                    │                │   └─export GLB      │                 │
  │                          │                    │                │◄─success────────────┤                 │
  │                          │                    │                ├─upload GLB──────────────────────────►│
  │                          │                    │                ├─update DB (COMPLETED)│                │
  │                          │                    ├◄─publish───────┤                   │                 │
  │◄─SSE event (COMPLETED)───────────────────────┤                │                   │                 │
```

---

## Real-Time Notification Architecture

```
3D Worker                Redis                Notifications Service         Browser
    │                      │                          │                        │
    ├─publish─────────────►│                          │                        │
    │  channel:            │  subscribed to same      │                        │
    │  user_notifications: │  channel (per user)      │                        │
    │  {user_id}           ├─push message─────────────►│                        │
    │                      │                          ├─SSE event push──────────►│
    │                      │                          │    event: message        │
    │                      │                          │    data: {...}           │
```

---

## Service Dependencies

| Service | Depends On |
|---|---|
| `service-auth` | PostgreSQL |
| `service-rooms` | PostgreSQL, service-auth (JWT validation) |
| `service-assets` | PostgreSQL, Redis, MinIO, service-auth (JWT) |
| `service-notifications` | Redis |
| `service-3d-worker` | PostgreSQL, Redis, MinIO |
| `api-gateway` | All 4 FastAPI services |
| `frontend` | api-gateway |

---

## Shared Code Layer

All Python microservices share a common `shared/` package mounted via Docker build context:

| File | Purpose |
|---|---|
| `shared/models.py` | SQLAlchemy ORM models (User, Room, RoomMember, Asset) |
| `shared/schemas.py` | Pydantic request/response schemas |
| `shared/database.py` | SQLAlchemy engine + SessionLocal + Base |
| `shared/auth_utils.py` | bcrypt hashing, JWT create/verify, constants |
| `shared/dependencies.py` | FastAPI `get_current_user` dependency (JWT decode + DB lookup) |

---

## Docker Compose Services Summary

| Container | Image/Dockerfile | External Ports | Internal Port |
|---|---|---|---|
| `cortex_api_gateway` | custom Nginx | **8000** | 8000 |
| `cortex_frontend` | custom Node | **5173** | 5173 |
| `cortex_db` | postgres:15 | **5433** | 5432 |
| `cortex_minio` | minio/minio | **9000** (API), **9001** (Console) | 9000, 9001 |
| `cortex_redis` | redis:7 | none (internal) | 6379 |
| `cortex_service_auth` | custom Python | none | 8000 |
| `cortex_service_rooms` | custom Python | none | 8000 |
| `cortex_service_assets` | custom Python | none | 8000 |
| `cortex_service_notifications` | custom Python | none | 8000 |
| `cortex_service_3d_worker` | custom Python | none | – (Celery) |

---

## RBAC Permission Matrix

| Action | STUDENT | TA | TEACHER |
|---|---|---|---|
| Register / Login | ✅ | ✅ | ✅ |
| View own rooms | ✅ | ✅ | ✅ |
| Create rooms | ❌ | ✅ | ✅ |
| Invite to rooms | ❌ (owner only) | ✅ (own rooms) | ✅ (own rooms) |
| Join via invite | ✅ | ✅ | ✅ |
| Upload assets | ❌ | ✅ | ✅ |
| View own assets | ✅ | ✅ | ✅ |
| Delete own assets | ✅ | ✅ | ✅ |
| Update room status | ❌ (owner only) | ✅ (own rooms) | ✅ (own rooms) |
| Delete rooms | ❌ (owner only) | ✅ (own rooms) | ✅ (own rooms) |
