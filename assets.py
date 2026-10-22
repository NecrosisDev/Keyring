"""Build a keyring project from offline snapshots; never accesses a game install."""
import copy
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/exanimate'))
from exanimate import level, rdb, rfc, rfi
from surface import SIZE, uv_for, texture_rgba

MODEL = 'keyring_a'
MOD_NAME = 'Keyring'
VERSION = '0.3.0'
IDENTITY = (1., 0., 0., 0., 1., 0., 0., 0., 1.)

from mesh import geometry, components, collision_spheres, METALS

def transformed(point,matrix):
    return tuple(sum(matrix[i][j]*point[j] for j in range(3))+matrix[i][3] for i in range(3))

def body_for(name):
    return 'hoop' if name in ('hoop','clasp') else 'key'+next(c for c in name if c.isdigit())

def make_model(template, segments, sides, pose):
    model = copy.deepcopy(rfc.parse(template, MODEL))
    node = model.nodes[0]
    positions, uv, faces, vertex_ranges, triangle_ranges = [], [], [], [], []
    for material in METALS:
        first_vertex,first_triangle=len(positions),len(faces)
        for name,mat,points,triangles in components(segments,sides):
            if mat!=material:
                continue
            offset=len(positions)
            positions.extend(transformed(p,pose['transforms'][body_for(name)]) for p in points)
            uv.extend(uv_for(p) for p in points)
            faces.extend(tuple(offset+i for i in tri) for tri in triangles)
        vertex_ranges.append(rfc.MaterialRange(material,first_vertex,len(positions)-1))
        triangle_ranges.append(rfc.MaterialRange(material,first_triangle,len(faces)-1))
    indices = list(range(len(positions)))
    node.mesh = rfc.Mesh(0, [rfc.Stream(1, 0xf30001, positions), rfc.Stream(16, 0xf20010, uv)],
                         len(positions), [(0x10001, indices), (0x10010, indices), (2, indices)],
                         vertex_ranges, faces, triangle_ranges)
    model.materials=[]
    for name,(colour,gloss) in METALS.items():
        raw=bytearray(0xb8)
        struct.pack_into('<4f',raw,0x10,*colour,1.)
        struct.pack_into('<4f',raw,0x20,.38,.39,.40,1.)
        struct.pack_into('<4f',raw,0x34,.5,1.,gloss,.35)
        struct.pack_into('<4I',raw,0x44,0x100,7|0x20000,0,1)
        struct.pack_into('<I',raw,0x94,1)
        raw[0xac:0xaf]=b'mtl'
        texture=name+'_d'
        raw.extend(struct.pack('<4I4f2I16s',0x20000,0x38,0,0,1.,1.,0.,0.,0x30,0,texture.encode().ljust(16,b'\0')))
        model.materials.append(rfc.Material(name,[texture],bytes(raw)))
    model.material_slots=len(model.materials)
    model.order=['materials','nodes']+['unknown']*len(model.unknown)
    node.name = 'Keyring'
    node.rotation, node.translation = IDENTITY, (0., 0., 0.)
    lo = [min(p[i] for p in positions) for i in range(3)]
    hi = [max(p[i] for p in positions) for i in range(3)]
    node.center = tuple((lo[i] + hi[i]) * .5 for i in range(3))
    node.half_extents = tuple((hi[i] - lo[i]) * .5 + .001 for i in range(3))
    node.radius = max(math.dist(p, node.center) for p in positions) + .001
    body = next(c for c in node.unknown if c.tag == 0x3dd0b001)
    header = bytearray(body.data[:92])
    # Native rigid-body header and its four independent mass-frame points.
    cx,cy,cz=node.center
    hx,hy,hz=node.half_extents
    hy=max(hy,.3)
    tetra = [(cx-hx,cy+hy,cz),(cx-hx,cy-hy,cz),(cx+hx,cy,cz+hz),(cx+hx,cy,cz-hz)]
    struct.pack_into('<12f', header, 8, *(x for p in tetra for x in p))
    spheres = []
    for index,sphere in enumerate(collision_spheres()):
        body_name='hoop' if index<24 else 'key'+str((index-24)//16)
        spheres.append(transformed(sphere[:3],pose['transforms'][body_name])+(sphere[3],))
    sphere_data = struct.pack('<II', 0, len(spheres)) + b''.join(struct.pack('<4f', *s) for s in spheres)
    body.data = bytes(header) + struct.pack('<II', 0xcd00, len(sphere_data)) + sphere_data
    pick = next(c for c in node.unknown if c.tag == 0x3d0cec05)
    pick.data = struct.pack('<II6f', 40, 2, *lo, *hi)
    return model

def build(inputs, output):
    inputs, output = Path(inputs), Path(output)
    if output.exists():
        raise ValueError('output must be a new folder')
    pose_path=Path(__file__).with_name('world_pose.json')
    pose=json.loads(pose_path.read_text())
    if pose['source_sha256']!=hashlib.sha256(Path(__file__).with_name('mesh.py').read_bytes()).hexdigest():
        raise ValueError('world physics bake does not match the current source mesh')
    data = (inputs / 'objdb.rdb').read_bytes()
    strings_data = (inputs / 'objstrings.rdb').read_bytes()
    db, strings = rdb.parse(data), rdb.strings_package(strings_data)
    if any(r.model == MODEL for r in db.records):
        raise ValueError('input database already contains a keyring; merge from inputs without this mod to avoid duplicate items')
    source_keys=[r for r in db.records if (r.chunk(0x10000) or b'')[:2]==b'\x01\x00']
    largest_key=max([1]+[rdb.item_size(r) for r in source_keys])
    before = {r.id: r.data for r in db.records}
    pouch = next(r for r in db.records if r.name == 'Pouch A')
    key = next(r for r in db.records if r.name == 'Key A01')
    ring = rdb.clone_record(db, pouch.id, 'Keyring', MODEL)
    device = key.chunk(0x10000)
    ring.data += struct.pack('<II', 0x10000, len(device) + 8) + device
    ring.flags |= 0x10000
    ring.size = len(ring.data)
    rdb.set_container(ring, capacity=65535, largest=largest_key)
    rdb.set_item_size(ring, 1)
    strings += [(0, 1, MOD_NAME), (0, 1, 'An old metal hoop with two plain display keys threaded directly onto it. The display keys are decorative. Use the ring on itself in inventory to open its contents. Close the contents, then use the ring on a locked door.')]
    rdb.set_display_strings(ring, len(strings) - 1, len(strings))
    tables = [r for r in db.records if db.path(r) in ('+Drop Tables/Civ LC Personal', '+Drop Tables/Civ MC Personal')]
    for table in tables:
        rdb.add_drop_entry(db, table.id, ring.id, a=10)
    mod = output / 'mods/com.necrosis.keyring'
    resources, objects = mod / 'assets/packages/Resource', mod / 'assets/packages/Objects'
    resources.mkdir(parents=True)
    objects.mkdir(parents=True)
    (resources / 'objdb.rdb').write_bytes(rdb.pack(db))
    (resources / 'objstrings.rdb').write_bytes(rdb.pack_strings(strings, strings_data))
    # The ring's spot in level 1 is declared to the runtime (levels.add_placement), which adds it when the game
    # reads the level; the mod never ships a level file, so it cannot replace the installed level or another mod's.
    source_level = (inputs / 'exanima01.rfc').read_bytes()
    lv = level.parse(source_level)
    anchor_id=next(r.id for r in db.records if r.name=='Key B01')
    anchor = next((i for i in lv.items if (i.item & 0x7fffffff) == anchor_id), None)
    # The installed Hellmode level 1 has no loose Key B01 (no loose keys at all); there the ring lies on the table
    # "table_m_re a" (4976, -0.2, 1177), chosen from the level data (2026-10-22): nothing within 1.2 m but a saw.
    pos, yaw = ([anchor.pos[0] + 12., anchor.pos[1] + 1., anchor.pos[2]], 0.0) if anchor else ([4996.0, 86.0, 1192.0], 176.0)
    placement = (f'return {{level = "exanima01.rfc", item = {ring.id}, position = {{{pos[0]!r}, {pos[1]!r}, {pos[2]!r}}}, '
                 f'yaw = {yaw!r}}}\n')
    template = (inputs / 'key-a01.rfc').read_bytes()
    game_model, world_model = make_model(template, 72, 8, pose), make_model(template, 144, 12, pose)
    (objects / MODEL).write_bytes(rfc.pack(game_model))
    meshes = output / 'meshes'
    meshes.mkdir()
    textures=mod/'assets/packages/Textures'
    textures.mkdir()
    texture_pngs={}
    for material in METALS:
        pixels=texture_rgba(material)
        header=rfi.Header(SIZE,SIZE,1,0x0100E608,0x20000000|rfi.FLAG_MIPS,0x10000000,0).pack()
        (textures/(material+'_d')).write_bytes(rfi.encode(pixels,SIZE,SIZE,header))
        png=rfi.png_bytes(SIZE,SIZE,rfi.flip_v(pixels,SIZE,SIZE))
        (meshes/(material+'_d.png')).write_bytes(png)
        texture_pngs[material]=png
    (meshes / 'keyring-game.rfc').write_bytes(rfc.pack(game_model))
    (meshes / 'keyring-game.obj').write_text(rfc.to_obj(game_model), encoding='utf-8')
    (meshes / 'keyring-world.obj').write_text(rfc.to_obj(world_model), encoding='utf-8')
    gltf=rfc.to_gltf(game_model,textures=texture_pngs)
    for material in gltf['materials']:
        colour,gloss=METALS[material['name']]
        material['pbrMetallicRoughness'].update(baseColorFactor=[*colour,1.],metallicFactor=.85,roughnessFactor=1.-gloss)
    (meshes / 'keyring-game.gltf').write_text(json.dumps(gltf), encoding='utf-8')
    (mod / 'manifest.toml').write_text(f'[plugin]\nname = "{MOD_NAME}"\nversion = "{VERSION}"\n\n[script]\nruntime = "com.necrosis.script-runtime"\nentry = "scripts/main.lua"\nrequires = ["events.item_use", "items.read", "containers.read", "containers.open", "doors.unlock"]\noptional = ["levels.serve"]\n\n[script.modules]\nplacement = "scripts/placement.lua"\n')
    # This disabled legacy config also prevents an older extracted DLL from competing.
    (mod / 'config.toml').write_text(f'[plugin]\nid = "com.necrosis.keyring"\nname = "{MOD_NAME}"\nversion = "{VERSION}"\nsupported_versions = []\nurl = ""\nenabled = false\n[plugin.author]\nname = "NecrosisDev"\n')
    scripts=mod/'scripts'
    scripts.mkdir()
    (scripts/'main.lua').write_bytes(Path(__file__).with_name('scripts').joinpath('main.lua').read_bytes())
    (scripts/'placement.lua').write_text(placement, encoding='utf-8')
    changed = [r.id for r in db.records if r.id in before and r.data != before[r.id]]
    assert sorted(changed) == sorted(t.id for t in tables)
    assert not (resources / 'exanima01.rfc').exists()
    assert rfc.pack(rfc.parse((objects / MODEL).read_bytes())) == (objects / MODEL).read_bytes()
    report = {'item_id': ring.id, 'model': MODEL, 'world_physics_bake':pose, 'decorative_keys': 2, 'initial_contents': [], 'game_triangles': len(game_model.nodes[0].mesh.triangles),
              'world_triangles': len(world_model.nodes[0].mesh.triangles), 'world_placement': pos,
              'loot_tables': [db.path(t) for t in tables], 'changed_existing_records': changed,
              'source_key_ids': [r.id for r in source_keys], 'largest_key_size': largest_key,
              'input_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs.iterdir() if p.is_file()},
              'status': 'offline candidate; activation, rendering, persistence and gameplay unverified'}
    (output / 'assets-report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return mod
