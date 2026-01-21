import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from main import app
    import main
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    
    # Patch DB
    test_engine = create_engine("sqlite:///:memory:")
    main.engine = test_engine
    
    print("Import successful, patched engine")
    
    with TestClient(app) as client:
        print("Client created, startup complete")
        
        resp = client.post("/auth/register", json={"username": "debuguser", "password": "pwm", "role": "STUDENT"})
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.json()}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
