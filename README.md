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

The mod ships only its own records (`[script.records]`); the runtime merges them
into the installed database, so no whole database or level file is replaced.
The builder reads key IDs, placement anchor and sizes from the installed game
instead of a fixed key list.

```powershell
python -X utf8 -B release.py --workspace <Exanimate workspace> [--game <Exanima folder>]
```

This builds `dist/mods/com.necrosis.keyring/` through `build.py` (which reads the
installed game and the workspace's ExaniMate library and records-delta tool) and
writes `dist/Keyring-<version>.zip` with its SHA256. The Lua runtime ships as its
own package.

Keep this mod enabled for saves containing its item, or restore a pre-mod save
when removing it. Deleting files does not migrate existing saves.

Owned-process tests run real Lua, simulated game records/calls and real hook
chaining. They do not establish in-game startup, rendering, door use, combined
mod behavior or save/load acceptance. The existing ExaniMate editor/file APIs
remain unchanged; this adds the synchronous in-process scripting layer.
