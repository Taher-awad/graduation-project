# Deep Analysis Report: Cortex AI

This report provides a comprehensive, top-to-bottom audit of the repository, covering architecture, performance, resource usage, security, and overall code health.

---

## 1. Architecture & Code Quality

### 🚨 Critical Findings
* **Incomplete Microservices Migration (Monolithic Remnants):**
  The system is caught in a transitional state. The `api-gateway/nginx.conf` correctly routes traffic to specific microservices (`/auth`, `/rooms`, `/assets`), but it also includes a global catch-all `location /` that forwards unmapped requests directly to the old monolith (`http://api:8000`). This keeps deprecated, potentially unstable code accessible and running.
* **Severe DRY/SOLID Violations:**
  Entire chunks of the monolith's code (e.g., `backend/routers/auth.py`, `backend/routers/rooms.py`, `backend/routers/assets.py`) have been copy-pasted directly into the new microservices (`microservices/service-*/`) with minimal alterations. This includes core logic, database setup, and dependency management.
* **Tight Coupling via Shared Directory:**
  The microservices rely on a `shared` directory (`microservices/shared/`) using `sys.path.append()`. While code reuse is necessary, this method of sharing database models (`models.py`) and schemas forces all services to depend on a single, unified database schema. If one microservice needs to update a table, all microservices are impacted, breaking the boundary context principles of microservices.

### ⚠️ High Findings
* **Duplicated Database Initialization:**
  Both the monolithic `backend/main.py` and several microservices trigger `Base.metadata.create_all(bind=engine)` independently upon startup. This can lead to race conditions during container orchestration (e.g., Docker Compose startup) where multiple services attempt to alter/create tables concurrently.

### ℹ️ Low/Nitpick Findings
* **Dead/Unused Code:**
  The monolith contains old implementations (like monolithic Celery task triggering) that are superseded by the direct Redis task submission used in `service-assets`.

---

## 2. Performance & Resource Usage

### 🚨 Critical Findings
* **Synchronous Database Operations & API Logic:**
  Despite using asynchronous web frameworks (FastAPI/Starlette) and defining `async def` route handlers in places, all database interactions (via SQLAlchemy) and MinIO operations (via `boto3`) are executed synchronously. Under load, these blocking calls will starve the ASGI event loop, significantly degrading concurrency and throughput.
* **O(N²) Algorithms in 3D Worker:**
  In `microservices/service-3d-worker/process_model.py`, the vertex iteration during geometry validation (`validate_model`) contains potentially slow loops. Additionally, `optimize_textures` processes images sequentially and performs arbitrary `scale()` operations without caching. For high-poly models, this will block the Celery worker for extended periods.

### ⚠️ High Findings
* **Missing Connection Pooling:**
  The SQLAlchemy engine is initialized via `create_engine` without explicit pooling configurations optimized for high-concurrency environments (like PGBouncer or SQLAlchemy's `QueuePool` with sensible limits). The `SessionLocal` dependency is created per request, but the underlying connections may bottleneck if traffic spikes.
* **Inefficient API Queries:**
  The `list_rooms` endpoint fetches owned rooms and joined rooms sequentially and manipulates them in Python memory (using `list(set(...))`) rather than executing an optimized `UNION` query at the database level.
* **Unpaginated Responses:**
  The `/assets` and `/rooms` endpoints return `.all()` without limit/offset or cursor-based pagination. This will cause memory bloat and slow response times as the dataset grows.

### ℹ️ Low/Nitpick Findings
* **Hardcoded Concurrency Limit:**
  The `docker-compose.yml` restricts the `service-3d-worker` to `--concurrency=2`. Depending on instance size, this might drastically under-utilize CPU resources.

---

## 3. Security Audit

### 🚨 Critical Findings
* **Hardcoded Secrets & Credentials:**
  Both the monolith and the `shared` directory hardcode the JWT Secret Key (`"supersecretkey"`) in `auth_utils.py` and the MinIO credentials (`"minioadmin"`/`"minioadmin"`) directly in `assets.py` and `worker.py`. While they use `os.getenv` as a fallback, checking these fallbacks into version control is a critical vulnerability.
* **Overly Permissive CORS Configuration:**
  The FastAPI applications (both monolith and microservices) utilize `CORSMiddleware` with `allow_origins=["*"]`, `allow_credentials=True`, and allow all methods/headers. This completely bypasses the dynamic, restricted CORS mapping defined in `api-gateway/nginx.conf`, exposing the internal APIs to Cross-Origin Resource Sharing attacks.

### ⚠️ High Findings
* **Insecure S3 URL Generation:**
  The `s3_signer` in `assets.py` generates presigned URLs assuming the endpoint is `http://localhost:9000`. This tightly couples the URL generation to a local dev environment and presents potential Server-Side Request Forgery (SSRF) or broken link risks if deployed to production without overriding the environment variables correctly.

### ℹ️ Low/Nitpick Findings
* **Rate Limiting Gaps:**
  While Nginx implements a global rate limit (`limit_req_zone`), there is no application-level rate limiting (e.g., login attempts, model processing requests). A malicious actor could exhaust the 3D worker queue without tripping the Nginx global burst limits.

---

## 4. Action Plan for Refactoring

To resolve the identified issues and achieve a healthy, production-ready state, we must execute the following prioritized steps:

### Phase 1: Security & Immediate Fixes (Priority: High)
1. **Remove Hardcoded Secrets:** Migrate all default fallback secrets (JWT, MinIO, Postgres) to `.env` files and remove them from the codebase logic. Implement strict environment variable validation on startup.
2. **Fix CORS Policies:** Remove `allow_origins=["*"]` from FastAPI instances. Rely on the API Gateway (Nginx) for edge routing and CORS, or explicitly configure internal domains for microservices.

### Phase 2: Architectural Decoupling (Priority: High)
3. **Sever the Monolith:** Remove the catch-all `location /` routing in Nginx to `api:8000`. Fully deprecate and delete the `backend/` folder once all parity is verified in the microservices.
4. **Refactor Shared State:** Move away from `sys.path.append()` for the `shared` directory. Extract shared models, schemas, and utils into a versioned internal Python package, or isolate databases per microservice (Database-per-Service pattern).
5. **Centralize DB Migrations:** Remove `Base.metadata.create_all` from application lifespan events. Introduce Alembic to manage database schema migrations centrally and safely.

### Phase 3: Performance Optimization (Priority: Medium)
6. **Implement Async I/O:** Refactor SQLAlchemy to use `asyncpg` and update all database interactions to be fully asynchronous (`await session.execute(...)`). Similarly, utilize `aiobotocore` for non-blocking MinIO interactions.
7. **Optimize Queries & Add Pagination:** Refactor the `list_rooms` endpoint to use a single SQL query. Add pagination parameters (`skip`, `limit`) to all collection endpoints.
8. **Optimize 3D Worker:** Profile `process_model.py` to identify exact bottlenecks in the validation loops. Investigate parallelizing texture resizing or caching previously scaled images.