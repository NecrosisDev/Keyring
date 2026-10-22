import json
import math
import struct
import sys
import unittest
from pathlib import Path

import assets
from mesh import attachment_clearance, collision_spheres, components, key_frame, KEYS, METALS
from surface import SIZE
from exanimate import level, rdb, rfc, rfi

class AssetTests(unittest.TestCase):
    def test_keys_have_different_bow_shapes(self):
        bows={name:points for name,_,points,_ in components(72,8) if name.startswith('bow')}
        corner_extent=[]
        for index,(angle,_) in enumerate(KEYS):
            origin,across,inward,_=key_frame(index,angle)
            vertices=bows['bow'+str(index)]
            centers=[tuple(sum(p[k] for p in vertices[j:j+8])/8-origin[k] for k in range(3)) for j in range(0,len(vertices),8)]
            corner_extent.append(max(abs(sum(p[k]*across[k] for k in range(3))/.60)+abs(sum(p[k]*inward[k] for k in range(3))/.74) for p in centers))
        self.assertLess(corner_extent[0],1.45)
        self.assertGreater(corner_extent[1],1.6)

    def test_key_bows_clear_hoop(self):
        for gap in attachment_clearance():
            self.assertGreater(gap, .05)

    def test_key_bows_pass_directly_through_hoop(self):
        crossings=(2.8-.74,2.8+.74)
        self.assertEqual([r<2.6-.19 for r in crossings],[True,False])
        self.assertEqual(len([name for name,_,_,_ in components(72,8) if name.startswith('bow')]),2)
        self.assertFalse(any(name.startswith('link') for name,_,_,_ in components(72,8)))

    def test_geometry(self):
        vertices, _, faces = assets.geometry(72, 8)
        edges = {}
        for tri in faces:
            self.assertEqual(len(set(tri)), 3)
            a, b, c = [vertices[i] for i in tri]
            u, v = [b[k] - a[k] for k in range(3)], [c[k] - a[k] for k in range(3)]
            cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
            self.assertGreater(sum(x*x for x in cross), 1e-12)
            for a, b in zip(tri, tri[1:] + tri[:1]):
                key = tuple(sorted((a, b)))
                edges.setdefault(key, []).append((a, b))
        self.assertTrue(all(len(e) == 2 and e[0] == e[1][::-1] for e in edges.values()))
        self.assertTrue(all(math.isfinite(x) for p in vertices for x in p))

    def test_candidate(self):
        output = Path(sys.argv[1])
        report = json.loads((output / 'assets-report.json').read_text())
        mod = output / 'mods/com.necrosis.keyring'
        db = rdb.parse((mod / 'assets/packages/Resource/objdb.rdb').read_bytes())
        ring = db.by_id()[report['item_id']]
        self.assertEqual(ring.model, assets.MODEL)
        self.assertEqual(rdb.container(ring)['capacity'], 65535)
        keys = [r for r in db.records if (r.chunk(0x10000) or b'')[:2] == b'\x01\x00' and r.id != ring.id]
        self.assertEqual({k.id for k in keys},set(report['source_key_ids']))
        self.assertEqual(rdb.container(ring)['largest item size'], report['largest_key_size'])
        self.assertTrue(all(rdb.item_size(k) <= rdb.container(ring)['largest item size'] for k in keys))
        # No level file ships; the placement is declared for the runtime's levels.add_placement.
        self.assertFalse((mod / 'assets/packages/Resource/exanima01.rfc').exists())
        placement = (mod / 'scripts/placement.lua').read_text(encoding='utf-8')
        self.assertIn(f'item = {ring.id},', placement)
        self.assertIn('level = "exanima01.rfc"', placement)
        model = rfc.parse((mod / 'assets/packages/Objects/keyring_a').read_bytes())
        node = model.nodes[0]
        for point in node.mesh.stream(1).data:
            self.assertTrue(all(abs(point[i] - node.center[i]) <= node.half_extents[i] for i in range(3)))
        rigid = next(c.data for c in node.unknown if c.tag == 0x3dd0b001)
        tag, size, zero, count = struct.unpack_from('<4I', rigid, 92)
        self.assertEqual((tag, zero, count), (0xcd00, 0, len(collision_spheres())))
        self.assertEqual(len(rigid), 100 + size)
        self.assertEqual(struct.unpack_from('<I', ring.chunk(0x20000), 20)[0], 0)
        self.assertEqual(report['decorative_keys'], 2)
        self.assertEqual({m.name for m in model.materials}, set(METALS))
        self.assertEqual({r.name for r in node.mesh.vertex_materials}, set(METALS))
        self.assertGreaterEqual(min(p[1] for p in node.mesh.stream(1).data),-.005)
        pose=report['world_physics_bake']
        self.assertLess(pose['last_second_max_motion_cm'],.01)
        self.assertEqual(set(pose['transforms']),{'hoop','key0','key1'})
        for mat in model.materials:
            colour=rfc.material_params(mat.raw)['diffuse'][:3]
            if mat.name!='kr_brass':
                self.assertLess(max(colour)-min(colour),.05)
            self.assertEqual(mat.textures,[mat.name+'_d'])
            data=(mod/'assets/packages/Textures'/(mat.name+'_d')).read_bytes()
            w,h,pixels=rfi.decode(data)
            self.assertEqual((w,h),(SIZE,SIZE))
            self.assertTrue(rfi.parse_header(data).has_mips)
            self.assertGreater(max(pixels[0::4])-min(pixels[0::4]),50)
        colours={m.name:rfc.material_params(m.raw)['diffuse'][:3] for m in model.materials}
        brightness=lambda rgb:sum(a*b for a,b in zip(rgb,(.2126,.7152,.0722)))
        self.assertGreater(brightness(colours['kr_iron']),2.5*brightness(colours['kr_hoop']))
        self.assertGreater(math.dist(colours['kr_iron'],colours['kr_brass']),.25)
        parts=components(72,8)
        self.assertEqual({material for name,material,_,_ in parts if assets.body_for(name)=='key0'},{'kr_iron'})
        self.assertEqual({material for name,material,_,_ in parts if assets.body_for(name)=='key1'},{'kr_brass'})
        self.assertGreater(len(set(node.mesh.stream(16).data)),100)

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AssetTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
