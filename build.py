"""Build the script-based keyring with the shared Lua runtime; never installs files."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
import assets
from exanimate import rpk  # assets puts tools/exanimate on the path

SOURCE=Path(__file__).resolve().parent
ROOT=SOURCE.parents[1]
RUNTIME=ROOT/'mods/script-runtime'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--merge-mod',type=Path,action='append',default=[])
    parser.add_argument('--runtime-candidate',type=Path,help='reuse a matching verified shared-runtime build')
    parser.add_argument('--emtk-startup',type=Path,help='bundle the compiled Lua-aware EMTK framework update')
    parser.add_argument('--game',type=Path,default=os.environ.get('EXANIMA_DIR'),
        help='installed game folder (or EXANIMA_DIR): level 1 is always read from its Resource.rpk, the level the game loads')
    args=parser.parse_args();out=args.out.resolve()
    if out.exists() or out.is_relative_to(ROOT/'release'):parser.error('use a new candidate folder outside release/')
    if not args.game or not (args.game/'Resource.rpk').is_file():parser.error('--game (or EXANIMA_DIR) must name the installed game folder')
    inputs=args.inputs.resolve()
    # Level 1 never comes from --inputs or another mod: an exanima01.rfc from an older game build there once
    # replaced the installed (Hellmode) level wholesale. Other mods' placements in it are not merged.
    merged=Path(tempfile.mkdtemp(prefix='Keyring-Merged-'))
    for name in ('objdb.rdb','objstrings.rdb','key-a01.rfc'):shutil.copyfile(inputs/name,merged/name)
    for source in args.merge_mod:
        resources=source/'assets/packages/Resource'
        if not resources.is_dir():parser.error(f'missing Resource directory: {resources}')
        for name in ('objdb.rdb','objstrings.rdb'):
            if (resources/name).is_file():shutil.copyfile(resources/name,merged/name)
    (merged/'exanima01.rfc').write_bytes(rpk.read(args.game.resolve()/'Resource.rpk','exanima01.rfc'))
    inputs=merged
    mod=assets.build(inputs,out)
    subprocess.run([sys.executable,'-B',str(SOURCE/'test_assets.py'),str(out)],check=True)
    native=args.runtime_candidate.resolve() if args.runtime_candidate else out/'runtime-build'
    if not args.runtime_candidate:
        subprocess.run([sys.executable,'-B',str(RUNTIME/'build.py'),'--out',str(native)],check=True)
    proof=json.loads((native/'verification.json').read_text())
    assert proof['native_tests']=='passed'
    assert proof['keyring_script_sha256']==digest(SOURCE/'scripts/main.lua')
    for name,expected in proof['files'].items():assert digest(native/name)==expected,name
    native_mod=native/'mods/com.necrosis.script-runtime'
    for file in (RUNTIME/'src').iterdir():assert digest(native_mod/'source'/file.name)==digest(file),file.name
    assert digest(native_mod/'source/shared/game_structs.h')==digest(ROOT/'continuation/game_structs.h'),'shared field definitions'
    for original,name in [('game_layout.h','game_layout.h'),('game_signatures.h','game_signatures.h'),('npc/npc_live.h','npc_live.h'),('hotload.h','hotload.h')]:
        assert digest(native_mod/'source/shared'/name)==digest(ROOT/'continuation'/original),name
    shutil.copytree(native_mod,out/'mods/com.necrosis.script-runtime')
    shutil.copytree(SOURCE/'scripts',mod/'source/scripts')
    for name in ('assets.py','mesh.py','surface.py','world_pose.json','bake_world.py','refresh_material_preview.py'):
        shutil.copyfile(SOURCE/name,mod/'source'/name)
    shutil.copytree(out/'meshes',mod/'source-meshes')
    shutil.copyfile(SOURCE/'README.md',mod/'README.md')
    shutil.copyfile(ROOT/'LICENSE',mod/'LICENSE')
    roots=[out/'mods']
    if args.emtk_startup:
        toolkit=args.emtk_startup.resolve();update=out/'EMTK-framework-update';update.mkdir()
        framework=toolkit/'target/release/emtk_framework.dll'
        startup=json.loads((toolkit/'startup-verification.json').read_text())
        assert startup['result']=='passed' and startup['framework_sha256']==digest(framework)
        assert startup['native_plugin_sha256']==digest(native_mod/'ScriptRuntime.dll')
        for name in ('LICENSE-MIT','LICENSE-APACHE'):shutil.copyfile(toolkit/name,update/name)
        shutil.copyfile(framework,update/framework.name)
        for name in ('emtk-startup.patch','EMTK-STARTUP.md','test_startup.py'):shutil.copyfile(RUNTIME/name,update/name)
        shutil.copytree(RUNTIME/'test_fixture',update/'test_fixture')
        shutil.copyfile(toolkit/'startup-verification.json',update/'startup-verification.json')
        (update/'INSTALL.txt').write_text('With Exanima closed, back up emtk_framework.dll beside your EMTK launcher.\nCopy this framework DLL beside that launcher once. Install the ZIP mods folder into Exanima.\nEnable Exanima Lua Runtime and Keyring in the profile, then launch normally through EMTK.\nNo addon EXE is required. Retain your current framework if it already supports this script API.\nUse the supplied disabled legacy keyring config to prevent an older Keyring.dll from loading.\nTo roll back the framework, restore its backup with Exanima closed. Save compatibility is separate.\n')
        (update/'SOURCE.json').write_text(json.dumps({'upstream':'https://github.com/ExanimaModding/Toolkit',
            'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=toolkit,text=True).strip(),
            'patch_sha256':digest(RUNTIME/'emtk-startup.patch'),'framework_sha256':digest(framework),
            'acceptance':'owned-process native/script startup; game unverified'},indent=2))
        roots.append(update)
    files={p.relative_to(out).as_posix():digest(p) for root in roots for p in sorted(root.rglob('*')) if p.is_file()}
    (out/'verification.json').write_text(json.dumps({'native_tests':'passed','lua_version':proof['lua_version'],
        'files':files,'status':'offline candidate; game startup and gameplay unverified'},indent=2))
    archive=out/f'Keyring-{assets.VERSION}-Lua-candidate.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for name in files:z.write(out/name,name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in z.namelist():assert z.read(name)==(out/name).read_bytes()
        assert not any(name.lower().endswith('.exe') or name.endswith('/Keyring.dll') for name in z.namelist())
        assert 'mods/com.necrosis.keyring/scripts/main.lua' in z.namelist()
    print('LUA_KEYRING_PACKAGE_PASSED='+str(archive))

if __name__=='__main__':main()
