bl_info = {
    "name": "Export All STL to Downloads",
    "author": "JoeMirai",
    "version": (1, 2, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar > STL Export",
    "description": "Export every scene mesh into its own STL in a new folder",
    "category": "Import-Export",
}

import re
import struct
from pathlib import Path

import bpy
from bpy.props import BoolProperty, StringProperty


def downloads_directory():
    config = Path.home() / ".config" / "user-dirs.dirs"
    if config.exists():
        match = re.search(r'^XDG_DOWNLOAD_DIR="(.*)"$', config.read_text(), re.M)
        if match:
            return match.group(1).replace("$HOME", str(Path.home()))
    return str(Path.home() / "Downloads")


def safe_name(name):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .") or "Unnamed"


def triangle_groups(mesh, keep_joined):
    triangles = list(mesh.loop_triangles)
    if keep_joined:
        return [triangles]
    parents = list(range(len(mesh.vertices)))

    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    for edge in mesh.edges:
        a, b = edge.vertices
        parents[find(a)] = find(b)
    groups = {}
    for triangle in triangles:
        groups.setdefault(find(triangle.vertices[0]), []).append(triangle)
    return list(groups.values())


def write_stl(obj, depsgraph, path, keep_joined=True):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.transform(obj.matrix_world)
        mesh.calc_loop_triangles()
        groups = triangle_groups(mesh, keep_joined)
        for index, triangles in enumerate(groups, 1):
            output_path = path if len(groups) == 1 else path.with_name(f"{path.stem}_part_{index:03d}.stl")
            with output_path.open("wb") as output:
                output.write(b"Export All STL".ljust(80, b"\0"))
                output.write(struct.pack("<I", len(triangles)))
                for triangle in triangles:
                    a, b, c = (mesh.vertices[i].co for i in triangle.vertices)
                    # Reverse winding for mirrored objects so outward normals survive.
                    if obj.matrix_world.determinant() < 0:
                        b, c = c, b
                    normal = (b - a).cross(c - a).normalized()
                    output.write(struct.pack("<12fH", *normal, *a, *b, *c, 0))
        return len(groups)
    finally:
        evaluated.to_mesh_clear()


class EXPORTALLSTL_OT_export(bpy.types.Operator):
    bl_idname = "export_mesh.all_stl_to_folder"
    bl_label = "Export All To…"
    bl_description = "Create a new folder and export every mesh object separately"

    folder_name: StringProperty(name="Folder Name", default="STL Export")
    destination: StringProperty(name="Parent Folder", subtype="DIR_PATH")
    keep_joined: BoolProperty(
        name="Export Joined Objects Together",
        description="Keep all parts of each object in one STL, including parts joined with Ctrl+J. Disable to export loose parts separately",
        default=True,
    )

    selected_only: BoolProperty(
        name="Selected Objects Only", default=False,
        description="Export only selected mesh objects; select a joined object to export just that assembly",
    )
    include_hidden: BoolProperty(
        name="Include Hidden Objects", default=False,
        description="Also export hidden source and reference meshes when exporting the whole scene",
    )

    def invoke(self, context, event):
        self.destination = downloads_directory()
        if bpy.data.filepath:
            self.folder_name = Path(bpy.data.filepath).stem + " STLs"
        return context.window_manager.invoke_props_dialog(self, width=440)

    def draw(self, context):
        self.layout.prop(self, "folder_name")
        self.layout.prop(self, "destination")
        self.layout.prop(self, "keep_joined")
        self.layout.prop(self, "selected_only")
        row = self.layout.row()
        row.enabled = not self.selected_only
        row.prop(self, "include_hidden")
        self.layout.label(text="One STL per object." if self.keep_joined else "One STL per connected mesh part.")

    def execute(self, context):
        if context.mode != "OBJECT":
            self.report({"ERROR"}, "Switch to Object Mode before exporting")
            return {"CANCELLED"}
        source = context.selected_objects if self.selected_only else context.scene.objects
        objects = [obj for obj in source if obj.type == "MESH" and
                   (self.selected_only or self.include_hidden or obj.visible_get(view_layer=context.view_layer))]
        if not objects:
            self.report({"ERROR"}, "No mesh objects match the export options")
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
            exported = 0
            for obj in objects:
                base = safe_name(obj.name)
                name = base
                suffix = 2
                while name.casefold() in used:
                    name = f"{base} ({suffix})"
                    suffix += 1
                used.add(name.casefold())
                # Reserve names also against generated loose-part filenames.
                while any(p.stem.casefold() == name.casefold() or p.stem.casefold().startswith(name.casefold() + "_part_") for p in target.glob("*.stl")):
                    name = f"{base} ({suffix})"
                    suffix += 1
                exported += write_stl(obj, depsgraph, target / (name + ".stl"), self.keep_joined)
        except Exception as exc:
            self.report({"ERROR"}, f"Export failed: {exc}. Partial files may be in {target}")
            return {"CANCELLED"}
        self.report({"INFO"}, f"Exported {exported} STLs to {target}")
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
