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
    # Select all meshes
    # Ensure we are in the correct view layer
    view_layer = bpy.context.view_layer
    
    # Selecting objects needs to be done via the collection or view layer
    bpy.ops.object.select_all(action='DESELECT')
    
    # Only process objects in the current view layer to avoid selection errors
    mesh_objects = [obj for obj in bpy.context.view_layer.objects if obj.type == 'MESH']
    
    if not mesh_objects:
        return

    for obj in mesh_objects:
        obj.select_set(True)

    # Join into one object for easier pivot handling
    view_layer.objects.active = mesh_objects[0]
    bpy.ops.object.join()
    active_obj = bpy.context.active_object

    # Calculate Bounding Box
    import mathutils
    bbox_corners = [active_obj.matrix_world @ mathutils.Vector(corner) for corner in active_obj.bound_box]
    
    min_x = min([v[0] for v in bbox_corners])
    max_x = max([v[0] for v in bbox_corners])
    min_y = min([v[1] for v in bbox_corners])
    max_y = max([v[1] for v in bbox_corners])
    min_z = min([v[2] for v in bbox_corners])
    max_z = max([v[2] for v in bbox_corners])
    
    size_x = max_x - min_x
    size_y = max_y - min_y
    size_z = max_z - min_z
    
    # Scale to fit in 1m box (approx)
    max_dim = max(size_x, size_y, size_z)
    scale_factor = 1.0 / max_dim if max_dim > 0 else 1.0
    active_obj.scale = (scale_factor, scale_factor, scale_factor)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)

    # Pivot Adjustment
    # Reset Origin first
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    
    if is_sliceable:
        # Center Pivot (already done by ORIGIN_GEOMETRY CENTER)
        # Position object at 0,0,0
        active_obj.location = (0, 0, 0)
    else:
        # Bottom Center: Move object so its bottom (min Z in Blender) is at Z=0
        min_z_new = min([ (active_obj.matrix_world @ v)[2] for v in active_obj.bound_box ])
        active_obj.location.z -= min_z_new

    # Metadata Injection
    # Blender exports custom properties as 'extras' if configured (default is usually required explicit check, 
    # but Standard glTF exporter exports them if 'Export Custom Properties' is on.
    # We will ensure they are set on the object.
    active_obj["id"] = asset_id
    active_obj["interaction_type"] = "sliceable" if is_sliceable else "static"
    active_obj["original_scale"] = [1.0, 1.0, 1.0] # Normalized to 1m

def export_model(output_path):
    # Ensure export_extras is True
    bpy.ops.export_scene.gltf(filepath=output_path, export_format='GLB', export_extras=True)

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
        export_model(parsed_args.output)
        print("Blender Processing Complete.")

    except Exception:
        traceback.print_exc()
        sys.exit(1)
