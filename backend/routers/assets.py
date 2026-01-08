from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import boto3
from botocore.client import Config
import os

from database import get_db
from models import Asset, User, AssetStatus, AssetType
from dependencies import get_current_user
from schemas import AssetResponse

from worker import process_asset

router = APIRouter(prefix="/assets", tags=["assets"])

# MinIO Client Setup
# ... (existing setup)

@router.get("/test-s3")
def test_s3_connection():
    try:
        response = s3.list_buckets()
        return {"status": "ok", "buckets": response.get('Buckets')}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# MinIO Client Setup
s3 = boto3.client('s3',
                    endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
                    aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                    aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                    config=Config(signature_version='s3v4'),
                    region_name='us-east-1')

# Public S3 Client (For generating browser-accessible URLs with correct signature)
# We use localhost:9000 so the signature matches what the browser requests.
s3_signer = boto3.client('s3',
                    endpoint_url="http://localhost:9000",
                    aws_access_key_id="minioadmin",
                    aws_secret_access_key="minioadmin",
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
    asset_type: AssetType = Form(...),
    is_sliceable: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    asset_id = uuid.uuid4()
    file_ext = file.filename.split('.')[-1].lower()
    
    # Validation per type
    if asset_type == AssetType.MODEL:
        ALLOWED = {'glb', 'gltf', 'fbx', 'obj', 'blend', 'stl'}
    elif asset_type == AssetType.VIDEO:
        ALLOWED = {'mp4', 'mov', 'avi'}
    elif asset_type == AssetType.SLIDE:
        ALLOWED = {'pdf', 'pptx', 'png', 'jpg'} # Slides can be images too, but kept separate for logic
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
    
    # Determine Initial Status
    # Models need processing. Videos/Slides are done (or just stored).
    initial_status = AssetStatus.PENDING if asset_type == AssetType.MODEL else AssetStatus.COMPLETED
    processed_path = s3_key if asset_type != AssetType.MODEL else None # For non-models, raw IS the processed

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
    
    # Trigger Celery Task ONLY for Models
    if asset_type == AssetType.MODEL:
        task = process_asset.delay(str(asset_id))
    
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
    # Generate URLs for all assets
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
def get_asset(asset_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.owner_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Generate Presigned URL
    download_url = None
    if asset.status == AssetStatus.COMPLETED and asset.processed_path:
        try:
            download_url = s3_signer.generate_presigned_url('get_object',
                                                    Params={'Bucket': BUCKET_NAME,
                                                            'Key': asset.processed_path},
                                                    ExpiresIn=3600)
        except Exception as e:
            print(f"Error generating url: {e}")
            
    # For Schema response, we attach the url manually (since it's not in DB)
    # But Pydantic 'orm_mode' usually grabs DB fields. We need to construct response or use a helper.
    # Actually, returning the ORM object works if the Pydantic model has matching fields.
    # But 'download_url' is computed. We should set it on the object or return a dict.
    
    asset.download_url = download_url # Monkey-patch for Pydantic (works usually)
    return asset

@router.delete("/{asset_id}", status_code=204)
def delete_asset(asset_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.owner_id == current_user.id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Delete from S3
    # We need to delete both original and processed paths if they exist
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

    # Delete from DB
    db.delete(asset)
    db.commit()
    return None
