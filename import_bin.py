import mathutils
import bpy
import bpy_extras
import sys
import itertools
from . import objset

def pairwise(iterable):
    from itertools import tee, islice
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    return zip(a, islice(b, 1, None))


def make_uv(mesh, uv):
    if len(uv) != 0:
        uv_lay = mesh.uv_layers.new(do_init=False)
        for loop in mesh.loops:
            idx = loop.vertex_index
            uv_lay.data[loop.index].uv = uv[idx]

def make_vertex_color(mesh, col):
    if len(col) != 0:
        bpy.ops.mesh.vertex_color_add()
        for loop in mesh.loops:
            idx = loop.vertex_index
            mesh.vertex_colors[-1].data[loop.index].color = col[idx]

def get_group(obj, bone):
    try:
        return obj.vertex_groups[bone.name]
    except KeyError:
        bpy.ops.object.vertex_group_add()
        group = obj.vertex_groups[-1]
        group.name = bone.name
        return group

def make_weights(obj, dmesh, skel, group_weights):
    for submesh in dmesh.submeshes:
        sub = dmesh.get_submesh_vbo(submesh)
        for (i, bone_idx) in enumerate(submesh.bone_indicies):
            bone = skel.bones[bone_idx]
            weights = zip(range(sub.start, sub.end), group_weights[sub.start:sub.end])
            for (id, bone_weights) in weights:
                make_weight(i, id, obj, bone, bone_weights.first)
                make_weight(i, id, obj, bone, bone_weights.second)
                make_weight(i, id, obj, bone, bone_weights.third)
                make_weight(i, id, obj, bone, bone_weights.fourth)

def make_weight(i, id, obj, bone, group):
    if group.index is not None and group.index//3 == i:
        get_group(obj, bone).add([id], group.weight, "ADD")


def make_material(mesh, submesh, mats, tex_db):
    dmat = mats[submesh.material_index]
    mat = bpy.data.materials.new(name=dmat.name)
    mat.use_nodes = True
    out = mat.node_tree.nodes[1]
    mat.node_tree.nodes.remove(mat.node_tree.nodes[0])

    if dmat.shader == "CLOTH":
        shader_cloth(mat, dmat, tex_db, out)
    elif dmat.shader == "ITEM":
        shader_item(mat, dmat, tex_db)
    else:
        shader_cloth(mat, dmat, tex_db, out)

    mat.use_backface_culling = True
    mat.blend_method = "CLIP"
    mesh.materials.append(mat)


def shader_cloth(mat, dmat, tex_db, out):
    bsdf = mat.node_tree.nodes.new("ShaderNodeEeveeSpecular")

    for tex in dmat.textures:
        if tex_db is None:
            break
        tex_name = tex_db.entries[tex.id]
        try:
            image = bpy.data.images[tex_name]
            imnode = mat.node_tree.nodes.new("ShaderNodeTexImage")
            imnode.image = image
            if "TOONCURVE" in tex_name:
                bsdf.inputs[2].default_value = 0.4
            # COLOR MAP
            if tex.flags.map == 1 and "TOONCURVE" not in tex_name:
                imnode.name = "Diffuse"
                mat.node_tree.links.new(bsdf.inputs[0], imnode.outputs[0])
                mix = mat.node_tree.nodes.new("ShaderNodeMath")
                mix.operation = "SUBTRACT"
                mix.inputs[0].default_value = 1.
                mat.node_tree.links.new(mix.inputs[1], imnode.outputs[1])
                mat.node_tree.links.new(bsdf.inputs[4], mix.outputs[0])
            #SPECULAR MAP
            elif tex.flags.map == 3:
                imnode.name = "Specular"
                mix = mat.node_tree.nodes.new("ShaderNodeMixRGB")
                mix.blend_type = "MULTIPLY"
                mix.inputs[0].default_value = 1.
                mat.node_tree.links.new(mix.inputs[1], imnode.outputs[0])
                mat.node_tree.links.new(mix.inputs[2], imnode.outputs[1])
                mat.node_tree.links.new(bsdf.inputs[1], mix.outputs[0])

        except KeyError:
            print(f"Skipping `{tex_name}` as it's not loaded")
    mat.node_tree.links.new(out.inputs[0], bsdf.outputs[0])


def shader_item(mat, dmat, tex_db):
    out = mat.node_tree.nodes[-1]
    bsdf = mat.node_tree.nodes.new("ShaderNodeEmission")
    bsdf.inputs[1].default_value = 5.
    trans = mat.node_tree.nodes.new("ShaderNodeBsdfTransparent")
    mix = mat.node_tree.nodes.new("ShaderNodeMixShader")
    mat.node_tree.links.new(mix.inputs[1], trans.outputs[0])
    mat.node_tree.links.new(mix.inputs[2], bsdf.outputs[0])
    for tex in dmat.textures:
        if tex_db is None:
            break
        tex_name = tex_db.entries[tex.id]
        try:
            image = bpy.data.images[tex_name]
            imnode = mat.node_tree.nodes.new("ShaderNodeTexImage")
            imnode.image = image
            # COLOR MAP
            if tex.flags.map == 1 and "TOONCURVE" not in tex_name:
                mat.node_tree.links.new(bsdf.inputs[0], imnode.outputs[0])
                mat.node_tree.links.new(mix.inputs[0], imnode.outputs[1])

        except KeyError:
            print(f"Skipping `{tex_name}` as it's not loaded")
    print("going to connect to out")
    mat.node_tree.links.new(out.inputs[0], mix.outputs[0])


