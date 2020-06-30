import mathutils
import bpy
import bpy_extras
import sys
import itertools
import imbuf
from . import txp
from . import diva_db

def make_images(txp, tex_names):
    for (i, map) in enumerate(txp.maps):
        if len(map.sides) == 1:
            mip = map.sides[0].mipmaps[0]
            pixels = mip.to_rgba()
            if pixels is not None:
                try:
                    image = bpy.data.images[tex_names[i]]
                except KeyError:
                    bpy.ops.image.new(name=tex_names[i], width=mip.width, height=mip.height, generated_type='BLANK', float=True)
                image = bpy.data.images[tex_names[i]]
                print(len(pixels))
                pixels = itertools.chain.from_iterable(pixels)
                pixels = [(x/256)**2.2 for x in pixels]
                # pixels = list(pixels)
                image.pixels = pixels
