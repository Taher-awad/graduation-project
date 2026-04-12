# EduVR – Cortex AI Platform: Infrastructure & Deployment

## Docker Compose Deployment

The entire platform is orchestrated via a single `docker-compose.yml` file.

### Start the Platform
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild a specific service after code changes
docker-compose up -d --build service-assets
```

### Service Health Check
After `docker-compose up`, verify all containers are running:
```bash
docker-compose ps
```

Expected containers:
| Container | Status |
|---|---|
| `cortex_api_gateway` | Up 0.0.0.0:8000->8000 |
| `cortex_frontend` | Up 0.0.0.0:5173->5173 |
| `cortex_db` | Up 0.0.0.0:5433->5432 |
| `cortex_minio` | Up 0.0.0.0:9000->9000, 9001->9001 |
| `cortex_redis` | Up (internal) |
| `cortex_service_auth` | Up (internal) |
| `cortex_service_rooms` | Up (internal) |
| `cortex_service_assets` | Up (internal) |
| `cortex_service_notifications` | Up (internal) |
| `cortex_service_3d_worker` | Up (Celery) |

---

## Public Endpoints

| URL | Service |
|---|---|
| `http://localhost:8000` | API Gateway (all API calls) |
| `http://localhost:5173` | Frontend Web App |
| `http://localhost:9000` | MinIO API (presigned URLs) |
| `http://localhost:9001` | MinIO Console (browser UI) |
| `localhost:5433` | PostgreSQL (dev tools) |

---

## Environment Configuration

Copy `.env.example` to `.env` and fill in values:

```env
# JWT
SECRET_KEY=supersecretkey_change_in_prod

# PostgreSQL
POSTGRES_USER=cortex
POSTGRES_PASSWORD=cortex
POSTGRES_DB=cortex
DATABASE_URL=postgresql://cortex:cortex@db:5432/cortex

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=assets
MINIO_ENDPOINT=http://minio:9000
MINIO_EXTERNAL_ENDPOINT=http://localhost:9000
```

> **Note**: `MINIO_ENDPOINT` uses the internal Docker hostname `minio`. `MINIO_EXTERNAL_ENDPOINT` uses `localhost` so the browser can resolve presigned download URLs.

---

## Build Contexts

All Python microservices share the `./microservices` build context so the `shared/` package is available inside every container:

```
docker-compose build context: ./microservices
│
├── shared/           # Mounted for ALL Python services
├── service-auth/     # Own Dockerfile copies itself
├── service-rooms/
├── service-assets/
├── service-notifications/
└── service-3d-worker/
```

---

## Nginx API Gateway Configuration

**File**: `api-gateway/nginx.conf`

| Feature | Configuration |
|---|---|
| Rate limit | `100r/m` per IP, burst 20, no delay |
| CORS | Whitelist: `http://localhost:5173` |
| Max upload size | `500MB` (for `/assets/`) |
| SSE support | `proxy_buffering off`, `proxy_read_timeout 86400s` for `/notifications/` |

---

## Blender Worker: Required System Setup

The `service-3d-worker` container requires **Blender** to be installed inside the Docker image. The Dockerfile installs it during build.

The worker runs Blender in **headless background mode**:
```bash
blender -b -P /app/service-3d-worker/process_model.py -- \
  --input /tmp/{id}/model.fbx \
  --output /tmp/{id}/mid.glb \
  --sliceable True \
  --id {asset_id}
```

Worker concurrency is set to **2 parallel Blender processes** via:
```
celery -A celery_app worker --loglevel=info --concurrency=2
```

---

## Volumes

| Volume | Purpose |
|---|---|
| `postgres_data` | PostgreSQL data persistence |
| `minio_data` | MinIO object storage persistence |
| `./frontend:/app` | Frontend hot-reload mount (dev mode) |

---

## Network

All services run on the default Docker Compose bridge network and communicate by service name DNS (e.g., `http://service-auth:8000`). Only the Gateway, Frontend, PostgreSQL (dev port), and MinIO expose ports to the host machine.

---

## Startup Order (depends_on)

```
db, redis, minio          ← Infrastructure (no dependencies)
    ↓
service-auth              ← Depends: db (seeds users, creates tables)
    ↓
service-rooms             ← Depends: db, service-auth
service-assets            ← Depends: db, redis, minio, service-auth
    ↓
service-notifications     ← Depends: redis
service-3d-worker         ← Depends: db, redis, minio
    ↓
api-gateway               ← Depends: all 4 services
    ↓
frontend                  ← Depends: api-gateway
```

---

## Default Seed Data

On first startup, `service-auth` seeds these users (if they don't exist):

| Username | Password | Role |
|---|---|---|
| `taher` | `123` | TEACHER |
| `student1` | `123` | STUDENT |

---

## Development Quick Start

```bash
# 1. Clone repo
git clone <repo-url>
cd "graduation v1"

# 2. Setup environment
cp .env.example .env
# (edit .env if needed)

# 3. Start everything
docker-compose up -d

# 4. Open in browser
# Frontend:  http://localhost:5173
# API Docs:  http://localhost:8000/docs (only exposed if auth service direct port open)
# MinIO:     http://localhost:9001 (admin UI)

# 5. Login with seed accounts
# Teacher:  taher / 123
# Student:  student1 / 123
```

---

## Frontend Development (Hot Reload)

The frontend is mounted as a volume, so changes to `frontend/src/` are reflected live without rebuild:

```bash
# Frontend container runs: npm run dev (vite dev server)
# Changes appear instantly at http://localhost:5173
```

---

## Testing

Test scripts are located in `test_scripts/` and each service has a `tests/` directory.

```bash
# Run service tests
docker-compose exec service-auth pytest tests/

# Or run test scripts directly
python test_scripts/test_auth.py
```
