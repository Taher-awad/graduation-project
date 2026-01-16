# API Specification

## Auth Module (`/auth`)

| Method   | Endpoint         | Description          | Payload (Body)                                              | Response                                                         |
| :------- | :--------------- | :------------------- | :---------------------------------------------------------- | :--------------------------------------------------------------- |
| **POST** | `/auth/register` | Register a new user. | `{"username": "str", "password": "str", "role": "STUDENT"}` | `{"message": "User created successfully"}`                       |
| **POST** | `/auth/login`    | Login and get JWT.   | `{"username": "str", "password": "str"}`                    | `{"access_token": "str", "token_type": "bearer", "role": "str"}` |

## Assets Module (`/assets`)

| Method     | Endpoint          | Description                 | Payload                                                | Response                                      |
| :--------- | :---------------- | :-------------------------- | :----------------------------------------------------- | :-------------------------------------------- |
| **GET**    | `/assets/test-s3` | Debug S3 connection.        | N/A                                                    | `{"status": "ok", "buckets": [...]}`          |
| **POST**   | `/assets/upload`  | Upload new asset.           | `Multipart-Form`: `file`, `asset_type`, `is_sliceable` | `{"id": "uuid", "status": "PENDING", ...}`    |
| **GET**    | `/assets/`        | List user's assets.         | Query Param: `?asset_type=MODEL` (Optional)            | `[{"id": "...", "download_url": "...", ...}]` |
| **GET**    | `/assets/{id}`    | Get specific asset details. | N/A                                                    | `{"id": "...", "download_url": "...", ...}`   |
| **DELETE** | `/assets/{id}`    | Delete asset (DB & S3).     | N/A                                                    | `204 No Content`                              |

## Rooms Module (`/rooms`)

| Method   | Endpoint             | Description                         | Payload                                      | Response                                          |
| :------- | :------------------- | :---------------------------------- | :------------------------------------------- | :------------------------------------------------ |
| **POST** | `/rooms/`            | Create a new room (Staff only).     | `{"name": "str", "description": "str", ...}` | `{"id": "...", "name": "...", "owner_id": "..."}` |
| **GET**  | `/rooms/`            | List active rooms (Owned + Joined). | N/A                                          | `[{"id": "...", "role_in_room": "OWNER/MEMBER"}]` |
| **GET**  | `/rooms/invitations` | List pending invites.               | N/A                                          | `[{"room_id": "...", "invited_by": "..."}]`       |
| **POST** | `/rooms/{id}/invite` | Invite user to room (Owner only).   | `{"username": "str", "permissions": {...}}`  | `{"message": "Invitation sent..."}`               |
| **POST** | `/rooms/{id}/join`   | Accept invitation.                  | N/A                                          | `{"message": "You have joined the room"}`         |
| **PUT**  | `/rooms/{id}/status` | Toggle room online status.          | Query Param: `?is_online=true`               | `{"status": "updated", "is_online": true}`        |
