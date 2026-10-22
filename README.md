# Keyring 0.3.0 — Lua addon candidate

The keyring now ships as assets and `scripts/main.lua`, without a per-addon DLL
or activator EXE. One shared Exanima Lua Runtime DLL provides the reviewed
engine operations and starts through EMTK. ExaniMate and ExCamera are not required.

The download is the standalone addon. Pair it with the
separate current Lua runtime package, which carries its framework update.
Older combined bundles are archived; avoid copying their older runtime over a
newer one. The builder below can still produce a combined developer bundle.

## Install and use

With Exanima closed and a pre-mod save backup preserved, copy the package's
`mods` folder into Exanima. Install the runtime package's framework update beside
the EMTK launcher once, after backing up its existing DLL. Keep your own framework
if it already supports this script-startup interface. Enable both **Exanima
Lua Runtime** and **Keyring** in the profile, then launch normally.

The supplied disabled legacy config.toml prevents an older extracted
Keyring.dll from loading. Leave it in place when upgrading. There is no game
version or executable-hash allowlist; the runtime checks its required operations.
This does not establish support for arbitrary changed native layouts.

The empty ring is placed in Story Level 1, about 12 cm beside Key B01, and in
civilian personal-loot tables. Already-generated saved levels do not gain the
placement automatically. Use the ring on itself in inventory to open storage;
add keys, close storage, then use the ring on a locked door. Only this ring's
direct committed ordinary keys participate. Wrong keys use native feedback.
Removed rows, nested rings and decorative mesh keys do not grant access.

The hoop is dark iron, with two different worn display keys in iron and brass.
Both mesh resolutions share the physics-settled pose. Display keys are geometry,
not items; the container starts empty.

## Compatibility and building

Whole-member database, strings and first-level replacements still require
composition. Repeat `--merge-mod <folder>` in load order to add the ring after
selected Resource inputs. Conflicts between those inputs must already be
resolved. Preserve composed item IDs across saves. The builder reads key IDs,
placement anchor and sizes from its inputs instead of a fixed key list.

```powershell
python -B <runtime>/build.py --out <runtime-out>
python -B build.py --inputs <inputs> --runtime-candidate <runtime-out> --emtk-startup <emtk-checkout> --out <new folder>
```

Omit --runtime-candidate to build the shared runtime during packaging. The
framework checkout needs the supplied patch and a matching startup-test receipt.
Source, licenses and build instructions accompany the framework update.

Keep this mod enabled for saves containing its item, or restore a pre-mod save
when removing it. Deleting files does not migrate existing saves.

Owned-process tests run real Lua, simulated game records/calls and real hook
chaining. They do not establish in-game startup, rendering, door use, combined
mod behavior or save/load acceptance. The existing ExaniMate editor/file APIs
remain unchanged; this adds the synchronous in-process scripting layer.
