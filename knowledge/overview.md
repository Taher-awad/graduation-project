# EduVR – Cortex AI: Project Overview

## What is This?

EduVR (internal: Cortex AI) is a graduation project — a full-stack virtual reality education platform that lets teachers upload 3D models and share them with students in virtual collaborative rooms.

## Key Technical Decisions

| Decision | Choice | Reason |
|---|---|---|
| Backend | Python FastAPI microservices | Fast async, auto-docs, easy containerization |
| Auth | JWT Bearer (HS256, 15min) | Stateless, scales across services |
| 3D Processing | Blender headless (bpy) | Industry-standard, free, handles FBX/OBJ/BLEND |
| File Storage | MinIO (S3-compatible) | Self-hosted, no AWS cost, presigned URLs |
| Task Queue | Celery + Redis | Decouple heavy Blender work from HTTP request |
| Real-time | Server-Sent Events (SSE) | One-way push, simpler than WebSockets for status |
| Database | PostgreSQL | Robust, handles UUIDs, JSON columns natively |
| Reverse Proxy | Nginx | Rate limiting, CORS, SSE buffering config |
| Frontend | React 19 + TypeScript + Vite | Modern, type-safe, fast HMR |
| 3D Viewer | React Three Fiber + drei | Three.js in React, component model |

## Project Structure

```
graduation v1/
├── api-gateway/          # Nginx config (reverse proxy)
├── microservices/
│   ├── shared/           # Shared ORM models, schemas, auth utils
│   ├── service-auth/     # Registration, login, JWT
│   ├── service-rooms/    # Room CRUD, invitations
│   ├── service-assets/   # Upload, list, delete assets
│   ├── service-notifications/  # SSE stream
│   └── service-3d-worker/      # Celery + Blender pipeline
├── frontend/             # React/Vite app
├── documentation/        # All docs (you are here)
├── knowledge/            # Quick reference notes
├── docker-compose.yml
└── .env.example
```

## Roles

| Role | Can Create Rooms | Can Upload Assets | Can Join Rooms |
|---|---|---|---|
| TEACHER | ✅ | ✅ | ✅ (as owner) |
| TA | ✅ | ✅ | ✅ |
| STUDENT | ❌ | ❌ | ✅ (via invite) |

## Default Dev Users

| Username | Password | Role |
|---|---|---|
| `taher` | `123` | TEACHER |
| `student1` | `123` | STUDENT |

## Quick Start

```bash
cp .env.example .env
docker-compose up -d
# API: http://localhost:8000
# App: http://localhost:5173
# MinIO Console: http://localhost:9001
```
