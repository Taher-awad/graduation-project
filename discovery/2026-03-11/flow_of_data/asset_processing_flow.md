# 3D Asset Processing Pipeline Data Flow

This diagram illustrates the complex data flow and branching logic of the background 3D processing worker, specifically detailing how the system reacts to the `is_sliceable` parameter and potential Zip bombs.

```mermaid
graph TD
    A[Teacher Uploads 3D File via Web] --> B[API Gateway]
    B --> C[Asset Microservice]
    
    C --> D{Magic Byte File Validation}
    D -- Invalid/Spoofed File --> E[Return HTTP 400 Bad Request]
    D -- Valid Format --> F[Upload file stream to MinIO Storage]
    
    F --> G[Insert Asset Pending record into DB]
    G --> H[Enqueue Job in Redis Broker with client_id]
    H --> I[Return HTTP 202 Accepted + SSE Sub ID]
    
    I -.-> |Asynchronous| J[3D Worker Celery pops Job]
    J --> K[Download File from MinIO to /tmp local]
    K --> L{Is it a .ZIP archive?}
    
    L -- Yes --> M[Start Zip Extraction]
    M --> N{Uncompressed Size > 2GB limits?}
    N -- Yes --> O[ABORT: Potential Zip Bomb]
    N -- No --> P[Find root model file in extracted folder]
    P --> Q[Set Blender Input Path]
    
    L -- No --> Q
    O -.-> ERROR_STATE
    
    Q --> R[Execute Headless Blender Python Script]
    R --> S[Normalize transforms and origins]
    S --> T{is_sliceable == True?}
    
    T -- Yes --> U[BMesh Watertight Check]
    U --> V{Is Manifold?}
    V -- No --> W[ABORT: Mesh cannot be sliced]
    W -.-> ERROR_STATE
    V -- Yes --> X[Generate basic Convex Hull Collider]
    X --> Y[Retain Uncompressed Geometry for Unity]
    
    T -- No --> Z[Apply high-fidelity CoACD collision]
    Z --> AA[Decimate polygons & apply Meshopt compression]
    
    Y --> AB[Texture Baking: Enforce 2048x2048 Limit]
    AA --> AB
    
    AB --> AC[Export Final .GLB File]
    
    AC --> AD[Upload processed .GLB to MinIO]
    AD --> AE[Update DB Status: COMPLETED]
    AE --> AF[Publish 'Success' to Redis PubSub]
    
    ERROR_STATE[Log Error] -.-> AG[Update DB Status: FAILED]
    AG -.-> AH[Publish 'Error Message' to Redis PubSub]
    
    AF -.-> |SSE Notify Viewer| AI((Frontend UI Completes))
    AH -.-> |SSE Notify Viewer| AI
```
