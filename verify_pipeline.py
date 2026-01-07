import requests
import time
import sys
import os
import mimetypes

BASE_URL = "http://localhost:8000"
USERNAME = "taher"
PASSWORD = "123"

def login():
    print(f"\n[Auth] Logging in as {USERNAME}...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={"username": USERNAME, "password": PASSWORD})
        resp.raise_for_status()
        token = resp.json()["access_token"]
        print("      Success! Token received.")
        return token
    except Exception as e:
        print(f"!!! Login Failed: {e}")
        try: print(resp.json())
        except: pass
        sys.exit(1)

def verify_asset(filename, token):
    if not os.path.exists(filename):
        print(f"!!! File not found: {filename}")
        return False

    print(f"\n--- Verifying {filename} ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Detect Mime (fallback for blend)
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = "application/octet-stream"
    
    # Upload
    print(f"    Uploading...")
    with open(filename, "rb") as f:
        files = {"file": (filename, f, mime_type)}
        data = {"is_sliceable": "true"}
        
        try:
            resp = requests.post(f"{BASE_URL}/assets/upload", headers=headers, files=files, data=data)
            resp.raise_for_status()
            asset_id = resp.json()["id"]
            status = resp.json()["status"]
            print(f"    Success! Asset ID: {asset_id}, Initial Status: {status}")
        except Exception as e:
            print(f"!!! Upload Failed: {e}")
            try: print(resp.json())
            except: pass
            return False

    # Poll
    print(f"    Polling for completion...")
    for i in range(45): # Wait up to 90 seconds (Blender can be slow)
        try:
            resp = requests.get(f"{BASE_URL}/assets/{asset_id}", headers=headers)
            resp.raise_for_status()
            current_status = resp.json()["status"]
            
            if current_status != "PENDING" and current_status != "PROCESSING":
                 print(f"    Attempt {i+1}: Status = {current_status}")

            if current_status == "COMPLETED":
                print("    Processing Complete!")
                download_url = resp.json().get("download_url")
                print(f"    Download URL: {download_url}")
                
                # Download File for validation
                try:
                    # Fix URL for localhost access (Docker returns internal hostname)
                    host_url = download_url.replace("http://minio:9000", "http://127.0.0.1:9000")
                    print(f"    DEBUG: Downloading from {host_url}")
                    dl_resp = requests.get(host_url, headers={"Host": "minio:9000"})
                    dl_resp.raise_for_status()
                    out_name = f"verified_{os.path.basename(filename)}.glb"
                    with open(out_name, "wb") as f_out:
                        f_out.write(dl_resp.content)
                    print(f"    Saved downloaded asset to: {out_name}")
                except Exception as dl_err:
                    print(f"    !!! Failed to download file for validation: {dl_err}")

                return True
            
            if current_status == "FAILED":
                 metadata = resp.json().get("metadata")
                 print(f"!!! Processing FAILED. Metadata: {metadata}")
                 return False
                 
        except Exception as e:
             print(f"!!! Polling Error: {e}")
             
        time.sleep(2)
    else:
        print("!!! Timeout waiting for processing.")
        return False

def run_tests():
    print("=== Starting Multi-Asset E2E Verification ===")
    token = login()
    
    assets = [
        "3d models for test/Duck.glb", 
        "3d models for test/TREE/TREE.fbx", 
        "3d models for test/packed_cannon.blend"
    ]
    results = {}
    
    for asset in assets:
        results[asset] = verify_asset(asset, token)
        
    print("\n=== Final Results ===")
    success_count = 0
    for asset, result in results.items():
        status = "PASS" if result else "FAIL"
        if result: success_count += 1
        print(f"{asset}: {status}")

    if success_count == len(assets):
        print("\nAll assets passed!")
    else:
        print(f"\n{len(assets) - success_count} assets failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
