import requests
import os
import time
import sys

# Config
API_URL = "http://localhost:8000"
TEMP_ZIPS = r"c:\Users\taher\Desktop\graduation v1\temp_test_zips"
TEST_MODELS = r"c:\Users\taher\Desktop\graduation v1\3d models for test"

# Test User
EMAIL = "test_bot_v2@example.com"
PASSWORD = "password123"

def get_auth_token():
    # Register
    print("Registering...")
    # NOTE: UserCreate schema only has username, password, role
    reg_res = requests.post(f"{API_URL}/auth/register", json={"username": EMAIL, "password": PASSWORD, "role": "STUDENT"})
    print(f"Register status: {reg_res.status_code} {reg_res.text}")
    
    # Login
    print("Logging in...")
    res = requests.post(f"{API_URL}/auth/login", json={"username": EMAIL, "password": PASSWORD})
    
    if res.status_code != 200:
        print(f"Auth Failed: {res.text}")
        sys.exit(1)
    return res.json()["access_token"]

def upload_and_monitor(token, file_path, label):
    print(f"\n--- Testing: {label} ---")
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False

    file_name = os.path.basename(file_path)
    print(f"Uploading {file_name}...")
    
    with open(file_path, 'rb') as f:
        res = requests.post(
            f"{API_URL}/assets/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": f},
            data={"asset_type": "MODEL", "is_sliceable": "false"}
        )
    
    if res.status_code != 200:
        print(f"❌ Upload Failed: {res.text}")
        return False
    
    asset_id = res.json()["id"]
    print(f"Upload Success. Asset ID: {asset_id}. Waiting for processing...")
    
    # Poll
    for i in range(60): # Wait up to 60 seconds
        time.sleep(2)
        status_res = requests.get(f"{API_URL}/assets/{asset_id}", headers={"Authorization": f"Bearer {token}"})
        status = status_res.json()["status"]
        if status == "COMPLETED":
            print("✅ Processing COMPLETED")
            return True
        elif status == "FAILED":
            err = status_res.json().get("metadata_json", {})
            print(f"❌ Processing FAILED: {err}")
            return False
        
        print(f"   Status: {status}...", end="\r")
        
    print("❌ Timed Out")
    return False

def run():
    token = get_auth_token()
    print("Authenticated.")
    
    tests = [
        # (File Path, Label)
        (os.path.join(TEST_MODELS, "packed_cannon.blend"), "Single Packed .blend"),
        (os.path.join(TEMP_ZIPS, "cannon_01_4k.blend.zip"), "Zip: Split .blend + Textures"),
        (os.path.join(TEMP_ZIPS, "realistic_tree.zip"), "Zip: Split .gltf + Textures"),
        (os.path.join(TEMP_ZIPS, "rainier-ak-3d.zip"), "Zip: Nested Folder (.fbx/obj?)"),
        (os.path.join(TEST_MODELS, "DamagedHelmet.glb"), "Single .glb")
    ]
    
    results = []
    for path, label in tests:
        success = upload_and_monitor(token, path, label)
        results.append((label, success))
        
    print("\n\n=== SUMMARY ===")
    all_pass = True
    for label, success in results:
        icon = "✅" if success else "❌"
        print(f"{icon} {label}")
        if not success: all_pass = False
        
    if not all_pass:
        sys.exit(1)

if __name__ == "__main__":
    run()
