bl_info = {
    "name": "Export All STL to Downloads",
    "author": "JoeMirai",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > STL Export",
    "description": "Export every scene mesh into its own STL in a new folder",
    "category": "Import-Export",
}

import os
import re
import struct
from pathlib import Path

import bpy
from bpy.props import StringProperty


def downloads_directory():
    config = Path.home() / ".config" / "user-dirs.dirs"
    if config.exists():
        match = re.search(r'^XDG_DOWNLOAD_DIR="(.*)"$', config.read_text(), re.M)
        if match:
            return match.group(1).replace("$HOME", str(Path.home()))
    return str(Path.home() / "Downloads")


def safe_name(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .") or "Unnamed"


def write_stl(obj, depsgraph, path):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.transform(obj.matrix_world)
        mesh.calc_loop_triangles()
        with path.open("wb") as output:
            output.write(b"Export All STL".ljust(80, b"\0"))
            output.write(struct.pack("<I", len(mesh.loop_triangles)))
            for triangle in mesh.loop_triangles:
                a, b, c = (mesh.vertices[i].co for i in triangle.vertices)
                # Reverse winding for mirrored objects so outward normals survive.
                if obj.matrix_world.determinant() < 0:
                    b, c = c, b
                normal = (b - a).cross(c - a).normalized()
                output.write(struct.pack("<12fH", *normal, *a, *b, *c, 0))
    finally:
        evaluated.to_mesh_clear()


class EXPORTALLSTL_OT_export(bpy.types.Operator):
    bl_idname = "export_mesh.all_stl_to_folder"
    bl_label = "Export All To…"
    bl_description = "Create a new folder and export every mesh object separately"

    folder_name: StringProperty(name="Folder Name", default="STL Export")
    destination: StringProperty(name="Parent Folder", subtype="DIR_PATH")

    def invoke(self, context, event):
        self.destination = downloads_directory()
        if bpy.data.filepath:
            self.folder_name = Path(bpy.data.filepath).stem + " STLs"
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        self.layout.prop(self, "folder_name")
        self.layout.prop(self, "destination")
        self.layout.label(text="One STL per mesh, including hidden scene objects.")

    def execute(self, context):
        if context.mode != "OBJECT":
            self.report({"ERROR"}, "Switch to Object Mode before exporting")
            return {"CANCELLED"}
        objects = [obj for obj in context.scene.objects if obj.type == "MESH"]
        if not objects:
            self.report({"ERROR"}, "No mesh objects in the scene")
            return {"CANCELLED"}
        folder = safe_name(self.folder_name)
        parent = Path(bpy.path.abspath(self.destination)).expanduser()
        target = parent / folder
        try:
            parent.mkdir(parents=True, exist_ok=True)
            suffix = 2
            while True:
                try:
                    target.mkdir()
                    break
                except FileExistsError:
                    target = parent / f"{folder} ({suffix})"
                    suffix += 1
            depsgraph = context.evaluated_depsgraph_get()
            used = set()
            for obj in objects:
                base = safe_name(obj.name)
                name = base
                suffix = 2
                while name.casefold() in used:
                    name = f"{base} ({suffix})"
                    suffix += 1
                used.add(name.casefold())
                write_stl(obj, depsgraph, target / (name + ".stl"))
        except Exception as exc:
            self.report({"ERROR"}, f"Export failed: {exc}. Partial files may be in {target}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Exported {len(objects)} STLs to {target}")
        return {"FINISHED"}


class EXPORTALLSTL_PT_panel(bpy.types.Panel):
    bl_label = "Export All STL"
    bl_idname = "EXPORTALLSTL_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "STL Export"

    def draw(self, context):
        self.layout.operator(EXPORTALLSTL_OT_export.bl_idname, icon="EXPORT")


classes = (EXPORTALLSTL_OT_export, EXPORTALLSTL_PT_panel)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
