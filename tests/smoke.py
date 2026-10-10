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
        assert bpy.ops.export_mesh.all_stl_to_folder(folder_name="Test", destination=destination, include_hidden=True) == {"FINISHED"}
    assert (Path(destination) / "Test (2)").is_dir()
    assert bpy.ops.export_mesh.all_stl_to_folder(folder_name="Visible", destination=destination) == {"FINISHED"}
    assert len(list((Path(destination) / "Visible").glob("*.stl"))) == 1
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

# Real Ctrl+J equivalent: two disconnected cubes become one Blender object.
addon.register()
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
first = bpy.context.object
bpy.ops.mesh.primitive_cube_add(location=(4, 0, 0))
second = bpy.context.object
first.select_set(True)
bpy.ops.object.join()
assert len([o for o in bpy.context.scene.objects if o.type == 'MESH']) == 1
with tempfile.TemporaryDirectory() as destination:
    assert bpy.ops.export_mesh.all_stl_to_folder(folder_name='Joined', destination=destination) == {'FINISHED'}
    joined_files = list((Path(destination) / 'Joined').glob('*.stl'))
    assert len(joined_files) == 1
    assert struct.unpack_from('<I', joined_files[0].read_bytes(), 80)[0] == 24
    assert bpy.ops.export_mesh.all_stl_to_folder(folder_name='Split', destination=destination, keep_joined=False) == {'FINISHED'}
    split_files = list((Path(destination) / 'Split').glob('*.stl'))
    assert len(split_files) == 2
    assert all(struct.unpack_from('<I', p.read_bytes(), 80)[0] == 12 for p in split_files)
    bpy.ops.mesh.primitive_cube_add(location=(12, 0, 0))
    assert bpy.ops.export_mesh.all_stl_to_folder(folder_name='Selected', destination=destination, selected_only=True) == {'FINISHED'}
    assert len(list((Path(destination) / 'Selected').glob('*.stl'))) == 1
addon.unregister()
print('PASS: Ctrl+J joined cubes stay in one STL by default; checkbox off exports two loose parts')
