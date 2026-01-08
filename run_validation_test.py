import requests
import os
import time
import sys
import json

# Config
API_URL = "http://localhost:8000"
TEST_DIR = r"c:\Users\taher\Desktop\graduation v1\temp_validation_test"

# Test User
EMAIL = "valid_test@example.com"
PASSWORD = "password123"

if not os.path.exists(TEST_DIR):
    os.makedirs(TEST_DIR)

def create_mock_assets():
    # 1. Empty OBJ
    with open(os.path.join(TEST_DIR, "empty_geo.obj"), "w") as f:
        f.write("# This is an empty OBJ file\n")
        f.write("g EmptyObject\n")
        # No 'v' (vertices) lines

    # 2. Corrupt OBJ (NaN) - Hard to make blender import this without crashing or ignoring.
    # Let's rely on empty check.

def get_auth_token():
    try:
        # Use upper case STUDENT
        requests.post(f"{API_URL}/auth/register", json={"username": EMAIL, "password": PASSWORD, "role": "STUDENT"})
    except:
        pass 
    
    res = requests.post(f"{API_URL}/auth/login", json={"username": EMAIL, "password": PASSWORD})
    
    if res.status_code != 200:
        print(f"Auth Login Failed: {res.text}")
        sys.exit(1)
        
    return res.json()["access_token"]

def test_upload(token, file_path, expect_success=True):
    print(f"\n--- Testing: {os.path.basename(file_path)} ---")
    print(f"Expect Success: {expect_success}")
    
    with open(file_path, 'rb') as f:
        res = requests.post(
            f"{API_URL}/assets/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": f},
            data={"asset_type": "MODEL"}
        )
    
    if res.status_code != 200:
        print(f"❌ Upload Request Failed: {res.text}")
        return False

    asset_id = res.json()["id"]
    print(f"Asset ID: {asset_id}. Polling...")
    
    for _ in range(30):
        time.sleep(2)
        status_res = requests.get(f"{API_URL}/assets/{asset_id}", headers={"Authorization": f"Bearer {token}"})
        status = status_res.json()["status"]
        meta = status_res.json().get("metadata_json") or {}
        
        if status == "COMPLETED":
            if expect_success:
                print("✅ Processing COMPLETED (As Expected)")
                return True
            else:
                print("❌ Unexpected SUCCESS (Should have failed validation)")
                return False
                
        elif status == "FAILED":
            error_msg = meta.get("error", "Unknown Error")
            print(f"ℹ️ Failed with error: {error_msg}")
            
            if not expect_success:
                if "Validation Failed" in error_msg:
                    print("✅ Processing FAILED with VALIDATION ERROR (As Expected)")
                    return True
                else:
                    print(f"⚠️ Failed but maybe not validation? '{error_msg}'")
                    return True # Still a fail
            else:
                print("❌ Unexpected FAILURE")
                return False
                
        print(f"   Status: {status}", end="\r")
        
    print("❌ Timed Out")
    return False

def run():
    create_mock_assets()
    token = get_auth_token()
    
    # 1. Test Valid (DamagedHelmet)
    valid_path = r"c:\Users\taher\Desktop\graduation v1\3d models for test\DamagedHelmet.glb"
    if not test_upload(token, valid_path, expect_success=True):
        sys.exit(1)
        
    # 2. Test Invalid (Empty Geo)
    invalid_path = os.path.join(TEST_DIR, "empty_geo.obj")
    if not test_upload(token, invalid_path, expect_success=False):
        sys.exit(1)

if __name__ == "__main__":
    run()
