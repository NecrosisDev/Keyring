"""Builds the ready-to-ship mod into dist/mods/com.necrosis.keyring from source.

Reads the installed game's own members (database, strings, level 1 and the Key A01 model), runs assets.py
(the Keyring record, its model, textures and level-1 placement), then the Lua runtime's records_delta.py to cut
the database down to this mod's [script.records] range, and assembles manifest, scripts, records and assets.
Files already in the dist folder are overwritten; nothing else is touched.

    python -X utf8 -B build.py [--game <Exanima folder>] [--workspace <Exanimate workspace>]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOD_ID = 'com.necrosis.keyring'
ID_RANGE = ('0x590', '0x590')
STRING_RANGE = ('1201', '1216')
INPUTS = {'objdb.rdb': ('Resource.rpk', 'objdb.rdb'), 'objstrings.rdb': ('Resource.rpk', 'objstrings.rdb'),
          'exanima01.rfc': ('Resource.rpk', 'exanima01.rfc'), 'key-a01.rfc': ('Objects.rpk', 'key a01')}
SHIPPED_ASSETS = ('Objects/keyring_a', 'Textures/kr_brass_d', 'Textures/kr_hoop_d', 'Textures/kr_iron_d')


def records_block(manifest: str) -> str:
    match = re.search(r'^\[script\.records\]\n(?:[^\[\n].*\n?)*', manifest, re.M)
    return match.group(0).strip() if match else ''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--game', type=Path, default=os.environ.get('EXANIMA_DIR'), required=not os.environ.get('EXANIMA_DIR'),
                        help='the Exanima folder (or set EXANIMA_DIR)')
    parser.add_argument('--workspace', type=Path, default=Path(os.environ['EXANIMATE_WORKSPACE']) if os.environ.get('EXANIMATE_WORKSPACE') else None,
                        required=not os.environ.get('EXANIMATE_WORKSPACE'))
    args = parser.parse_args()
    tools = args.workspace / 'tools' / 'exanimate'
    delta_tool = args.workspace / 'mods' / 'script-runtime' / 'records_delta.py'
    for needed in (tools, delta_tool, args.game / 'Resource.rpk', args.game / 'Objects.rpk'):
        if not needed.exists():
            parser.error(f'missing {needed}')
    os.environ['EXANIMATE_TOOLS'] = str(tools)
    sys.path.insert(0, str(tools))
    from exanimate import rpk
    import assets

    dist = ROOT / 'dist' / 'mods' / MOD_ID
    with tempfile.TemporaryDirectory(prefix='keyring-dist-') as staging:
        stage = Path(staging)
        inputs = stage / 'inputs'
        inputs.mkdir()
        for name, (archive, member) in INPUTS.items():
            (inputs / name).write_bytes(rpk.read(args.game / archive, member))
        built = assets.build(inputs, stage / 'full')
        subprocess.run([sys.executable, '-X', 'utf8', '-B', str(delta_tool), '--game', str(args.game),
                        '--full', str(built / 'assets/packages/Resource'), '--ids', *ID_RANGE, '--strings', *STRING_RANGE,
                        '--out', str(stage / 'delta')], check=True)

        # manifest.toml and scripts/placement.lua are kept in source; a build that would change them stops here.
        manifest = (ROOT / 'manifest.toml').read_text(encoding='utf-8')
        if records_block(manifest) != (stage / 'delta' / 'manifest-records.toml').read_text(encoding='utf-8').strip():
            raise SystemExit('manifest.toml [script.records] no longer matches the built records; update it')
        if (built / 'scripts/placement.lua').read_bytes() != (ROOT / 'scripts/placement.lua').read_bytes():
            raise SystemExit('scripts/placement.lua no longer matches the built placement; update it')

        for folder in ('scripts', 'records', 'assets/packages/Objects', 'assets/packages/Textures'):
            (dist / folder).mkdir(parents=True, exist_ok=True)
        for name in ('main.lua', 'placement.lua'):
            shutil.copyfile(ROOT / 'scripts' / name, dist / 'scripts' / name)
        for name in ('objdb.rdb', 'objstrings.rdb'):
            shutil.copyfile(stage / 'delta' / 'records' / name, dist / 'records' / name)
        for name in SHIPPED_ASSETS:
            shutil.copyfile(built / 'assets/packages' / name, dist / 'assets/packages' / name)
        for name in ('manifest.toml', 'LICENSE'):
            shutil.copyfile(ROOT / name, dist / name)
    print(f'KEYRING_BUILT={dist}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
