# EduVR – Cortex AI Platform: Data Models & Class Structure

## Database: PostgreSQL (shared schema across all microservices)

All models are defined in `microservices/shared/models.py` and use SQLAlchemy ORM.

---

## Enumerations

### `UserRole`
```python
class UserRole(str, Enum):
    TEACHER = "TEACHER"
    TA      = "TA"
    STUDENT = "STUDENT"
```
Controls RBAC permissions across all services.

### `AssetType`
```python
class AssetType(str, Enum):
    MODEL = "MODEL"   # 3D models → Blender pipeline
    VIDEO = "VIDEO"   # Lecture recordings
    SLIDE = "SLIDE"   # PDF/PPTX presentations
    IMAGE = "IMAGE"   # Static images
```

### `AssetStatus`
```python
class AssetStatus(str, Enum):
    PENDING    = "PENDING"    # Uploaded, awaiting Celery task
    PROCESSING = "PROCESSING" # Blender is currently processing
    COMPLETED  = "COMPLETED"  # GLB available for download
    FAILED     = "FAILED"     # Processing failed (see metadata_json.error)
```

### `RoomMemberStatus`
```python
class RoomMemberStatus(str, Enum):
    INVITED = "INVITED" # Invitation sent, not yet accepted
    JOINED  = "JOINED"  # User accepted the invitation
```

---

## Database Tables

### Table: `users`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, DEFAULT uuid4() | |
| `username` | VARCHAR | UNIQUE, NOT NULL, INDEX | Login identifier |
| `password_hash` | VARCHAR | NOT NULL | bcrypt hash |
| `role` | ENUM(UserRole) | NOT NULL, DEFAULT 'STUDENT' | |

**Relationships**:
- `assets` — one-to-many → `Asset` (back_populates="owner")
- `owned_rooms` — one-to-many → `Room` (back_populates="owner")
- `room_memberships` — one-to-many → `RoomMember` (back_populates="user")

---

### Table: `rooms`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, DEFAULT uuid4() | |
| `name` | VARCHAR | NOT NULL | Display name |
| `description` | VARCHAR | NULLABLE | Optional |
| `owner_id` | UUID | FK → users.id, NOT NULL | |
| `is_online` | BOOLEAN | DEFAULT False | Live session flag |
| `max_participants` | INTEGER | DEFAULT 20 | |
| `created_at` | DATETIME | DEFAULT utcnow() | UTC |

**Relationships**:
- `owner` — many-to-one → `User` (back_populates="owned_rooms")
- `members` — one-to-many → `RoomMember` (back_populates="room")

---

### Table: `room_members`
**Composite primary key**: (`room_id`, `user_id`)

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `room_id` | UUID | PK, FK → rooms.id | |
| `user_id` | UUID | PK, FK → users.id | |
| `status` | ENUM(RoomMemberStatus) | DEFAULT 'INVITED' | |
| `permissions` | JSON | DEFAULT `{"can_slice": true, "can_talk": false, "can_interact": true}` | Per-user room permissions |

**Relationships**:
- `room` — many-to-one → `Room`
- `user` — many-to-one → `User`

---

### Table: `assets`
| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | UUID | PK, DEFAULT uuid4() | |
| `owner_id` | UUID | FK → users.id, NOT NULL | |
| `filename` | VARCHAR | NOT NULL | Original filename |
| `asset_type` | ENUM(AssetType) | DEFAULT 'MODEL' | |
| `is_sliceable` | BOOLEAN | DEFAULT False | Enables manifold/cross-section in VR |
| `status` | ENUM(AssetStatus) | DEFAULT 'PENDING' | Processing lifecycle |
| `original_path` | VARCHAR | NULLABLE | MinIO key: `raw/{id}.{ext}` |
| `processed_path` | VARCHAR | NULLABLE | MinIO key: `processed/{id}.glb` (MODEL only) |
| `metadata_json` | JSON | NULLABLE | Processing info or error detail |

