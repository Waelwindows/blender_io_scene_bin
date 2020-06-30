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

if "bpy" in locals():
    import importlib
    if "import_bin" in locals():
        importlib.reload(import_bin)
    if "import_txp" in locals():
        importlib.reload(import_txp)

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

    def draw(self, context):
        pass

    def execute(self, context):
        from . import objset
        from . import txp
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
                tex_db = diva_db.tex.read_db("/home/waelwindows/rust/diva_db/assets/aft_tex_db.bin")
                tex_names = [tex_db.entries[x] for x in object_set.tex_ids]
                import_txp.make_images(atlas, tex_names)
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
