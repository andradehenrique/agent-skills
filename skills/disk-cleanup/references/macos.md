# macOS specifics

## Why the actual gain can be smaller than the estimate

- **Local Time Machine and APFS snapshots.** While a snapshot references a deleted
  file, the space does not come back. macOS releases those snapshots on its own when
  the disk gets tight. To force it, the user runs
  `sudo tmutil thinlocalsnapshots / 999999999999 4`. The skill never runs
  commands with `sudo`.
- **APFS clones.** Copies made by Finder or `cp -c` share blocks, and `scan.py`
  cannot detect that cheaply. Deleting a clone may free less than the size shown.
- **Docker Desktop.** Images, containers and volumes live in a virtual disk
  (`~/Library/Containers/com.docker.docker/.../Docker.raw`). `prune` frees space
  inside that disk, but the file may take a while to shrink. Colima behaves the
  same way.
- **Hardlinks.** `scan.py` only counts an inode as freeable when all of its links are
  inside the item. The rest shows as "shared". The common case is pnpm's
  `node_modules`.
- **Apps that recreate the cache on the spot.** That is why app caches require the
  app to be closed (`requires_closed`).

## Permissions (TCC / Full Disk Access)

Some folders can only be read with "Full Disk Access" granted to the terminal:
`~/.Trash`, `~/Library/Mail`, `~/Library/Containers/*`, among others. Without that
permission, `scan.py` marks the item as a "partial read" and moves on. Do not ask
the user to grant access just for this skill; explaining that the size may be
underestimated is enough.

## Trash

The `trash` method moves the item to `~/.Trash`, renaming it when one with the same
name already exists. If `rename` fails (another volume, permission), the script asks
the Finder through `osascript`, which may open an Automation permission prompt.

## Process names for `requires_closed`

To find a process name, run `ps -axco comm=`. The main ones:

| Process | Name |
|---|---|
| Claude app | `Claude` |
| Cursor | `Cursor` |
| VS Code | `Code` (older versions: `Electron`) |
| Xcode | `Xcode` |
| Simulator | `Simulator` |
| Docker Desktop | `Docker Desktop` |

## Items left out on purpose

- **`/private/var/folders`**: system-managed temporaries; macOS cleans them itself.
- **iPhone backups** (`~/Library/Application Support/MobileSync`): personal data in a
  protected area. Point the user to the Finder (device tab).
- **`/Library/Caches`**: would only be touched with `sudo`.
