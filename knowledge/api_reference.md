# API Quick Reference

> Base URL: `http://localhost:8000`  
> Auth header: `Authorization: Bearer <token>`

## Auth Service `/auth`

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| POST | `/auth/register` | ❌ | Any | Create account |
| POST | `/auth/login` | ❌ | Any | Get JWT token |

### Login Response
```json
{"access_token": "...", "token_type": "bearer", "role": "TEACHER"}
```

## Rooms Service `/rooms`

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| POST | `/rooms/` | ✅ | TEACHER/TA | Create room |
| GET | `/rooms/` | ✅ | Any | List my rooms |
| GET | `/rooms/invitations` | ✅ | Any | List pending invites |
| POST | `/rooms/{id}/invite` | ✅ | OWNER | Invite user |
| POST | `/rooms/{id}/join` | ✅ | Invited | Accept invite |
| PUT | `/rooms/{id}/status?is_online=true` | ✅ | OWNER | Toggle live |
| DELETE | `/rooms/{id}` | ✅ | OWNER | Delete room |

## Assets Service `/assets`

| Method | Path | Auth | Role | Description |
|---|---|---|---|---|
| POST | `/assets/upload` | ✅ | TEACHER/TA | Upload file (`multipart/form-data`) |
| GET | `/assets/` | ✅ | Any | List my assets |
| GET | `/assets/?asset_type=MODEL` | ✅ | Any | Filter by type |
| GET | `/assets/{id}` | ✅ | OWNER | Get single asset |
| DELETE | `/assets/{id}` | ✅ | OWNER | Delete asset + MinIO files |

### Upload Form Fields
```
file: <binary>
asset_type: MODEL | VIDEO | SLIDE | IMAGE
is_sliceable: true | false  (MODEL only)
```

## Notifications Service `/notifications`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/notifications/stream/{user_id}` | ❌ | SSE stream for processing updates |

### SSE Event Format
```
event: message
data: {"asset_id": "...", "status": "PROCESSING", "message": "..."}
data: {"asset_id": "...", "status": "COMPLETED", "processed_url": "..."}
data: {"asset_id": "...", "status": "FAILED", "error": "..."}
```

## Asset Types & Allowed Extensions

| Type | Extensions |
|---|---|
| `MODEL` | `.glb`, `.gltf`, `.fbx`, `.obj`, `.blend`, `.stl`, `.zip` |
| `VIDEO` | `.mp4`, `.mov`, `.avi` |
| `SLIDE` | `.pdf`, `.pptx`, `.png`, `.jpg` |
| `IMAGE` | `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` |

## Asset Processing Status Flow

```
PENDING → PROCESSING → COMPLETED
                     → FAILED
```
