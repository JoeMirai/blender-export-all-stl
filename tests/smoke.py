import importlib.util
import struct
import tempfile
from pathlib import Path
import bpy

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("addon", root / "export_all_stl.py")
addon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(addon)
addon.register()
bpy.ops.mesh.primitive_cube_add(location=(5, 0, 0))
second = bpy.context.object
second.name = "Hidden/Part"
second.hide_set(True)
second.modifiers.new("Subdivision", "SUBSURF").levels = 1
selected = list(bpy.context.selected_objects)
with tempfile.TemporaryDirectory() as destination:
    for _ in range(2):
        assert bpy.ops.export_mesh.all_stl_to_folder(folder_name="Test", destination=destination) == {"FINISHED"}
    assert (Path(destination) / "Test (2)").is_dir()
    files = list((Path(destination) / "Test").glob("*.stl"))
    assert len(files) == 2, files
    assert any(p.name == "Hidden_Part.stl" for p in files)
    for path in files:
        data = path.read_bytes()
        count = struct.unpack_from("<I", data, 80)[0]
        assert count > 0 and len(data) == 84 + count * 50
    hidden = (Path(destination) / "Test" / "Hidden_Part.stl").read_bytes()
    assert struct.unpack_from("<I", hidden, 80)[0] > 12
    assert list(bpy.context.selected_objects) == selected
addon.unregister()
print("PASS: hidden meshes, modifiers, binary STL, separate files, folder collisions, selection preservation")
