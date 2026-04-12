# 3D Processing Pipeline: Knowledge Notes

## Pipeline Summary

```
Upload (FBX/OBJ/BLEND/ZIP/GLB)
→ MinIO raw/
→ Redis Celery queue
→ service-3d-worker
→ Blender headless
→ MinIO processed/{id}.glb
→ SSE notification → Browser
```

## Blender Pipeline Steps

1. **Reset scene** — remove default objects
2. **Import** — FBX/OBJ/STL/GLTF/BLEND (dispatcher by extension)
3. **Normalize** — unit scale, center, inject `id` + `interaction_type` metadata
4. **Relink textures** — fix broken image paths by scanning disk
5. **Auto-connect** — match texture files to BSDF channels by name tokens
6. **Fix transparency** — vegetation→HASHED, glass→BLEND, suspicious links→OPAQUE
7. **Validate** — NaN geometry, zero vertices, missing textures
8. **Export GLB** — with modifiers baked, extras=True to preserve metadata

## Sliceable vs Static

| | Sliceable | Static |
|---|---|---|
| Centering | Geometric center | Bottom center (sits on ground) |
| Manifold check | ✅ Warns if non-manifold | ❌ |
| Metadata | `interaction_type: sliceable` | `interaction_type: static` |

## ZIP Handling

Extracts ZIP into `/tmp/{id}/extracted/`, searches for model in priority:
`.blend > .gltf > .fbx > .obj > .stl`

If nothing found in root → checks for **nested ZIPs** (common in Sketchfab downloads).

Blender CWD is set to the **directory of the model file** so relative texture paths work.

## Redis Pub/Sub Channels

```
worker publishes to: "user_notifications:{owner_id}"
notifications service subscribes to same channel
```

Event payloads:
```json
{"asset_id": "...", "status": "PROCESSING", "message": "..."}
{"asset_id": "...", "status": "COMPLETED", "processed_url": "processed/...glb"}
{"asset_id": "...", "status": "FAILED", "error": "..."}
```

## Celery Configuration

```python
celery -A celery_app worker --loglevel=info --concurrency=2
```
- Broker: Redis (`REDIS_URL`)
- Backend: Redis (task result storage)
- Concurrency: 2 (two parallel Blender processes)
- Task name: `"worker.process_asset"`

## Common Issues

| Problem | Cause | Fix |
|---|---|---|
| Model renders as ghost / invisible | Transparent material wrongly applied | `fix_transparency()` handles this |
| Missing textures in GLB | Relative paths broken post-ZIP | `relink_textures()` + set `blender_cwd` to model dir |
| Validation fails with NaN | Corrupt normals from FBX importer | Usually means bad source file |
| Non-manifold edges warning | Open/duplicate geometry | Warn only; doesn't block export |
| Spaghetti explosion on export | Flattening hierarchy broke transforms | Fixed by parenting to `ASSET_ROOT` instead of flattening |
