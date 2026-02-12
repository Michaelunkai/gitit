# gitit - Bulletproof GitHub Push

Force-push ANY folder to GitHub with zero configuration.

## Features

- **Auto-creates repos** - Creates GitHub repo if it doesn't exist
- **Auto-excludes large files** - Skips files >100MB (GitHub limit)
- **Fresh init** - Always starts with clean git history
- **Handles nested repos** - Works even inside other git repos
- **Progress bar** - Visual feedback during operation
- **Timing** - Shows elapsed time

## Installation

### Windows (PowerShell)

The `gitit` command is already configured:
```powershell
gitit <folder_path>
```

### Manual Installation

1. Copy `a.py` to any location
2. Create batch wrapper:
```batch
@echo off
python "path/to/a.py" %*
```

## Usage

```bash
# Push current directory
gitit .

# Push specific folder
gitit "C:\Projects\MyApp"
gitit "F:\study\Dev_Toolchain\programming\.NET\projects\C#\StartupMaster"
```

## Output Example

```
Processing: C:\Projects\MyApp

[████████████████████████████████████████] 100% - Verifying

==================================================
SUMMARY
==================================================
Local files:      1173
Files staged:     1173
Large files:      6 (skipped)
Push success:     ✓ Yes
GitHub items:     36
Time elapsed:     45.2s
==================================================

✓ SUCCESS: MyApp
→ https://github.com/Michaelunkai/myapp
```

## Large Files

Files exceeding GitHub's 100MB limit are:
- Automatically detected
- Added to `.gitignore`
- NOT pushed (would fail anyway)

For large files, use [Git LFS](https://git-lfs.github.com).

## Requirements

- Python 3.7+
- Git
- GitHub CLI (`gh`) - for repo creation

## License

MIT
