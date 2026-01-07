# **Project Master Specification: Intelligent 3D Asset Pipeline for VR Learning Platform**

## **1\. Abstract: The Full Vision**

The larger ecosystem is a **Multi-player VR Learning Platform** designed to democratize virtual education.

* **Workflow:** Teachers access a web dashboard to create "Rooms" based on templates. They populate these rooms with custom data: 3D models, PDF slides, and videos.  
* **AI Integration:** Uploaded slides are processed by an AI RAG system to power an "AI Tutor" capable of answering student questions in the absence of a teacher.  
* **VR Experience:** Teachers can enter the room in VR to arrange objects (using tools like Grabbable, Resizable) before inviting students.  
* **Runtime Logic:** Objects act differently based on their type (e.g., an anatomy heart can be sliced, a desk cannot).

**Current Focus:** This document details the implementation of the **backend infrastructure** responsible for ingesting, standardizing, and optimizing the 3D content for this platform.

## **2\. Core Objective (The Pipeline)**

To build an asynchronous backend bridge that transforms arbitrary user-uploaded 3D files (FBX, OBJ, STL) into "VR-Ready" assets. The system ensures that all content streaming into a multi-player session is performance-safe, standardized, and tagged with correct interaction properties (specifically slicing capability).

## **3\. Functional Requirements**

### **A. Ingestion & Database**

* **Upload Handling:** Accept standard 3D formats (.fbx, .obj, .stl, .glb).  
* **Database Schema:** The database record for each asset must store a critical boolean flag: is\_sliceable.  
  * This value is set by the user during upload on the web dashboard.  
  * It determines which processing path the worker takes.  
  * It dictates which script the VR client attaches at runtime.  
* **Job Queueing:** Immediately offload processing to a background worker to prevent API blocking.

### **B. The Processing Core (The Worker)**

The worker acts on the is\_sliceable flag retrieved from the DB/Job. **Optimization is strictly aligned with glTFast capabilities.**

#### **Path A: Static/Prop (is\_sliceable \= FALSE)**

* *Examples:* Furniture, Statues, Walls, Background items.  
* **Optimization:** Aggressive mesh simplification (Target: \~50k polys).  
* **Physics:** High-fidelity **CoACD** collision generation (supports hollow concave shapes like cups or rooms).  
* **Compression (glTFast Optimized):**  
  * **Geometry:** Use **Meshopt (EXT\_meshopt\_compression)** via gltfpack \-c. This is preferred over Draco for VR as it has significantly faster decode times, preventing frame-drops during loading.  
  * **Textures:** Use **KTX2 (KHR\_texture\_basisu)** via gltfpack \-tc. This allows GPU direct loading without CPU decompression.  
  * **Instancing:** Enable GPU Instancing (EXT\_mesh\_gpu\_instancing) via gltfpack \-mi to optimize rendering if the scene contains duplicate meshes.  
* **Normalization:** Scale to 1m bounding box; Pivot at bottom-center (0, min\_Y, 0).

#### **Path B: Interactable (is\_sliceable \= TRUE)**

* *Examples:* Biological organs, Fruits, Clay, Soft materials.  
* **Optimization:** **Conservative simplification** (Target: \~75k+ polys) to preserve edge loops and manifold geometry needed for clean slicing.  
* **Physics:** Generates a basic **Convex Hull** (lighter weight, meant to be destroyed and regenerated dynamically in Unity after a slice).  
* **Compression:**  
  * **Geometry:** **NO COMPRESSION** (No Draco/Meshopt). This is critical. Slicing scripts require immediate access to the Mesh.vertices array. Decompressing geometry at runtime often results in "Non-Readable" mesh errors or complex vertex reordering that breaks slicing math.  
  * **Textures:** KTX2 is allowed and recommended.  
* **Normalization:** Scale to 1m bounding box; Pivot at center (better for holding in hand).

### **C. Delivery & Metadata**

* **Output:** Binary glTF (.glb) version 2.0.  
* **Metadata Injection:** The system must embed the database values into the .glb file's extras JSON field:  
  {  
    "id": "asset\_uuid",  
    "interaction\_type": "sliceable",  
    "original\_scale": \[1.0, 1.0, 1.0\]  
  }

### **D. Client Consumption (Unity \+ glTFast)**

To ensure the backend work functions correctly in Unity, the client must use specific glTFast settings:

* **For Static Objects:**  
  * Load with default settings. glTFast will leverage jobs to decode Meshopt/KTX2 in the background.  
* **For Sliceable Objects:**  
  * **Critical:** When calling Load(), use an ImportSettings object with codeHook or explicit flags to ensure the mesh remains **Readable**.  
  * By default, glTFast may discard CPU mesh data after upload to GPU. Slicing scripts will crash if they cannot read the mesh.

## **4\. Technical Architecture & Stack**

| Component | Technology | Role |
| :---- | :---- | :---- |
| **Orchestrator** | **FastAPI** | REST API for uploads, status checks, and serving metadata. |
| **Database** | **PostgreSQL** | Stores asset metadata, is\_sliceable status, and user ownership. |
| **Task Queue** | **Celery \+ Redis** | Manages the async processing pipeline. |
| **Worker Engine** | **Blender (Headless)** | The Python-scripted 3D engine handling import, transform, and export. |
| **Physics Tool** | **CoACD** | Generates complex collision meshes for static props. |
| **Optimizer** | **gltfpack** | **Crucial:** configured to output files strictly compatible with glTFast features (Meshopt, KTX2). |
| **Storage** | **MinIO (S3)** | Object storage for raw inputs and processed outputs. |
| **Client** | **Unity \+ GLTFast** | VR runtime loader. Supports EXT\_meshopt\_compression and KHR\_texture\_basisu. |

## **5\. Pipeline Logic Workflow**

1. **Teacher** uploads Heart.obj on dashboard, selects **"Allow Slicing"**.  
2. **FastAPI** creates DB entry: { filename: "Heart", is\_sliceable: true, status: "pending" }.  
3. **FastAPI** uploads file to MinIO and sends Job ID to **Redis**.  
4. **Celery Worker** picks up job:  
   * Checks is\_sliceable flag.  
   * **TRUE detected:**  
     * Launch Blender.  
     * Import Heart.obj.  
     * Scale to 1m, Center Pivot.  
     * **Skip** aggressive decimation (keep geometry clean).  
     * Export to .glb.  
     * Run gltfpack **without** \-c (Meshopt) or \-cc (Draco) flags. Use \-tc for KTX2.  
   * Updates DB status to "completed".  
5. **VR Client** (Teacher's Headset):  
   * Downloads model.  
   * Reads metadata interaction\_type: "sliceable".  
   * Attaches Grabbable.cs.  
   * Attaches Sliceable.cs (knowing mesh data is readable/uncompressed).  
   * Teacher cuts the heart in half. Success.