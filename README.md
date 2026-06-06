# PN & MIK Artwork Restorer

**A free, open-source tool to restore lost cover art in FLAC files after using
Platinum Notes 10 or exporting playlists with Mixed In Key 11 Pro
(macOS and Windows)**

> Searches: *Platinum Notes 10 artwork bug*, *Mixed In Key 11 FLAC artwork lost*,
> *MIK11 export missing cover art*, *PN10 picture metadata stripped*,
> *restore embedded artwork FLAC DJ tool*

---

## Table of Contents

1. [What This Tool Does](#what-this-tool-does)
2. [Why It Exists](#why-it-exists)
3. [Installation — macOS](#installation--macos)
4. [Installation — Windows](#installation--windows)
5. [How to Use — PN Artwork Restorer tab](#how-to-use--pn-artwork-restorer-tab)
6. [How to Use — MIK Artwork Restorer tab](#how-to-use--mik-artwork-restorer-tab)
7. [Running the Tests](#running-the-tests)
8. [Project Structure](#project-structure)
9. [Features](#features)
10. [Technical Notes](#technical-notes)
11. [Troubleshooting](#troubleshooting)
12. [License](#license)

---

## What This Tool Does

This tool fixes **two separate artwork-stripping bugs** in the Platinum Notes 10
+ Mixed In Key 11 Pro suite, each addressed in its own tab:

| Tab | Problem fixed |
|---|---|
| **PN Artwork Restorer** | PN10 strips embedded cover art from FLAC files during its *Replace Original Files* processing on macOS. This tab copies artwork from the flat PN backup folder back into your library. |
| **MIK Artwork Restorer** | MIK 11 strips embedded cover art from FLAC files when you export playlists to separate folders. This tab copies artwork from your main music library into the exported folder tree. |

Neither tab touches audio data, moves files, or changes any other metadata tag.

---

## Why It Exists

Many DJs and music producers use **Mixed In Key 11 Pro** together with
**Platinum Notes 10** to improve the loudness and dynamics of their library.

### Bug 1 — Platinum Notes 10 strips artwork during library processing

The standard workflow:

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

The **PN Artwork Restorer** tab fixes this by copying artwork from the PN backup
folder back into the processed files.

### Bug 2 — Mixed In Key 11 strips artwork when exporting playlists

Mixed In Key 11 lets you export one or more playlists to separate folders (for
e.g. putting tracks on a USB stick). During this export:

> **Embedded artwork (the `PICTURE` metadata block) is stripped from every
> FLAC file that MIK copies into the export folder.**

This leaves you with a correctly organised folder of tracks that play fine in
your DJ software but display no cover art. Restoring artwork manually for
hundreds of exported tracks is not feasible.

The **MIK Artwork Restorer** tab fixes this by finding every exported FLAC file
in your MIK export tree, locating the matching original in your main music
library (matched by filename), and copying the intact artwork across.

Both bugs affect the same suite of software and are often encountered together.
This tool addresses both in a single application.

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

## How to Use — PN Artwork Restorer tab

1. **Music Library Root** — Click **Browse…** and select the root folder that
   contains your entire music collection (the folder Platinum Notes processed
   files *into*). The tool will scan it recursively.

2. **PN Backup Folder** — Click **Browse…** and select the flat folder where
   Platinum Notes saved its backup copies of the original files.
   The app remembers your last selected folders and reloads them at startup.

3. **Dry Run** (default: ON) — Leave this ticked the first time you run the
   tool. It will show you exactly what it *would* do without modifying any
   files. Review the log, and when you are satisfied, untick it to run for real.

4. Click **Start Restoration**.

5. Watch the progress bar and log window. When it finishes, a summary popup
   shows how many files were processed.

6. Restart Mixed In Key — cover art will now be restored on all processed
   tracks.

---

## How to Use — MIK Artwork Restorer tab

Use this tab after exporting playlists from Mixed In Key 11 to fix the missing
cover art in the exported files.

1. **MIK Export Root** — Click **Browse…** and select the root of the folder
   structure that Mixed In Key created when you exported your playlists. The
   tool will scan it recursively for `.flac` files.

2. **Music Library Root** — Click **Browse…** and select the root of your main
   music library — the folder that contains the same tracks *with their artwork
   intact*. The tool will scan this tree recursively to build a filename index.

3. **Dry Run** (default: ON) — Leave this ticked the first time. It shows
   exactly what would be copied without writing anything. Untick to run for real.

4. Click **Start Restoration**.

5. The tool matches files by filename (case-insensitive). For each exported
   FLAC it finds a file with the same name in your library and copies the
   `PICTURE` blocks across. All other tags and audio data are left untouched.

6. When finished, a summary shows how many files were restored, how many had no
   library match, and how many library files had no artwork to copy.

---

## Running the Tests

The test suite uses **pytest** and requires no special setup beyond activating
the virtual environment.

```
python -m pytest tests/ -v
```

You should see all tests pass:

```
82 passed in 0.xx s
```

The suite contains:
- **Unit tests** (`tests/test_core.py`) — test each method of `ArtworkRestorer`
  in isolation, covering normal operation, edge cases, and error handling.
- **MIK unit tests** (`tests/test_mik_restorer.py`) — same coverage for
  `MIKArtworkRestorer`.
- **Regression tests** (`tests/test_regression.py`) — exercise the full
  end-to-end workflow for both restorers against realistic fixture structures,
  including idempotency, data integrity, and large-batch smoke tests.

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
│   ├── test_core.py         # Unit tests for ArtworkRestorer
│   ├── test_mik_restorer.py # Unit tests for MIKArtworkRestorer
│   └── test_regression.py   # Regression / integration tests (both restorers)
└── logs/                    # Log files (git-ignored; created on first run)
    └── .gitkeep
```

---

## Features

| Feature | Detail |
|---|---|
| Two-tab GUI | Tab 1: PN Artwork Restorer &nbsp;·&nbsp; Tab 2: MIK Artwork Restorer |
| Simple Tkinter GUI | No command line required |
| Remembers last folders | Saves all four folder paths between app restarts |
| Dry Run mode | Default ON — preview before any file is changed |
| Live progress bar | Updates per file with percentage |
| Detailed log window | Colour-coded by severity (info / warning / error) |
| Full log file on disk | Written to `logs/PN_Artwork_Restorer.log` |
| Case-insensitive matching | `Song.flac` matches `SONG.FLAC` in source |
| Duplicate handling | First occurrence wins; warning logged |
| Idempotent | Running twice leaves files in the same state |
| Safe | Never deletes or moves any file |
| Only FLAC | Only `.flac` files are processed |
| Cross-platform | macOS and Windows |

---

## Technical Notes

- **Matching strategy**: filenames are normalised to lower-case before
  comparison. Only the filename (not the path) is used for matching.
  - *PN tab*: a flat backup folder matches a deeply nested library.
  - *MIK tab*: a deeply nested export tree matches a differently nested library;
    the same filename under any subdirectory is treated as a match.
- **What is copied**: only the `PICTURE` metadata block(s). All other Vorbis
  comment tags, audio data, file names, and folder structure are left completely
  untouched.
- **What happens to existing artwork in the target**: it is cleared and replaced
  by the source's artwork. This prevents duplicate picture blocks accumulating
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
(`python-tk@<python-version>`). Installing only `python@<python-version>` gives
you a Python interpreter with no GUI toolkit.

**Fix — if it still fails, use this verified recovery sequence**:

```
# 1. Install Tkinter for Python 3.14
brew install python-tk@3.14

# 2. Deactivate and delete the old venv
deactivate
rm -rf .venv

# 3. Create a fresh venv (it will now include tkinter)
/opt/homebrew/opt/python@3.14/libexec/bin/python -m venv .venv

# 4. Activate it
source .venv/bin/activate

# 5. Install requirements again
pip install --upgrade pip
pip install -r requirements.txt
```

Then launch the app:
```
python3 pn_artwork_restorer.py
```

---

## License

MIT — see [LICENSE](LICENSE).
