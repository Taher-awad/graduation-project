# EduVR – Cortex AI Platform: Full API Endpoints Reference

> **Base URL**: `http://localhost:8000` (via Nginx API Gateway)  
> **Auth**: All protected endpoints require `Authorization: Bearer <JWT_TOKEN>` header  
> **Token**: Obtained from `/auth/login`, valid for **15 minutes**

---

## Table of Contents

1. [Authentication Service (`/auth`)](#1-authentication-service-auth)
2. [Rooms Service (`/rooms`)](#2-rooms-service-rooms)
3. [Assets Service (`/assets`)](#3-assets-service-assets)
4. [Notifications Service (`/notifications`)](#4-notifications-service-notifications)

---

## 1. Authentication Service `/auth`

### `POST /auth/register`

**Description**: Register a new user account with a specified role. Anyone can register.

**Auth Required**: ❌ No

**Request Body** (JSON):
```json
{
  "username": "john_teacher",
  "password": "mypassword123",
  "role": "TEACHER"
}
```

| Field | Type | Required | Values |
|---|---|---|---|
| `username` | string | ✅ | Any unique string |
| `password` | string | ✅ | Any string |
| `role` | string | ❌ | `"TEACHER"` \| `"TA"` \| `"STUDENT"` (default: `"STUDENT"`) |

**Success Response** `201 Created`:
```json
{
  "message": "User created successfully"
}
```

**Error Responses**:
| Status | Condition |
|---|---|
| `400 Bad Request` | `"Username already registered"` – username is taken |

---

### `POST /auth/login`

**Description**: Authenticate a user and return a JWT access token.

**Auth Required**: ❌ No

**Request Body** (JSON):
```json
{
  "username": "john_teacher",
  "password": "mypassword123"
}
```

| Field | Type | Required |
|---|---|---|
| `username` | string | ✅ |
| `password` | string | ✅ |

**Success Response** `200 OK`:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "TEACHER"
}
```

| Field | Type | Description |
|---|---|---|
| `access_token` | string | JWT token to use in `Authorization: Bearer` header |
| `token_type` | string | Always `"bearer"` |
| `role` | string | `"TEACHER"` \| `"TA"` \| `"STUDENT"` |

**Error Responses**:
| Status | Condition |
|---|---|
| `401 Unauthorized` | Wrong username or password |

---

## 2. Rooms Service `/rooms`

> All endpoints require a valid JWT token.

---

### `POST /rooms/`

**Description**: Create a new virtual classroom or lab room. Only **TEACHER** and **TA** roles are allowed.

**Auth Required**: ✅ (TEACHER or TA only)

**Request Body** (JSON):
```json
{
  "name": "Anatomy Lab - Session 1",
  "description": "Virtual dissection lab for semester 3",
  "is_online": false,
  "max_participants": 30
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `name` | string | ✅ | – | Room display name |
| `description` | string | ❌ | `null` | Optional description |
| `is_online` | boolean | ❌ | `false` | Whether the room is live |
| `max_participants` | integer | ❌ | `20` | Maximum allowed members |

**Success Response** `201 Created`:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Anatomy Lab - Session 1",
  "description": "Virtual dissection lab for semester 3",
  "owner_id": "a3e1b2c3-...",
  "is_online": false,
  "active_users_count": 0,
  "created_at": "2026-04-12T17:00:00",
  "role_in_room": "OWNER"
}
```

**Error Responses**:
| Status | Condition |
|---|---|
| `403 Forbidden` | User role is STUDENT |
| `401 Unauthorized` | No/invalid token |

---

### `GET /rooms/`

**Description**: List all rooms accessible to the current user — rooms they **own** plus rooms they have **joined** (accepted invitations).

**Auth Required**: ✅

**Query Parameters**: None

**Success Response** `200 OK` (array):
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Anatomy Lab - Session 1",
    "description": "Virtual dissection lab",
    "owner_id": "a3e1b2c3-...",
    "is_online": true,
    "active_users_count": 0,
    "created_at": "2026-04-12T17:00:00",
    "role_in_room": "OWNER"
  },
  {
    "id": "7a2c8a00-...",
    "name": "Physics Room",
    "description": null,
    "owner_id": "b9f7d1c2-...",
    "is_online": false,
    "active_users_count": 0,
    "created_at": "2026-04-10T09:30:00",
    "role_in_room": "MEMBER"
  }
]
```

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Room identifier |
| `name` | string | Room display name |
| `description` | string\|null | Optional description |
| `owner_id` | UUID | The user who created the room |
| `is_online` | boolean | Live session status |
| `active_users_count` | integer | Currently 0 (placeholder for future WebSocket integration) |
| `created_at` | datetime | UTC creation timestamp |
| `role_in_room` | string | `"OWNER"` or `"MEMBER"` |

---

### `GET /rooms/invitations`

**Description**: List all **pending** room invitations for the current user (invites not yet accepted).

**Auth Required**: ✅

**Success Response** `200 OK` (array):
```json
[
  {
    "room_id": "550e8400-e29b-41d4-a716-446655440000",
    "room_name": "Anatomy Lab - Session 1",
    "invited_by": "john_teacher",
    "status": "INVITED"
  }
]
```

| Field | Type | Description |
|---|---|---|
| `room_id` | UUID | Room being invited to |
| `room_name` | string | Room display name |
| `invited_by` | string | Username of room owner who sent invite |
| `status` | string | Always `"INVITED"` for pending invitations |

---

### `POST /rooms/{room_id}/invite`

**Description**: Invite a user (by username) to a room. Only the **room owner** can invite.

**Auth Required**: ✅ (must be room OWNER)

**Path Parameters**:
| Param | Type | Description |
|---|---|---|
| `room_id` | UUID | The target room's ID |

**Request Body** (JSON):
```json
{
  "username": "student_alice",
  "permissions": {
    "can_slice": true,
    "can_talk": false
  }
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `username` | string | ✅ | – | The username of the user to invite |
| `permissions` | object | ❌ | `{"can_slice": true, "can_talk": false}` | Interaction permissions in the room |

**Success Response** `200 OK`:
```json
{
  "message": "Invitation sent to student_alice"
}
```

**Error Responses**:
| Status | Condition |
|---|---|
| `400 Bad Request` | Invalid room ID format |
| `400 Bad Request` | User already invited or joined |
| `403 Forbidden` | Current user is not the room owner |
| `404 Not Found` | Room not found |
| `404 Not Found` | Target user not found |

---

### `POST /rooms/{room_id}/join`

**Description**: Accept a pending invitation to join a room. Changes membership status from `INVITED` → `JOINED`.

**Auth Required**: ✅ (must have a pending invitation)

**Path Parameters**:
| Param | Type | Description |
|---|---|---|
| `room_id` | UUID | The room to join |

**Request Body**: None

**Success Response** `200 OK`:
```json
{
  "message": "You have joined the room"
}
```

Special case — if the current user is the room owner:
```json
{
  "message": "You are the owner of this room"
}
```

**Error Responses**:
| Status | Condition |
|---|---|
| `400 Bad Request` | Invalid room ID format |
| `400 Bad Request` | No pending invitation found for this room |

---

### `PUT /rooms/{room_id}/status`

**Description**: Toggle the online/offline status of a room. Only the **room owner** can do this.

**Auth Required**: ✅ (must be room OWNER)

**Path Parameters**:
| Param | Type | Description |
|---|---|---|
| `room_id` | UUID | The room to update |

**Query Parameters**:
| Param | Type | Required | Description |
|---|---|---|---|
| `is_online` | boolean | ✅ | `true` to go live, `false` to go offline |

**Example**: `PUT /rooms/550e8400-.../status?is_online=true`

**Success Response** `200 OK`:
```json
{
  "status": "updated",
  "is_online": true
}
```

**Error Responses**:
| Status | Condition |
|---|---|
| `400 Bad Request` | Invalid room ID format |
| `403 Forbidden` | Not the room owner |
| `404 Not Found` | Room not found |

---

### `DELETE /rooms/{room_id}`

**Description**: Permanently delete a room and all its members. Only the **room owner** can delete.

**Auth Required**: ✅ (must be room OWNER)

**Path Parameters**:
| Param | Type | Description |
|---|---|---|
| `room_id` | UUID | The room to delete |

**Success Response** `204 No Content` (empty body)

**Error Responses**:
| Status | Condition |
|---|---|
| `400 Bad Request` | Invalid room ID format |
| `403 Forbidden` | Not the room owner |
| `404 Not Found` | Room not found |

---

## 3. Assets Service `/assets`

> All endpoints require a valid JWT token.  
> Upload is restricted to **TEACHER** and **TA** roles.  
> Assets are **user-scoped** — users can only see/delete their own assets.

---

### `POST /assets/upload`

**Description**: Upload a new asset (3D model, video, slide, or image). For `MODEL` type assets, a Celery background task is automatically queued to convert the model to optimized GLB format.

**Auth Required**: ✅ (TEACHER or TA only)

**Content-Type**: `multipart/form-data`

**Form Fields**:
| Field | Type | Required | Description |
|---|---|---|---|
| `file` | file | ✅ | The binary file to upload |
| `asset_type` | string (enum) | ✅ | `"MODEL"` \| `"VIDEO"` \| `"SLIDE"` \| `"IMAGE"` |
| `is_sliceable` | boolean | ❌ | Default `false`. For MODEL type only — enables manifold check and centers geometry for cross-sectioning in VR |

**Allowed File Extensions per Type**:
| `asset_type` | Allowed Extensions |
|---|---|
| `MODEL` | `.glb`, `.gltf`, `.fbx`, `.obj`, `.blend`, `.stl`, `.zip` |
| `VIDEO` | `.mp4`, `.mov`, `.avi` |
| `SLIDE` | `.pdf`, `.pptx`, `.png`, `.jpg` |
| `IMAGE` | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` |

**Example (curl)**:
```bash
curl -X POST http://localhost:8000/assets/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@human_heart.glb" \
  -F "asset_type=MODEL" \
  -F "is_sliceable=true"
```

**Success Response** `200 OK`:
```json
{
  "id": "f7c3e2b1-4a5d-48ce-9200-123456789abc",
  "status": "PENDING",
  "type": "MODEL"
}
```

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Asset identifier (use to poll status) |
| `status` | string | `"PENDING"` for models, `"COMPLETED"` for non-model types |
| `type` | string | The asset type that was uploaded |

**Processing Flow for MODEL assets**:
```
PENDING → (Celery worker picks up) → PROCESSING → COMPLETED / FAILED
```
Subscribe to `/notifications/stream/{user_id}` to receive real-time status updates.

**Error Responses**:
| Status | Condition |
|---|---|
| `400 Bad Request` | Invalid file extension for the chosen asset_type |
| `403 Forbidden` | User role is STUDENT |
| `500 Internal Server Error` | MinIO upload failed |

---

### `GET /assets/`

**Description**: List all assets owned by the current user. Optionally filter by type. Generates fresh presigned download URLs (1-hour expiry) for completed assets.

**Auth Required**: ✅

**Query Parameters**:
| Param | Type | Required | Description |
|---|---|---|---|
| `asset_type` | string | ❌ | Filter by type: `MODEL`, `VIDEO`, `SLIDE`, `IMAGE` |

**Examples**:  
- `GET /assets/` — all assets  
- `GET /assets/?asset_type=MODEL` — only 3D models

**Success Response** `200 OK` (array):
```json
[
  {
    "id": "f7c3e2b1-4a5d-48ce-9200-123456789abc",
    "filename": "human_heart.glb",
    "asset_type": "MODEL",
    "status": "COMPLETED",
    "is_sliceable": true,
    "download_url": "http://localhost:9000/assets/processed/f7c3e2b1...?X-Amz-Expires=3600&...",
    "metadata_json": {
      "interaction_type": "sliceable",
      "original_file": "human_heart.glb"
    }
  },
  {
    "id": "c9d1a2b3-...",
    "filename": "lecture_slides.pdf",
    "asset_type": "SLIDE",
    "status": "COMPLETED",
    "is_sliceable": false,
    "download_url": "http://localhost:9000/assets/raw/c9d1a2b3...?...",
    "metadata_json": null
  }
]
```

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Asset identifier |
| `filename` | string | Original uploaded filename |
| `asset_type` | string | Asset type enum |
| `status` | string | `PENDING` / `PROCESSING` / `COMPLETED` / `FAILED` |
| `is_sliceable` | boolean | Whether slicing/cross-section is enabled |
| `download_url` | string\|null | Presigned URL (1h expiry). `null` if not yet completed |
| `metadata_json` | object\|null | Processing metadata or error details |

---

### `GET /assets/{asset_id}`

**Description**: Get details for a single asset owned by the current user. Generates a fresh presigned download URL if completed.

**Auth Required**: ✅

**Path Parameters**:
| Param | Type | Description |
|---|---|---|
| `asset_id` | UUID (string) | Asset identifier |

**Success Response** `200 OK`:
```json
{
  "id": "f7c3e2b1-4a5d-48ce-9200-123456789abc",
  "filename": "human_heart.glb",
  "asset_type": "MODEL",
  "status": "COMPLETED",
  "is_sliceable": true,
  "download_url": "http://localhost:9000/assets/processed/f7c3e2b1...?X-Amz-Expires=3600&...",
  "metadata_json": {
    "interaction_type": "sliceable",
    "original_file": "human_heart.glb"
  }
}
```

**Error Responses**:
| Status | Condition |
|---|---|
| `404 Not Found` | Asset does not exist or belongs to another user |

---

### `DELETE /assets/{asset_id}`

**Description**: Delete an asset. Removes the database record **and** deletes both the original and processed files from MinIO storage.

**Auth Required**: ✅ (must be asset owner)

**Path Parameters**:
| Param | Type | Description |
|---|---|---|
| `asset_id` | UUID (string) | Asset to delete |

**Success Response** `204 No Content` (empty body)

**Error Responses**:
| Status | Condition |
|---|---|
| `404 Not Found` | Asset does not exist or belongs to another user |

---

## 4. Notifications Service `/notifications`

---

### `GET /notifications/stream/{client_id}`

**Description**: Open a **Server-Sent Events (SSE)** stream for real-time notifications. The client must keep the connection open; the server pushes messages when asset processing status changes.

This endpoint is used by the frontend to receive live updates when a 3D model upload is being processed by the Celery worker.

**Auth Required**: ❌ (No JWT validation — uses `client_id` which is the user's UUID from the JWT token)

**Path Parameters**:
| Param | Type | Description |
|---|---|---|
| `client_id` | string (UUID) | The user's UUID from the JWT payload (identifies the Redis pub/sub channel) |

**Connection Headers (important)**:
```
Accept: text/event-stream
Cache-Control: no-cache
```

**Stream Format**: Server-Sent Events (SSE)

Each event pushed to the client has this format:
```
event: message
data: {"asset_id": "f7c3e2b1-...", "status": "PROCESSING", "message": "Optimizing geometry and generating textures..."}
```

**Possible event `data` payloads**:

| Event Stage | Example Data |
|---|---|
| Worker picks up task | `{"asset_id": "...", "status": "PROCESSING", "message": "Beginning extraction and geometry normalization."}` |
| Downloading from storage | `{"asset_id": "...", "status": "PROCESSING", "message": "Downloading model from storage..."}` |
| Extracting ZIP | `{"asset_id": "...", "status": "PROCESSING", "message": "Extracting archive contents..."}` |
| Running Blender | `{"asset_id": "...", "status": "PROCESSING", "message": "Optimizing geometry and generating textures..."}` |
| Uploading result | `{"asset_id": "...", "status": "PROCESSING", "message": "Uploading optimized model to storage..."}` |
| Processing complete | `{"asset_id": "...", "status": "COMPLETED", "processed_url": "processed/f7c3e2b1....glb", "message": "Optimization and baking finished successfully!"}` |
| Processing failed | `{"asset_id": "...", "status": "FAILED", "error": "Blender Failed: ..."}` |

**Event Data Fields**:
| Field | Type | Present When | Description |
|---|---|---|---|
| `asset_id` | UUID string | Always | Which asset this event is about |
| `status` | string | Always | `"PROCESSING"` / `"COMPLETED"` / `"FAILED"` |
| `message` | string | Most events | Human-readable progress message |
| `processed_url` | string | COMPLETED | MinIO key for the processed GLB |
| `error` | string | FAILED | Error description from Blender/worker |

**How to use in the frontend (JavaScript)**:
```javascript
const userId = getUserIdFromToken(); // extract from JWT
const eventSource = new EventSource(
  `http://localhost:8000/notifications/stream/${userId}`
);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(`Asset ${data.asset_id} status: ${data.status}`);
  if (data.status === 'COMPLETED') {
    // Refetch asset list to get download URL
    refetchAssets();
    eventSource.close();
  }
};
```

**Connection Behavior**:
- Connection stays open indefinitely until client disconnects
- Nginx is configured with: `proxy_buffering off`, `proxy_read_timeout 86400s`
- The worker broadcasts to Redis channel `user_notifications:{client_id}`

---

## Error Response Format

All error responses from FastAPI services follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

---

## Authentication Flow Summary

```
1. POST /auth/register  →  Create account
2. POST /auth/login     →  Get JWT token + role
3. Use token in header: Authorization: Bearer <token>
4. All protected endpoints validate the JWT and load the user from DB
5. Token expires after 15 minutes → re-authenticate
```

## 3D Model Processing Flow Summary

```
1. POST /assets/upload (file + asset_type=MODEL)
   └─ Returns: { id, status: "PENDING" }

2. Subscribe: GET /notifications/stream/{user_id}
   └─ Receives SSE events

3. Background (Celery worker):
   ├─ Download raw .glb/.fbx/.zip from MinIO
   ├─ Extract ZIP (handles nested ZIPs)
   ├─ Run Blender headlessly:
   │   ├─ Import model
   │   ├─ Normalize geometry (unit scale, centering)
   │   ├─ Relink & auto-connect textures
   │   ├─ Fix material transparency
   │   ├─ Validate (NaN, manifold, textures)
   │   └─ Export as GLB
   └─ Upload processed GLB to MinIO

4. Events pushed via SSE:
   PROCESSING → PROCESSING → ... → COMPLETED (or FAILED)

5. GET /assets/{id}
   └─ Returns download_url (presigned, 1h expiry) for the processed GLB
```
