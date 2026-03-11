import os

def find_main_model_file(root_dir):
    """
    Recursively scans directory to find the likely 'Main' 3D model.
    Priority: .blend > .gltf > .fbx > .obj > .glb
    Tie-breaker: Filename 'scene' or 'main' > File Size
    """
    PRIORITY = {'.blend': 5, '.gltf': 4, '.glb': 3, '.fbx': 2, '.obj': 1}
    candidates = []

    for root, dirs, files in os.walk(root_dir):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in PRIORITY:
                full_path = os.path.join(root, f)
                size = os.path.getsize(full_path)
                score = PRIORITY[ext] * 100
                
                # Bonus for naming
                lower_name = f.lower()
                if 'scene' in lower_name: score += 50
                if 'main' in lower_name: score += 50
                if 'model' in lower_name: score += 20
                
                candidates.append({
                    'path': full_path,
                    'score': score,
                    'size': size
                })
    
    if not candidates:
        return None
        
    # Sort by Score (Desc), then Size (Desc)
    candidates.sort(key=lambda x: (x['score'], x['size']), reverse=True)
    
    # Debug print available candidates
    print(f"Found {len(candidates)} model candidates inside ZIP:")
    for c in candidates[:3]:
        print(f"  - {os.path.basename(c['path'])} (Score: {c['score']}, Size: {c['size']})")
        
    return candidates[0]['path']
