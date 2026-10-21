# Changelog

## Stand Alone Save Editor (no game mods) v2.1.2 — Save-safety fixes

- Undo after a size-changing edit (Add Pack, knowledge inject, dyes, sockets,
  vendor clone, mercenary edits, quest inserts) no longer writes old bytes at
  shifted offsets. Those edits now keep a full snapshot, and undo restores it.
- Add Pack and Clone/Add to Vendor build new items from a live record in your
  save instead of the bundled templates, which use an older save format and
  broke the inventory/store parse. New items get a real item number instead of
  1, 2, 3... Every insert is re-checked and refused if the item parse is not
  complete afterwards.
- Add Pack no longer crashes after inserting (which invited inserting twice).
- The item list is rescanned after any insert, so later edits use current offsets.
- Fast Inject (Knowledge) blocks the window while it runs and discards its
  result if the save changed or another save was loaded meanwhile.
- Item Swap on small item keys (Copper, Camp Funds, ...) and Swap All only
  patch item-key fields instead of every matching value in the save.
- Prompts before closing or loading another save with unsaved edits.
- Warns before saving if the game is running or the save changed on disk since
  it was opened (an autosave).
- Dragon (Blackstar) No Quests: if the dragon is already in your mercenary
  list, it now adds the missing dragon knowledge instead of stopping. Quests
  are not touched.
- Quest Editor edits mark the save as modified.

## Stand Alone Save Editor (no game mods) v2.1.1 — Game 2.03.02 support

- Item list refreshed from the 2.03.02 client: 582 new items, current English
  names and stack limits (6,818 known records).
- "Refresh from local game" now reads English names and stack limits from the
  client's per-category `eng/item.paloc`, not just internal names.
- Removed false item matches in vendor data (shown as `Unknown (28)`,
  `Unknown (999)`, etc.). The schema parse is now authoritative when every
  item block parses.
- Items whose record omits the slot field, and second copies of an item number
  (equipped + bag), now appear in the list.
- Fixed edits on a duplicated item number landing on the other copy.
- Game-data features read the 2.01+ staticinfo archive names through the shared
  `dmm_parser`, which is now bundled with the build.

## Stand Alone Save Editor (no game mods) v2.1.0 (2.1.0) — Pre-release testing

This is a testing release. Use a copied save slot and keep the original backup
until the edited save has loaded successfully in-game.

### Save safety and current-game compatibility

- Added a native C++ backend for pre-load validation and validated SAVE writes.
- Validates HMAC, embedded PARC schema, TOC/object bounds, parse/serialize
  stability, schema fingerprint, written payload, and the reopened output.
- Writes through a temporary file and replaces the destination only after every
  validation succeeds.
- Rejects corrupt/HMAC-invalid saves and inspection-only raw streams instead of
  attempting to produce a potentially unusable SAVE container.
- Scalar item edits now use field offsets resolved from each loaded save's
  embedded schema rather than old release-era fixed offsets.
- Removed legacy automatic duplicate-item-ID rewriting during load. Opening or
  rescanning a save no longer silently modifies it.
- Validated against the supplied current-game slot107 and slot108 saves, which
  use different schema fingerprints and object counts.

### Offline operation and local content

- Removed GitHub/server refresh, updater, pack downloader, icon downloader,
  remote template sync, and other network control code rather than disabling it.
- Removed packaged Python HTTP/socket/SSL modules and QtNetwork/Web modules.
- Item names refresh directly from the locally installed Crimson Desert client.
- Current local scan contains 6,813 client items and 6,815 total known records.
- Item and template refreshes now persist beside the one-file executable.
- Icons use the optional `icons_local` pack placed next to the executable.
- Community templates can be imported/exported as local JSON files.

### Diagnostics and interface

- Added persistent `logs.txt` beside the executable, capturing startup details,
  Python output, Qt warnings, thread failures, native diagnostics, and full
  save-load/write tracebacks.
- Renamed the splash to **Crimson Save Editor Enhanced Update**.
- Renamed and widened **Auto-Detect Client** so its complete label remains visible.

### Known testing limitations

- This is the first hybrid backend release. Native C++ validates and writes the
  save, while some complex mutations—including template swaps, insertion, and
  repurchase operations—still originate in Python.
- Structural validation cannot guarantee that an incorrect donor/template will
  have the intended in-game appearance. Test complex equipment and vendor
  repurchase changes on disposable save copies.
- If anything fails, attach the generated `logs.txt` when reporting the issue.

### Release automation

- GitHub tag: `standalone-v2.1.0`
- Nexus Mods Group ID: `7306307`

### Attribution

This editor builds on the community-maintained Crimson Desert Save Editor v1.17
base by **jacobdyoung20-tech**. Original release:

https://github.com/jacobdyoung20-tech/CDesertGameMods/releases/tag/save-editor-v1.17-v11

## Crimson Save Editor Enhanced Update (offline 2.01)

- Combined the community socket, knowledge, startup, and theme improvements.
- Added local Crimson Desert client item-data scanning for current `staticinfo` archives.
- Refreshed the bundled item database from the installed client (6,815 records).
- Removed online updater, GitHub item/pack/icon refresh, and remote-download behavior.
- Icons are optional local assets: place an `icons_local` folder next to the executable.
- Improved the global game-path toolbar so the full Detect button remains visible.
- Disabled executable packing to reduce antivirus false-positive risk.

### Attribution

This editor builds on the community-maintained Crimson Desert Save Editor v1.17 base
by **jacobdyoung20-tech**. The original release and its socket, knowledge, startup,
and theme fixes are credited here:

https://github.com/jacobdyoung20-tech/CDesertGameMods/releases/tag/save-editor-v1.17-v11

This project modifies that base for an offline, locally maintained 2.0+ editor.
