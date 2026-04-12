from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import uuid
import boto3
from botocore.client import Config
import os
from celery import Celery

from shared.database import get_db
from shared.models import Asset, User, AssetStatus, AssetType, UserRole
from shared.dependencies import get_current_user
from shared.schemas import AssetResponse

router = APIRouter(prefix="/assets", tags=["assets"])

# Configure Celery Client (Decoupled from actual worker code)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
celery_app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

# MinIO Client Setup
s3 = boto3.client('s3',
                    endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
                    aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                    aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                    config=Config(signature_version='s3v4'),
                    region_name='us-east-1')

# Public S3 Client (For generating browser-accessible URLs)
s3_signer = boto3.client('s3',
                    endpoint_url=os.getenv("MINIO_EXTERNAL_ENDPOINT", "http://localhost:9000"),
                    aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                    aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                    config=Config(signature_version='s3v4', s3={'addressing_style': 'path'}),
                    region_name='us-east-1')

BUCKET_NAME = os.getenv("MINIO_BUCKET", "assets")

# Ensure bucket exists
try:
    s3.head_bucket(Bucket=BUCKET_NAME)
except:
    try:
        s3.create_bucket(Bucket=BUCKET_NAME)
    except:
        pass

@router.post("/upload")
async def upload_asset(
    file: UploadFile = File(...),
    asset_type: AssetType = Form(...),
    is_sliceable: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # RBAC: Only Teachers and TAs can upload
    if current_user.role not in [UserRole.TEACHER, UserRole.TA]:
        raise HTTPException(status_code=403, detail="Only Teachers and TAs can upload assets.")

    asset_id = uuid.uuid4()
    file_ext = file.filename.split('.')[-1].lower()
    
    # Validation per type
    if asset_type == AssetType.MODEL:
        ALLOWED = {'glb', 'gltf', 'fbx', 'obj', 'blend', 'stl', 'zip'}
    elif asset_type == AssetType.VIDEO:
        ALLOWED = {'mp4', 'mov', 'avi'}
    elif asset_type == AssetType.SLIDE:
        ALLOWED = {'pdf', 'pptx', 'png', 'jpg'} 
    elif asset_type == AssetType.IMAGE:
        ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    else:
        ALLOWED = set()

    if file_ext not in ALLOWED:
        raise HTTPException(status_code=400, detail=f"Invalid file type for {asset_type.value}. Allowed: {ALLOWED}")
    
    # Ensure bucket exists (Race condition fix)
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except:
        try:
            s3.create_bucket(Bucket=BUCKET_NAME)
        except Exception as e:
            print(f"Bucket creation failed: {e}")
            
    s3_key = f"raw/{asset_id}.{file_ext}"
    
    # Upload to MinIO
    try:
        s3.upload_fileobj(file.file, BUCKET_NAME, s3_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload Failed: {str(e)}")
    
    initial_status = AssetStatus.PENDING if asset_type == AssetType.MODEL else AssetStatus.COMPLETED
    processed_path = s3_key if asset_type != AssetType.MODEL else None

    # Create DB Entry
    new_asset = Asset(
        id=asset_id,
        owner_id=current_user.id,
        filename=file.filename,
        asset_type=asset_type,
        is_sliceable=is_sliceable if asset_type == AssetType.MODEL else False,
        original_path=s3_key,
        processed_path=processed_path,
        status=initial_status
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    
    # Trigger scan (scan decides whether to auto-process or wait for user)
    if asset_type == AssetType.MODEL:
        celery_app.send_task("worker.scan_asset", args=[str(asset_id)])
    
    return {"id": str(new_asset.id), "status": new_asset.status, "type": new_asset.asset_type}

@router.get("/", response_model=List[AssetResponse])
def list_assets(
    asset_type: Optional[AssetType] = None,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    query = db.query(Asset).filter(Asset.owner_id == current_user.id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
        
    assets = query.all()
    # Generate URLs
    for asset in assets:
        if asset.status == AssetStatus.COMPLETED and asset.processed_path:
            try:
                asset.download_url = s3_signer.generate_presigned_url('get_object',
                                                        Params={'Bucket': BUCKET_NAME,
                                                                'Key': asset.processed_path},
                                                        ExpiresIn=3600)
            except Exception as e:
                print(f"Error generating url for {asset.id}: {e}")
                
    return assets


class ConfirmSelectionRequest(BaseModel):
    selections: List[str]  # List of object names chosen by the user
    is_sliceable: bool = False


@router.post("/{asset_id}/confirm-selection")
def confirm_selection(
    asset_id: str,
    body: ConfirmSelectionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """User has confirmed which objects to import from a multi-object file.
    Creates one Asset record per selected object and starts processing.
    """
    parent = db.query(Asset).filter(
        Asset.id == asset_id,
        Asset.owner_id == current_user.id
    ).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Asset not found")
    if parent.status != AssetStatus.PENDING_SELECTION:
        raise HTTPException(status_code=400,
                            detail="Asset is not awaiting object selection")

    if not body.selections:
        raise HTTPException(status_code=400, detail="No objects selected")

    created_ids = []
    for obj_name in body.selections:
        child_id = uuid.uuid4()
        child_asset = Asset(
            id=child_id,
            owner_id=current_user.id,
            filename=obj_name,          # Real in-file object name
            asset_type=parent.asset_type,
            is_sliceable=body.is_sliceable,
            original_path=parent.original_path,   # Same raw file
            processed_path=None,
            status=AssetStatus.PENDING
        )
        db.add(child_asset)
        db.flush()  # Get the ID before commit
        celery_app.send_task("worker.process_asset",
                             args=[str(child_id), obj_name])
        created_ids.append(str(child_id))

    # Delete the placeholder parent asset
    # (raw file in S3 is kept via original_path references in children)
    db.delete(parent)
    db.commit()

    return {"created": created_ids}

@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Try uuid parsing so it matches db schema strictness if needed, though postgres usually handles string uuids
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.owner_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    download_url = None
    if asset.status == AssetStatus.COMPLETED and asset.processed_path:
        try:
            download_url = s3_signer.generate_presigned_url('get_object',
                                                    Params={'Bucket': BUCKET_NAME,
                                                            'Key': asset.processed_path},
                                                    ExpiresIn=3600)
        except Exception as e:
            print(f"Error generating url: {e}")
            
    asset.download_url = download_url
    return asset

@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.owner_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    paths_to_delete = []
    if asset.original_path:
        paths_to_delete.append(asset.original_path)
    if asset.processed_path:
        paths_to_delete.append(asset.processed_path)
        
    for path in paths_to_delete:
        try:
            s3.delete_object(Bucket=BUCKET_NAME, Key=path)
        except Exception as e:
            print(f"Failed to delete S3 object {path}: {e}")

    db.delete(asset)
    db.commit()
    return None
