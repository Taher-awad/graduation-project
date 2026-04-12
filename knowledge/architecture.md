# Architecture Knowledge: Cortex AI Microservices

## Service Map

```
Browser ──► Nginx :8000 ──► service-auth       (JWT auth)
                       ──► service-rooms      (room CRUD)
                       ──► service-assets     (file upload + Celery dispatch)
                       ──► service-notifications (SSE stream)
                                                       ▲
                                                       │ Redis pub/sub
                                              service-3d-worker
                                              (Celery + Blender)
```

## Shared Layer

All Python services share `microservices/shared/`:
- `models.py` — SQLAlchemy ORM (User, Room, RoomMember, Asset)
- `schemas.py` — Pydantic request/response models
- `database.py` — Engine + SessionLocal
- `auth_utils.py` — bcrypt + JWT (SECRET_KEY, HS256, 15min expiry)
- `dependencies.py` — `get_current_user` FastAPI dependency

## Real-Time Architecture

```
Worker ──publish──► Redis channel "user_notifications:{user_id}"
Notifications Service ──subscribe──► same channel
Browser ──SSE stream──► Notifications Service
```

## Key Design Patterns

### User-Scoped Data
All asset queries filter by `owner_id = current_user.id`:
```python
query = db.query(Asset).filter(Asset.owner_id == current_user.id)
```

### Decoupled Task Dispatch
Assets service sends Celery task **without importing worker code**:
```python
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)
celery_app.send_task("worker.process_asset", args=[str(asset_id)])
```

### Presigned URL Generation
Two MinIO clients exist in assets service:
- `s3`: internal endpoint (`http://minio:9000`) — for uploads/downloads inside Docker
- `s3_signer`: external endpoint (`http://localhost:9000`) — for presigned URLs that the browser can access

### Dual MinIO Endpoints (Important Gotcha)
Internal (`MINIO_ENDPOINT=http://minio:9000`) — used by Python containers  
External (`MINIO_EXTERNAL_ENDPOINT=http://localhost:9000`) — used to sign URLs that browsers resolve

## Ports Summary

| Service | External Port | Internal Port |
|---|---|---|
| API Gateway | **8000** | 8000 |
| Frontend | **5173** | 5173 |
| PostgreSQL | **5433** | 5432 |
| MinIO API | **9000** | 9000 |
| MinIO Console | **9001** | 9001 |
| Redis | — (internal) | 6379 |

## RBAC Rules

- **Create rooms**: TEACHER or TA
- **Upload assets**: TEACHER or TA
- **Invite to room**: Room OWNER only
- **Update room status / Delete room**: Room OWNER only
- **Join room**: Any user with a pending invitation
- **View/download assets**: Asset OWNER only
