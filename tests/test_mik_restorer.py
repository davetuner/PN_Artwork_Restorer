"""
Unit tests for pn_artwork_restorer.MIKArtworkRestorer

Each test focuses on one specific method or behaviour so that failures are
easy to diagnose.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from mutagen.flac import FLAC

from pn_artwork_restorer import MIKArtworkRestorer
from tests.conftest import make_flac, picture_count, FAKE_PNG_DATA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_restorer(mik_export, library, dry_run=True, logs=None):
    """Return a MIKArtworkRestorer whose callbacks append to *logs*."""
    if logs is None:
        logs = []
    return MIKArtworkRestorer(
        mik_export_root=mik_export,
        library_root=library,
        dry_run=dry_run,
        log_callback=lambda msg, level="info": logs.append((level, msg)),
    ), logs


# ---------------------------------------------------------------------------
# build_library_dict
# ---------------------------------------------------------------------------

class TestBuildLibraryDict:
    def test_empty_library(self, tmp_path):
        lib = tmp_path / "lib"
        lib.mkdir()
        restorer, _ = _make_restorer(lib, lib)
        ld, dupes = restorer.build_library_dict()
        assert ld == {}
        assert dupes == []

    def test_single_flac_at_root(self, tmp_path):
        lib = tmp_path / "lib"
        lib.mkdir()
        make_flac(lib / "song.flac")
        restorer, _ = _make_restorer(lib, lib)
        ld, _ = restorer.build_library_dict()
        assert "song.flac" in ld

    def test_recursive_scan(self, tmp_path):
        """Files in nested subdirectories must be indexed."""
        lib = tmp_path / "lib"
        (lib / "Artist A" / "Album 1").mkdir(parents=True)
        (lib / "Artist B" / "Album 2").mkdir(parents=True)
        make_flac(lib / "Artist A" / "Album 1" / "track01.flac")
        make_flac(lib / "Artist B" / "Album 2" / "track02.flac")
        restorer, _ = _make_restorer(lib, lib)
        ld, _ = restorer.build_library_dict()
        assert "track01.flac" in ld
        assert "track02.flac" in ld
        assert len(ld) == 2

    def test_keys_are_lower_case(self, tmp_path):
        lib = tmp_path / "lib"
        lib.mkdir()
        make_flac(lib / "UPPER.flac")
        restorer, _ = _make_restorer(lib, lib)
        ld, _ = restorer.build_library_dict()
        assert "upper.flac" in ld

    def test_non_flac_files_ignored(self, tmp_path):
        lib = tmp_path / "lib"
        lib.mkdir()
        (lib / "cover.jpg").write_bytes(b"\xff\xd8")
        (lib / "info.txt").write_text("notes")
        restorer, _ = _make_restorer(lib, lib)
        ld, _ = restorer.build_library_dict()
        assert ld == {}

    def test_duplicate_names_across_subdirs(self, tmp_path):
        """When two different subdirs hold the same filename, first wins."""
        lib = tmp_path / "lib"
        (lib / "a").mkdir(parents=True)
        (lib / "b").mkdir(parents=True)
        make_flac(lib / "a" / "song.flac", with_picture=True)
        make_flac(lib / "b" / "song.flac", with_picture=False)

        restorer, logs = _make_restorer(lib, lib)
        ld, dupes = restorer.build_library_dict()

        assert len(ld) == 1
        assert "song.flac" in dupes
        assert any("duplicate" in msg.lower() for _, msg in logs)

    def test_multiple_unique_files(self, tmp_path):
        lib = tmp_path / "lib"
        (lib / "sub").mkdir(parents=True)
        for name in ("a.flac", "b.flac"):
            make_flac(lib / name)
        make_flac(lib / "sub" / "c.flac")
        restorer, _ = _make_restorer(lib, lib)
        ld, dupes = restorer.build_library_dict()
        assert len(ld) == 3
        assert dupes == []


# ---------------------------------------------------------------------------
# find_mik_files
# ---------------------------------------------------------------------------

class TestFindMIKFiles:
    def test_empty_export_dir(self, tmp_path):
        export = tmp_path / "export"
        export.mkdir()
        lib = tmp_path / "lib"
        lib.mkdir()
        restorer, _ = _make_restorer(export, lib)
        assert restorer.find_mik_files() == []

    def test_recursive_scan(self, tmp_path):
        export = tmp_path / "export"
        (export / "Playlist A").mkdir(parents=True)
        (export / "Playlist B").mkdir(parents=True)
        make_flac(export / "Playlist A" / "t01.flac")
        make_flac(export / "Playlist B" / "t02.flac")
        lib = tmp_path / "lib"
        lib.mkdir()
        restorer, _ = _make_restorer(export, lib)
        files = restorer.find_mik_files()
        assert len(files) == 2

    def test_non_flac_excluded(self, tmp_path):
        export = tmp_path / "export"
        export.mkdir()
        make_flac(export / "track.flac")
        (export / "cover.jpg").write_bytes(b"\xff\xd8")
        lib = tmp_path / "lib"
        lib.mkdir()
        restorer, _ = _make_restorer(export, lib)
        files = restorer.find_mik_files()
        assert len(files) == 1

    def test_results_are_sorted(self, tmp_path):
        export = tmp_path / "export"
        export.mkdir()
        for name in ("c.flac", "a.flac", "b.flac"):
            make_flac(export / name)
        lib = tmp_path / "lib"
        lib.mkdir()
        restorer, _ = _make_restorer(export, lib)
        names = [f.name for f in restorer.find_mik_files()]
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# restore_artwork_for_file
# ---------------------------------------------------------------------------

class TestMIKRestoreArtworkForFile:
    def test_dry_run_does_not_write(self, tmp_path):
        target = make_flac(tmp_path / "target.flac", with_picture=False)
        source = make_flac(tmp_path / "source.flac", with_picture=True)
        restorer = MIKArtworkRestorer(tmp_path, tmp_path, dry_run=True)
        success, msg = restorer.restore_artwork_for_file(target, source)
        assert success is True
        assert "[DRY RUN]" in msg
        assert picture_count(target) == 0

    def test_live_run_writes_picture(self, tmp_path):
        target = make_flac(tmp_path / "target.flac", with_picture=False)
        source = make_flac(tmp_path / "source.flac", with_picture=True)
        restorer = MIKArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        success, _ = restorer.restore_artwork_for_file(target, source)
        assert success is True
        assert picture_count(target) == 1

    def test_existing_picture_in_target_is_replaced(self, tmp_path):
        """Artwork already in the target is cleared and replaced."""
        target = make_flac(tmp_path / "target.flac", with_picture=True)
        source = make_flac(tmp_path / "source.flac", with_picture=True)
        restorer = MIKArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        success, _ = restorer.restore_artwork_for_file(target, source)
        assert success is True
        assert picture_count(target) == 1

    def test_source_with_no_artwork_returns_failure(self, tmp_path):
        target = make_flac(tmp_path / "target.flac", with_picture=False)
        source = make_flac(tmp_path / "source.flac", with_picture=False)
        restorer = MIKArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        success, msg = restorer.restore_artwork_for_file(target, source)
        assert success is False
        assert "no embedded artwork" in msg.lower()

    def test_corrupt_source_returns_failure(self, tmp_path):
        target = make_flac(tmp_path / "target.flac", with_picture=False)
        corrupt = tmp_path / "corrupt.flac"
        corrupt.write_bytes(b"not a valid flac file")
        restorer = MIKArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        success, msg = restorer.restore_artwork_for_file(target, corrupt)
        assert success is False
        assert "cannot open source" in msg.lower()

    def test_picture_data_preserved_exactly(self, tmp_path):
        source = make_flac(tmp_path / "source.flac", with_picture=True)
        target = make_flac(tmp_path / "target.flac", with_picture=False)
        restorer = MIKArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        restorer.restore_artwork_for_file(target, source)
        pic = FLAC(str(target)).pictures[0]
        assert pic.data == FAKE_PNG_DATA
        assert pic.mime == "image/png"


# ---------------------------------------------------------------------------
# run — integration-level unit tests
# ---------------------------------------------------------------------------

class TestMIKRun:
    def test_summary_counts_all_cases(self, tmp_path):
        """
        MIK export: 3 tracks
          - track_match.flac  → library file WITH artwork   → matched
          - track_noart.flac  → library file WITHOUT artwork → no_artwork_in_library
          - track_only.flac   → no library match at all     → no_library_match
        """
        export = tmp_path / "export"
        lib = tmp_path / "lib"
        export.mkdir()
        lib.mkdir()

        make_flac(export / "track_match.flac", with_picture=False)
        make_flac(export / "track_noart.flac", with_picture=False)
        make_flac(export / "track_only.flac", with_picture=False)

        make_flac(lib / "track_match.flac", with_picture=True)
        make_flac(lib / "track_noart.flac", with_picture=False)
        # no library file for track_only.flac

        restorer, _ = _make_restorer(export, lib, dry_run=True)
        summary = restorer.run()

        assert summary["total"] == 3
        assert summary["matched"] == 1
        assert summary["no_library_match"] == 1
        assert summary["no_artwork_in_library"] == 1
        assert summary["duplicate_mik_filenames"] == 0
        assert summary["duplicate_library_filenames"] == 0
        assert summary["errors"] == 0

    def test_empty_export_returns_zero_summary(self, tmp_path):
        export = tmp_path / "export"
        lib = tmp_path / "lib"
        export.mkdir()
        lib.mkdir()
        restorer, _ = _make_restorer(export, lib)
        summary = restorer.run()
        assert summary == {
            "total": 0,
            "matched": 0,
            "no_library_match": 0,
            "no_artwork_in_library": 0,
            "duplicate_mik_filenames": 0,
            "duplicate_library_filenames": 0,
            "errors": 0,
        }

    def test_progress_callback_called_for_each_file(self, tmp_path):
        export = tmp_path / "export"
        lib = tmp_path / "lib"
        export.mkdir()
        lib.mkdir()
        for i in range(5):
            make_flac(export / f"t{i:02d}.flac")

        calls = []
        restorer = MIKArtworkRestorer(
            export, lib, dry_run=True,
            progress_callback=lambda cur, tot: calls.append((cur, tot)),
        )
        restorer.run()

        assert len(calls) == 5
        for i, (cur, tot) in enumerate(calls, start=1):
            assert cur == i
            assert tot == 5

    def test_dry_run_does_not_modify_files(self, tmp_path):
        export = tmp_path / "export"
        lib = tmp_path / "lib"
        export.mkdir()
        lib.mkdir()
        target = make_flac(export / "song.flac", with_picture=False)
        make_flac(lib / "song.flac", with_picture=True)

        restorer, _ = _make_restorer(export, lib, dry_run=True)
        restorer.run()
        assert picture_count(target) == 0

    def test_live_run_modifies_files(self, tmp_path):
        export = tmp_path / "export"
        lib = tmp_path / "lib"
        export.mkdir()
        lib.mkdir()
        target = make_flac(export / "song.flac", with_picture=False)
        make_flac(lib / "song.flac", with_picture=True)

        restorer, _ = _make_restorer(export, lib, dry_run=False)
        restorer.run()
        assert picture_count(target) == 1

    def test_existing_artwork_always_overwritten(self, tmp_path):
        """A MIK export file that already has artwork should be overwritten."""
        export = tmp_path / "export"
        lib = tmp_path / "lib"
        export.mkdir()
        lib.mkdir()
        target = make_flac(export / "song.flac", with_picture=True)
        make_flac(lib / "song.flac", with_picture=True)

        restorer, _ = _make_restorer(export, lib, dry_run=False)
        summary = restorer.run()

        assert summary["matched"] == 1
        assert picture_count(target) == 1  # replaced, not duplicated

    def test_nested_export_and_nested_library(self, tmp_path):
        """Both trees are nested; files matched by filename across structures."""
        export = tmp_path / "export"
        (export / "Playlist A" / "Hip Hop").mkdir(parents=True)
        lib = tmp_path / "lib"
        (lib / "Artist X" / "Album Y").mkdir(parents=True)

        target = make_flac(
            export / "Playlist A" / "Hip Hop" / "banger.flac", with_picture=False
        )
        make_flac(lib / "Artist X" / "Album Y" / "banger.flac", with_picture=True)

        restorer, _ = _make_restorer(export, lib, dry_run=False)
        summary = restorer.run()

        assert summary["matched"] == 1
        assert picture_count(target) == 1

    def test_dry_run_logged(self, tmp_path):
        export = tmp_path / "export"
        lib = tmp_path / "lib"
        export.mkdir()
        lib.mkdir()
        make_flac(export / "song.flac", with_picture=False)
        make_flac(lib / "song.flac", with_picture=True)

        restorer, logs = _make_restorer(export, lib, dry_run=True)
        restorer.run()

        combined = "\n".join(msg for _, msg in logs)
        assert "DRY RUN" in combined
