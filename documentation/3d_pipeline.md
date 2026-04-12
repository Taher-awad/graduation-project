# EduVR – Cortex AI Platform: 3D Processing Pipeline

## Overview

The 3D processing pipeline converts raw uploaded 3D models (FBX, OBJ, BLEND, GLTF, STL, ZIP archives) into optimized, standardized GLB files ready for VR rendering in the browser via React Three Fiber.

---

## Pipeline Stages

```
Upload (FastAPI)
     │
     ▼
MinIO (raw/ storage)
     │
     ▼
Redis Queue (Celery task: worker.process_asset)
     │
     ▼
3D Worker Service
     │
     ├─ 1. Download from MinIO
     ├─ 2. Extract ZIP (+ nested ZIPs)
     ├─ 3. Find main model file
     │
     ▼
Blender (headless, -b flag)
     ├─ 4. Reset scene
     ├─ 5. Import model
     ├─ 6. Normalize geometry
     │   ├─ Bounding box calculation
     │   ├─ Root anchor creation
     │   ├─ Uniform scale (unit cube)
     │   ├─ Center positioning
     │   └─ Metadata injection
     ├─ 7. Texture relinking
     ├─ 8. Auto-connect textures (name matching)
     ├─ 9. Transparency fixing
     ├─ 10. Validation
     └─ 11. Export as GLB
     │
     ▼
Upload to MinIO (processed/ storage)
     │
     ▼
Database update (COMPLETED)
     │
     ▼
Redis Pub/Sub → SSE → Browser
```

---

## Stage Details

### Stage 1: Download from MinIO
- Downloads the raw uploaded file from `raw/{asset_id}.{ext}`
- Saves to `/tmp/{asset_id}/{original_filename}`

### Stage 2-3: ZIP Handling
- Detects ZIP files by extension
- Extracts into `/tmp/{asset_id}/extracted/`
- Searches for main model file by priority:
  - `.blend` → `.gltf` → `.fbx` → `.obj` → `.stl`
- **Nested ZIP support**: If no model found, searches inside inner ZIP files (e.g., Sketchfab downloads often have `source/model.zip`)
- Sets Blender CWD to the directory of the found model file (critical for relative texture paths like `./textures/wood.png`)

### Stage 4: Scene Reset
```python
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
```

### Stage 5: Model Import
Supports multiple formats:
| Extension | Blender Operator |
|---|---|
| `.fbx` | `bpy.ops.import_scene.fbx` |
| `.obj` | `bpy.ops.import_scene.obj` |
| `.stl` | `bpy.ops.import_mesh.stl` |
| `.glb`, `.gltf` | `bpy.ops.import_scene.gltf` |
| `.blend` | `bpy.ops.wm.open_mainfile` |

### Stage 6: Geometry Normalization

**Purpose**: Ensure every model loads consistently in Unity/Three.js — same scale, centered, with correct rotation.

Steps:
1. Calculate world-space bounding box (min/max XYZ across all mesh objects)
2. Create an `ASSET_ROOT` empty object as root anchor
3. Parent all existing root objects to `ASSET_ROOT` (preserves internal hierarchies like Gun Body → Trigger)
4. Apply uniform scale: `scale = 1.0 / max_dimension`
5. Center positioning:
   - **Sliceable** models: Geometric center → (0,0,0) — so slicing plane always bisects the model
   - **Static** models: Bottom center → (0,0,0) — so models "sit" on the ground plane
6. Inject metadata custom properties on root and all children:
   ```python
   root_obj["id"] = asset_id
   root_obj["interaction_type"] = "sliceable" | "static"
   ```
7. Enable Auto Smooth (60°) on all meshes

### Stage 7: Texture Relinking (`relink_textures`)
- Scans all Blender image data blocks for missing file paths
- Searches recursively from parent directory of model CWD
- Relinks image filepath to found file on disk
- Fixes: "Texture not found" errors common in Sketchfab/Blenderkit exports

### Stage 8: Auto-Connect Textures (`auto_connect_textures`)
Dynamic texture-to-material matching by name similarity:

1. Indexes all texture files in the directory tree (`.png`, `.jpg`, `.tga`, `.tif`, etc.)
2. For each Blender material:
   - Tokenizes material name (split by `._- `)
   - Also uses names of objects using that material (for generic "Material" names)
   - Finds best file match per channel using token intersection scoring:
     - **Base Color**: matches `color`, `diffuse`, `albedo`, `basecolor`
     - **Alpha**: matches `alpha`, `opacity`, `mask`, `transparent`
     - **Normal**: matches `normal`, `nrm`, `bump`, `normalmap`
     - **Roughness**: matches `roughness`, `rough`, `gloss`, `smoothness`
   - Banned keywords prevent wrong channel matches (e.g., Normal map file → Base Color socket)
3. Creates Tex Image nodes and links them to the Principled BSDF shader

### Stage 9: Transparency Fix (`fix_transparency`)
Smart material transparency handling:
- **Vegetation** (leaf/tree/plant/foliage in material name): Forces `HASHED` blend mode
- **Glass/Water** (glass/water/liquid/ice): Forces `BLEND` mode
- **Generic with suspicious Alpha link** (diffuse/roughness/normal wired to Alpha): Removes bad link, forces `OPAQUE`
- **Valid Alpha**: Sets `HASHED` blend mode

### Stage 10: Validation (`validate_model`)
Checks that raise `VALIDATION_FAILED` and stop export:
- **Missing textures**: Referenced image files don't exist on disk (and aren't packed)
- **Zero geometry**: No meshes or 0 vertices total
- **NaN/Inf geometry**: First 50 vertices sampled per mesh for corrupt coordinate values

Checks that only log warnings:
- **Non-manifold edges** (when `is_sliceable=True`): Warns that slicing may fail, but doesn't abort

### Stage 11: Export
```python
bpy.ops.export_scene.gltf(
    filepath=output_path,
    export_format='GLB',
    export_extras=True,      # Preserves custom properties (id, interaction_type)
    export_materials='EXPORT',
    export_image_format='AUTO',
    export_apply=True,       # Bakes modifiers
    export_normals=True,
    export_tangents=True,
    export_texcoords=True
)
```

---

## Sliceable vs Static Models

| Property | Sliceable | Static |
|---|---|---|
| `is_sliceable` flag | `true` | `false` |
| Centering | Geometric center → origin | Bottom center → ground |
| Manifold check | ✅ (warned if non-manifold) | ❌ |
| Injected metadata | `"interaction_type": "sliceable"` | `"interaction_type": "static"` |
| VR behavior | Can be cross-sectioned | Placed as decoration |

---

## Status Event Timeline

| Event | Status Field | Trigger |
|---|---|---|
| Task dequeued | `PROCESSING` | Celery task starts |
| Downloading | `PROCESSING` | Before MinIO download |
| Extracting | `PROCESSING` | ZIP detected |
| Blender started | `PROCESSING` | Before Blender subprocess |
| Uploading GLB | `PROCESSING` | After Blender success |
| Done | `COMPLETED` | After MinIO upload + DB update |
| Error | `FAILED` | Any exception caught |

---

## File Lifecycle

```
/tmp/{asset_id}/
├── {original_filename}     ← downloaded raw file
├── extracted/              ← ZIP contents (if applicable)
│   └── ...
├── mid.glb                 ← Blender output
└── final.glb               ← Copy of mid.glb (optimization step placeholder)

After upload to MinIO:
→ /tmp/{asset_id}/ is deleted (cleanup)
→ MinIO: processed/{asset_id}.glb is the permanent artifact
```
