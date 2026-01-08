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
from utils_worker import find_main_model_file

# Debugging Paths
# Debugging Paths
import sys


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

        # Logic for Zip Files
        target_model_path = local_input_path
        blender_cwd = work_dir # Default CWD is the tmp root

        if input_filename.lower().endswith('.zip'):
            print("Detected ZIP file. Extracting...")
            import zipfile
            
            extract_dir = os.path.join(work_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)
            
            with zipfile.ZipFile(local_input_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                
            # Find the main model file
            found_file = find_main_model_file(extract_dir)
            if not found_file:
                raise Exception("No valid 3D model (.blend, .gltf, .fbx, .obj) found in ZIP")
                
            target_model_path = found_file
            # CRITICAL: We must run Blender from the directory OF the model file
            # so relative texture paths (like ./textures/wood.png) work.
            blender_cwd = os.path.dirname(found_file)
            print(f"Main model found: {target_model_path}")
            print(f"Setting Blender CWD to: {blender_cwd}")

        # 2. Blender Processing (Import -> Normalize -> Export GLB)
        print("Running Blender...")
        blender_cmd = [
            "blender",
            "-b", # Background
            "-P", "/app/process_model.py", # Absolute path to ensure it runs from any CWD
            "--", # Split args
            "--input", target_model_path,
            "--output", mid_glb_path,
            "--sliceable", str(asset.is_sliceable),
            "--id", str(asset.id)
        ]
        
        # Capture output for debugging
        result = subprocess.run(blender_cmd, capture_output=True, text=True, cwd=blender_cwd)
        
        # ALWAYS print Blender output (so we can see if it did nothing on success)
        print("--- BLENDER STDOUT ---")
        print(result.stdout)
        print("--- BLENDER STDERR ---")
        print(result.stderr)
        
        if result.returncode != 0:
            # Check for Validation JSON
            import json
            if "VALIDATION_FAILED" in result.stdout:
                try:
                    # Find the line after VALIDATION_FAILED
                    lines = result.stdout.splitlines()
                    for i, line in enumerate(lines):
                        if "VALIDATION_FAILED" in line:
                            error_json = lines[i+1]
                            errors = json.loads(error_json)
                            # Raise specific error
                            raise Exception(f"Validation Failed: {', '.join(errors)}")
                except ValueError:
                    pass
            
            raise Exception(f"Blender Failed: {result.stderr}")



        # 3. Optimization (gltfpack)
        # Note: Optimization disabled to prevent shader/color artifacts (Division by Zero).
        # We simply copy the intermediate file to the final path.
        shutil.copy(mid_glb_path, final_glb_path)

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
        
        # Parse Blender Output for Specific Validation Errors
        error_msg = str(e)
        if "Blender Failed" in error_msg:
             # Logic to find "VALIDATION_FAILED" in stdout? 
             # We need to capture stdout in the Exception context or read it here.
             # subprocess.run captured output is in `result`. 
             # BUT `result` is local to the try block.
             # We need to raise Exception with the stdout attached?
             pass 
             
        # Because 'result' scope is tricky, let's just assert:
        # If the worker logic sees VALIDATION_FAILED in the logs, it should ideally pass it up.
        # For now, let's put a generic error, but if we can parse it from `e` or logs...
        
        # Improved: We can't access `result.stdout` here easily unless we change the flow.
        # But wait, look at where we raise Exception: raise Exception(f"Blender Failed: {result.stderr}")
        # Blender prints VALIDATION_FAILED to stdout, not stderr usually (unless we force it).
        # We should parse result.stdout INSIDE the try block.
        
        asset.metadata_json = {"error": str(e)}
        db.commit()
        # Cleanup
        if os.path.exists(f"/tmp/{asset_id}"):
            shutil.rmtree(f"/tmp/{asset_id}")
        return f"Failed: {e}"
    finally:
        db.close()
