# PN Artwork Restorer

**A free, open-source tool to restore lost cover art after using Platinum Notes 10
with Mixed In Key 11 Pro (FLAC files on macOS and Windows)**

---

## Table of Contents

1. [What This Tool Does](#what-this-tool-does)
2. [Why It Exists](#why-it-exists)
3. [Installation — macOS](#installation--macos)
4. [Installation — Windows](#installation--windows)
5. [How to Use](#how-to-use)
6. [Running the Tests](#running-the-tests)
7. [Project Structure](#project-structure)
8. [Features](#features)
9. [Technical Notes](#technical-notes)
10. [License](#license)

---

## What This Tool Does

PN Artwork Restorer scans your music library and automatically copies the
embedded cover art (the `PICTURE` metadata block) from your Platinum Notes
backup files back into the processed FLAC files — without touching any other
tag, without moving any file, and without re-importing anything into Mixed In Key.

---

## Why It Exists

Many DJs and music producers use **Mixed In Key 11 Pro** together with
**Platinum Notes 10** to improve the loudness and dynamics of their library.

### The standard workflow

1. Mixed In Key analyses the library and adds tracks to the **"PN Improve Tracks"**
   playlist.
2. You drag those tracks into Platinum Notes 10.
3. In PN10 you enable **"Replace Original Files"** + **"Same folder as original
   file"** + **"Match Input Format"**.
4. PN10 creates a backup of every original file in a flat backup folder and
   replaces the original file in-place with the processed version.

Mixed In Key correctly detects the new files and keeps all playlists, hot cues,
energy levels, and keys intact. **However**, there is a well-known bug in
Platinum Notes 10:

> **Embedded artwork (the `PICTURE` metadata block in FLAC files) is frequently
> lost during the replace process on macOS.**

Restoring artwork manually for thousands of tracks is not feasible. This tool
automates the entire process.

---

## Installation — macOS

Follow every step exactly. Each command is shown in a grey box — copy and paste
it into **Terminal** (you can find Terminal in Applications → Utilities →
Terminal, or press **⌘ Space** and type `terminal`).

### Step 1 — Check that Python 3.10 or newer is installed

```
python3 --version
```

You should see something like `Python 3.12.3`. If you see an error, or a
version below 3.10, install Python from the official website:

1. Go to **https://www.python.org/downloads/**
2. Click the big **"Download Python 3.x.x"** button.
3. Open the downloaded `.pkg` file and follow the installer.
4. Open a new Terminal window and run `python3 --version` again.

---

### Step 2 — Download the project

**Option A — with Git (recommended)**

If you have Git installed:

```
git clone https://github.com/davetuner/PN_Artwork_Restorer.git
cd PN_Artwork_Restorer
```

**Option B — without Git**

1. Go to **https://github.com/davetuner/PN_Artwork_Restorer**
2. Click the green **"Code"** button → **"Download ZIP"**.
3. Double-click the downloaded ZIP to extract it.
4. In Terminal, navigate to the extracted folder. For example, if it was
   extracted to your Downloads folder:
   ```
   cd ~/Downloads/PN_Artwork_Restorer-main
   ```

---

### Step 3 — Create a virtual environment

A virtual environment keeps the tool's dependencies isolated from the rest of
your system so nothing ever conflicts.

```
python3 -m venv .venv
```

This creates a hidden folder called `.venv` inside the project folder. You only
need to do this once.

---

### Step 4 — Activate the virtual environment

```
source .venv/bin/activate
```

Your Terminal prompt will now start with `(.venv)` to show the environment is
active. **You need to run this command every time you open a new Terminal window
before using the tool.**

---

### Step 5 — Install the required library

```
pip install -r requirements.txt
```

This installs `mutagen`, the library used to read and write FLAC metadata.

---

### Step 6 — Launch the application

```
python3 pn_artwork_restorer.py
```

The GUI window will open. You are ready to use the tool (see
[How to Use](#how-to-use) below).

---

### Quick-start cheat sheet (macOS — after first setup)

Every subsequent time, open Terminal, navigate to the project folder, activate
the environment, and run:

```
cd ~/path/to/PN_Artwork_Restorer
source .venv/bin/activate
python3 pn_artwork_restorer.py
```

---

## Installation — Windows

Follow every step exactly. Each command is shown in a grey box — copy and paste
it into **Command Prompt** or **PowerShell**.

To open **Command Prompt**: press **Win + R**, type `cmd`, press **Enter**.  
To open **PowerShell**: press **Win + X** → click **Windows PowerShell**.

### Step 1 — Install Python 3.10 or newer

**Option A — Microsoft Store (easiest)**

1. Open the Microsoft Store.
2. Search for **Python 3.12** (or the latest 3.x version).
3. Click **Install**.

**Option B — python.org installer**

1. Go to **https://www.python.org/downloads/windows/**
2. Click **"Download Python 3.x.x"** (the latest stable release).
3. Run the installer.
4. ⚠️ On the first screen, tick **"Add Python to PATH"** before clicking
   Install Now. This is important — without it the commands below will not work.

Verify the installation worked:

```
python --version
```

You should see `Python 3.x.x`. If you see an error, close Command Prompt,
reopen it, and try again.

---

### Step 2 — Download the project

**Option A — with Git**

If you have Git for Windows installed (**https://git-scm.com/download/win**):

```
git clone https://github.com/davetuner/PN_Artwork_Restorer.git
cd PN_Artwork_Restorer
```

**Option B — without Git**

1. Go to **https://github.com/davetuner/PN_Artwork_Restorer**
2. Click the green **"Code"** button → **"Download ZIP"**.
3. Right-click the downloaded ZIP → **"Extract All…"** → choose a location.
4. In Command Prompt, navigate to the extracted folder. For example:
   ```
   cd C:\Users\YourName\Downloads\PN_Artwork_Restorer-main
   ```

---

### Step 3 — Create a virtual environment

```
python -m venv .venv
```

This creates a folder called `.venv` inside the project folder. You only need to
do this once.

---

### Step 4 — Activate the virtual environment

**Command Prompt:**

```
.venv\Scripts\activate.bat
```

**PowerShell:**

```
.venv\Scripts\Activate.ps1
```

> If PowerShell blocks the script with an error about execution policy, run this
> first:
> ```
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Then try `.venv\Scripts\Activate.ps1` again.

Your prompt will now start with `(.venv)` to confirm the environment is active.
**You need to activate the environment every time you open a new Command Prompt
or PowerShell window.**

---

### Step 5 — Install the required library

```
pip install -r requirements.txt
```

---

### Step 6 — Launch the application

```
python pn_artwork_restorer.py
```

The GUI window will open.

---

### Quick-start cheat sheet (Windows — after first setup)

Every subsequent time, open Command Prompt, navigate to the project folder,
activate the environment, and run:

```
cd C:\path\to\PN_Artwork_Restorer
.venv\Scripts\activate.bat
python pn_artwork_restorer.py
```

---

## How to Use

1. **Music Library Root** — Click **Browse…** and select the root folder that
   contains your entire music collection (the folder Platinum Notes processed
   files *into*). The tool will scan it recursively.

2. **PN Backup Folder** — Click **Browse…** and select the flat folder where
   Platinum Notes saved its backup copies of the original files.

3. **Dry Run** (default: ON) — Leave this ticked the first time you run the
   tool. It will show you exactly what it *would* do without modifying any
   files. Review the log, and when you are satisfied, untick it to run for real.

4. Click **Start Restoration**.

5. Watch the progress bar and log window. When it finishes, a summary popup
   shows how many files were processed.

6. Restart Mixed In Key — cover art will now be restored on all processed
   tracks.

---

## Running the Tests

The test suite uses **pytest** and requires no special setup beyond activating
the virtual environment.

```
python -m pytest tests/ -v
```

You should see all tests pass:

```
41 passed in 0.17s
```

The suite contains:
- **Unit tests** (`tests/test_core.py`) — test each method of `ArtworkRestorer`
  in isolation, covering normal operation, edge cases, and error handling.
- **Regression tests** (`tests/test_regression.py`) — exercise the full
  end-to-end workflow against a realistic fixture structure, including
  idempotency, data integrity, and large-batch smoke tests.

---

## Project Structure

```
PN_Artwork_Restorer/
├── pn_artwork_restorer.py   # Main application (GUI + core logic)
├── requirements.txt         # Python dependencies
├── README.md                # This file
├── LICENSE                  # MIT licence
├── .gitignore
├── example/                 # Illustrative directory layout (see example/README.md)
│   ├── library/
│   ├── pn_backups/
│   └── README.md
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Shared fixtures and helpers
│   ├── test_core.py         # Unit tests
│   └── test_regression.py   # Regression / integration tests
└── logs/                    # Log files (git-ignored; created on first run)
    └── .gitkeep
```

---

## Features

| Feature | Detail |
|---|---|
| Simple Tkinter GUI | No command line required |
| Dry Run mode | Default ON — preview before any file is changed |
| Live progress bar | Updates per file with percentage |
| Detailed log window | Colour-coded by severity (info / warning / error) |
| Full log file on disk | Written to `logs/PN_Artwork_Restorer.log` |
| Case-insensitive matching | `Song.flac` matches `SONG.FLAC` in backup |
| Duplicate handling | First occurrence wins; warning logged |
| Idempotent | Running twice leaves files in the same state |
| Safe | Never deletes or moves any file |
| Only FLAC | Only `.flac` files are processed |
| Cross-platform | macOS and Windows |

---

## Technical Notes

- **Matching strategy**: filenames are normalised to lower-case before
  comparison. Only the filename (not the path) is used for matching, so a flat
  backup folder can match a deeply nested library.
- **What is copied**: only the `PICTURE` metadata block(s). All other Vorbis
  comment tags, audio data, file names, and folder structure are left completely
  untouched.
- **What happens to existing artwork in the target**: it is cleared and replaced
  by the backup's artwork. This prevents duplicate picture blocks accumulating
  on repeated runs.
- **Logging**: all actions are written to `logs/PN_Artwork_Restorer.log`
  alongside the GUI log window. The log file is appended on each run so you
  have a complete history.

---

## License

MIT — see [LICENSE](LICENSE).
