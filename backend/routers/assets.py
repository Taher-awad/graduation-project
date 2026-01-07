from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid
import boto3
from botocore.client import Config
import os

from database import get_db
from models import Asset, User, AssetStatus
from dependencies import get_current_user

from worker import process_asset

router = APIRouter(prefix="/assets", tags=["assets"])

# MinIO Client Setup
s3 = boto3.client('s3',
                    endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
                    aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                    aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                    config=Config(signature_version='s3v4'),
                    region_name='us-east-1')

BUCKET_NAME = os.getenv("MINIO_BUCKET", "assets")

# Ensure bucket exists (simplified for dev)
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
    is_sliceable: bool = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    asset_id = uuid.uuid4()
    file_ext = file.filename.split('.')[-1].lower()
    
    ALLOWED_EXTENSIONS = {'glb', 'gltf', 'fbx', 'obj', 'blend', 'stl'}
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {ALLOWED_EXTENSIONS}")
        
    s3_key = f"raw/{asset_id}.{file_ext}"
    
    # Upload to MinIO
    try:
        s3.upload_fileobj(file.file, BUCKET_NAME, s3_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"S3 Upload Failed: {str(e)}")
    
    # Create DB Entry
    new_asset = Asset(
        id=asset_id,
        owner_id=current_user.id,
        filename=file.filename,
        is_sliceable=is_sliceable,
        original_path=s3_key,
        status=AssetStatus.PENDING
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    
    # Trigger Celery Task
    task = process_asset.delay(str(asset_id))
    
    return {"id": str(new_asset.id), "status": new_asset.status}

@router.get("/", response_model=List[dict])
def list_assets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    assets = db.query(Asset).filter(Asset.owner_id == current_user.id).all()
    return [{"id": str(a.id), "filename": a.filename, "status": a.status} for a in assets]

@router.get("/{asset_id}")
def get_asset(asset_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.owner_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Generate Presigned URL for processed file if completed
    download_url = None
    if asset.status == AssetStatus.COMPLETED and asset.processed_path:
        try:
            download_url = s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': BUCKET_NAME,
                                                            'Key': asset.processed_path},
                                                    ExpiresIn=3600)
        except Exception as e:
            print(f"Error generating url: {e}")

    return {
        "id": str(asset.id),
        "status": asset.status,
        "filename": asset.filename,
        "is_sliceable": asset.is_sliceable,
        "download_url": download_url,
        "metadata": asset.metadata_json
    }
