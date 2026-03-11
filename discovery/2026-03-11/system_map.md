# Cortex Project - Architecture Overview

## 1. System Architecture

The project is composed of a FastAPI-powered backend with background processing via Celery, and a React/Vite-based frontend (not containerized with the rest of the stack). 

The infrastructure is orchestrated using Docker Compose, consisting of:
- **FastAPI Backend (`cortex_api`)**: Handles REST API requests from the frontend or Unity app.
- **Celery Worker (`cortex_worker`)**: Manages 3D asset processing pipelines asynchronously using Blender.
- **PostgreSQL (`cortex_db`)**: Primary relational database.
- **Redis (`cortex_redis`)**: Message broker for the Celery tasks.
- **MinIO (`cortex_minio`)**: S3-compatible object storage for 3D assets, slides, videos, and images.

---

## 2. Inter-Service Communication

The backend ecosystem relies on an internal Docker network where services interconnect using container aliases:

- **API -> DB**: Connects to `db:5432` for user authentication, room management, and tracking asset metadata/status.
- **API -> Redis**: Uses `redis:6379` to dispatch Celery tasks when 3D models are uploaded.
- **API -> MinIO**: Interacts with `http://minio:9000` to stream directly uploaded files into raw storage, and issues presigned URLs (`http://localhost:9000` for client-side resolution) to download processed `.glb` assets.
- **Worker -> Redis**: Polls `redis:6379` to fetch pending `process_asset` tasks.
- **Worker -> MinIO**: Downloads raw models from `http://minio:9000`, processes them locally (handling `.zip` extractions), and uploads optimized GLB versions back to the bucket.
- **Worker -> DB**: Connects to `db:5432` to update the state of the asset (`PENDING` -> `PROCESSING` -> `COMPLETED` or `FAILED`).
- **Frontend -> API**: Connects over HTTP to `http://localhost:8000`. The frontend is run externally (via Vite development server) rather than within the Docker network context.

---

## 3. Data Flow and Sequence Analysis

### Core User Action: 3D Asset Upload & Optimization Life-Cycle

This outlines the process of uploading an interactive 3D model, optimizing it, and providing it back to the client.

1. **Client Request**:
   - The user (must have `STAFF` role) selects a `.zip`, `.blend`, or `.fbx` via the frontend UI.
   - The front-end makes a `POST /assets/upload` request attaching the file as `FormData` (with `asset_type: "MODEL"` and `is_sliceable: boolean`).

2. **API Processing**:
   - The FastAPI backend validates the file extension, ensures the user is `STAFF`, and creates an ID.
   - It streams the raw file directly into MinIO S3 bucket (`assets/raw/{id}.{ext}`).
   - It inserts a new `Asset` record into PostgreSQL with `status=PENDING`.
   - It pushes a task `process_asset(asset_id)` securely onto the Redis queue.
   - The API immediately returns a status `PENDING` along with the `asset_id` to the frontend.

3. **Background Worker (Celery / Blender)**:
   - `cortex_worker` fetches the task from Redis.
   - It connects to Postgres and marks the Asset `status=PROCESSING`.
   - It connects to MinIO and downloads the raw model file into a temporary `/tmp/{id}/` folder.
   - If the file is a `.zip`, it unzips everything (even handling nested zip archives) and searches for the root model file (.glb, .fbx, .blend).
   - The worker spins up a Headless Blender process (`subprocess.run(["blender", "-b", "-P", "/app/process_model.py", ...])`).
   - The `process_model.py` script normalizes the model, applies sliceable configuration if requested, and exports a final `.glb` file.
   - The worker uploads this new `.glb` file back to MinIO (`assets/processed/{id}.glb`).
   - The worker marks the Asset `status=COMPLETED` in PostgreSQL and updates the `metadata_json`.
   - The worker destroys the local `/tmp/` staging directory.

4. **Client Retrieval**:
   - The frontend polls `GET /assets/` (or `GET /assets/{id}`).
   - The API checks the DB. Since it is `COMPLETED`, the API generates a presigned secure S3 download URL from MinIO.
   - The frontend receives the response with a valid `.glb` link and renders the optimized 3D model using `@react-three/fiber` components.
