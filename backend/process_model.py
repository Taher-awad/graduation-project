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
    
    # Parent all meshes to Root
    for obj in mesh_objects:
        # Keep transform ensures they stay in visual place relative to new parent
        # But we want to move them logically.
        # Standard parenting:
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
        # Move root to compensate for center
        # We need to consider that scaling happens AFTER translation if we edit location directly?
        # No, transform order is Loc -> Rot -> Scale.
        # But here we are setting properties.
        # Let's just adjust the root location?
        # If we move root to -center, the attached children move with it.
        # However, the children data is still at world coordinates.
        # To make "Applied" visual transform correct:
        
        # Strategy: Move Root so that visual center aligns with world 0,0,0
        # The visual center of the group is at (center_x, center_y, center_z).
        # We want that point to be at (0,0,0).
        # Translation vector = (0,0,0) - (center_x, center_y, center_z) * scale_factor?
        # No, simpler to just inverse parent everything, move objects, then scale?
        
        # Let's try the simple Empty move.
        # If I have a box at (10, 10, 10). I parent to Root (0,0,0). 
        # I move Root to (-10, -10, -10). Box is now at (0,0,0).
        
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
    # Apply to all children (Meshes)
    for obj in mesh_objects:
        for k, v in meta_props.items():
            obj[k] = v

    # Ensure textures are available (Standard Blender behavior)
    try:
        bpy.ops.file.unpack_all(method='USE_LOCAL')
    except:
        pass

def validate_model():
    """
    Performs extensive checks on the scene data.
    Raises SystemExit(1) if Critical Errors are found.
    """
    import json
    import math
    
    errors = []
    
    print("--- DEBUG: RUNNING VALIDATION ---")
    
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
    # Arg parsing manually because blender arguments interfere
    # Expected: ... -- --input X --output Y --sliceable True/False
    
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
        validate_model()
        export_model(parsed_args.output)
        print("Blender Processing Complete.")

    except Exception:
        traceback.print_exc()
        sys.exit(1)
