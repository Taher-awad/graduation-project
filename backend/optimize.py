import subprocess
import os

def run_optimization(input_glb, output_glb, is_sliceable):
    """
    failed to load gltfpack? ensure it is installed.
    """
    
    cmd = ["gltfpack", "-i", input_glb, "-o", output_glb]
    
    if is_sliceable:
        # Sliceable: NO GEOMETRY COMPRESSION, NO TEXTURE COMPRESSION (Max Compatibility)
        # Compression breaks direct vertex access needed for slicing scripts
        pass
    else:
        # Static: MAXIMUM COMPRESSION (Geometry only)
        # -c: Meshopt compression (Geometry)
        # -mi: Mesh instancing
        # Removed -tc (KTX2) to avoid Unity dependency issues
        cmd.extend(["-c", "-mi"])
        
        # Note: CoACD generation would happen here if we had the tool.
        # For this implementation, we skip external CoACD tool to avoid dependency hell,
        # relying on Unity to generate MeshColliders for static objects or implementing it later.
    
    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(f"gltfpack failed: {result.stderr}")
    
    print("Optimization Complete.")
