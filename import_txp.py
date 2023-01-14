import mathutils
import bpy
import bpy_extras
import sys
import itertools
import imbuf
import tempfile
from bpy_extras import image_utils

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

def import_textures(path, tex_names):
    for name in tex_names:
        print(f"importing {name}")
        image = image_utils.load_image(
                    f"{name}.png",
                    dirname=path,
                    place_holder=True,
                    recursive=True,
                )
        image.name = name

def make_images(txp, tex_names):
    print("Importing txps")
    print(txp.textures)
    for txp_tex, name in zip(txp.textures, tex_names):
        if name in [x.name for x in bpy.data.images]:
            continue
        tex = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".dds", delete=False) as file:
                file.write(bytes(txp_tex.to_dds_bytes()))
                print(f"image is at {file.name}")
                tex = image_utils.load_image(
                        file.name,
                        place_holder=True,
                    )
                tex.name = name
        except Exception as e:
            if tex is not None:
                bpy.data.images.remove(tex)
            raise e
