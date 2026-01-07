from sqlalchemy import Column, String, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.orm import relationship
import uuid
import enum
from database import Base

class AssetStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    
    assets = relationship("Asset", back_populates="owner")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    filename = Column(String, nullable=False)
    is_sliceable = Column(Boolean, default=False)
    status = Column(Enum(AssetStatus), default=AssetStatus.PENDING)
    
    original_path = Column(String, nullable=True) # S3 Key
    processed_path = Column(String, nullable=True) # S3 Key
    
    metadata_json = Column(JSON, nullable=True)
    
    owner = relationship("User", back_populates="assets")
