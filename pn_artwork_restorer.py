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

# ---------------------------------------------------------------------------
# Core logic — no GUI dependency whatsoever
# ---------------------------------------------------------------------------


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
        ``errors``.
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

        matched = 0
        no_backup = 0
        no_artwork = 0
        errors = 0

        for idx, lib_path in enumerate(library_files, start=1):
            self._progress_cb(idx, total)

            key = lib_path.name.lower()
            if key not in backup_dict:
                no_backup += 1
                self._log_cb(f"No backup: {lib_path.name}", "debug")
                continue

            backup_path = backup_dict[key]
            success, msg = self.restore_artwork_for_file(lib_path, backup_path)

            if success:
                matched += 1
                self._log_cb(f"{msg} → {lib_path}", "info")
            else:
                if "no embedded artwork" in msg.lower():
                    no_artwork += 1
                    self._log_cb(
                        f"Skipped (no artwork in backup): {lib_path.name}", "warning"
                    )
                else:
                    errors += 1
                    self._log_cb(f"ERROR: {msg} | file: {lib_path}", "error")

        separator = "=" * 60
        self._log_cb(
            f"\n{separator}\n"
            f"  Run complete ({'DRY RUN' if self.dry_run else 'LIVE'})\n"
            f"  FLAC files found     : {total}\n"
            f"  Artwork restored     : {matched}\n"
            f"  No backup found      : {no_backup}\n"
            f"  Backup has no art    : {no_artwork}\n"
            f"  Errors               : {errors}\n"
            f"{separator}",
            "info",
        )

        return {
            "total": total,
            "matched": matched,
            "no_backup": no_backup,
            "no_artwork_in_backup": no_artwork,
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
            self.title("PN Artwork Restorer")
            self.resizable(True, True)
            self.minsize(720, 560)
            self._build_ui()

        # ----------------------------------------------------------------
        # UI construction
        # ----------------------------------------------------------------

        def _build_ui(self) -> None:
            pad = {"padx": 10, "pady": 5}

            # --- Folder selectors ----------------------------------------
            frm_folders = ttk.LabelFrame(self, text="Folders", padding=10)
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
            frm_opts = ttk.LabelFrame(self, text="Options", padding=10)
            frm_opts.pack(fill=tk.X, **pad)

            self.var_dry_run = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                frm_opts,
                text="Dry Run (preview only — no files will be modified)",
                variable=self.var_dry_run,
            ).pack(anchor=tk.W)

            # --- Action buttons ------------------------------------------
            frm_actions = ttk.Frame(self)
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
                self,
                variable=self.progress_var,
                maximum=100,
                mode="determinate",
            )
            self.progressbar.pack(fill=tk.X, **pad)

            self.lbl_progress = ttk.Label(self, text="")
            self.lbl_progress.pack(anchor=tk.W, padx=10)

            # --- Log window ----------------------------------------------
            frm_log = ttk.LabelFrame(self, text="Log", padding=5)
            frm_log.pack(fill=tk.BOTH, expand=True, **pad)

            self.log_text = scrolledtext.ScrolledText(
                frm_log,
                state=tk.DISABLED,
                height=15,
                font=("Courier", 10),
                wrap=tk.WORD,
            )
            self.log_text.pack(fill=tk.BOTH, expand=True)

            self._configure_log_colors()

        def _configure_log_colors(self) -> None:
            """Set readable log colors for both light and dark backgrounds."""
            try:
                bg = self.log_text.cget("background")
                r, g, b = self.log_text.winfo_rgb(bg)
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
                self.log_text.tag_config(level, foreground=color)

        # ----------------------------------------------------------------
        # Event handlers
        # ----------------------------------------------------------------

        def _browse(self, var: tk.StringVar) -> None:
            folder = filedialog.askdirectory()
            if folder:
                var.set(folder)

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
        level=logging.DEBUG,
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