**Relationships**:
- `owner` — many-to-one → `User`

**`metadata_json` structure**:
```json
// On success:
{
  "interaction_type": "sliceable",
  "original_file": "human_heart.fbx",
  "processing_time": "TODO"
}

// On failure:
{
  "error": "Blender Failed: ..."
}
```

---

## Pydantic Schemas

Defined in `microservices/shared/schemas.py`.

### Request Schemas

#### `UserCreate`
```python
class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.STUDENT
```
Used by: `POST /auth/register`, `POST /auth/login`

#### `RoomCreate`
```python
class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_online: bool = False
    max_participants: int = 20
```
Used by: `POST /rooms/`

#### `InviteCreate`
```python
class InviteCreate(BaseModel):
    username: str
    permissions: Dict[str, bool] = {"can_slice": True, "can_talk": False}
```
Used by: `POST /rooms/{room_id}/invite`

---

### Response Schemas

#### `Token`
```python
class Token(BaseModel):
    access_token: str
    token_type: str      # "bearer"
    role: UserRole
```
Returned by: `POST /auth/login`

#### `UserResponse`
```python
class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    role: UserRole
```

#### `RoomResponse`
```python
class RoomResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    owner_id: uuid.UUID
    is_online: bool
    active_users_count: int = 0      # Placeholder (future WebRTC/WS integration)
    created_at: datetime
    role_in_room: Optional[str]      # "OWNER" or "MEMBER"
```

#### `InvitationResponse`
```python
class InvitationResponse(BaseModel):
    room_id: uuid.UUID
    room_name: str
    invited_by: str        # Owner's username
    status: RoomMemberStatus
```

#### `AssetResponse`
```python
class AssetResponse(BaseModel):
    id: uuid.UUID
    filename: str
    asset_type: AssetType
    status: AssetStatus
    is_sliceable: bool
    download_url: Optional[str] = None   # Presigned URL (1h), null if not COMPLETED
    metadata_json: Optional[dict] = None
```

---

## Entity Relationship Diagram

```
┌─────────────┐         ┌─────────────────┐         ┌──────────┐
│    users     │         │   room_members  │         │  rooms   │
│─────────────│         │─────────────────│         │──────────│
│ id (PK)     │◄────────┤ user_id (PK,FK) │         │ id (PK)  │
│ username    │         │ room_id (PK,FK) ├────────►│ name     │
│ password_   │         │ status          │         │ owner_id ├──────────┐
│  hash       │         │ permissions     │         │ is_online│          │
│ role        │         └─────────────────┘         │ max_par- │          │
└──────┬──────┘                                     │  ticip.  │          │
       │                                            │ created_ │          │
       │  owns                                      │  at      │          │
       │                                            └──────────┘          │
       │    ┌──────────────────────────────┐                              │
       └───►│         assets               │◄─────────────────────────────┘
            │──────────────────────────────│  owner_id FK
            │ id (PK)                      │
            │ owner_id (FK → users.id)     │
            │ filename                     │
            │ asset_type                   │
            │ is_sliceable                 │
            │ status                       │
            │ original_path                │
            │ processed_path               │
            │ metadata_json                │
            └──────────────────────────────┘
```

---

## MinIO Storage Structure

```
assets bucket/
├── raw/
│   ├── {asset_id}.glb         # Raw upload for MODEL
│   ├── {asset_id}.fbx
│   ├── {asset_id}.zip
│   ├── {asset_id}.mp4         # VIDEO (served directly)
│   ├── {asset_id}.pdf         # SLIDE (served directly)
│   └── {asset_id}.png         # IMAGE (served directly)
└── processed/
    └── {asset_id}.glb         # Blender-processed GLB (MODEL only)
```

Non-model assets use `raw/` path as both `original_path` and `processed_path` (served directly). Model assets start as `raw/` and get a new `processed/` path after worker completes.
