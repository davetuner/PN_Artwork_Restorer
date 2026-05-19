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
10. [Troubleshooting](#troubleshooting)
11. [License](#license)

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

### Step 1 — Install Python 3.10 or newer via Homebrew (recommended on macOS)

> **Why Homebrew and not python.org?**
> The official Python.org installer bundles its own copy of Tcl/Tk (the GUI
> framework). On some macOS versions that copy of Tcl/Tk performs a hard
> build-number check and crashes with a message like
> `macOS 15 (1507) or later required, have instead 15 (1506)` — before any of
> our code has a chance to run. Homebrew's Python links against Homebrew's own
> Tcl/Tk which does **not** have this check, making it the most reliable choice
> on macOS.

**Option A — Homebrew (recommended)**

1. If Homebrew is not already installed, paste this into Terminal and press
   **Return**:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
   Follow the on-screen prompts (it may ask for your Mac login password).  
   *(You can skip this step if you already have Homebrew — test with `brew --version`.)*

2. Install Python and its Tcl/Tk GUI bindings:
   ```
   brew install python@3.12 python-tk@3.12
   ```
   > `python-tk@3.12` is required — Homebrew splits the GUI bindings into a
   > separate package and without it the app will fail to start with
   > `ERROR: tkinter is not available`.

3. Verify:
   ```
   /opt/homebrew/bin/python3 --version
   ```
   You should see `Python 3.12.x`.  
   > **Apple Silicon Mac (M1/M2/M3/M4)?** Homebrew lives at `/opt/homebrew`.  
   > **Intel Mac?** Homebrew lives at `/usr/local` — use
   > `/usr/local/bin/python3 --version` instead.

**Option B — python.org installer (not recommended on macOS 15)**

If you cannot use Homebrew:

1. Go to **https://www.python.org/downloads/**
2. Click the **"Download Python 3.x.x"** button (choose 3.12.x, *not* 3.13.x — 3.13 bundles the version of Tcl/Tk most likely to trigger the crash).
3. Open the downloaded `.pkg` file and follow the installer.
4. Open a new Terminal window and run `python3 --version`.

> If you see the `macOS 15 (1507) or later required` crash even after
> installing from python.org, switch to Option A (Homebrew) or see the
> [Troubleshooting](#troubleshooting) section.

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

**If you installed Python via Homebrew (recommended):**

Apple Silicon Mac:
```
/opt/homebrew/bin/python3 -m venv .venv
```

Intel Mac:
```
/usr/local/bin/python3 -m venv .venv
```

**If you installed Python via python.org:**
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

## Troubleshooting

### `macOS 15 (NNNN) or later required, have instead 15 (MMMM)` — app crashes immediately on macOS

**Cause:** The official Python.org installer bundles its own copy of Tcl/Tk
(the GUI framework used by `tkinter`). That bundled Tcl/Tk contains a hard
macOS build-number check written in C. When the check fails it calls `abort()`
— a hard crash that happens *before* any Python code runs, so no error
handling in our script can prevent it.

**Fix — switch to Homebrew Python** (one-time setup, ~5 minutes):

1. Install Homebrew if you haven't already:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

2. Install Python and its Tcl/Tk GUI bindings via Homebrew:
   ```
   brew install python@3.12 python-tk@3.12
   ```
   > `python-tk@3.12` is a **separate** Homebrew package — without it you get
   > `ERROR: tkinter is not available` even though Python itself works fine.

3. Delete your old virtual environment and recreate it with Homebrew's Python:

   Apple Silicon Mac (M1/M2/M3/M4):
   ```
   cd ~/path/to/PN_Artwork_Restorer
   rm -rf .venv
   /opt/homebrew/bin/python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   Intel Mac:
   ```
   cd ~/path/to/PN_Artwork_Restorer
   rm -rf .venv
   /usr/local/bin/python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Launch the app:
   ```
   python3 pn_artwork_restorer.py
   ```

The crash will not occur again because Homebrew's Tcl/Tk does not include the
build-number check.

---

### `ERROR: tkinter is not available` — app exits immediately on macOS with Homebrew Python

**Cause:** Homebrew intentionally splits Tcl/Tk support into a separate package
(`python-tk@3.12`). Installing only `python@3.12` gives you a Python interpreter
with no GUI toolkit.

**Fix — install the missing Homebrew package** (one command):

```
brew install python-tk@3.12
```

Then recreate your virtual environment so it picks up the newly installed
Tcl/Tk:

Apple Silicon Mac (M1/M2/M3/M4):
```
cd ~/path/to/PN_Artwork_Restorer
rm -rf .venv
/opt/homebrew/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Intel Mac:
```
cd ~/path/to/PN_Artwork_Restorer
rm -rf .venv
/usr/local/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then launch the app:
```
python3 pn_artwork_restorer.py
```

---

## License

MIT — see [LICENSE](LICENSE).
