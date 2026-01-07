from pydantic import BaseModel
from typing import Optional, List, Dict
from models import UserRole, AssetType, AssetStatus, RoomMemberStatus
import uuid
from datetime import datetime

# --- User Schemas ---
class UserCreate(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.STUDENT

class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    role: UserRole

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: UserRole

# --- Asset Schemas ---
class AssetResponse(BaseModel):
    id: uuid.UUID
    filename: str
    asset_type: AssetType
    status: AssetStatus
    is_sliceable: bool
    download_url: Optional[str] = None
    metadata: Optional[dict] = None

    class Config:
        orm_mode = True

# --- Room Schemas ---
class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_online: bool = False
    max_participants: int = 20

class RoomResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    owner_id: uuid.UUID
    is_online: bool
    active_users_count: int = 0
    created_at: datetime
    role_in_room: Optional[str] = None # OWNER, MEMBER, or None

    class Config:
        orm_mode = True

class InviteCreate(BaseModel):
    username: str
    permissions: Dict[str, bool] = {"can_slice": True, "can_talk": False}

class InvitationResponse(BaseModel):
    room_id: uuid.UUID
    room_name: str
    invited_by: str # Owner username
    status: RoomMemberStatus
