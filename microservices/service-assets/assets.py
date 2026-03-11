from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
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

# Env variable validation
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
if not MINIO_ACCESS_KEY or not MINIO_SECRET_KEY:
    raise ValueError("MINIO_ACCESS_KEY or MINIO_SECRET_KEY environment variable is missing")

# MinIO Client Setup
s3 = boto3.client('s3',
                    endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
                    aws_access_key_id=MINIO_ACCESS_KEY,
                    aws_secret_access_key=MINIO_SECRET_KEY,
                    config=Config(signature_version='s3v4'),
                    region_name='us-east-1')

# Public S3 Client (For generating browser-accessible URLs)
s3_signer = boto3.client('s3',
                    endpoint_url=os.getenv("MINIO_EXTERNAL_ENDPOINT", "http://localhost:9000"),
                    aws_access_key_id=MINIO_ACCESS_KEY,
                    aws_secret_access_key=MINIO_SECRET_KEY,
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
    db: AsyncSession = Depends(get_db)
):
    # RBAC: Only Staff can upload
    if current_user.role != UserRole.STAFF:
        raise HTTPException(status_code=403, detail="Only Staff members can upload assets.")

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
    await db.commit()
    await db.refresh(new_asset)
    
    # Decentralized Task Trigger: Send to Redis directly without importing the heavy worker
    if asset_type == AssetType.MODEL:
        celery_app.send_task("worker.process_asset", args=[str(asset_id)])
    
    return {"id": str(new_asset.id), "status": new_asset.status, "type": new_asset.asset_type}

@router.get("/", response_model=List[AssetResponse])
async def list_assets(
    skip: int = 0,
    limit: int = 50,
    asset_type: Optional[AssetType] = None,
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db)
):
    query = select(Asset).filter(Asset.owner_id == current_user.id)
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
        
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    assets = result.scalars().all()
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

@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Try uuid parsing so it matches db schema strictness if needed, though postgres usually handles string uuids
    result = await db.execute(select(Asset).filter(Asset.id == asset_id, Asset.owner_id == current_user.id))
    asset = result.scalars().first()
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
async def delete_asset(asset_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Asset).filter(Asset.id == asset_id, Asset.owner_id == current_user.id))
    asset = result.scalars().first()
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

    await db.delete(asset)
    await db.commit()
    return None