def make_mesh(dmesh, mats, skel, arm, tex_db):
    mesh = bpy.data.meshes.new(dmesh.name)  # add the new mesh
    obj = bpy.data.objects.new(mesh.name, mesh)
    col = bpy.data.collections.get("Collection")
    col.objects.link(obj)
    bpy.context.view_layer.objects.active = obj

    vbo = dmesh.vertex_buffers

    verts = vbo.positions
    faces = dmesh.get_mesh_indicies()

    mesh.from_pydata(verts, [], faces)

    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))

    # normals = [*itertools.chain.from_iterable(vbo.normals)]
    # mesh.vertices.foreach_set("normal", normals)
    mesh.use_auto_smooth = True
    # normal custom verts on each axis
    # mesh.normals_split_custom_set([(0, 0, 0) for l in mesh.loops])
    mesh.normals_split_custom_set_from_vertices(vbo.normals)

    mat_idx_faces = [len(x.indicies) for x in dmesh.submeshes]
    mat_idx_faces.insert(0, 0)
    midx_faces = list(pairwise(mat_idx_faces))
    # print(type(mesh))
    # print(dir(mesh))

    # for (id, (start, end)) in zip(mat_idx, midx_faces):
    #     print(f"id {id} from [{start}..{end}]")
    #     mat_len = len(mesh.materials)
    #     mat = bpy.data.materials.new(name=mats[id].name)
    #     mat.use_nodes = True
    #     mesh.materials.append(mat)
    #     for face in mesh.polygons:
    #         for submesh in dmesh.submeshes:
    #             if face.vertices in submesh.indicies:
    #                 face.material_index = mat_len

    # print(f"mesh polys: {len(mesh.polygons)}")
    # for poly in mesh.polygons:
    #     poly.material_index = 39
    for (submesh, (start, end)) in zip(dmesh.submeshes, midx_faces):
        # print(f"submesh polys: {len(submesh.indicies)}")
        if bpy.data.materials.find(mats[submesh.material_index].name) == -1:
            make_material(mesh, submesh, mats, tex_db)
        else:
            bpy.ops.object.material_slot_add()
            obj = bpy.context.active_object
            mat_slot = obj.material_slots[-1]
            mat_id = bpy.data.materials.find(mats[submesh.material_index].name)
            mat_slot.material = bpy.data.materials[mat_id]
        mat_idx = bpy.data.materials.find(mats[submesh.material_index].name)
        # print(f"setting from {start} to {end}")
        sub = dmesh.get_submesh_vbo(submesh)
        for face in mesh.polygons[start:end]:
            face.material_index = mat_idx
        # for face in submesh.indicies:
        #     for poly in mesh.polygons:
        #         pids = poly.vertices
        #         pids = (pids[0], pids[1], pids[2])
        #         if face == pids:
        #             poly.material_index = mat_idx

    make_uv(mesh, vbo.uv1)
    make_uv(mesh, vbo.uv2)
    make_uv(mesh, vbo.uv3)
    make_uv(mesh, vbo.uv4)
    
    make_vertex_color(mesh, vbo.color1)
    make_vertex_color(mesh, vbo.color2)

    make_weights(obj, dmesh, skel, vbo.weights)

    if skel is not None:
        bpy.ops.object.modifier_add(type='ARMATURE')
        obj.modifiers["Armature"].object = arm
    
    return mesh


def make_arm(skel, connect_children):
    bpy.ops.object.add(type="ARMATURE")
    bpy.ops.object.mode_set(mode='EDIT')
    arm = bpy.context.active_object
    bone_correction_matrix = bpy_extras.io_utils.axis_conversion(from_forward='X',
                                             from_up='Y',
                                             to_forward="Y",
                                             to_up="X",
                                             ).to_4x4()
    for b in skel.bones:
        bones = arm.data.edit_bones
        bpy.ops.armature.bone_primitive_add()
        bone = bones[-1]
        bone.name = b.name
        if "_ex" in b.name:
            bone.layers[1] = True
            bone.layers[0] = False
        bone.matrix = make_matrix(b.bind_pose()) @ bone_correction_matrix
        bone.length = 0.1
    for b in skel.bones:
        e = arm.data.edit_bones[b.name]
        parent = skel.parent(b)
        if parent is not None:
            parent = arm.data.edit_bones[parent.name]
            e.parent = parent
            if connect_children and len(parent.children) == 1:
                print(parent.children)
                parent.tail = e.head
                e.use_connect = True
        else:
            print(f"bone `{b.name}` has no parent")

    bpy.ops.object.mode_set(mode='OBJECT')

def make_root(skel, connect_children):
    if skel is None:
        bpy.ops.object.add(type="EMPTY")
        bpy.context.object.empty_display_size = 0.0001
        return bpy.context.active_object
    else:
        return make_arm(skel, connect_children)

def make_matrix(mat):
    return mathutils.Matrix([mat[0:4], mat[4:8], mat[8:12], mat[12:16]])


def make_object(obj, tex_db, connect_children):
    make_root(obj.skeleton, connect_children)
    root = bpy.context.active_object
    root.name = obj.name
    for mesh in obj.meshes:
        mesh = make_mesh(mesh, obj.materials, obj.skeleton, root, tex_db)
        child = bpy.context.active_object
        bpy.ops.object.shade_smooth()
        child.parent = root
            
    # for x in obj.skeleton.bones:
    #     print(f"id: {x.id}, {x.name} parent {x.parent}")
    bpy.ops.transform.rotate(value=1.5708, orient_axis='X', orient_type='GLOBAL', orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)), orient_matrix_type='GLOBAL', constraint_axis=(
        True, False, False), mirror=True, use_proportional_edit=False, proportional_edit_falloff='SMOOTH', proportional_size=1, use_proportional_connected=False, use_proportional_projected=False)

print("imported import_bin sucessfully")
