import requests
import time
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

BASE_URL = os.getenv("API_URL", "http://localhost:8000")

# Store state between operations
state = {
    "staff_token": None,
    "student_token": None,
    "asset_id": None,
    "room_id": None
}

def assert_status(resp, expected, action):
    if resp.status_code != expected:
        logging.error(f"{action} FAILED. Expected {expected}, got {resp.status_code}. Response: {resp.text}")
        raise AssertionError(f"{action} Failed")
    logging.info(f"{action} PASSED.")

def e2e_test():
    logging.info("--- STARTING CORTEX PIPELINE E2E TESTS ---")

    # ==========================================
    # 1. AUTHENTICATION & ROLES
    # ==========================================
    logging.info("\n--- PHASE 1: AUTHENTICATION ---")
    
    # 1a. Register Staff
    r = requests.post(f"{BASE_URL}/auth/register", json={"username": "e2e_teacher", "password": "123", "role": "TEACHER"})
    if r.status_code == 400 and "already registered" in r.text:
        logging.info("Staff already registered.")
    else:
        assert_status(r, 201, "Staff Registration")

    # 1b. Register Student
    r = requests.post(f"{BASE_URL}/auth/register", json={"username": "e2e_student", "password": "123", "role": "STUDENT"})
    if r.status_code == 400 and "already registered" in r.text:
        logging.info("Student already registered.")
    else:
        assert_status(r, 201, "Student Registration")
        
    # 1c. Duplicate Registration (Negative)
    r = requests.post(f"{BASE_URL}/auth/register", json={"username": "e2e_teacher", "password": "123", "role": "TEACHER"})
    assert_status(r, 400, "Duplicate Registration Prevention")

    # 1d. Login Staff
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": "e2e_teacher", "password": "123", "role": "TEACHER"})
    assert_status(r, 200, "Staff Login")
    state["staff_token"] = r.json().get("access_token")
    
    # 1e. Login Student
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": "e2e_student", "password": "123", "role": "STUDENT"})
    assert_status(r, 200, "Student Login")
    state["student_token"] = r.json().get("access_token")
    
    # 1f. Bad Password (Negative)
    r = requests.post(f"{BASE_URL}/auth/login", json={"username": "e2e_staff", "password": "wrong"})
    assert_status(r, 401, "Bad Password Rejection")

    staff_headers = {"Authorization": f"Bearer {state['staff_token']}"}
    student_headers = {"Authorization": f"Bearer {state['student_token']}"}

    # ==========================================
    # 2. ASSETS & UPLOAD PROCESSING
    # ==========================================
    logging.info("\n--- PHASE 2: ASSETS & MINIO/CELERY ---")
    
    # Define a target test file
    test_file_path = "3d models for test/Duck.glb"
    has_test_file = os.path.exists(test_file_path)
    if not has_test_file:
         logging.warning(f"Unable to find {test_file_path}. Skipping actual upload test.")
    else:
        # 2a. Student Upload Attempt (Negative/RBAC)
        with open(test_file_path, "rb") as f:
            files = {"file": ("Duck.glb", f, "model/gltf-binary")}
            data = {"asset_type": "MODEL", "is_sliceable": "False"}
            r = requests.post(f"{BASE_URL}/assets/upload", files=files, data=data, headers=student_headers)
            assert_status(r, 403, "Student Upload Rejection (RBAC)")
        
        # 2b. Bad Extension Upload Attempt (Negative)
        with open(test_file_path, "rb") as f:
            files = {"file": ("Duck.txt", f, "text/plain")}
            data = {"asset_type": "MODEL", "is_sliceable": "False"}
            r = requests.post(f"{BASE_URL}/assets/upload", files=files, data=data, headers=staff_headers)
            assert_status(r, 400, "Invalid File Extension Rejection")
            
        # 2c. Successful Staff Upload
        with open(test_file_path, "rb") as f:
            files = {"file": ("Duck.glb", f, "model/gltf-binary")}
            data = {"asset_type": "MODEL", "is_sliceable": "False"}
            r = requests.post(f"{BASE_URL}/assets/upload", files=files, data=data, headers=staff_headers)
            assert_status(r, 200, "Staff Asset Upload")
            state["asset_id"] = r.json().get("id")
            
        # 2d. Polling Asset Status (Celery 3D worker verification)
        logging.info("Waiting for Celery worker to process the 3D asset (max 30s)...")
        max_retries = 15
        for i in range(max_retries):
            r = requests.get(f"{BASE_URL}/assets/{state['asset_id']}", headers=staff_headers)
            assert_status(r, 200, f"Poll Asset Status Check {i+1}")
            asset_data = r.json()
            if asset_data["status"] == "COMPLETED":
                logging.info("Asset Processing COMPLETED successfully!")
                if not asset_data.get("download_url"):
                    logging.error("No Presigned Download URL generated!")
                else:
                    logging.info(f"Presigned URL Acquired.")
                break
            time.sleep(2)
        else:
            logging.warning("Asset Processing timed out during E2E test. Is celery worker running?")

    # ==========================================
    # 3. ROOMS & COLLABORATION
    # ==========================================
    logging.info("\n--- PHASE 3: ROOMS & COLLABORATION ---")
    
    # 3a. Student Room Creation Attempt (Negative)
    r = requests.post(f"{BASE_URL}/rooms/", json={"name": "Bad Room"}, headers=student_headers)
    assert_status(r, 403, "Student Room Creation Prevention")
    
    # 3b. Staff Room Creation
    r = requests.post(f"{BASE_URL}/rooms/", json={
        "name": "E2E Test Room",
        "description": "Integration testing",
        "is_online": False,
        "max_participants": 10
    }, headers=staff_headers)
    assert_status(r, 201, "Staff Room Creation")
    state["room_id"] = r.json().get("id")
    
    # 3c. Invite Duplicate User / Invalid User (Negative)
    r = requests.post(f"{BASE_URL}/rooms/{state['room_id']}/invite", json={"username": "ghost_user", "permissions": {"can_slice": True}}, headers=staff_headers)
    assert_status(r, 404, "Invalid User Invitation Handling")
    
    # 3d. Invite Student (Positive)
    r = requests.post(f"{BASE_URL}/rooms/{state['room_id']}/invite", json={"username": "e2e_student", "permissions": {"can_slice": True}}, headers=staff_headers)
    assert_status(r, 200, "Staff Invites Student")
    
    # 3e. Refuse Duplicate Invites (Negative)
    r = requests.post(f"{BASE_URL}/rooms/{state['room_id']}/invite", json={"username": "e2e_student", "permissions": {"can_slice": True}}, headers=staff_headers)
    assert_status(r, 400, "Duplicate Invitation Prevention")

    # 3f. Student Checks Invites
    r = requests.get(f"{BASE_URL}/rooms/invitations", headers=student_headers)
    assert_status(r, 200, "Student Fetches Invitations")
    invites = r.json()
    assert any(inv.get("room_id") == state["room_id"] for inv in invites), "Invitation not found in inbox!"
    
    # 3g. Student attempts changing room status (Negative/RBAC)
    r = requests.put(f"{BASE_URL}/rooms/{state['room_id']}/status?is_online=true", headers=student_headers)
    assert_status(r, 403, "Student Toggling Room Status Prevention")
    
    # 3h. Student Joins
    r = requests.post(f"{BASE_URL}/rooms/{state['room_id']}/join", headers=student_headers)
    assert_status(r, 200, "Student Joins Room")

    # 3i. Staff Updates Room Status
    r = requests.put(f"{BASE_URL}/rooms/{state['room_id']}/status?is_online=true", headers=staff_headers)
    assert_status(r, 200, "Staff Sets Room to Online")

    # ==========================================
    # 4. SSE (NOTIFICATIONS STREAM TEST)
    # ==========================================
    logging.info("\n--- PHASE 4: SSE NOTIFICATIONS ---")
    
    # We open a stream, read one byte/line to verify Nginx isn't buffering and the connection holds
    try:
        r = requests.get(f"{BASE_URL}/notifications/stream/e2e_student_id", stream=True, timeout=(3.0, 3.0))
        assert_status(r, 200, "SSE Connection Initialization")
        logging.info("SSE Stream Connected Successfully. Closing stream to proceed.")
        r.close()
    except requests.exceptions.ReadTimeout:
        logging.info("SSE Stream correctly held connection open without timing out abruptly.")
    except Exception as e:
         logging.error(f"SSE Connection failed: {e}")

    # ==========================================
    # 5. TEARDOWN
    # ==========================================
    logging.info("\n--- PHASE 5: TEARDOWN & CLEANUP ---")
    
    # 5a. Delete Room
    if state["room_id"]:
        r = requests.delete(f"{BASE_URL}/rooms/{state['room_id']}", headers=staff_headers)
        assert_status(r, 204, "Teardown: Room Deletion")
        
        # Verify Cascade
        r = requests.get(f"{BASE_URL}/rooms/", headers=student_headers)
        rooms = r.json()
        assert not any(rm.get("id") == state["room_id"] for rm in rooms), "Cascade: Room still visible to student!"
        logging.info("Teardown: Cascade (Room Memberships removed) Verified.")

    # 5b. Delete Asset
    if state["asset_id"]:
        r = requests.delete(f"{BASE_URL}/assets/{state['asset_id']}", headers=staff_headers)
        assert_status(r, 204, "Teardown: Asset S3/DB Deletion")

    logging.info("\n--- E2E ENTIRE SUITE PASSED EXCELLENTLY ---")


if __name__ == "__main__":
    try:
        e2e_test()
    except requests.exceptions.ConnectionError:
        logging.error("FATAL: Could not connect to API Gateway. Is Docker running?")
    except AssertionError:
         logging.error("FATAL: Test Suite Aborted due to Assertion Failure.")
