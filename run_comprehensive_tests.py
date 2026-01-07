import requests
import time
import os
import sys
import uuid
import struct
import json

# Configuration
BASE_URL = "http://localhost:8000"
TEST_ASSETS_DIR = "3d models for test"
ASSETS = {
    "glb": os.path.join(TEST_ASSETS_DIR, "Duck.glb"),
    "fbx": os.path.join(TEST_ASSETS_DIR, "TREE", "TREE.fbx"),
    "blend": os.path.join(TEST_ASSETS_DIR, "packed_cannon.blend")
}

# Colors
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def log(msg, type="info"):
    if type == "header": print(f"{Colors.HEADER}=== {msg} ==={Colors.ENDC}")
    elif type == "success": print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")
    elif type == "fail": print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")
    elif type == "warn": print(f"{Colors.WARNING}! {msg}{Colors.ENDC}")
    else: print(f"  {msg}")

class CortexTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.user_id = f"test_{uuid.uuid4().hex[:8]}"
        self.password = "secret123"
        self.uploaded_assets = {}

    def check_integrity(self, filepath):
        """Checks if GLB is valid and has NO KTX2 compression"""
        try:
            with open(filepath, 'rb') as f:
                magic = f.read(4)
                if magic != b'glTF': return False, "Not a GLB file"
                
                version = struct.unpack('<I', f.read(4))[0]
                _ = struct.unpack('<I', f.read(4))[0] # length

                # Chunk 0: JSON
                chunk_len = struct.unpack('<I', f.read(4))[0]
                chunk_type = f.read(4)
                if chunk_type != b'JSON': return False, "Invalid Chunk Type"
                
                json_bytes = f.read(chunk_len)
                data = json.loads(json_bytes.decode('utf-8'))
                
                required = data.get("extensionsRequired", [])
                if 'KHR_texture_basisu' in required:
                    return False, "Contains KHR_texture_basisu (KTX2) which breaks Unity default load"
                
                return True, "Valid"
        except Exception as e:
            return False, str(e)

    # --- Auth Tests ---
    def test_auth(self):
        log("Testing Authentication Module", "header")
        
        # 1. Register
        try:
            resp = self.session.post(f"{BASE_URL}/auth/register", json={"username": self.user_id, "password": self.password})
            if resp.status_code == 201: log("Register New User", "success")
            else: 
                log(f"Register Failed: {resp.text}", "fail")
                return False
        except Exception as e:
            log(f"Connection Failed: {e}", "fail")
            return False

        # 2. Duplicate Register
        resp = self.session.post(f"{BASE_URL}/auth/register", json={"username": self.user_id, "password": self.password})
        if resp.status_code == 400: log("Duplicate Registration Rejected", "success")
        else: log(f"Duplicate Registration Allowed? {resp.status_code}", "fail")

        # 3. Login
        resp = self.session.post(f"{BASE_URL}/auth/login", json={"username": self.user_id, "password": self.password})
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            log("Login Successful", "success")
        else:
            log("Login Failed", "fail")
            return False
            
        return True

    # --- API Tests ---
    def test_api(self):
        log("Testing API Module", "header")
        
        # 1. List Empty
        resp = self.session.get(f"{BASE_URL}/assets/")
        if resp.status_code == 200 and resp.json() == []: log("List Empty Assets", "success")
        else: log("List Assets Failed", "fail")

        # 2. 404 Check
        resp = self.session.get(f"{BASE_URL}/assets/{uuid.uuid4()}")
        if resp.status_code == 404: log("404 Validation", "success")
        else: log("404 Check Failed", "fail")
        
        # 3. Invalid File Upload
        dummy_file = "test.txt"
        with open(dummy_file, "w") as f: f.write("dummy")
        with open(dummy_file, "rb") as f:
            resp = self.session.post(
                f"{BASE_URL}/assets/upload",
                files={"file": (dummy_file, f, "text/plain")},
                data={"is_sliceable": "false"}
            )
        os.remove(dummy_file)
        
        if resp.status_code == 400: log("Invalid File Rejected", "success")
        else: log(f"Invalid File Allowed? Status: {resp.status_code}", "fail")
        
        return True

    # --- Pipeline Tests ---
    def test_pipeline(self):
        log("Testing Processing Pipeline & Integrity", "header")
        
        files_to_test = [
            ("Duck (GLB)", ASSETS["glb"], "true"),
            ("Tree (FBX)", ASSETS["fbx"], "false"), # Not sliceable
            ("Cannon (Blend)", ASSETS["blend"], "true")
        ]

        # 1. Upload All
        for name, path, sliceable in files_to_test:
            if not os.path.exists(path):
                log(f"Asset not found: {path}", "warn")
                continue
                
            with open(path, "rb") as f:
                resp = self.session.post(
                    f"{BASE_URL}/assets/upload",
                    files={"file": f},
                    data={"is_sliceable": sliceable}
                )
                if resp.status_code == 200:
                    asset_id = resp.json()["id"]
                    self.uploaded_assets[asset_id] = name
                    log(f"Uploaded {name} -> ID: {asset_id}", "success")
                else:
                    log(f"Failed to upload {name}", "fail")

        # 2. Poll All
        log("Polling for completion (Max 120s)...")
        completed = set()
        start = time.time()
        
        while len(completed) < len(self.uploaded_assets) and (time.time() - start) < 120:
            for aid, name in list(self.uploaded_assets.items()):
                if aid in completed: continue
                
                try:
                    r = self.session.get(f"{BASE_URL}/assets/{aid}")
                    status = r.json()["status"]
                    if status == "COMPLETED":
                        log(f"{name} Finished Processing", "success")
                        completed.add(aid)
                        
                        # 3. Verify Download & Integrity
                        dl_url = r.json().get("download_url")
                        if dl_url:
                            # Fix localhost
                            dl_url = dl_url.replace("http://minio:9000", "http://127.0.0.1:9000")
                            try:
                                # Host header forced for MinIO
                                file_resp = requests.get(dl_url, headers={"Host": "minio:9000"})
                                file_resp.raise_for_status()
                                
                                # Check Integrity
                                tmp_name = f"temp_check_{aid}.glb"
                                with open(tmp_name, "wb") as f_tmp:
                                    f_tmp.write(file_resp.content)
                                
                                is_valid, msg = self.check_integrity(tmp_name)
                                if is_valid: log(f"{name} Integrity Check Passed", "success")
                                else: log(f"{name} Integrity Failed: {msg}", "fail")
                                
                                os.remove(tmp_name)
                                
                            except Exception as e:
                                log(f"Download/Check Failed for {name}: {e}", "fail")
                    elif status == "FAILED":
                        log(f"{name} Processing FAILED: {r.json().get('metadata')}", "fail")
                        completed.add(aid) # Mark handled
                except:
                    pass
            time.sleep(2)
            
        if len(completed) == len(self.uploaded_assets):
            log("All assets processed.", "success")
        else:
            log("Timeout waiting for assets.", "fail")


if __name__ == "__main__":
    tester = CortexTester()
    if tester.test_auth():
        tester.test_api()
        tester.test_pipeline()
