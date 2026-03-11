# Project Overview: Intelligent 3D Asset Pipeline for VR Learning Platform

## 1. High-Level Vision
This project backend serves a **Multi-player VR Learning Platform** (often referred to as EduVR). The platform is designed to democratize virtual education by providing immersive, interactive virtual classrooms.

### Roles and Workflow
- **Teachers (Staff):** Access a web dashboard to create "Rooms". They upload custom learning materials into the system, including arbitrary 3D models (FBX, OBJ, STL, GLB, ZIP), PDF slides, and videos. Teachers can enter these rooms in VR to arrange the educational objects (e.g., placing anatomy models on desks).
- **Students:** Are invited to these VR rooms to participate in interactive lessons.
- **AI Tutor:** Uploaded slides are intended to be processed by an AI RAG (Retrieval-Augmented Generation) system to power a virtual AI Tutor capable of answering student questions in the room.

## 2. Core Purpose of the Current Pipeline
The specific codebase (Cortex AI 3D Pipeline) is the **backend infrastructure** responsible for automating the ingestion, standardizing, processing, and optimization of 3D content for the VR platform. 

Since VR environments require highly optimized assets to maintain framerates and prevent motion sickness, this pipeline acts as an asynchronous bridge transforming heavy, arbitrary 3D files into lightweight, "VR-Ready" `.glb` (glTF 2.0) assets.

## 3. The "Sliceable" Business Logic
A fundamental feature of the VR learning platform is that objects behave differently based on their educational context. For instance, an anatomy model of a heart should be *sliceable* in VR to see inside, whereas a static classroom desk should not.

During upload, the teacher dictates an `is_sliceable` boolean flag. This single flag dictates the entire backend processing path:

### Path A: Static / Prop (`is_sliceable = FALSE`)
- **Use Case:** Furniture, statues, background environment items.
- **Optimization:** Aggressive polygon simplification (~50k target).
- **Physics:** High-fidelity CoACD collision generation (handles concave shapes).
- **Compression:** Uses *Meshopt* (geometry) and *KTX2* (textures) to ensure ultra-fast GPU loading without CPU bottlenecking. 

### Path B: Interactable / Educational (`is_sliceable = TRUE`)
- **Use Case:** Biological organs, clay, soft interactive materials.
- **Optimization:** Conservative simplification (~75k+ target) to preserve edge loops required for clean 3D slices.
- **Physics:** Generates a basic Convex Hull (which is destroyed and regenerated dynamically in Unity after a slice occurs).
- **Compression:** **NO geometry compression is applied.** This is a critical requirement. Slicing runtime scripts in Unity require immediate access to readable mesh vertices. Decompressing geometry at runtime causes non-readable mesh errors and breaks the slicing mathematics.

## 4. Technical Integration
Once the asset is processed by the headless Blender Celery worker, it is uploaded to MinIO. The generated `.glb` file embeds the `is_sliceable` status straight into its JSON metadata (e.g., `"interaction_type": "sliceable"`). 

When the VR Client (Unity + glTFast) downloads the asset, it reads this metadata. If it is sliceable, Unity ensures the mesh data is kept readable in memory and automatically attaches the necessary `Sliceable.cs` and `Grabbable.cs` scripts to the object, completing the seamless pipeline from a teacher's web browser straight into the student's VR hands.

## 5. Why It Is Useful

This architecture solves several major bottlenecks in VR education:
1. **Content Agnosticism:** Teachers do not need to be 3D artists. They can download standard models from anywhere (e.g., Sketchfab) and upload them directly. The pipeline handles the complex math of making them work in VR.
2. **Performance Safety:** In VR, dropping below 72/90 FPS causes immediate motion sickness. Unoptimized 3D models are the primary cause of frame drops. The automated simplification and Meshopt compression protect users from poorly optimized teacher uploads.
3. **Dynamic Interaction:** The `is_sliceable` toggle allows identical models to be treated dynamically in a single room. A teacher can have a static "display" heart (highly compressed) and an interactable "surgical" heart (uncompressed geometry for real-time slicing calculation).
4. **Scalable Asynchronous Design:** Using Celery + Redis ensures the main API never blocks while a heavy 100MB `.blend` file is being processed. It can handle concurrent uploads efficiently.

## 6. Areas for Improvement

1. **Error Handling & Feedback:** If Blender fails (e.g., corrupted ZIP), the `warnings.log` and Redis queues catch it, but the frontend needs a WebSocket or Server-Sent Events (SSE) connection to provide real-time visual feedback to the teacher rather than polling.
2. **Advanced Mesh Analysis:** The pipeline currently relies blindly on the teacher's `is_sliceable` toggle. It could be upgraded to automatically detect if a mesh *can* be sliced (e.g., checking if it comprises a single manifold, watertight mesh vs. 100 disjointed floating vertices).
3. **Texture Baking:** The pipeline leaves PBR materials intact, but heavy texture setups (8K resolutions) could be further baked down or automatically atlased by Blender before export to save GPU VRAM on standalone mobile headsets like Meta Quest.
4. **Security & Validation:** While MinIO and FastAPI handle the payloads, deeper malicious payload scanning inside ZIP files before Blender attempts to open them would prevent exploit vectors targeting the headless 3D engine.

## 7. System Requirements

### Backend / Server (Docker Environment)
- **OS:** Linux-based OS recommended (Ubuntu 22.04 LTS+) for optimal Docker performance.
- **CPU:** Minimum 4 Cores (8+ Recommended for parallel Celery processing). Blender tasks are CPU-bound without GPU acceleration configured.
- **RAM:** Minimum 8GB (16GB+ Recommended). Extracting and optimizing Large 3D models can cause massive, short-term memory spikes.
- **Storage:** NVMe SSDs recommended for MinIO speed. Minimum 50GB allocated for the `minio_data` and `postgres_data` persistent volumes.
- **Dependencies:** Docker Desktop / Docker Compose v2.

### Frontend (Web Dashboard)
- **Environment:** Node.js v20+ with `npm` or `yarn`.
- **Browser:** Modern Chromium, Firefox, or Safari (Requires WebGL support for `@react-three/fiber` previews).

### Client (VR Application)
- **Engine:** Unity 2022.3 LTS or newer.
- **Key Packages:** `glTFast` (configured to support `EXT_meshopt_compression` and `KHR_texture_basisu`).
- **Hardware:** Standalone VR Headsets (Meta Quest 2 / 3 / Pro) or PCVR.
