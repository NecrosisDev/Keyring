# EMTK native startup update

This is a small source patch to the existing EMTK framework, based on upstream
revision `b422845374d579e155dd4a07d85b5ebc0f779650`. It restores the native-plugin
startup path that upstream currently leaves commented out. There is no second
bootstrap, proxy DLL, process injector or keyring activator in this package.

Install the included framework DLL beside the EMTK launcher once, while the
game is closed, after backing up its existing framework DLL. Keep an existing
native-enabled framework instead if it already performs this job. Thereafter,
enable Keyring in the normal profile and launch normally through EMTK.

The loader uses the same enabled, manifest-validated entries for assets and
native code, ordered by profile priority. An asset-only mod needs no legacy
native config. A native mod supplies `config.toml`, `enable` and `disable`;
disabled profile/config entries stay unloaded. A missing export, missing DLL,
path escape or declined enable is logged without preventing subsequent mods.
Loading and enabling run before the original game entry point, outside DllMain.
This update does not install the old GUI or change the archive hook provider.

Source changes are included in `emtk-startup.patch`, with upstream licenses and
source/build fingerprints. To rebuild, clone the upstream repository, check out
the revision above, initialize its submodules and apply the patch. From a Visual
Studio x64 developer command prompt with Rust nightly installed, run:

```text
cargo +nightly build --locked --release -p emtk_framework
```

On this machine, `legacy_stdio_definitions.lib` is installed only under the
MSVC OneCore x64 library directory. The successful build appended that directory
to `LIB`; no global environment or upstream dependency version was changed:

```bat
set "LIB=%LIB%;%VCToolsInstallDir%lib\onecore\x64"
```

The supplied test runner builds three owned fixture DLLs and exercises the real
profile loader. It checks enabled/disabled entries, missing exports, declined
activation, path confinement, continued loading after failure, and the real
Keyring.dll safely declining an unsupported test host. Tests do not launch or
attach to Exanima, and do not prove game startup or gameplay acceptance.

To roll back the framework, restore the backed-up framework DLL while the game
is closed. Save compatibility is separate: retain the keyring item mod for
saves containing it, or restore a pre-mod save.
