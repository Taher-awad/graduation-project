import bpy
import os
import sys

# Path to the specific extracted FBX (simulated)
# We need to unzip it first to test locally or just rely on the user provided info.
# Actually, I can use the functionality of finding it if I assume it's unzipped in temp.
# But I can't access /tmp/uuid...
# So I will replicate the "Import" step on the local file system using the realistic-tree files.

# Assumes '3d models for test/realistic-tree/source/TREE.zip' is the target.
# Depending on how the user unzipped it locally...
# The user's folder `3d models for test/realistic-tree` has `source/TREE.zip` and `textures/`.
# IF I import `source/TREE.fbx` (extracted), does it find `../../textures`? 

# Let's try to simulate what happens in the worker.
# I will use the `process_model.py` logic but printed.

fbx_path = r"c:\Users\taher\Desktop\graduation v1\3d models for test\realistic-tree\source\TREE.fbx" # Assuming I extract it there?
# Wait, I need to extract it first.

import zipfile
zip_path = r"c:\Users\taher\Desktop\graduation v1\3d models for test\realistic-tree\source\TREE.zip"
extract_path = r"c:\Users\taher\Desktop\graduation v1\temp_debug_tree"

if not os.path.exists(extract_path):
    os.makedirs(extract_path)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_path)

# Now import
fbx_file = os.path.join(extract_path, "TREE.fbx")
# Note: The zip might contain 'source/TREE.fbx' or just 'TREE.fbx' depending on how it was zipped. 
# debug_zip_structure.py will tell us. 
# Assuming it is at root of zip based on logs "Found 1 model candidates... TREE.fbx"

bpy.ops.wm.read_factory_settings(use_empty=True)
try:
    bpy.ops.import_scene.fbx(filepath=fbx_file)
except Exception as e:
    print(f"Import Failed: {e}")

print(f"\n--- Materials & Nodes Report ---")
for mat in bpy.data.materials:
    print(f"Material: {mat.name}")
    if not mat.use_nodes:
        print("  [No Nodes]")
        continue
        
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_IMAGE':
            img_name = node.image.name if node.image else "None"
            print(f"  - Image Node: {img_name} (Filepath: {node.image.filepath if node.image else 'None'})")
        elif node.type == 'BSDF_PRINCIPLED':
            print("  - Principled BSDF found")
            inputs = node.inputs
            if inputs['Base Color'].is_linked:
                print(f"    -> Base Color linked to {inputs['Base Color'].links[0].from_node.name}")
            if inputs['Alpha'].is_linked:
                print(f"    -> Alpha linked to {inputs['Alpha'].links[0].from_node.name}")

print("\n--- Images in Data ---")
for img in bpy.data.images:
    print(f"Image: {img.name} | Path: {img.filepath}")
