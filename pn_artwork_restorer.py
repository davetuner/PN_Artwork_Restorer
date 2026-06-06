#!/usr/bin/env python3
"""
PN Artwork Restorer
===================
Restores lost cover art (PICTURE metadata blocks) in FLAC files after using
Platinum Notes 10 with Mixed In Key 11 Pro on macOS or Windows.

Usage:
    python pn_artwork_restorer.py        # launch the GUI
    python -m pytest tests/              # run the test suite

Requires:
    Python 3.10+
    mutagen  (pip install mutagen)
    tkinter  (bundled with most Python distributions)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
from pathlib import Path

try:
    from mutagen.flac import FLAC, Picture
except ImportError:  # pragma: no cover
    print(
        "ERROR: mutagen is not installed.\n"
        "Please activate your virtual environment and run:\n"
        "    pip install mutagen"
    )
    sys.exit(1)

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, scrolledtext, ttk

    HAS_TKINTER = True
except ImportError:  # pragma: no cover
    HAS_TKINTER = False

# ---------------------------------------------------------------------------
# Module-level logger (handlers added only when running as __main__)
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)
CONFIG_FILENAME = ".pn_artwork_restorer_config.json"


def _config_file() -> Path:
    """Return the user config file path for GUI settings."""
    return Path.home() / CONFIG_FILENAME


def _load_saved_paths(config_path: Path | None = None) -> dict[str, str]:
    """Load last-used folders from config, falling back to empty values."""
    defaults = {
        "library_root": "",
        "backup_folder": "",
        "mik_export_root": "",
        "mik_library_root": "",
    }
    path = config_path or _config_file()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return defaults

    if not isinstance(payload, dict):
        return defaults

    def _str(key: str) -> str:
        val = payload.get(key, "")
        return val if isinstance(val, str) else ""

    return {
        "library_root": _str("library_root"),
        "backup_folder": _str("backup_folder"),
        "mik_export_root": _str("mik_export_root"),
        "mik_library_root": _str("mik_library_root"),
    }


def _save_saved_paths(
    library_root: str,
    backup_folder: str,
    mik_export_root: str = "",
    mik_library_root: str = "",
    config_path: Path | None = None,
) -> None:
    """Persist last-used folders for the next app launch."""
    path = config_path or _config_file()
    payload = {
        "library_root": library_root,
        "backup_folder": backup_folder,
        "mik_export_root": mik_export_root,
        "mik_library_root": mik_library_root,
    }

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not save config file %s: %s", path, exc)

# ---------------------------------------------------------------------------
# Core logic — no GUI dependency whatsoever
# ---------------------------------------------------------------------------


def _copy_artwork_blocks(
    source_path: Path, target_path: Path, dry_run: bool
) -> tuple[bool, str]:
    """
    Copy every PICTURE block from *source_path* into *target_path*.

    Returns ``(success, message)``.  In dry-run mode the file is **not**
    modified; only ``success=True`` and a ``[DRY RUN]`` message are returned.
    """
    try:
        source_flac = FLAC(str(source_path))
    except Exception as exc:
        return False, f"Cannot open source file: {exc}"

    pictures = source_flac.pictures
    if not pictures:
        return False, "Source file has no embedded artwork"

    if dry_run:
        return True, f"[DRY RUN] Would restore {len(pictures)} picture(s)"

    try:
        target_flac = FLAC(str(target_path))
        target_flac.clear_pictures()
        for pic in pictures:
            target_flac.add_picture(pic)
        target_flac.save()
    except Exception as exc:
        return False, f"Cannot write target file: {exc}"

    return True, f"Restored {len(pictures)} picture(s)"


class ArtworkRestorer:
    """
    Scans a music library tree and copies PICTURE blocks from matching files
    in a flat Platinum Notes backup folder.

    Parameters
    ----------
    library_root:
        Root directory of the music library (searched recursively).
    backup_folder:
        Flat directory that Platinum Notes wrote backup files into.
    dry_run:
        When True (default) no files are written; actions are only logged.
    progress_callback:
        Called as ``progress_callback(current: int, total: int)`` after each
        library file is processed.
    log_callback:
        Called as ``log_callback(message: str, level: str)`` where *level* is
        one of ``"info"``, ``"warning"``, ``"error"``, ``"debug"``.
    """

    def __init__(
        self,
        library_root: str | Path,
        backup_folder: str | Path,
        dry_run: bool = True,
        progress_callback=None,
        log_callback=None,
    ) -> None:
        self.library_root = Path(library_root)
        self.backup_folder = Path(backup_folder)
        self.dry_run = dry_run
        self._progress_cb = progress_callback or (lambda current, total: None)
        self._log_cb = log_callback or (lambda msg, level="info": None)

    # ------------------------------------------------------------------
    # Public helpers — individually unit-testable
    # ------------------------------------------------------------------

    def build_backup_dict(self) -> tuple[dict[str, Path], list[str]]:
        """
        Scan *backup_folder* (flat, non-recursive) and return:

        * ``backup_dict``  – ``{filename.lower(): Path}``
        * ``duplicates``   – lower-case names that appeared more than once
          (only the *first* occurrence is kept in ``backup_dict``).
        """
        backup_dict: dict[str, Path] = {}
        duplicates: list[str] = []

        for entry in self.backup_folder.iterdir():
            if entry.is_file() and entry.suffix.lower() == ".flac":
                key = entry.name.lower()
                if key in backup_dict:
                    if key not in duplicates:
                        duplicates.append(key)
                    self._log_cb(
                        f"WARNING: duplicate filename in backup folder: {entry.name}",
                        "warning",
                    )
                else:
                    backup_dict[key] = entry

        return backup_dict, duplicates

    def find_library_files(self) -> list[Path]:
        """Return all ``.flac`` files under *library_root* (recursive, sorted)."""
        return sorted(self.library_root.rglob("*.flac"))

    def restore_artwork_for_file(
        self, target_path: Path, backup_path: Path
    ) -> tuple[bool, str]:
        """
        Copy every PICTURE block from *backup_path* into *target_path*.

        Returns ``(success, message)``.  In dry-run mode the file is **not**
        modified; only ``success=True`` and a ``[DRY RUN]`` message are returned.
        """
        try:
            backup_flac = FLAC(str(backup_path))
        except Exception as exc:
            return False, f"Cannot open backup file: {exc}"

        pictures = backup_flac.pictures
        if not pictures:
            return False, "Backup file has no embedded artwork"

        if self.dry_run:
            return True, f"[DRY RUN] Would restore {len(pictures)} picture(s)"

        try:
            target_flac = FLAC(str(target_path))
            target_flac.clear_pictures()
            for pic in pictures:
                target_flac.add_picture(pic)
            target_flac.save()
        except Exception as exc:
            return False, f"Cannot write target file: {exc}"

        return True, f"Restored {len(pictures)} picture(s)"

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """
        Execute the full restoration pass.

        Returns a summary ``dict`` with keys:
        ``total``, ``matched``, ``no_backup``, ``no_artwork_in_backup``,
        ``errors``, ``duplicate_backups``, ``duplicate_library_filenames``.
        """
        self._log_cb("Building backup index…", "info")
        backup_dict, duplicates = self.build_backup_dict()
        self._log_cb(
            f"Backup index: {len(backup_dict)} unique file(s), "
            f"{len(duplicates)} duplicate filename(s) (first copy kept)",
            "info",
        )

        self._log_cb("Scanning music library…", "info")
        library_files = self.find_library_files()
        total = len(library_files)
        self._log_cb(f"Library scan: {total} FLAC file(s) found", "info")
        library_name_counts: dict[str, int] = {}
        for lib_path in library_files:
            key = lib_path.name.lower()
            library_name_counts[key] = library_name_counts.get(key, 0) + 1
        duplicate_library_filenames = sum(
            count - 1 for count in library_name_counts.values() if count > 1
        )

        matched = 0
        no_backup = 0
        no_artwork = 0
        errors = 0
        restored_files: list[Path] = []

        for idx, lib_path in enumerate(library_files, start=1):
            self._progress_cb(idx, total)

            key = lib_path.name.lower()
            if key not in backup_dict:
                no_backup += 1
                continue

            backup_path = backup_dict[key]
            success, msg = self.restore_artwork_for_file(lib_path, backup_path)

            if success:
                matched += 1
                restored_files.append(lib_path)
            else:
                if "no embedded artwork" in msg.lower():
                    no_artwork += 1
                    self._log_cb(
                        f"Skipped (no artwork in backup): {lib_path.name}", "warning"
                    )
                else:
                    errors += 1
                    self._log_cb(f"ERROR: {msg} | file: {lib_path}", "error")

        if restored_files:
            heading = (
                "Files that would be restored:"
                if self.dry_run
                else "Files restored:"
            )
            self._log_cb(heading, "info")
            for restored in restored_files:
                try:
                    display_path = restored.relative_to(self.library_root)
                except ValueError:
                    display_path = restored
                self._log_cb(f"  - {display_path}", "info")

        separator = "=" * 60
        self._log_cb(
            f"\n{separator}\n"
            f"  Run complete ({'DRY RUN' if self.dry_run else 'LIVE'})\n"
            f"  FLAC files found     : {total}\n"
            f"  Artwork restored     : {matched}\n"
            f"  No backup found      : {no_backup}\n"
            f"  Backup has no art    : {no_artwork}\n"
            f"  Duplicate library    : {duplicate_library_filenames}\n"
            f"  Duplicate backups    : {len(duplicates)}\n"
            f"  Errors               : {errors}\n"
            f"{separator}",
            "info",
        )

        return {
            "total": total,
            "matched": matched,
            "no_backup": no_backup,
            "no_artwork_in_backup": no_artwork,
            "duplicate_library_filenames": duplicate_library_filenames,
            "duplicate_backups": len(duplicates),
            "errors": errors,
        }


# ---------------------------------------------------------------------------
# MIK Artwork Restorer — fixes artwork lost during MIK 11 playlist exports
# ---------------------------------------------------------------------------


class MIKArtworkRestorer:
    """
    Copies PICTURE blocks from a source music library tree into a Mixed In Key
    export tree, restoring artwork that MIK 11 strips during playlist export.

    Both trees are scanned recursively; files are matched by lower-cased
    filename.  The source file's artwork always overwrites any existing artwork
    in the target file.

    Parameters
    ----------
    mik_export_root:
        Root of the MIK-exported folder structure (artwork missing).
    library_root:
        Root of your main music library (artwork intact — the reference copy).
    dry_run:
        When True (default) no files are written; actions are only logged.
    progress_callback:
        Called as ``progress_callback(current: int, total: int)`` after each
        exported file is processed.
    log_callback:
        Called as ``log_callback(message: str, level: str)`` where *level* is
        one of ``"info"``, ``"warning"``, ``"error"``, ``"debug"``.
    """

    def __init__(
        self,
        mik_export_root: str | Path,
        library_root: str | Path,
        dry_run: bool = True,
        progress_callback=None,
        log_callback=None,
    ) -> None:
        self.mik_export_root = Path(mik_export_root)
        self.library_root = Path(library_root)
        self.dry_run = dry_run
        self._progress_cb = progress_callback or (lambda current, total: None)
        self._log_cb = log_callback or (lambda msg, level="info": None)

    # ------------------------------------------------------------------
    # Public helpers — individually unit-testable
    # ------------------------------------------------------------------

    def build_library_dict(self) -> tuple[dict[str, Path], list[str]]:
        """
        Scan *library_root* recursively and return:

        * ``library_dict`` – ``{filename.lower(): Path}``
        * ``duplicates``   – lower-case names that appeared more than once
          (only the *first* occurrence is kept in ``library_dict``).
        """
        library_dict: dict[str, Path] = {}
        duplicates: list[str] = []

        for entry in self.library_root.rglob("*.flac"):
            if entry.is_file():
                key = entry.name.lower()
                if key in library_dict:
                    if key not in duplicates:
                        duplicates.append(key)
                    self._log_cb(
                        f"WARNING: duplicate filename in library: {entry.name}",
                        "warning",
                    )
                else:
                    library_dict[key] = entry

        return library_dict, duplicates

    def find_mik_files(self) -> list[Path]:
        """Return all ``.flac`` files under *mik_export_root* (recursive, sorted)."""
        return sorted(self.mik_export_root.rglob("*.flac"))

    def restore_artwork_for_file(
        self, target_path: Path, source_path: Path
    ) -> tuple[bool, str]:
        """
        Copy every PICTURE block from *source_path* into *target_path*.

        Returns ``(success, message)``.  In dry-run mode the file is **not**
        modified; only ``success=True`` and a ``[DRY RUN]`` message are returned.
        """
        return _copy_artwork_blocks(source_path, target_path, self.dry_run)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self) -> dict:
        """
        Execute the full artwork-copy pass.

        Returns a summary ``dict`` with keys:
        ``total``, ``matched``, ``no_library_match``, ``no_artwork_in_library``,
        ``errors``, ``duplicate_library_filenames``, ``duplicate_mik_filenames``.
        """
        self._log_cb("Building library index…", "info")
        library_dict, lib_duplicates = self.build_library_dict()
        self._log_cb(
            f"Library index: {len(library_dict)} unique file(s), "
            f"{len(lib_duplicates)} duplicate filename(s) (first copy kept)",
            "info",
        )

        self._log_cb("Scanning MIK export folder…", "info")
        mik_files = self.find_mik_files()
        total = len(mik_files)
        self._log_cb(f"MIK export scan: {total} FLAC file(s) found", "info")

        mik_name_counts: dict[str, int] = {}
        for mik_path in mik_files:
            key = mik_path.name.lower()
            mik_name_counts[key] = mik_name_counts.get(key, 0) + 1
        duplicate_mik_filenames = sum(
            count - 1 for count in mik_name_counts.values() if count > 1
        )

        matched = 0
        no_library_match = 0
        no_artwork = 0
        errors = 0
        restored_files: list[Path] = []

        for idx, mik_path in enumerate(mik_files, start=1):
            self._progress_cb(idx, total)

            key = mik_path.name.lower()
            if key not in library_dict:
                no_library_match += 1
                continue

            source_path = library_dict[key]
            success, msg = self.restore_artwork_for_file(mik_path, source_path)

            if success:
                matched += 1
                restored_files.append(mik_path)
            else:
                if "no embedded artwork" in msg.lower():
                    no_artwork += 1
                    self._log_cb(
                        f"Skipped (no artwork in library): {mik_path.name}",
                        "warning",
                    )
                else:
                    errors += 1
                    self._log_cb(f"ERROR: {msg} | file: {mik_path}", "error")

        if restored_files:
            heading = (
                "Files that would be restored:"
                if self.dry_run
                else "Files restored:"
            )
            self._log_cb(heading, "info")
            for restored in restored_files:
                try:
                    display_path = restored.relative_to(self.mik_export_root)
                except ValueError:
                    display_path = restored
                self._log_cb(f"  - {display_path}", "info")

        separator = "=" * 60
        self._log_cb(
            f"\n{separator}\n"
            f"  Run complete ({'DRY RUN' if self.dry_run else 'LIVE'})\n"
            f"  MIK export files found   : {total}\n"
            f"  Artwork restored         : {matched}\n"
            f"  No library match found   : {no_library_match}\n"
            f"  Library file has no art  : {no_artwork}\n"
            f"  Duplicate MIK filenames  : {duplicate_mik_filenames}\n"
            f"  Duplicate library names  : {len(lib_duplicates)}\n"
            f"  Errors                   : {errors}\n"
            f"{separator}",
            "info",
        )

        return {
            "total": total,
            "matched": matched,
            "no_library_match": no_library_match,
            "no_artwork_in_library": no_artwork,
            "duplicate_mik_filenames": duplicate_mik_filenames,
            "duplicate_library_filenames": len(lib_duplicates),
            "errors": errors,
        }


# ---------------------------------------------------------------------------
# Tkinter GUI
# ---------------------------------------------------------------------------

if HAS_TKINTER:

    class App(tk.Tk):
        """Main application window."""

        def __init__(self) -> None:
            super().__init__()
            self.title("Artwork Restorer — PN10 & MIK11")
            self.resizable(True, True)
            self.minsize(720, 580)
            self._build_ui()
            self._load_saved_paths_into_ui()

        # ----------------------------------------------------------------
        # UI construction
        # ----------------------------------------------------------------

        def _build_ui(self) -> None:
            notebook = ttk.Notebook(self)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            pn_frame = ttk.Frame(notebook)
            mik_frame = ttk.Frame(notebook)
            notebook.add(pn_frame, text="PN Artwork Restorer")
            notebook.add(mik_frame, text="MIK Artwork Restorer")

            self._build_pn_tab(pn_frame)
            self._build_mik_tab(mik_frame)

        def _build_pn_tab(self, parent: ttk.Frame) -> None:
            pad = {"padx": 10, "pady": 5}

            # --- Folder selectors ----------------------------------------
            frm_folders = ttk.LabelFrame(parent, text="Folders", padding=10)
            frm_folders.pack(fill=tk.X, **pad)
            frm_folders.columnconfigure(1, weight=1)

            ttk.Label(frm_folders, text="Music Library Root:").grid(
                row=0, column=0, sticky=tk.W, padx=(0, 5)
            )
            self.var_library = tk.StringVar()
            ttk.Entry(frm_folders, textvariable=self.var_library).grid(
                row=0, column=1, sticky=tk.EW, padx=5
            )
            ttk.Button(
                frm_folders,
                text="Browse…",
                command=lambda: self._browse(self.var_library),
            ).grid(row=0, column=2)

            ttk.Label(frm_folders, text="PN Backup Folder:").grid(
                row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(8, 0)
            )
            self.var_backup = tk.StringVar()
            ttk.Entry(frm_folders, textvariable=self.var_backup).grid(
                row=1, column=1, sticky=tk.EW, padx=5, pady=(8, 0)
            )
            ttk.Button(
                frm_folders,
                text="Browse…",
                command=lambda: self._browse(self.var_backup),
            ).grid(row=1, column=2, pady=(8, 0))

            # --- Options -------------------------------------------------
            frm_opts = ttk.LabelFrame(parent, text="Options", padding=10)
            frm_opts.pack(fill=tk.X, **pad)

            self.var_dry_run = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                frm_opts,
                text="Dry Run (preview only — no files will be modified)",
                variable=self.var_dry_run,
            ).pack(anchor=tk.W)

            # --- Action buttons ------------------------------------------
            frm_actions = ttk.Frame(parent)
            frm_actions.pack(fill=tk.X, **pad)

            self.btn_start = ttk.Button(
                frm_actions, text="Start Restoration", command=self._on_start
            )
            self.btn_start.pack(side=tk.LEFT)

            self.btn_clear = ttk.Button(
                frm_actions, text="Clear Log", command=self._clear_log
            )
            self.btn_clear.pack(side=tk.LEFT, padx=(10, 0))

            # --- Progress bar --------------------------------------------
            self.progress_var = tk.DoubleVar(value=0)
            self.progressbar = ttk.Progressbar(
                parent,
                variable=self.progress_var,
                maximum=100,
                mode="determinate",
            )
            self.progressbar.pack(fill=tk.X, **pad)

            self.lbl_progress = ttk.Label(parent, text="")
            self.lbl_progress.pack(anchor=tk.W, padx=10)

            # --- Log window ----------------------------------------------
            frm_log = ttk.LabelFrame(parent, text="Log", padding=5)
            frm_log.pack(fill=tk.BOTH, expand=True, **pad)

            self.log_text = scrolledtext.ScrolledText(
                frm_log,
                state=tk.DISABLED,
                height=15,
                font=("Courier", 10),
                wrap=tk.WORD,
            )
            self.log_text.pack(fill=tk.BOTH, expand=True)
            self._configure_log_colors(self.log_text)

        def _build_mik_tab(self, parent: ttk.Frame) -> None:
            pad = {"padx": 10, "pady": 5}

            # --- Folder selectors ----------------------------------------
            frm_folders = ttk.LabelFrame(parent, text="Folders", padding=10)
            frm_folders.pack(fill=tk.X, **pad)
            frm_folders.columnconfigure(1, weight=1)

            ttk.Label(frm_folders, text="MIK Export Root:").grid(
                row=0, column=0, sticky=tk.W, padx=(0, 5)
            )
            self.var_mik_export = tk.StringVar()
            ttk.Entry(frm_folders, textvariable=self.var_mik_export).grid(
                row=0, column=1, sticky=tk.EW, padx=5
            )
            ttk.Button(
                frm_folders,
                text="Browse…",
                command=lambda: self._browse(self.var_mik_export),
            ).grid(row=0, column=2)

            ttk.Label(frm_folders, text="Music Library Root:").grid(
                row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(8, 0)
            )
            self.var_mik_library = tk.StringVar()
            ttk.Entry(frm_folders, textvariable=self.var_mik_library).grid(
                row=1, column=1, sticky=tk.EW, padx=5, pady=(8, 0)
            )
            ttk.Button(
                frm_folders,
                text="Browse…",
                command=lambda: self._browse(self.var_mik_library),
            ).grid(row=1, column=2, pady=(8, 0))

            # --- Options -------------------------------------------------
            frm_opts = ttk.LabelFrame(parent, text="Options", padding=10)
            frm_opts.pack(fill=tk.X, **pad)

            self.var_mik_dry_run = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                frm_opts,
                text="Dry Run (preview only — no files will be modified)",
                variable=self.var_mik_dry_run,
            ).pack(anchor=tk.W)

            # --- Action buttons ------------------------------------------
            frm_actions = ttk.Frame(parent)
            frm_actions.pack(fill=tk.X, **pad)

            self.btn_mik_start = ttk.Button(
                frm_actions, text="Start Restoration", command=self._on_mik_start
            )
            self.btn_mik_start.pack(side=tk.LEFT)

            self.btn_mik_clear = ttk.Button(
                frm_actions, text="Clear Log", command=self._mik_clear_log
            )
            self.btn_mik_clear.pack(side=tk.LEFT, padx=(10, 0))

            # --- Progress bar --------------------------------------------
            self.mik_progress_var = tk.DoubleVar(value=0)
            self.mik_progressbar = ttk.Progressbar(
                parent,
                variable=self.mik_progress_var,
                maximum=100,
                mode="determinate",
            )
            self.mik_progressbar.pack(fill=tk.X, **pad)

            self.lbl_mik_progress = ttk.Label(parent, text="")
            self.lbl_mik_progress.pack(anchor=tk.W, padx=10)

            # --- Log window ----------------------------------------------
            frm_log = ttk.LabelFrame(parent, text="Log", padding=5)
            frm_log.pack(fill=tk.BOTH, expand=True, **pad)

            self.mik_log_text = scrolledtext.ScrolledText(
                frm_log,
                state=tk.DISABLED,
                height=15,
                font=("Courier", 10),
                wrap=tk.WORD,
            )
            self.mik_log_text.pack(fill=tk.BOTH, expand=True)
            self._configure_log_colors(self.mik_log_text)

        def _configure_log_colors(self, log_widget) -> None:
            """Set readable log colors for both light and dark backgrounds."""
            try:
                bg = log_widget.cget("background")
                r, g, b = log_widget.winfo_rgb(bg)
                luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 65535.0
            except tk.TclError:
                luminance = 1.0  # Fallback to light theme colors.

            if luminance < 0.5:
                colors = {
                    "info": "#E6E6E6",
                    "warning": "#FFB347",
                    "error": "#FF7A7A",
                    "debug": "#B0B0B0",
                }
            else:
                colors = {
                    "info": "black",
                    "warning": "#CC6600",
                    "error": "red",
                    "debug": "gray",
                }

            for level, color in colors.items():
                log_widget.tag_config(level, foreground=color)

        # ----------------------------------------------------------------
        # Event handlers
        # ----------------------------------------------------------------

        def _browse(self, var: tk.StringVar) -> None:
            folder = filedialog.askdirectory()
            if folder:
                var.set(folder)
                self._save_current_paths()

        def _load_saved_paths_into_ui(self) -> None:
            saved = _load_saved_paths()
            self.var_library.set(saved.get("library_root", ""))
            self.var_backup.set(saved.get("backup_folder", ""))
            self.var_mik_export.set(saved.get("mik_export_root", ""))
            self.var_mik_library.set(saved.get("mik_library_root", ""))

        def _save_current_paths(self) -> None:
            _save_saved_paths(
                library_root=self.var_library.get().strip(),
                backup_folder=self.var_backup.get().strip(),
                mik_export_root=self.var_mik_export.get().strip(),
                mik_library_root=self.var_mik_library.get().strip(),
            )

        def _clear_log(self) -> None:
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self.log_text.config(state=tk.DISABLED)
            self.progress_var.set(0)
            self.lbl_progress.config(text="")

        def _on_start(self) -> None:
            library = self.var_library.get().strip()
            backup = self.var_backup.get().strip()

            if not library:
                messagebox.showwarning(
                    "Missing input", "Please select a Music Library Root folder."
                )
                return
            if not backup:
                messagebox.showwarning(
                    "Missing input", "Please select a PN Backup Folder."
                )
                return
            if not Path(library).is_dir():
                messagebox.showerror(
                    "Invalid path",
                    f"Music Library Root does not exist:\n{library}",
                )
                return
            if not Path(backup).is_dir():
                messagebox.showerror(
                    "Invalid path",
                    f"PN Backup Folder does not exist:\n{backup}",
                )
                return

            self._save_current_paths()
            self.btn_start.config(state=tk.DISABLED)
            self._clear_log()
            self._append_log("Starting…\n", "info")

            restorer = ArtworkRestorer(
                library_root=library,
                backup_folder=backup,
                dry_run=self.var_dry_run.get(),
                progress_callback=self._progress_callback,
                log_callback=self._log_callback,
            )

            def _worker() -> None:
                try:
                    summary = restorer.run()
                    self.after(0, lambda: self._on_complete(summary))
                except Exception as exc:
                    logger.exception("Unexpected error during restoration")
                    self.after(
                        0, lambda: messagebox.showerror("Unexpected error", str(exc))
                    )
                    self.after(0, lambda: self.btn_start.config(state=tk.NORMAL))

            threading.Thread(target=_worker, daemon=True).start()

        def _on_complete(self, summary: dict) -> None:
            self.btn_start.config(state=tk.NORMAL)
            dry_tag = "(DRY RUN) " if self.var_dry_run.get() else ""
            messagebox.showinfo(
                "Done",
                f"{dry_tag}Restoration complete!\n\n"
                f"FLAC files found     : {summary['total']}\n"
                f"Artwork restored     : {summary['matched']}\n"
                f"No backup found      : {summary['no_backup']}\n"
                f"Backup has no art    : {summary['no_artwork_in_backup']}\n"
                f"Duplicate library    : {summary['duplicate_library_filenames']}\n"
                f"Duplicate backups    : {summary['duplicate_backups']}\n"
                f"Errors               : {summary['errors']}\n\n"
                f"Full log: {_log_file()}",
            )

        # ----------------------------------------------------------------
        # Thread-safe callbacks
        # ----------------------------------------------------------------

        def _append_log(self, msg: str, level: str = "info") -> None:
            """Must be called from the main thread."""
            self.log_text.config(state=tk.NORMAL)
            self.log_text.insert(tk.END, msg + "\n", level)
            self.log_text.see(tk.END)
            self.log_text.config(state=tk.DISABLED)
            _level_map = {
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "debug": logging.DEBUG,
            }
            logger.log(_level_map.get(level, logging.INFO), msg)

        def _log_callback(self, msg: str, level: str = "info") -> None:
            """Safe to call from any thread."""
            self.after(0, lambda: self._append_log(msg, level))

        def _progress_callback(self, current: int, total: int) -> None:
            """Safe to call from any thread."""
            pct = (current / total * 100) if total else 0.0
            self.after(0, lambda: self.progress_var.set(pct))
            self.after(
                0,
                lambda: self.lbl_progress.config(
                    text=f"{current} / {total}  ({pct:.1f}%)"
                ),
            )

        # ----------------------------------------------------------------
        # MIK tab — event handlers and thread-safe callbacks
        # ----------------------------------------------------------------

        def _mik_clear_log(self) -> None:
            self.mik_log_text.config(state=tk.NORMAL)
            self.mik_log_text.delete("1.0", tk.END)
            self.mik_log_text.config(state=tk.DISABLED)
            self.mik_progress_var.set(0)
            self.lbl_mik_progress.config(text="")

        def _on_mik_start(self) -> None:
            export_root = self.var_mik_export.get().strip()
            lib_root = self.var_mik_library.get().strip()

            if not export_root:
                messagebox.showwarning(
                    "Missing input", "Please select a MIK Export Root folder."
                )
                return
            if not lib_root:
                messagebox.showwarning(
                    "Missing input", "Please select a Music Library Root folder."
                )
                return
            if not Path(export_root).is_dir():
                messagebox.showerror(
                    "Invalid path",
                    f"MIK Export Root does not exist:\n{export_root}",
                )
                return
            if not Path(lib_root).is_dir():
                messagebox.showerror(
                    "Invalid path",
                    f"Music Library Root does not exist:\n{lib_root}",
                )
                return

            self._save_current_paths()
            self.btn_mik_start.config(state=tk.DISABLED)
            self._mik_clear_log()
            self._mik_append_log("Starting…\n", "info")

            restorer = MIKArtworkRestorer(
                mik_export_root=export_root,
                library_root=lib_root,
                dry_run=self.var_mik_dry_run.get(),
                progress_callback=self._mik_progress_callback,
                log_callback=self._mik_log_callback,
            )

            def _worker() -> None:
                try:
                    summary = restorer.run()
                    self.after(0, lambda: self._on_mik_complete(summary))
                except Exception as exc:
                    logger.exception("Unexpected error during MIK restoration")
                    self.after(
                        0, lambda: messagebox.showerror("Unexpected error", str(exc))
                    )
                    self.after(0, lambda: self.btn_mik_start.config(state=tk.NORMAL))

            threading.Thread(target=_worker, daemon=True).start()

        def _on_mik_complete(self, summary: dict) -> None:
            self.btn_mik_start.config(state=tk.NORMAL)
            dry_tag = "(DRY RUN) " if self.var_mik_dry_run.get() else ""
            messagebox.showinfo(
                "Done",
                f"{dry_tag}Restoration complete!\n\n"
                f"MIK export files found   : {summary['total']}\n"
                f"Artwork restored         : {summary['matched']}\n"
                f"No library match found   : {summary['no_library_match']}\n"
                f"Library file has no art  : {summary['no_artwork_in_library']}\n"
                f"Duplicate MIK filenames  : {summary['duplicate_mik_filenames']}\n"
                f"Duplicate library names  : {summary['duplicate_library_filenames']}\n"
                f"Errors                   : {summary['errors']}\n\n"
                f"Full log: {_log_file()}",
            )

        def _mik_append_log(self, msg: str, level: str = "info") -> None:
            """Must be called from the main thread."""
            self.mik_log_text.config(state=tk.NORMAL)
            self.mik_log_text.insert(tk.END, msg + "\n", level)
            self.mik_log_text.see(tk.END)
            self.mik_log_text.config(state=tk.DISABLED)
            _level_map = {
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "debug": logging.DEBUG,
            }
            logger.log(_level_map.get(level, logging.INFO), msg)

        def _mik_log_callback(self, msg: str, level: str = "info") -> None:
            """Safe to call from any thread."""
            self.after(0, lambda: self._mik_append_log(msg, level))

        def _mik_progress_callback(self, current: int, total: int) -> None:
            """Safe to call from any thread."""
            pct = (current / total * 100) if total else 0.0
            self.after(0, lambda: self.mik_progress_var.set(pct))
            self.after(
                0,
                lambda: self.lbl_mik_progress.config(
                    text=f"{current} / {total}  ({pct:.1f}%)"
                ),
            )


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------


def _log_file() -> Path:
    """Return the path to the on-disk log file (created on first use)."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir / "PN_Artwork_Restorer.log"


def _setup_logging() -> None:
    """Configure root-level logging to both a file and stdout."""
    log_path = _log_file()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:  # pragma: no cover
    _setup_logging()
    if not HAS_TKINTER:
        print(
            "ERROR: tkinter is not available.\n"
            "On Linux install it with:     sudo apt install python3-tk\n"
            "On macOS with Homebrew:       brew install python-tk@3.12\n"
            "  (then recreate your venv — see README Troubleshooting)\n"
            "On macOS with python.org:     tkinter ships with the installer.\n"
            "On Windows:                   tkinter ships with the installer."
        )
        sys.exit(1)
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
