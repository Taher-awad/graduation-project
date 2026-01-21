import zipfile
import os

zip_path = r"c:\Users\taher\Desktop\graduation v1\3d models for test\realistic-tree\source\TREE.zip"
print(f"Inspecting: {zip_path}")

try:
    with zipfile.ZipFile(zip_path, 'r') as z:
        print("\n--- Inner Zip Contents ---")
        for f in z.namelist():
            print(f)
            
    # Also list the outer folder just in case
    outer_dir = r"c:\Users\taher\Desktop\graduation v1\3d models for test\realistic-tree"
    print(f"\n--- Outer Directory {outer_dir} ---")
    for root, dirs, files in os.walk(outer_dir):
        for f in files:
            print(os.path.join(root, f))

except Exception as e:
    print(f"Error: {e}")
