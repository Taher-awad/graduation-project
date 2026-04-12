import os
import time
import subprocess
import shutil
import json
import boto3
from botocore.client import Config
from sqlalchemy.orm import Session
from shared.database import SessionLocal
from shared.models import Asset, AssetStatus
from celery_app import celery_app

from utils_worker import find_main_model_file
import redis

# Redis Configuration for Pub/Sub SSE
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))

def broadcast_status(user_id: str, asset_id: str, status: str, extra: dict = None):
    channel = f"user_notifications:{user_id}"
    message = {
        "asset_id": asset_id,
        "status": status,
    }
    if extra:
        message.update(extra)
    redis_client.publish(channel, json.dumps(message))

import sys

# MinIO Setup
s3 = boto3.client('s3',
                    endpoint_url=os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
                    aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
                    aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
                    config=Config(signature_version='s3v4'),
                    region_name='us-east-1')

BUCKET_NAME = os.getenv("MINIO_BUCKET", "assets")


def _prepare_model_path(asset, work_dir):
    """
    Downloads the raw asset from S3, extracts ZIP if needed.
    Returns (target_model_path, blender_cwd).
    """
    input_filename = asset.filename
    local_input_path = os.path.join(work_dir, input_filename)

    s3.download_file(BUCKET_NAME, asset.original_path, local_input_path)

    if input_filename.lower().endswith('.zip'):
        import zipfile
        extract_dir = os.path.join(work_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)

        with zipfile.ZipFile(local_input_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        found_file = find_main_model_file(extract_dir)

        if not found_file:
            # Check nested ZIPs
            inner_zips = []
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.lower().endswith('.zip'):
                        inner_zips.append(os.path.join(root, f))
            if inner_zips:
                largest_zip = max(inner_zips, key=os.path.getsize)
                try:
                    with zipfile.ZipFile(largest_zip, 'r') as z_inner:
                        z_inner.extractall(os.path.dirname(largest_zip))
                    found_file = find_main_model_file(extract_dir)
                except Exception as e:
                    print(f"Failed to extract inner zip: {e}")

        if not found_file:
            raise Exception("No valid 3D model found in ZIP")

        return found_file, os.path.dirname(found_file)

    return local_input_path, work_dir


@celery_app.task(bind=True, name="worker.scan_asset")
def scan_asset(self, asset_id: str):
    """
    Runs Blender in --scan mode to detect objects and strip skyboxes.
    - 1 object  → auto-trigger process_asset
    - multiple  → set status PENDING_SELECTION, broadcast list to frontend
    """
    db: Session = SessionLocal()
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        db.close()
        return "Asset Not Found"

    work_dir = f"/tmp/scan_{asset_id}"
    os.makedirs(work_dir, exist_ok=True)

    try:
        asset.status = AssetStatus.SCANNING
        db.commit()
        broadcast_status(str(asset.owner_id), asset_id, "SCANNING",
                         {"message": "Analyzing file contents..."})

        target_model_path, blender_cwd = _prepare_model_path(asset, work_dir)

        blender_cmd = [
            "blender", "-b",
            "-P", "/app/service-3d-worker/process_model.py",
            "--",
            "--input", target_model_path,
            "--scan"
        ]

        result = subprocess.run(blender_cmd, capture_output=True, text=True,
                                cwd=blender_cwd, timeout=120)

        print("--- SCAN STDOUT ---")
        print(result.stdout)
        print("--- SCAN STDERR ---")
        print(result.stderr)

        # Parse SCAN_RESULT line from stdout
        objects = []
        for line in result.stdout.splitlines():
            if line.startswith("SCAN_RESULT:"):
                try:
                    objects = json.loads(line[len("SCAN_RESULT:"):])
                except Exception as e:
                    print(f"Failed to parse scan result: {e}")

        if not objects:
            raise Exception("Scan produced no objects. File may be empty or corrupt.")

        if len(objects) == 1:
            # Auto-process the single object
            print(f"Single object found: {objects[0]['name']}. Auto-processing...")
            asset.status = AssetStatus.PENDING
            asset.filename = objects[0]['name']  # Use real in-file name
            db.commit()
            shutil.rmtree(work_dir, ignore_errors=True)
            # Trigger full processing
            celery_app.send_task("worker.process_asset",
                                 args=[asset_id, objects[0]['name']])
        else:
            # Multiple objects — wait for user selection
            asset.status = AssetStatus.PENDING_SELECTION
            # Store object list in metadata for the frontend to read
            asset.metadata_json = {"scan_objects": objects}
            db.commit()
            broadcast_status(str(asset.owner_id), asset_id, "PENDING_SELECTION", {
                "message": f"Found {len(objects)} objects. Please select which to import.",
                "objects": objects
            })
            shutil.rmtree(work_dir, ignore_errors=True)
            # Schedule auto-discard after 10 minutes if user never selects
            celery_app.send_task("worker.auto_discard_asset",
                                 args=[asset_id],
                                 countdown=600)

        return "Scan Complete"

    except Exception as e:
        print(f"Scan Failed: {e}")
        asset.status = AssetStatus.FAILED
        asset.metadata_json = {"error": str(e)}
        db.commit()
        broadcast_status(str(asset.owner_id), asset_id, "FAILED", {"error": str(e)})
        shutil.rmtree(work_dir, ignore_errors=True)
        return f"Failed: {e}"
    finally:
        db.close()


@celery_app.task(bind=True, name="worker.auto_discard_asset")
def auto_discard_asset(self, asset_id: str):
    """
    Runs 10 minutes after a scan sets PENDING_SELECTION.
    If the user never confirmed their selection, delete the placeholder asset.
    """
    db: Session = SessionLocal()
    try:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            return "Already gone"
        if asset.status != AssetStatus.PENDING_SELECTION:
            return "User already selected"

        print(f"Auto-discarding timed-out PENDING_SELECTION asset {asset_id}")

        if asset.original_path:
            try:
                s3.delete_object(Bucket=BUCKET_NAME, Key=asset.original_path)
            except Exception as e:
                print(f"S3 cleanup error: {e}")

        broadcast_status(str(asset.owner_id), asset_id, "DISCARDED",
                         {"message": "Selection timed out. Asset was automatically removed."})

        db.delete(asset)
        db.commit()
        return "Discarded"
    except Exception as e:
        print(f"Auto-discard failed: {e}")
        return f"Failed: {e}"
    finally:
        db.close()


@celery_app.task(bind=True, name="worker.process_asset")

def process_asset(self, asset_id: str, object_name: str = None):
    db: Session = SessionLocal()
    asset = db.query(Asset).filter(Asset.id == asset_id).first()

    if not asset:
        db.close()
        return "Asset Not Found"

    try:
        asset.status = AssetStatus.PROCESSING
        db.commit()

        broadcast_status(str(asset.owner_id), asset_id, "PROCESSING",
                         {"message": "Beginning extraction and geometry normalization."})

        work_dir = f"/tmp/{asset_id}"
        os.makedirs(work_dir, exist_ok=True)

        input_filename = asset.filename
        # For child assets, original_path still points to the parent raw file
        local_input_path = os.path.join(work_dir, os.path.basename(asset.original_path))
        mid_glb_path = os.path.join(work_dir, "mid.glb")
        final_glb_path = os.path.join(work_dir, "final.glb")

        # 1. Download from S3
        print(f"Downloading {asset.original_path}...")
        broadcast_status(str(asset.owner_id), asset_id, "PROCESSING",
                         {"message": "Downloading model from storage..."})
        s3.download_file(BUCKET_NAME, asset.original_path, local_input_path)

        # Handle ZIP extraction
        target_model_path = local_input_path
        blender_cwd = work_dir

        if local_input_path.lower().endswith('.zip'):
            print("Detected ZIP file. Extracting...")
            broadcast_status(str(asset.owner_id), asset_id, "PROCESSING",
                             {"message": "Extracting archive contents..."})
            import zipfile

            extract_dir = os.path.join(work_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(local_input_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)

            found_file = find_main_model_file(extract_dir)

            if not found_file:
                inner_zips = []
                for root, dirs, files in os.walk(extract_dir):
                    for f in files:
                        if f.lower().endswith('.zip'):
                            inner_zips.append(os.path.join(root, f))
                if inner_zips:
                    largest_zip = max(inner_zips, key=os.path.getsize)
                    try:
                        with zipfile.ZipFile(largest_zip, 'r') as z_inner:
                            z_inner.extractall(os.path.dirname(largest_zip))
                        found_file = find_main_model_file(extract_dir)
                    except Exception as e:
                        print(f"Failed to extract inner zip: {e}")

            if not found_file:
                raise Exception("No valid 3D model found in ZIP")

            target_model_path = found_file
            blender_cwd = os.path.dirname(found_file)

        # 2. Blender Processing
        print("Running Blender...")
        broadcast_status(str(asset.owner_id), asset_id, "PROCESSING",
                         {"message": "Optimizing geometry and generating textures..."})

        blender_cmd = [
            "blender", "-b",
            "-P", "/app/service-3d-worker/process_model.py",
            "--",
            "--input", target_model_path,
            "--output", mid_glb_path,
            "--sliceable", str(asset.is_sliceable),
            "--id", str(asset.id)
        ]

        # Add object extraction if a specific object is requested
        if object_name:
            blender_cmd += ["--extract-object", object_name]

        result = subprocess.run(blender_cmd, capture_output=True, text=True, cwd=blender_cwd)

        print("--- BLENDER STDOUT ---")
        print(result.stdout)
        print("--- BLENDER STDERR ---")
        print(result.stderr)

        if result.returncode != 0:
            if "VALIDATION_FAILED" in result.stdout:
                try:
                    lines = result.stdout.splitlines()
                    for i, line in enumerate(lines):
                        if "VALIDATION_FAILED" in line:
                            error_json = lines[i+1]
                            errors = json.loads(error_json)
                            raise Exception(f"Validation Failed: {', '.join(errors)}")
                except ValueError:
                    pass
            raise Exception(f"Blender Failed: {result.stderr}")

        # 3. Copy to final
        shutil.copy(mid_glb_path, final_glb_path)

        # 4. Upload Result
        broadcast_status(str(asset.owner_id), asset_id, "PROCESSING",
                         {"message": "Uploading optimized model to storage..."})
        processed_key = f"processed/{asset_id}.glb"
        s3.upload_file(final_glb_path, BUCKET_NAME, processed_key)

        # 5. Update DB
        asset.status = AssetStatus.COMPLETED
        asset.processed_path = processed_key
        asset.metadata_json = {
            "processing_time": "TODO",
            "interaction_type": "sliceable" if asset.is_sliceable else "static",
            "original_file": asset.filename,
            "extracted_object": object_name
        }
        db.commit()

        broadcast_status(str(asset.owner_id), asset_id, "COMPLETED", {
            "processed_url": processed_key,
            "message": "Optimization and baking finished successfully!"
        })

        shutil.rmtree(work_dir)
        return "Success"

    except Exception as e:
        print(f"Task Failed: {e}")
        asset.status = AssetStatus.FAILED
        asset.metadata_json = {"error": str(e)}
        db.commit()

        broadcast_status(str(asset.owner_id), asset_id, "FAILED", {"error": str(e)})

        if os.path.exists(f"/tmp/{asset_id}"):
            shutil.rmtree(f"/tmp/{asset_id}")
        return f"Failed: {e}"
    finally:
        db.close()
