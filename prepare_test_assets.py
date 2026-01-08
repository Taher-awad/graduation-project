import os
import zipfile
import shutil

BASE_DIR = r"c:\Users\taher\Desktop\graduation v1\3d models for test"
OUTPUT_DIR = r"c:\Users\taher\Desktop\graduation v1\temp_test_zips"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

folders_to_zip = [
    "cannon_01_4k.blend",  # This is a folder name despite the extension
    "realistic_tree",
    "rainier-ak-3d"
]

def make_zip(source_folder_name, output_name):
    source_path = os.path.join(BASE_DIR, source_folder_name)
    output_path = os.path.join(OUTPUT_DIR, output_name)
    
    print(f"Zipping {source_path} -> {output_path}...")
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk and zip with relative paths
        for root, dirs, files in os.walk(source_path):
            for file in files:
                abs_path = os.path.join(root, file)
                # rel_path = os.path.relpath(abs_path, os.path.dirname(source_path)) 
                # ^ This creates a root folder inside zip.
                # Better: Flatten the root? Or keep it?
                # If I zip "myfolder", I usually expect "myfolder/file".
                # But my worker logic just extracts and searches. 
                # Let's keep the folder structure as is relative to the source folder.
                rel_path = os.path.relpath(abs_path, source_path)
                zipf.write(abs_path, rel_path)
    
    print(f"Created {output_name}")

for folder in folders_to_zip:
    make_zip(folder, f"{folder}.zip")

print("Zipping Complete.")
