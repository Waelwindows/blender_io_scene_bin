bl_info = {
    "name": "SEGA .bin format",
    "author": "Waelwindows",
    "version": (0, 1, 0),
    "blender": (2, 80, 0),
    "location": "File > Import-Export",
    "description": "SEGA .bin meshes, UV's vertex colors, materials, textures",
    "warning": "",
    # "doc_url": "{BLENDER_MANUAL_URL}/addons/import_export/scene_fbx.html",
    # "support": 'OFFICIAL',
    "category": "Import-Export",
}

import os
print(os.getcwd())

try:
    def reload_package(module_dict_main):
        """Reload Scripts."""
        import importlib
        from pathlib import Path

        def reload_package_recursive(current_dir, module_dict):
            exts = [".py" ".so" ".pyd"]
            for path in current_dir.iterdir():
                if "__init__" in str(path) or path.stem not in module_dict:
                    continue
                if path.is_file() and path.suffix in exts:
                    importlib.reload(module_dict[path.stem])
                elif path.is_dir():
                    reload_package_recursive(path, module_dict[path.stem].__dict__)

        reload_package_recursive(Path(__file__).parent, module_dict_main)

    if ".import_bin" in locals():
        reload_package(locals())
except ModuleNotFoundError as exc:
    print(exc)
    print('bpy not found.')

try:
    from . import objset
except ImportError:
    # import via PYTHONPATH
    import objset
try:
    from . import txp
except ImportError:
    # import via PYTHONPATH
    import txp
try:
    from . import diva_db
except ImportError:
    # import via PYTHONPATH
    import diva_db

import bpy
from bpy.props import (
        StringProperty,
        BoolProperty,
        FloatProperty,
        EnumProperty,
        CollectionProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper,
        path_reference_mode,
        axis_conversion,
        )

@orientation_helper(axis_forward='-Z', axis_up='Y')
class ImportBIN(bpy.types.Operator, ImportHelper):
    """Load a SEGA .bin file"""
    bl_idname = "import_scene.bin"
    bl_label = "Import SEGA .bin"
    bl_options = {'UNDO', 'PRESET'}

    filename_ext = ".bin"
    filter_glob: StringProperty(default="*_obj.bin", options={'HIDDEN'})

    files: CollectionProperty(
            name="File Path",
            type=bpy.types.OperatorFileListElement,
            )

    connect_child: BoolProperty(
            name="Connect Children",
            description="Connect bones with 1 child (this may cause bone orientations to get messed up)",
            default=False,
            )

    tex_db_path: StringProperty(
            name="Texture DB path",
            description="The path to the game's respective texture db. (usually named tex_db.bin)",
            subtype="FILE_PATH",
            )

    import_textures: BoolProperty(
            name="Import textures from TXP",
            description="Imports textures from the corresponding _tex.bin. (Requires tex_db to be set)",
            default=True,
            )

    def draw(self, context):
        pass

    def execute(self, context):
        from . import import_bin
        from . import import_txp
        import os

        if self.files:
            ret = {'CANCELLED'}
            dirname = os.path.dirname(self.filepath)
            for file in self.files:
                path = os.path.join(dirname, file.name)
                print((dirname, file.name))
                print(path)
                txp_path = os.path.join(dirname, file.name[:-7] + "tex.bin")
                print(txp_path)
                object_set = objset.object_set(path)
                atlas = txp.read(txp_path)
                if self.tex_db_path == "":
                    tex_db = None
                else:
                    tex_db = diva_db.tex.read_db(self.tex_db_path)
                tex_names = [tex_db.entries[x] if tex_db else "" for x in object_set.tex_ids]
                if self.import_textures:
                    import_txp.make_images(atlas, tex_names)
                else:
                    import_txp.import_textures(dirname, tex_names)
                for obj in object_set.objects:
                    import_bin.make_object(obj, tex_db, self.connect_child)
            ret = {'FINISHED'}
            return ret

class BIN_PT_import_include(bpy.types.Panel):
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'TOOL_PROPS'
    bl_label = "Include"
    bl_parent_id = "FILE_PT_operator"

    @classmethod
    def poll(cls, context):
        sfile = context.space_data
        operator = sfile.active_operator

        return operator.bl_idname == "IMPORT_SCENE_OT_bin"

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        layout.use_property_decorate = False  # No animation.

        sfile = context.space_data
        operator = sfile.active_operator

        layout.prop(operator, "connect_child")
        layout.prop(operator, "tex_db_path")
        layout.prop(operator, "import_textures")

def menu_func_import(self, context):
    self.layout.operator(ImportBIN.bl_idname, text="SEGA Object Set (_obj.bin)")

classes = (
    ImportBIN,
    BIN_PT_import_include,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    # bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    # bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
