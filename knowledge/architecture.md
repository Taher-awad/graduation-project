# EduVR System Architecture

## High-Level Architecture
The EduVR platform is built on a modular and scalable architecture designed to support real-time VR multiplayer interactions, web interfaces, and AI services.

The system is broadly divided into:
1. **User Interfaces**: Unity VR Client & Web Visualization Interface.
2. **Central Backend**: Handles authentication, session management, and cross-platform communication.
3. **EduVR Core (AI Service)**: Manages RAG-based intelligence and content processing.
4. **Data Storage**: Stores user data, assets, and learning materials.

## Key Subsystems

### 1. Collaboration Room Manager
- Orchestrates multi-user sessions.
- Generates unique Session IDs consumed by the **Photon Fusion** networking engine.
- Allows instructors to create virtual classrooms and manage student access via an invitation system.
- Controls room states natively (Online/Offline).

### 2. Automated 3D Asset Processor
- Pipeline built using **Celery** and **Headless Blender**.
- Automatically ingests raw uploaded 3D files (GLB, FBX, ZIP).
- Performs geometry validation, texture link repairs, transparency artifact fixes, and mesh optimization.
- Ensures assets perform optimally on both Web (Three.js) and VR (Unity Meta Quest target) clients.

### 3. Asset Management System
- A web interface allowing staff to upload, organize, and manage 3D content.
- Enforces strict **Role-Based Access Control (RBAC)** to ensure only authorized personnel can manipulate learning assets.

### 4. RAG-Powered AI Tutor (EduVR Core)
- Implements a Retrieval-Augmented Generation (RAG) approach (likely via LangChain as per references).
- Processes user queries by retrieving validated educational material prior to generating answers, preventing AI hallucinations.
- Serves as the backbone for both text and voice-based interaction with students.

## Technology Stack (Inferred from Report)
- **VR Engine**: Unity
- **Networking/Multiplayer**: Photon Fusion 2
- **3D Processing Backend**: Python (Celery, Headless Blender)
- **AI/LLM Integration**: LangChain (RAG)
- **Web 3D Visualization**: Three.js
- **Model Standard**: glTF 2.0 / GLB
