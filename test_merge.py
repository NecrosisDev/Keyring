"""Exercise the real --merge-mod CLI with an additional key from another mod.

Run with the offline input folder, a NEW scratch folder and the installed game folder (or EXANIMA_DIR). Never
installs files. Level 1 always comes from the game's Resource.rpk and the keyring's spot is declared as a
placement, so the other mod's database records and strings must survive and no level file may ship.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import assets
from exanimate import rdb

inputs,work=map(lambda p:Path(p).resolve(),sys.argv[1:3])
game=Path(sys.argv[4] if len(sys.argv)>4 else os.environ['EXANIMA_DIR']).resolve()
work.mkdir(parents=True,exist_ok=False)
other=work/'other-mod'
resources=other/'assets/packages/Resource'
resources.mkdir(parents=True)
db=rdb.parse((inputs/'objdb.rdb').read_bytes())
old=next(r for r in db.records if r.name=='Key B01')
old.data=old.data.replace(b'Key B01'.ljust(16,b'\0'),b'Old B01'.ljust(16,b'\0'),1)
new=rdb.clone_record(db,old.id,'Key B01')
rdb.set_item_size(new,2)
(resources/'objdb.rdb').write_bytes(rdb.pack(db))
original={r.id:r.data for r in db.records}
strings_data=(inputs/'objstrings.rdb').read_bytes()
strings=rdb.strings_package(strings_data)+[(0,1,'Other mod text preserved')]
(resources/'objstrings.rdb').write_bytes(rdb.pack_strings(strings,strings_data))
output=work/'candidate'
reuse=['--runtime-candidate',str(Path(sys.argv[3]).resolve())] if len(sys.argv)>3 and sys.argv[3] else []
result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('build.py')),
    '--inputs',str(inputs),'--merge-mod',str(other),'--game',str(game),'--out',str(output)]+reuse,capture_output=True)
(work/'build-output.log').write_bytes(result.stdout+result.stderr)
assert result.returncode==0, result.stderr.decode(errors='replace')[-2000:]
report=json.loads((output/'assets-report.json').read_text())
mod=output/'mods/com.necrosis.keyring'
res=mod/'assets/packages/Resource'
merged=rdb.parse((res/'objdb.rdb').read_bytes()).by_id()
assert report['item_id']>new.id
assert report['largest_key_size']==2 and new.id in report['source_key_ids']
for rid,data in original.items():
    if rid not in report['changed_existing_records']:
        assert merged[rid].data==data, rid
assert rdb.strings_package((res/'objstrings.rdb').read_bytes())[:len(strings)]==strings
assert not (res/'exanima01.rfc').exists()
assert f"item = {report['item_id']}," in (mod/'scripts/placement.lua').read_text(encoding='utf-8')
print('KEYRING_MERGE_PASSED: existing records/strings preserved; added key accepted; ring placement declared, no level file shipped')
