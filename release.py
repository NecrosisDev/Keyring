"""Packages the Keyring release from dist/mods/com.necrosis.keyring/: dist/Keyring-<version>.zip and its .sha256.

    python -X utf8 -B release.py [--tag v<version>]

The ZIP holds mods/com.necrosis.keyring/ as EMTK loads it from the Exanima folder. Its entries carry a fixed
timestamp, so the same files always give the same SHA256. This repository cannot rebuild the mod folder yet:
build.py still expects the workspace layout it was imported from, and the manifest and placement script exist
only in dist/. So this packages the mod folder as it stands. --tag stops unless the tag is v<manifest version>.
"""
import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = 'Keyring'
MOD_ID = 'com.necrosis.keyring'
DIST = ROOT / 'dist'


def version(mod: Path) -> str:
    match = re.search(r'^version = "([^"]+)"', (mod / 'manifest.toml').read_text(encoding='utf-8'), re.M)
    if not match:
        raise SystemExit(f'{mod / "manifest.toml"} has no version line')
    return match.group(1)


def package(mod: Path, name: str) -> Path:
    files = sorted(p for p in mod.rglob('*') if p.is_file())
    archive = mod.parents[1] / f'{name}-{version(mod)}.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        for path in files:
            info = zipfile.ZipInfo(f'mods/{mod.name}/{path.relative_to(mod).as_posix()}', date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            z.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + '.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(f'RELEASE={archive} files={len(files)} sha256={digest}')
    return archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--tag', help='release tag; must be v<manifest version>')
    args = parser.parse_args()
    mod = DIST / 'mods' / MOD_ID
    if not (mod / 'manifest.toml').is_file():
        raise SystemExit(f'no built mod in {mod}')
    if args.tag and args.tag != f'v{version(mod)}':
        raise SystemExit(f'tag {args.tag} does not match manifest version {version(mod)}')
    package(mod, NAME)
    return 0


if __name__ == '__main__':
    sys.exit(main())
