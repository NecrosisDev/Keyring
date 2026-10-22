"""Refresh the saved baked Blender scene's materials without touching its geometry or pose."""
import hashlib
import json
import sys
from pathlib import Path

import bpy

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from mesh import METALS,components
from surface import SIZE,uv_for,texture_rgba

args=sys.argv[sys.argv.index('--')+1:]
source,out=Path(args[0]).resolve(),Path(args[1]).resolve()
if out.exists():
    raise RuntimeError('material preview output must be new')
out.mkdir(parents=True)
bpy.ops.wm.open_mainfile(filepath=str(source))
def geometry_hash():
    data={obj.name:[list(obj.matrix_world@v.co) for v in obj.data.vertices]
          for obj in bpy.context.scene.objects if obj.type=='MESH' and obj.name.startswith('Baked_')}
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
before=geometry_hash()
for name,(rgb,gloss) in METALS.items():
    material=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes=True
    material.diffuse_color=(*rgb,1.)
    shader=material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*rgb,1.)
    shader.inputs['Metallic'].default_value=.85
    shader.inputs['Roughness'].default_value=1.-gloss
    image=bpy.data.images.new(name+'_wear',width=SIZE,height=SIZE,alpha=True)
    image.colorspace_settings.name='Non-Color'
    image.pixels.foreach_set([v/255 for v in texture_rgba(name)])
    image.update()
    image.pack()
    nodes,links=material.node_tree.nodes,material.node_tree.links
    texture=nodes.new('ShaderNodeTexImage')
    texture.image=image
    texture.extension='REPEAT'
    multiply=nodes.new('ShaderNodeMixRGB')
    multiply.blend_type='MULTIPLY'
    multiply.inputs[0].default_value=1.
    multiply.inputs[1].default_value=(*rgb,1.)
    links.new(texture.outputs['Color'],multiply.inputs[2])
    links.new(multiply.outputs['Color'],shader.inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value=.12
    bump.inputs['Distance'].default_value=.008
    links.new(texture.outputs['Color'],bump.inputs['Height'])
    links.new(bump.outputs['Normal'],shader.inputs['Normal'])
for name,material,points,_ in components(144,12):
    obj=bpy.data.objects['Baked_'+name]
    obj.data.materials.clear()
    obj.data.materials.append(bpy.data.materials[material])
    uv=obj.data.uv_layers.new(name='WearUV')
    for loop in obj.data.loops:
        uv.data[loop.index].uv=uv_for(points[loop.vertex_index])
assert geometry_hash()==before
scene=bpy.context.scene
scene.render.filepath=str(out/'settled-world.png')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'keyring-physics-and-bake.blend'))
bpy.ops.render.render(write_still=True)
(out/'materials-report.json').write_text(json.dumps({'geometry_unchanged':True,'geometry_sha256':before,'materials':METALS},indent=2))
print('MATERIAL_REFRESH_PASSED: baked geometry and poses unchanged',flush=True)
