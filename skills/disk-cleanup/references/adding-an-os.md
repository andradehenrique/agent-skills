# How to add Linux or Windows

The flow (`SKILL.md`), the scripts and the plan format do not change. To bring the
skill to another OS, do three things.

## 1. Rules

Create `rules/linux.json` or `rules/windows.json` in the same format as
`rules/macos.json`. Before that, review `rules/common.json`: several rules already
have per-OS paths (`{"macos": [...], "linux": [...]}`) and only need the new key.

Starting points on Linux:

- caches in `~/.cache/*` (a generic rule, like the macOS `user-caches`);
- `~/.local/share/Trash` as 🔴;
- `journalctl --vacuum-time`, `apt clean` and `snap` with old revisions: they need
  `sudo`, so they stay 🔴 informational;
- Electron caches in `~/.config/<App>/Cache`;
- unused Flatpak: `flatpak uninstall --unused`.

Starting points on Windows:

- `%LOCALAPPDATA%\Temp`;
- `%LOCALAPPDATA%\<App>\Cache`;
- `%APPDATA%\Cursor\Cache`;
- npm at `%LOCALAPPDATA%\npm-cache`;
- WSL: the `ext4.vhdx` virtual disk does not shrink by itself, so it stays 🔴 with
  instructions;
- Docker Desktop with the same virtual disk problem.

## 2. OS-specific code in `scripts/common.py`

| Function | Linux | Windows |
|---|---|---|
| `current_os()` | already recognizes it | already recognizes it |
| `PROTECTED_HOME[<os>]` / `PROTECTED_ABS[<os>]` | fill in | fill in (`C:\Windows`, `C:\Program Files`, `%USERPROFILE%\OneDrive`…) |
| `allowed_roots()` | `/tmp`, `/var/tmp` | `%TEMP%` |
| `running_processes()` | `ps -eo comm=` (ready) | `tasklist` (ready, untested) |
| `move_to_trash()` | implement the freedesktop spec (`~/.local/share/Trash/files` + `.trashinfo`) | implement through `SHFileOperation` / PowerShell `Microsoft.VisualBasic.FileIO` |
| `measure()` | works (`st_blocks`) | no `st_blocks`: uses `st_size` and does not detect sparse files |

While `move_to_trash()` does not exist on an OS, `method: "trash"` rules fail with a
clear message and nothing is deleted.

## 3. Tests

Copy the cases from `evals/` that make sense and adapt the fixtures (fake HOME) to
the new OS.
