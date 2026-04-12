from sqlalchemy import Column, String, Boolean, Enum, ForeignKey, Integer, DateTime, Uuid, JSON
from sqlalchemy.orm import relationship
import uuid
import enum
import datetime
from .database import Base

class UserRole(str, enum.Enum):
    TEACHER = "TEACHER"
    TA = "TA"
    STUDENT = "STUDENT"

class AssetType(str, enum.Enum):
    MODEL = "MODEL"
    VIDEO = "VIDEO"
    SLIDE = "SLIDE"
    IMAGE = "IMAGE"

class RoomMemberStatus(str, enum.Enum):
    INVITED = "INVITED"
    JOINED = "JOINED"

class AssetStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, nullable=False)
    
    assets = relationship("Asset", back_populates="owner")
    owned_rooms = relationship("Room", back_populates="owner")
    room_memberships = relationship("RoomMember", back_populates="user")

class Room(Base):
    __tablename__ = "rooms"
    
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    is_online = Column(Boolean, default=False)
    max_participants = Column(Integer, default=20)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    owner = relationship("User", back_populates="owned_rooms")
    members = relationship("RoomMember", back_populates="room")

class RoomMember(Base):
    __tablename__ = "room_members"
    
    room_id = Column(Uuid, ForeignKey("rooms.id"), primary_key=True)
    user_id = Column(Uuid, ForeignKey("users.id"), primary_key=True)
    status = Column(Enum(RoomMemberStatus), default=RoomMemberStatus.INVITED)
    permissions = Column(JSON, default={"can_slice": True, "can_talk": False, "can_interact": True})
    
    room = relationship("Room", back_populates="members")
    user = relationship("User", back_populates="room_memberships")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    
    filename = Column(String, nullable=False)
    asset_type = Column(Enum(AssetType), default=AssetType.MODEL)
    is_sliceable = Column(Boolean, default=False)
    status = Column(Enum(AssetStatus), default=AssetStatus.PENDING)
    
    original_path = Column(String, nullable=True)
    processed_path = Column(String, nullable=True)
    
    metadata_json = Column(JSON, nullable=True)
    
    owner = relationship("User", back_populates="assets")
