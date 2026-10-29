# Orion - Blender DAXİLİNDƏ işləyən skript (birbaşa işə salınmır, blender_bridge.py çağırır):
# blender --background --factory-startup --python blender_runner.py -- <model_skripti.py> <çıxış.blend>

import json
import sys

import bpy

script_path, output_path, fbx_path = sys.argv[sys.argv.index("--") + 1:]

# Başlanğıc səhnəni təmizləyirik (default kub, kamera, işıq) - model boş səhnədə yaradılsın
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
for collection in (bpy.data.meshes, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
    for item in list(collection):
        collection.remove(item)

# Claude-un yazdığı model skriptini icra edirik
with open(script_path, encoding="utf-8") as f:
    code = f.read()
exec(compile(code, script_path, "exec"), {"__name__": "__main__", "bpy": bpy})

bpy.ops.wm.save_as_mainfile(filepath=output_path)

# Roblox-a yükləmək üçün FBX ixracı - alınmasa .blend nəticəsini pozmuruq,
# sadəcə xəbərdarlıq yazırıq (Roblox tərəfi bunsuz da işləyə bilər)
try:
    bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=False, mesh_smooth_type="FACE")
except Exception as e:
    print(f"ORION_FBX_ERROR:{e}")

# Nəticəni Orion-a bildiririk - səhnədə hansı obyektlər yarandı
objects = [
    {
        "name": obj.name,
        "type": obj.type,
        "dimensions": [round(v, 3) for v in obj.dimensions],
        "location": [round(v, 3) for v in obj.location],
    }
    for obj in bpy.context.scene.objects
]
print("ORION_RESULT:" + json.dumps(objects, ensure_ascii=False))
