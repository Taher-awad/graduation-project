import bpy
import sys
import argparse
import os

def reset_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

def import_model(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.fbx':
        bpy.ops.import_scene.fbx(filepath=filepath)
    elif ext == '.obj':
        bpy.ops.import_scene.obj(filepath=filepath)
    elif ext in ['.stl', '.stlb']:
        bpy.ops.import_mesh.stl(filepath=filepath)
    elif ext in ['.glb', '.gltf']:
        bpy.ops.import_scene.gltf(filepath=filepath)
    elif ext == '.blend':
        bpy.ops.wm.open_mainfile(filepath=filepath)
    else:
        print(f"Unsupported format: {ext}")
        sys.exit(1)

def normalize_model(is_sliceable, asset_id):
    # Ensure we are in the correct view layer
    view_layer = bpy.context.view_layer
    
    # Process only mesh objects
    mesh_objects = [obj for obj in bpy.context.view_layer.objects if obj.type == 'MESH']
    
    print(f"DEBUG: Found {len(mesh_objects)} meshes in active View Layer.")
    
    if not mesh_objects:
        print("DEBUG: View Layer empty! Checking all objects in file...")
        mesh_objects = [obj for obj in bpy.data.objects if obj.type == 'MESH']
        print(f"DEBUG: Found {len(mesh_objects)} meshes in bpy.data.objects.")
        
        # Ensure they are linked to the scene so we can process them
        if mesh_objects:
            for obj in mesh_objects:
                if obj.name not in bpy.context.scene.collection.objects:
                    try:
                        bpy.context.scene.collection.objects.link(obj)
                    except:
                        pass
    
    if not mesh_objects:
        print("ERROR: No meshes found in file!")
        return

    # 1. Calculate Global Bounding Box
    # Initialize with the first vertex of the first object
    import mathutils
    import math
    
    min_x = float('inf')
    max_x = float('-inf')
    min_y = float('inf')
    max_y = float('-inf')
    min_z = float('inf')
    max_z = float('-inf')
    
    has_geometry = False
    
    for obj in mesh_objects:
        # Get world matrix
        mw = obj.matrix_world
        # Check bounding box (8 corners)
        if hasattr(obj, 'bound_box') and obj.bound_box:
            has_geometry = True
            for corner in obj.bound_box:
                world_corner = mw @ mathutils.Vector(corner)
                min_x = min(min_x, world_corner.x)
                max_x = max(max_x, world_corner.x)
                min_y = min(min_y, world_corner.y)
                max_y = max(max_y, world_corner.y)
                min_z = min(min_z, world_corner.z)
                max_z = max(max_z, world_corner.z)
    
    if not has_geometry:
        return

    size_x = max_x - min_x
    size_y = max_y - min_y
    size_z = max_z - min_z
    
    # 2. Create a Root Anchor
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
    root_obj = bpy.context.active_object
    root_obj.name = "ASSET_ROOT"
    
    # Parent EXISTING ROOTS to ASSET_ROOT
    # This preserves internal hierarchies (e.g. Gun Body -> Trigger)
    # instead of flattening them which causes "spaghetti" explosion.
    
    # Find all objects that don't have a parent (excluding our new root)
    # We scan all scene objects, not just meshes, to catch Armatures/Empties.
    scene_objects = bpy.context.scene.objects
    existing_roots = [obj for obj in scene_objects if obj.parent is None and obj != root_obj]
    
    for obj in existing_roots:
        obj.parent = root_obj
        obj.matrix_parent_inverse = root_obj.matrix_world.inverted()

    # 3. Normalize Scale
    max_dim = max(size_x, size_y, size_z)
    scale_factor = 1.0 / max_dim if max_dim > 0 else 1.0
    
    # Apply scale to Root
    root_obj.scale = (scale_factor, scale_factor, scale_factor)
    
    # 4. Center Position
    # Calculate current center of bounds
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    center_z = (min_z + max_z) / 2.0 # Geometric center Z
    
    # We want to move the geometry so that:
    # - If sliceable: Geometric Center -> (0,0,0)
    # - If static: Bottom Center -> (0,0,0)
    
    # Since we act on the Root, we need to move the Root such that the children land at target.
    # Root is currently at (0,0,0). Children are at world positions.
    # Actually simpler: Move Root to the NEGATIVE of the center.
    
    if is_sliceable:
        root_obj.location = (-center_x * scale_factor, -center_y * scale_factor, -center_z * scale_factor)
    else:
        # Bottom Center
        # min_z is the bottom.
        root_obj.location = (-center_x * scale_factor, -center_y * scale_factor, -min_z * scale_factor)
        
    # Inject Metadata on Root AND Children
    # Ensuring children have metadata allows the slicer to work if it hits a child directly.
    meta_props = {
        "id": asset_id,
        "interaction_type": "sliceable" if is_sliceable else "static"
    }
    
    # Apply to Root
    for k, v in meta_props.items():
        root_obj[k] = v
        
    # Apply to all children (Meshes)
    for obj in mesh_objects:
        for k, v in meta_props.items():
            obj[k] = v

    # Ensure textures are available
    try:
        bpy.ops.file.unpack_all(method='USE_LOCAL')
    except:
        pass
        
    # --- AUTO SMOOTH FIX (Weighted Normal Modifier) ---
    print("DEBUG: Enabling Auto Smooth...", flush=True)
    try:
        for obj in mesh_objects:
            if obj.type == 'MESH':
                obj.data.use_auto_smooth = True
                obj.data.auto_smooth_angle = 3.14159 / 3 # 60 degrees
    except Exception as e:
        print(f"Error enabling Auto Smooth: {e}", flush=True)

    # --- STEPS WITH ERROR HANDLING ---
    
    try:
        # --- SMART TEXTURE RELINKING ---
        relink_textures()
    except Exception as e:
        print(f"Error in relink_textures: {e}", flush=True)
    
    try:
        # --- AUTO-CONNECT (Disk Search) ---
        auto_connect_textures()
    except Exception as e:
        print(f"Error in auto_connect_textures: {e}", flush=True)
    
    try:
        # --- TRANSPARENCY FIX ---
        fix_transparency()
    except Exception as e:
        print(f"Error in fix_transparency: {e}", flush=True)

# ... (relink_textures and auto_connect_textures remain similar, skipping to fix_transparency) ...

    """
    Ensures materials with Alpha connections are set to suitable Blend Modes.
    Redesigned to be CONSERVATIVE:
    - Vegetation -> Force HASHED
    - Glass/Water -> Force BLEND
    - Others -> Default to OPAQUE unless strong evidence implies transparency.
    """
    print("--- DEBUG: FIXING TRANSPARENCY ---", flush=True)
    
    for mat in bpy.data.materials:
        if not mat.use_nodes: continue
        
        bsdf = None
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        
        if not bsdf: continue
        
        mat_name_lower = mat.name.lower()
        is_vegetation = any(x in mat_name_lower for x in ['leaf', 'leaves', 'tree', 'plant', 'foliage', 'branch'])
        is_glass = any(x in mat_name_lower for x in ['glass', 'water', 'liquid', 'ice'])
        
        # 1. Inspect existing link
        alpha_socket = bsdf.inputs.get('Alpha')
        if alpha_socket and alpha_socket.is_linked:
            # We have a link. Is it legitimate transparency?
            link = alpha_socket.links[0]
            node = link.from_node
            
            # If it's the Cannon, we DO NOT want to force transparency just because of a stray link.
            # We only force HASHED if it is Vegetation.
            
            if is_vegetation:
                print(f"Material '{mat.name}': Detected Vegetation. Forcing HASHED.", flush=True)
                mat.blend_method = 'HASHED'
                mat.shadow_method = 'HASHED'
                mat.use_backface_culling = False
            elif is_glass:
                print(f"Material '{mat.name}': Detected Glass. Forcing BLEND.", flush=True)
                mat.blend_method = 'BLEND'
                mat.shadow_method = 'HASHED'
                mat.use_backface_culling = False
            else:
                # Generic Material (e.g. Cannon)
                # If the Blend Mode is currently OPAQUE, keep it OPAQUE!
                # Don't let a random map (like AO hooked to Alpha) turn it into a ghost.
                print(f"Material '{mat.name}': Generic material with Alpha link. Keep existing mode or Default to OPAQUE.", flush=True)
                if mat.blend_method == 'OPAQUE':
                     # Ensure it stays opaque even if there's a link (often a mistake in Sketchfab imports)
                     pass 
                else:
                    # If it WAS transparent, maybe it should be?
                    # But for "Ghost Cannon", it was likely OPAQUE in Blender but my previous script forced HASHED.
                    # Let's be safe: If it's not vegetation/glass, treat as OPAQUE unless user explicitly named it "Transparent".
                    if 'trans' not in mat_name_lower and 'alpha' not in mat_name_lower:
                        print(f"  -> Reverting '{mat.name}' to OPAQUE (Conservative Fix)", flush=True)
                        mat.blend_method = 'OPAQUE'
                        mat.shadow_method = 'OPAQUE'
            continue

def relink_textures():
    """
    Attempts to find missing textures by scanning the directory tree
    relative to the blend file/CWD.
    """
    import os
    
    print("--- DEBUG: RELINKING TEXTURES ---")
    
    # Gather missing images
    missing_images = []
    for img in bpy.data.images:
        if img.source == 'FILE' and img.filepath:
            path = bpy.path.abspath(img.filepath)
            if not os.path.exists(path):
                missing_images.append(img)
    
    if not missing_images:
        return

    # Scan the current working directory recursively
    # We assume CWD is set to the model directory or root extract
    # We walk UP one level to catch sibling folders like 'textures' if we are in 'source'
    cwd = os.getcwd()
    search_root = os.path.dirname(cwd) # Go up one level
    
    print(f"Scanning for missing textures in: {search_root}")
    
    found_files = {}
    for root, dirs, files in os.walk(search_root):
        for f in files:
            found_files[f] = os.path.join(root, f)
            
    # Relink
    for img in missing_images:
        fname = os.path.basename(img.filepath)
        if fname in found_files:
            new_path = found_files[fname]
            print(f"Relinking {img.name}: {img.filepath} -> {new_path}")
            img.filepath = new_path

def auto_connect_textures():
    """
    Dynamic Texture Matching:
    Scans all files and attempts to link them to materials based on 
    token overlap (name similarity) and channel keywords.
    Independent of specific asset names (e.g. works for 'Tree', 'Car', 'Gun').
    """
    print("--- DEBUG: RUNNING DYNAMIC AUTO-CONNECT ---")
    import re
    
    # 1. Index all files
    cwd = os.getcwd()
    search_root = os.path.dirname(cwd)
    
    print(f"Indexing files in {search_root}...")
    texture_candidates = []
    
    # Supported Extensions
    exts = ('.png', '.jpg', '.jpeg', '.tga', '.tif', '.tiff', '.bmp', '.webp')
    
    for root, dirs, files in os.walk(search_root):
        for f in files:
            if f.lower().endswith(exts):
                # Store full path and tokenized name
                full_path = os.path.join(root, f)
                # Split by underscore, dot, space, hyphen
                tokens = set(re.split(r'[._\-\s]+', f.lower()))
                texture_candidates.append({
                    'path': full_path,
                    'filename': f,
                    'tokens': tokens
                })
                
    if not texture_candidates:
        print("No textures found on disk.")
        return

    # Helper to find best match
    def find_best_match(mat_tokens, channel_keywords, banned_keywords=set()):
        best_file = None
        best_score = 0
        
        for cand in texture_candidates:
            score = 0
            cand_tokens = cand['tokens']
            
            # 0. Check Banned Keywords
            # If the file contains any word that implies a DIFFERENT channel, skip it.
            # CRITICAL FIX: If the banned word is part of the MATERIAL NAME, ignore the ban.
            # e.g. Material "normal_leaves" -> "normal" is in mat_tokens.
            # We shouldn't ban "normal_leaves_diffuse.png" just because it has "normal".
            
            effective_banned = banned_keywords - mat_tokens
            
            if any(b in cand_tokens for b in effective_banned):
                continue
            
            # 1. Name Match (Intersection of unique words)
            common_tokens = mat_tokens.intersection(cand_tokens)
            score += len(common_tokens) * 10
            
            # 2. Channel Match
            has_channel = any(k in cand_tokens for k in channel_keywords)
            if has_channel:
                score += 5
            
            # Threshold
            if score > best_score:
                best_score = score
                best_file = cand['path']
        
        if best_score >= 10:
            return best_file
        return None

    # 2. Iterate Materials
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            mat.use_nodes = True
            
        bsdf = None
        output_node = None
        
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
            if node.type == 'OUTPUT_MATERIAL':
                output_node = node
                
        # --- FIX: Handle Non-Standard Materials (e.g. Specular/Glossiness imports) ---
        # If no Principled BSDF exists, the Auto-Connect logic would skip it.
        # We enforce a Principled BSDF to ensure we can connect textures.
        if not bsdf:
            print(f"Material '{mat.name}' has no Principled BSDF. Resetting to PBR defaults...")
            mat.node_tree.nodes.clear()
            bsdf = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            bsdf.location = (0, 300)
            output_node = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
            output_node.location = (300, 300)
            mat.node_tree.links.new(bsdf.outputs['BSDF'], output_node.inputs['Surface'])
            
        if not bsdf: continue
        
        # Tokenize Material Name
        clean_name = mat.name.lower().replace('material', '').strip()
        if not clean_name:
            clean_name = mat.name.lower()
            
        mat_tokens = set(re.split(r'[._\-\s]+', clean_name))
        mat_tokens = {t for t in mat_tokens if len(t) > 2}
        
        # --- ENHANCEMENT: Include Object Names in Tokens ---
        # If the material name is generic (e.g., "Material"), it won't match anything.
        # We check which objects use this material and add their names to the tokens.
        
        # This is slightly expensive, but worth it for generic assets.
        users = [obj for obj in bpy.data.objects if obj.type == 'MESH' and mat.name in [m.name for m in obj.data.materials if m]]
        
        for obj in users:
            obj_name_clean = obj.name.lower()
            obj_tokens = set(re.split(r'[._\-\s]+', obj_name_clean))
            # Add reasonable tokens (len > 2), skipping generic ones like "mesh", "object", "poly"
            for t in obj_tokens:
                if len(t) > 2 and t not in {'mesh', 'object', 'poly', 'shape', 'model', 'group'}:
                    mat_tokens.add(t)
        
        print(f"Material '{mat.name}' tokens (incl. Objects): {mat_tokens}")
        
        if 'Base Color' in bsdf.inputs and not bsdf.inputs['Base Color'].is_linked:
            color_keys = {'color', 'diffuse', 'albedo', 'basecolor', 'base_color'}
            banned = {'normal', 'nrm', 'bump', 'roughness', 'rough', 'gloss', 'specular', 'ao', 'ambient', 'alpha', 'opacity', 'mask', 'occlusion'}
            match = find_best_match(mat_tokens, color_keys, banned)
            if match:
                print(f"  -> Matched Base Color: {os.path.basename(match)}")
                try:
                    img = bpy.data.images.load(match)
                    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    tex.image = img
                    tex.location = (-300, 300)
                    tex.location = (-300, 300)
                    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
                    
                    # --- AUTO-LINK EMBEDDED ALPHA ---
                    # Many PBR textures (especially from GLTF/Unity) have Alpha in the Diffuse/Albedo channel.
                    # If we just linked Base Color, let's also link its Alpha output to the BSDF Alpha.
                    # We can assume if there's a separate Alpha file, it will overwrite this later.
                    if 'Alpha' in bsdf.inputs:
                        mat.node_tree.links.new(tex.outputs['Alpha'], bsdf.inputs['Alpha'])
                        mat.blend_method = 'HASHED'
                        mat.shadow_method = 'HASHED'
                        mat.use_backface_culling = False
                        print(f"    -> Linked Embedded Alpha from {os.path.basename(match)}")
                except:
                    pass

        # --- Alpha ---
        if 'Alpha' in bsdf.inputs and not bsdf.inputs['Alpha'].is_linked:
            alpha_keys = {'alpha', 'opacity', 'mask', 'transparent'}
            # Ban color, normal, etc. to prevent "Trunk_Color.png" being used as alpha
            banned = {'color', 'diffuse', 'albedo', 'normal', 'nrm', 'bump', 'roughness', 'rough', 'specular', 'ao', 'occlusion'}
            
            match = find_best_match(mat_tokens, alpha_keys, banned)
            if match:
                print(f"  -> Matched Alpha: {os.path.basename(match)}")
                try:
                    img = bpy.data.images.load(match)
                    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    tex.image = img
                    tex.location = (-300, -300)
                    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Alpha'])
                    
                    mat.blend_method = 'HASHED'
                    mat.shadow_method = 'HASHED'
                    mat.use_backface_culling = False
                except:
                    pass

        # --- Normal ---
        if 'Normal' in bsdf.inputs and not bsdf.inputs['Normal'].is_linked:
            normal_keys = {'normal', 'nrm', 'bump', 'normalmap'}
            banned = {'color', 'diffuse', 'albedo', 'roughness', 'rough', 'specular', 'ao', 'alpha', 'occlusion'}
            match = find_best_match(mat_tokens, normal_keys, banned)
            if match:
                print(f"  -> Matched Normal: {os.path.basename(match)}")
                try:
                    img = bpy.data.images.load(match)
                    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    tex.image = img
                    tex.location = (-600, 0)
                    tex.image.colorspace_settings.name = 'Non-Color'
                    
                    norm_map = mat.node_tree.nodes.new('ShaderNodeNormalMap')
                    norm_map.location = (-300, 0)
                    
                    mat.node_tree.links.new(tex.outputs['Color'], norm_map.inputs['Color'])
                    mat.node_tree.links.new(norm_map.outputs['Normal'], bsdf.inputs['Normal'])
                except:
                    pass

        # --- Roughness ---
        if 'Roughness' in bsdf.inputs and not bsdf.inputs['Roughness'].is_linked:
            rough_keys = {'roughness', 'rough', 'gloss', 'smoothness'}
            banned = {'color', 'diffuse', 'albedo', 'normal', 'nrm', 'alpha', 'specular', 'ao', 'occlusion'}
            match = find_best_match(mat_tokens, rough_keys, banned)
            if match:
                print(f"  -> Matched Roughness: {os.path.basename(match)}")
                try:
                    img = bpy.data.images.load(match)
                    tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
                    tex.image = img
                    tex.image.colorspace_settings.name = 'Non-Color'
                    tex.location = (-300, 100)
                    mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Roughness'])
                except:
                    pass
            
def fix_transparency():
    """
    Ensures materials with Alpha connections are set to suitable Blend Modes.
    Also attempts to AUTO-CONNECT alpha textures if they are found but not linked
    (common in split texture sets like 'leaves color' + 'leaves alpha').
    """
    print("--- DEBUG: FIXING TRANSPARENCY ---")
    
    # Map of all images for lookups
    all_images = {img.name.lower(): img for img in bpy.data.images}
    
    for mat in bpy.data.materials:
        if not mat.use_nodes: continue
        
        bsdf = None
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                bsdf = node
                break
        
        if not bsdf: continue
        
        # 1. Check existing link
        alpha_socket = bsdf.inputs.get('Alpha')
        if alpha_socket and alpha_socket.is_linked:
            # Validate the link. Is it a mistake?
            link = alpha_socket.links[0]
            node = link.from_node
            
            is_valid_alpha = True
            
            if node.type == 'TEX_IMAGE' and node.image:
                img_name = node.image.name.lower()
                # If the image specifically says it's NOT alpha (e.g. Roughness, Normal, AO)
                # Then this link is likely garbage/mistake from an auto-importer.
                banned_for_alpha = ['diffuse', 'color', 'roughness', 'metal', 'normal', 'nrm', 'ao', 'occlusion', 'bump']
                # But be careful: "Leaves_Color_Alpha.png" might be valid.
                # So only ban if it DOESN'T contain "alpha" or "opacity".
                
                if any(x in img_name for x in banned_for_alpha) and not any(x in img_name for x in ['alpha', 'opacity', 'mask', 'trans']):
                    print(f"Material '{mat.name}': Found SUSPICIOUS Alpha Link to '{img_name}'. Unlinking and forcing OPAQUE.")
                    mat.node_tree.links.remove(link)
                    mat.blend_method = 'OPAQUE'
                    mat.shadow_method = 'OPAQUE'
                    is_valid_alpha = False
            
            if is_valid_alpha:
                print(f"Material '{mat.name}': Alpha ALREADY linked. Setting HASHED.")
                mat.blend_method = 'HASHED'
                mat.shadow_method = 'HASHED'
                mat.use_backface_culling = False
            continue
            
        # 2. Heuristic: Logic for "Leaves" or broken alpha
        # If material name implies vegetation, look for an alpha texture
        mat_name_lower = mat.name.lower()
        if 'leaf' in mat_name_lower or 'tree' in mat_name_lower or 'plant' in mat_name_lower:
            print(f"Material '{mat.name}' is vegetation. Searching for alpha texture (Existing Images)...")
            
            found_alpha_img = None
            used_images = [n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image]
            
            for img in bpy.data.images:
                if img.name in [u.name for u in used_images]: continue
                
                img_name = img.name.lower()
                if 'alpha' in img_name and any(x in img_name for x in ['leaf', 'leaves', 'foliage']):
                    found_alpha_img = img
                    break
            
            if found_alpha_img:
                print(f"  -> Found unlinked Alpha Texture: {found_alpha_img.name}")
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                tex_node = nodes.new('ShaderNodeTexImage')
                tex_node.image = found_alpha_img
                tex_node.location = (-300, -200)
                links.new(tex_node.outputs['Color'], alpha_socket)
                
                mat.blend_method = 'HASHED'
                mat.shadow_method = 'HASHED'
                mat.use_backface_culling = False


def validate_model(is_sliceable):
    """
    Performs extensive checks on the scene data.
    Raises SystemExit(1) if Critical Errors are found.
    """
    import json
    import math
    import bmesh
    
    errors = []
    
    print("--- DEBUG: RUNNING VALIDATION ---")
    
    # Manifold check for sliceable models
    if is_sliceable:
        print("--- DEBUG: CHECKING MANIFOLD EDGES ---")
        non_manifold_count = 0
        for obj in bpy.data.objects:
            if obj.type == 'MESH':
                bm = bmesh.new()
                bm.from_mesh(obj.data)
                for e in bm.edges:
                    if not e.is_manifold:
                        non_manifold_count += 1
                bm.free()
        print(f"DEBUG: Found {non_manifold_count} non-manifold edges.")
        if non_manifold_count > 0:
             print(f"WARNING: Mesh has {non_manifold_count} non-manifold edges, slicing may fail or produce artifacts.")
    
    # 1. Texture Check
    # We check if referenced images actually exist on disk (unless packed)
    for img in bpy.data.images:
        # Skip Render Results or generated images
        if img.source != 'FILE': 
            continue
            
        if img.filepath and not img.packed_file:
            path = bpy.path.abspath(img.filepath)
            if not os.path.exists(path):
                # Try to be smart: Check invalid paths too
                errors.append(f"Missing Texture: '{img.name}' (Path not found: {img.filepath})")

    # 2. Geometry Check
    total_verts = 0
    start_checking = True
    
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            mesh = obj.data
            total_verts += len(mesh.vertices)
            
            # NaN/Inf Check (Critical for WebGL)
            # Sample first 50 vertices for performance
            if start_checking and len(mesh.vertices) > 0:
                for i, v in enumerate(mesh.vertices):
                    if i > 50: break
                    if any(math.isnan(c) or math.isinf(c) for c in v.co):
                        errors.append(f"Corrupt Geometry (NaN/Inf values) in object '{obj.name}'")
                        start_checking = False # Stop checking to avoid flooding
                        break

    if total_verts == 0:
        errors.append("Model contains no geometry (0 Vertices).")
        
    if errors:
        print("VALIDATION_FAILED")
        print(json.dumps(errors))
        sys.exit(1)
    else:
        print("--- DEBUG: VALIDATION PASSED ---")

def optimize_textures():
    print("--- DEBUG: OPTIMIZING TEXTURES (Max 2048x2048) ---")
    max_size = 2048
    for img in bpy.data.images:
        if img.source == 'FILE' and img.has_data:
            width, height = img.size[0], img.size[1]
            if width > max_size or height > max_size:
                scale = max_size / max(width, height)
                new_w = max(1, int(width * scale))
                new_h = max(1, int(height * scale))
                print(f"Rescaling '{img.name}' from {width}x{height} to {new_w}x{new_h}")
                try:
                    img.scale(new_w, new_h)
                except Exception as e:
                    print(f"Failed to rescale {img.name}: {e}")

def export_model(output_path):
    print("--- DEBUG: EXPORTING (VANILLA) ---")
    # Ensure export_extras is True
    # Ensure reliable export
    bpy.ops.export_scene.gltf(
        filepath=output_path, 
        export_format='GLB', 
        export_extras=True,
        export_materials='EXPORT',
        export_image_format='AUTO',
        export_apply=True, # Apply modifiers
        export_colors=True, # Default behavior
        export_normals=True,
        export_tangents=True,
        export_texcoords=True
    )

if __name__ == "__main__":
    import traceback
    try:
        args = sys.argv
        try:
            idx = args.index("--")
            my_args = args[idx+1:]
        except ValueError:
            my_args = []

        parser = argparse.ArgumentParser()
        parser.add_argument("--input", required=True)
        parser.add_argument("--output", required=True)
        parser.add_argument("--sliceable", required=True)
        parser.add_argument("--id", required=True)
        
        parsed_args = parser.parse_args(my_args)
        
        is_sliceable = parsed_args.sliceable.lower() == 'true'

        print(f"Processing: Input={parsed_args.input}, Output={parsed_args.output}")

        reset_scene()
        import_model(parsed_args.input)
        normalize_model(is_sliceable, parsed_args.id)
        validate_model(is_sliceable)
        optimize_textures()
        export_model(parsed_args.output)
        print("Blender Processing Complete.")

    except Exception:
        traceback.print_exc()
        sys.exit(1)
