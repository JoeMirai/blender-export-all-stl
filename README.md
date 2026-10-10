# Export All STL to Downloads

A small Blender add-on: click **Export All To…**, name your folder, and get one STL per mesh object inside a new folder under Downloads.

## Install and use

1. Download `export_all_stl.py` from this repository.
2. In Blender, open **Edit → Preferences → Add-ons → Install from Disk** (older versions: **Install**), select the Python file, and enable **Export All STL to Downloads**.
3. In the 3D viewport, press **N**, open **STL Export**, and click **Export All To…**.
4. Enter a folder name, optionally change the parent folder, and confirm.

Existing folders are preserved: repeated exports create `Folder (2)`, `Folder (3)`, etc. Object names become filenames; invalid characters and duplicate names are handled automatically.

Exports every mesh in the current scene, including hidden meshes, with evaluated modifiers and world transforms. Cameras, lights, curves, and collection instances are skipped. Convert curves to meshes first if needed. Work in Object Mode.

STL is unitless; coordinates use Blender units without automatic millimeter conversion. Selection is preserved. Designed for Blender 3.6+; tested in Blender 5.2.

## Verification

Run `blender --background --factory-startup --python tests/smoke.py` from this directory.
