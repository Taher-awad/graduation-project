# Cortex Pipeline Analysis (Monolith to Microservices Migration)

## 📌 Migration Status: **Almost Complete (Functional)**
The core logic of the pipeline has been successfully dismantled from the monolithic `backend` folder and containerized into individual, scalable microservices (`service-auth`, `service-rooms`, `service-assets`, `service-notifications`). The API Gateway maps the endpoints correctly.

However, the original monolith container and fallback route are still active.

---

## 🧭 Endpoint Tracing & Verification

I have traced every request from the ingress point (API Gateway / Nginx) down to the specific FastAPI application routers. **The routing is perfectly correct.** 

Because `nginx.conf` does not use a trailing slash in its `proxy_pass` directives (e.g., `proxy_pass http://auth_service;`), it passes the entire URI down. Your microservices accommodate for this perfectly by explicitly defining API router prefixes (e.g. `APIRouter(prefix="/auth")`).

### 1. Auth Service (`/auth/`)
*   **Gateway Rule:** `location /auth/ -> proxy_pass http://auth_service`
*   **Microservice Container:** `cortex_service_auth` -> `service-auth/main.py`
    *   `POST /auth/register` - ✅ Passed through exactly.
    *   `POST /auth/login` - ✅ Passed through exactly.

### 2. Rooms Service (`/rooms/`)
*   **Gateway Rule:** `location /rooms/ -> proxy_pass http://rooms_service`
*   **Microservice Container:** `cortex_service_rooms` -> `service-rooms/main.py`
    *   `POST /rooms/` - ✅ Checked
    *   `GET /rooms/` - ✅ Checked
    *   `GET /rooms/invitations` - ✅ Checked
    *   `POST /rooms/{room_id}/invite` - ✅ Checked
    *   `POST /rooms/{room_id}/join` - ✅ Checked
    *   `PUT /rooms/{room_id}/status` - ✅ Checked
    *   `DELETE /rooms/{room_id}` - ✅ Checked

### 3. Assets Service (`/assets/`)
*   **Gateway Rule:** `location /assets/ -> proxy_pass http://assets_service`
*   **Microservice Container:** `cortex_service_assets` -> `service-assets/main.py`
    *   `POST /assets/upload` - ✅ Checked
    *   `GET /assets/` - ✅ Checked
    *   `GET /assets/{asset_id}` - ✅ Checked
    *   `DELETE /assets/{asset_id}` - ✅ Checked
*   *Note:* The background processing correctly delegates to `service-3d-worker` (using `celery.send_task` through Redis), completely decoupling heavy file crunching from the HTTP response loop.

### 4. Notifications Service (`/notifications/`)
*   **Gateway Rule:** `location /notifications/ -> proxy_pass http://notifications_service`
*   **Microservice Container:** `cortex_service_notifications` -> `service-notifications/main.py`
    *   `GET /notifications/stream/{client_id}` - ✅ Checked. Uses SSE Streaming via Redis Pub/Sub correctly. Nginx config `proxy_buffering off;` and `chunked_transfer_encoding off;` perfectly permits the stream to bleed through to the Unity/React clients.

---

## 🧹 What's Left? (To Make It 100% Complete)
Technically, the new Pipeline is 100% capable, but to declare the Monolith "Dead and Removed", three small steps remain:

**1. The Fallback Pattern in Nginx**
`api-gateway/nginx.conf` still has:
```nginx
location / {
    proxy_pass http://api:8000;
}
```
*Suggestion:* Now that everything is mapped, we can change this default block to return a `404 Not Found` or just route to the Frontend, dropping traffic to the old monolith.

**2. Docker Compose Cleanup**
`docker-compose.yml` still spins up the `api` (monolith container) and builds from `./backend`.
*Suggestion:* We can completely remove the `api` service definition from the `docker-compose.yml`.

**3. Cleanup the old Backend folder**
We can safely archive or delete `backend/routers` and `backend/main.py` since that code is now actively running in `microservices/service-*/`. 
