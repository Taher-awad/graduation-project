# 3D Asset Processor Security Strategy

## Approach: Payload Validation and Defensive Sandboxing

### Current Vulnerability
The background worker blindly extracts `.zip` files uploaded by users via Python's `zipfile.extractall()` and feeds arbitrary geometry descriptors to a headless Blender execution context. This opens the system to path traversal attacks (`../../`), "Zip Bombs", and potentially memory-corruption exploits in Blender's compiled C++ routines.

### Implementation Path
1. **Magic Byte File Verification (Asset Gateway):**
   - Do not trust the file extension provided by the frontend.
   - Use `python-magic` to read the raw headers of the uploaded file to ensure an `.fbx` is genuinely an Autodesk FBX, and a `.zip` is genuinely a Zip archive. Reject mismatches immediately before storing them in MinIO.
2. **Anti-Zip-Bomb Extraction (3D Worker):**
   - Replace `zipfile.extractall()` with a streaming constraint algorithm.
   - Track total extracted bytes during the loop. If the cumulative uncompressed byte size exceeds `2GB` (or an appropriate limit), abort the task, delete the partial contents, and flag the account.
3. **Path Traversal Protection (3D Worker):**
   - Ensure the filenames inside the archive do not contain relative path navigation (`../`).
   - Use `os.path.abspath()` checks to guarantee every extracted file roots inside the dedicated `/tmp/{asset_id}/` workspace folder.
4. **Firecracker MicroVMs (Future Production Only):**
   - Replace standard Docker containers for the Celery worker with AWS Firecracker instances.
   - Boot a lightweight (2GB RAM), heavily restricted Unix environment in literally milliseconds upon job enqueue. Execute Blender inside, export the `.glb`, and immediately destroy the VM to eliminate any possibility of a persistent rootkit or lateral movement via the backend database network.
