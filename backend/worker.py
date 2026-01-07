import os
import time
import subprocess
import shutil
import json
import boto3
from botocore.client import Config
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Asset, AssetStatus
from celery_app import celery_app
import optimize

# Debugging Paths
import sys
print(f"DEBUG: CWD={os.getcwd()}")
print(f"DEBUG: SYS.PATH={sys.path}")

# MinIO Setup
s3 = boto3.client('s3',
                    endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
                    aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                    aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                    config=Config(signature_version='s3v4'),
                    region_name='us-east-1')

BUCKET_NAME = os.getenv("MINIO_BUCKET", "assets")

@celery_app.task(bind=True)
def process_asset(self, asset_id: str):
    db: Session = SessionLocal()
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    
    if not asset:
        db.close()
        return "Asset Not Found"

    try:
        # Update Status
        asset.status = AssetStatus.PROCESSING
        db.commit()

        # Paths
        work_dir = f"/tmp/{asset_id}"
        os.makedirs(work_dir, exist_ok=True)
        
        input_filename = asset.filename
        local_input_path = os.path.join(work_dir, input_filename)
        mid_glb_path = os.path.join(work_dir, "mid.glb")
        final_glb_path = os.path.join(work_dir, "final.glb")

        # 1. Download from S3
        print(f"Downloading {asset.original_path}...")
        s3.download_file(BUCKET_NAME, asset.original_path, local_input_path)

        # 2. Blender Processing (Import -> Normalize -> Export GLB)
        # Note: We assume 'blender' is in PATH (handled by Dockerfile)
        # We pass arguments after --
        print("Running Blender...")
        blender_cmd = [
            "blender",
            "-b", # Background
            "-P", "process_model.py", # Script
            "--", # Split args
            "--input", local_input_path,
            "--output", mid_glb_path,
            "--sliceable", str(asset.is_sliceable),
            "--id", str(asset.id)
        ]
        
        # Capture output for debugging
        result = subprocess.run(blender_cmd, capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode != 0:
            raise Exception(f"Blender Failed: {result.stderr}")

        # 3. Optimization (gltfpack)
        print("Running Optimization...")
        optimize.run_optimization(mid_glb_path, final_glb_path, asset.is_sliceable)

        # 4. Upload Result
        processed_key = f"processed/{asset_id}.glb"
        s3.upload_file(final_glb_path, BUCKET_NAME, processed_key)

        # 5. Update DB
        asset.status = AssetStatus.COMPLETED
        asset.processed_path = processed_key
        asset.metadata_json = {
            "processing_time": "TODO",
            "interaction_type": "sliceable" if asset.is_sliceable else "static",
            "original_file": asset.filename
        }
        db.commit()

        # Cleanup
        shutil.rmtree(work_dir)
        return "Success"

    except Exception as e:
        print(f"Task Failed: {e}")
        asset.status = AssetStatus.FAILED
        asset.metadata_json = {"error": str(e)}
        db.commit()
        # Cleanup
        if os.path.exists(f"/tmp/{asset_id}"):
            shutil.rmtree(f"/tmp/{asset_id}")
        return f"Failed: {e}"
    finally:
        db.close()
