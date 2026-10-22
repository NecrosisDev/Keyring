"""Run in Blender background mode: drop three interlocked bodies and bake their resting mesh."""
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from mesh import components, METALS

out=Path(sys.argv[sys.argv.index('--')+1]).resolve()
if out.exists():
    raise RuntimeError('physics evidence folder must be new')
out.mkdir(parents=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.fps=60
scene.frame_start=1
scene.frame_end=660
scene.gravity=(0.,0.,-981.)
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=.01
C=Matrix(((1.,0.,0.,0.),(0.,0.,-1.,0.),(0.,1.,0.,0.),(0.,0.,0.,1.)))
materials={}
for name,(rgb,gloss) in METALS.items():
    colour=(*rgb,1.)
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=colour
    mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=colour
    shader.inputs['Metallic'].default_value=.85
    shader.inputs['Roughness'].default_value=1.-gloss
    materials[name]=mat

def make(name,points,faces):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata(points,[],faces)
    mesh.update()
    obj=bpy.data.objects.new(name,mesh)
    scene.collection.objects.link(obj)
    return obj

def rigid(obj,shape,mass=.04,passive=False):
    bpy.context.view_layer.objects.active=obj
    bpy.ops.rigidbody.object_add()
    rb=obj.rigid_body
    rb.type='PASSIVE' if passive else 'ACTIVE'
    rb.collision_shape=shape
    rb.mass=mass
    rb.friction=.72
    rb.restitution=.03
    rb.use_margin=True
    rb.collision_margin=.002
    rb.linear_damping=.35
    rb.angular_damping=.45
    rb.use_deactivation=True
    rb.deactivate_linear_velocity=.05
    rb.deactivate_angular_velocity=.05

parts=components(144,12)
groups={name:[] for name in ('hoop','key0','key1')}
for part in parts:
    name=part[0]
    group='hoop' if name in ('hoop','clasp') else 'key'+next(c for c in name if c.isdigit())
    groups[group].append(part)
initial=Matrix.Translation((0.,0.,7.))@__import__('mathutils').Euler((.38,.28,.17)).to_matrix().to_4x4()
roots={}
centers={}
for group,items in groups.items():
    points=[C@Vector(p) for _,_,vertices,_ in items for p in vertices]
    center=sum(points,Vector())/len(points)
    centers[group]=center
    root=make(group,[(p-center)[:] for p in points],[])
    root.matrix_world=initial@Matrix.Translation(center)
    rigid(root,'COMPOUND',.07 if group=='hoop' else .025)
    roots[group]=root
    for name,material,vertices,faces in items:
        local=[C@Vector(p)-center for p in vertices]
        if name=='hoop' or name.startswith('bow'):
            count=len(vertices)//12
            sections=[]
            for i in range(count):
                indices=list(range(i*12,(i+1)*12))+list(range(((i+1)%count)*12,((i+1)%count+1)*12))
                sections.append(([local[j][:] for j in indices],[(j,(j+1)%12,(j+1)%12+12,j+12) for j in range(12)]+[tuple(range(11,-1,-1)),tuple(range(12,24))]))
        else:
            sections=[([p[:] for p in local],faces)]
        for index,(vertices0,faces0) in enumerate(sections):
            child=make(f'{name}_collider_{index}',vertices0,faces0)
            child.parent=root
            child.matrix_parent_inverse=Matrix.Identity(4)
            child.matrix_basis=Matrix.Identity(4)
            rigid(child,'CONVEX_HULL')
            child.hide_render=True

bpy.ops.mesh.primitive_cube_add(size=1,location=(0.,0.,-.5))
floor=bpy.context.object
floor.name='FlatSurface'
floor.scale=(80.,80.,1.)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
rigid(floor,'BOX',passive=True)
world=scene.rigidbody_world
world.substeps_per_frame=40
world.solver_iterations=80
world.point_cache.frame_start=1
world.point_cache.frame_end=scene.frame_end
history=[]
for frame in range(1,scene.frame_end+1):
    scene.frame_set(frame)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    history.append({name:root.evaluated_get(depsgraph).matrix_world.copy() for name,root in roots.items()})
    if frame%60==0:
        print('PHYSICS_FRAME='+str(frame),flush=True)

def displacement(a,b):
    return max((a@p-b@p).length for p in (Vector((0.,0.,0.)),Vector((8.,0.,0.)),Vector((0.,8.,0.)),Vector((0.,0.,8.))))
motion=max(displacement(history[-1][name],sample[name]) for sample in history[-60:] for name in roots)
if motion>.01:
    raise RuntimeError(f'Bodies have not settled: {motion:.6f} cm movement over final second')
final=history[-1]
transforms={name:C.inverted()@final[name]@Matrix.Translation(-centers[name])@C for name in roots}
all_points=[]
for group,items in groups.items():
    all_points.extend(transforms[group]@Vector(p) for _,_,vertices,_ in items for p in vertices)
minimum_y=min(p.y for p in all_points)
if minimum_y<-.035:
    raise RuntimeError(f'Ground penetration {minimum_y:.6f} cm')
# Recenter only the complete assembly; preserve all relative simulated poses.
anchor=transforms['hoop']@Vector((0.,0.,0.))
shift=Matrix.Translation((-anchor.x,-minimum_y,-anchor.z))
transforms={name:shift@matrix for name,matrix in transforms.items()}
pose={'version':1,'solver':'Blender '+bpy.app.version_string+' / Bullet compound rigid bodies',
      'frames':scene.frame_end,'fps':60,'substeps':world.substeps_per_frame,'iterations':world.solver_iterations,
      'gravity_cm_s2':981,'last_second_max_motion_cm':motion,'floor_penetration_cm':max(0.,-minimum_y),
      'source_sha256':hashlib.sha256((HERE/'mesh.py').read_bytes()).hexdigest(),
      'transforms':{name:[list(row) for row in matrix] for name,matrix in transforms.items()}}
(out/'world_pose.json').write_text(json.dumps(pose,indent=2))

for root in roots.values():
    root.hide_render=True
for group,items in groups.items():
    for name,material,vertices,faces in items:
        points=[(final[group]@((C@Vector(p))-centers[group]))[:] for p in vertices]
        obj=make('Baked_'+name,points,faces)
        obj.data.materials.append(materials[material])
        for polygon in obj.data.polygons:
            polygon.use_smooth=name=='hoop' or name.startswith('bow')

floor_mat=bpy.data.materials.new('Surface')
floor_mat.diffuse_color=(.10,.105,.11,1.)
floor.data.materials.append(floor_mat)
scene.world=bpy.data.worlds.new('Studio')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.35,.38,.42,1.)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.6
baked=[obj for obj in scene.objects if obj.name.startswith('Baked_')]
bounds=[obj.matrix_world@vertex.co for obj in baked for vertex in obj.data.vertices]
target=Vector(((min(p.x for p in bounds)+max(p.x for p in bounds))/2,
               (min(p.y for p in bounds)+max(p.y for p in bounds))/2,.2))
bpy.ops.object.camera_add(location=target+Vector((8.,-10.,17.)))
camera=bpy.context.object
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=14.
scene.camera=camera
for location,power,size in (((-6.,-4.,12.),1500.,8.),((6.,4.,9.),1000.,6.)):
    bpy.ops.object.light_add(type='AREA',location=target+Vector(location))
    lamp=bpy.context.object
    lamp.data.energy=power
    lamp.data.shape='DISK'
    lamp.data.size=size
    lamp.rotation_euler=(target-lamp.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=32
scene.render.resolution_x=1100
scene.render.resolution_y=850
scene.render.resolution_percentage=100
scene.render.filepath=str(out/'settled-world.png')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'keyring-physics-and-bake.blend'))
bpy.ops.render.render(write_still=True)
print('PHYSICS_BAKE_PASSED='+json.dumps(pose),flush=True)
