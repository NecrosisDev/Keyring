# Keyring

Adds a key ring to Exanima. Put your keys on the ring, then use the ring on a
locked door: if one of its keys fits, the door unlocks.

## Features

- A new item, the **Keyring**: a dark iron hoop with two worn display keys, one
  iron and one brass. It starts empty.
- Use the ring on itself in your inventory to open its storage, and put your
  keys in.
- Close the storage, then use the ring on a locked door. If a key on the ring
  fits, the door unlocks. A wrong key gets the game's usual response.
- Only ordinary keys placed directly on the ring count. The two display keys
  are decoration, and a ring stored inside another ring does not lend its keys.
- Where to find one: lying on a table in the first level, and as loot in
  civilians' personal belongings.

## Requirements

- Exanima (Steam).
- EMTK with the script-runtime startup patch. The Exanima Lua Runtime's README
  explains how to get it.
- Exanima Lua Runtime 0.28.0 or newer.

## Install

1. Install the Exanima Lua Runtime and its EMTK patch first, following the
   runtime's instructions.
2. Download `Keyring-<version>.zip` from the Releases page.
3. Close Exanima.
4. Copy the ZIP's `mods` folder into your Exanima game folder. You should end
   up with `Exanima\mods\com.necrosis.keyring`.
5. In your EMTK profile, enable both **Exanima Lua Runtime** and **Keyring**.
6. Launch the game through EMTK.

## Saves and uninstalling

Back up your saves before installing. The Lua runtime also makes a backup at
the title menu, but keep your own.

The ring on the table is added when the game builds the first level. A level
your save has already generated keeps its saved copy, so in an existing game
you will only find the ring as loot.

Once you pick up a ring, it is an item in your save. Keep the mod enabled for
any save that contains a ring, or go back to a save from before you installed
it. Deleting the mod's files does not remove the ring from existing saves.

## Notes for modders

The mod ships only its own item record and strings through the runtime's
`[script.records]` (item ID `0x590`, string indices 1201 to 1216), plus a loot
entry added to two civilian personal loot tables. The runtime merges these into
the installed database, so no whole database or level file is replaced. The
table placement is added through `levels.add_placement`.

## Building from source

The build reads the installed game (its database, strings, first level and the
Key A01 model), so it needs an installed copy of Exanima. It also needs an
ExaniMate workspace, which provides the `tools/exanimate` format library and the
Lua runtime's `records_delta.py` (in `mods/script-runtime/`).

```powershell
python -X utf8 -B release.py --workspace <ExaniMate workspace> --game <Exanima folder>
```

`--game` and `--workspace` can also come from the `EXANIMA_DIR` and
`EXANIMATE_WORKSPACE` environment variables. The build writes:

- `dist/mods/com.necrosis.keyring/`
- `dist/Keyring-<version>.zip` with a `.sha256` beside it

A previous `dist/mods/com.necrosis.keyring/` is moved to `dist/previous/` first.
Other options:

- `--zip-only` packages the mod folder already in `dist/` without building.
- `--tag v<version>` stops unless the tag matches the version in
  `manifest.toml`.

## License

MIT (see [LICENSE](LICENSE)).
