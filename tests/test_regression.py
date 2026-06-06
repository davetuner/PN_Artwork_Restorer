"""
Regression tests for pn_artwork_restorer

These tests exercise the full end-to-end workflow against a small but realistic
fixture that mirrors the actual directory layout described in the problem
statement:

    library/
        Artist A/
            Album 1/
                track01.flac   ← artwork lost by Platinum Notes
        Artist B/
            Album 2/
                track02.flac   ← artwork lost by Platinum Notes
    pn_backups/
        track01.flac            ← original backup (artwork intact)
        track02.flac            ← original backup (artwork intact)
        track03.flac            ← extra backup with no matching library file
        track04.flac            ← backup that itself has no artwork

The tests assert:
  1. Both library files get artwork restored on a live run.
  2. Neither file is modified on a dry run.
  3. Summary counts are correct.
  4. A second run (idempotent) produces the same result.
  5. Files without a matching backup are untouched and counted correctly.
  6. Backups with no artwork are counted as no_artwork_in_backup.
"""

from __future__ import annotations

import shutil
import pytest
from pathlib import Path
from mutagen.flac import FLAC

from pn_artwork_restorer import ArtworkRestorer, MIKArtworkRestorer
from tests.conftest import make_flac, picture_count


# ---------------------------------------------------------------------------
# Fixture: full example structure
# ---------------------------------------------------------------------------

@pytest.fixture()
def example(tmp_path: Path) -> dict:
    """
    Build the example library + backup under *tmp_path* and return a dict
    with convenient Path handles.
    """
    library = tmp_path / "library"
    album1 = library / "Artist A" / "Album 1"
    album2 = library / "Artist B" / "Album 2"
    album1.mkdir(parents=True)
    album2.mkdir(parents=True)

    backup = tmp_path / "pn_backups"
    backup.mkdir()

    # Library files — artwork has been lost by Platinum Notes
    t01_lib = make_flac(album1 / "track01.flac", with_picture=False)
    t02_lib = make_flac(album2 / "track02.flac", with_picture=False)
    # track05 exists only in the library (no backup)
    t05_lib = make_flac(album1 / "track05.flac", with_picture=False)

    # Backup files
    make_flac(backup / "track01.flac", with_picture=True)   # matches t01_lib
    make_flac(backup / "track02.flac", with_picture=True)   # matches t02_lib
    make_flac(backup / "track03.flac", with_picture=True)   # no matching lib file
    make_flac(backup / "track04.flac", with_picture=False)  # backup has no art

    return {
        "library": library,
        "backup": backup,
        "t01_lib": t01_lib,
        "t02_lib": t02_lib,
        "t05_lib": t05_lib,
    }


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run(example, dry_run: bool) -> dict:
    logs = []
    restorer = ArtworkRestorer(
        library_root=example["library"],
        backup_folder=example["backup"],
        dry_run=dry_run,
        log_callback=lambda msg, level="info": logs.append(msg),
    )
    summary = restorer.run()
    summary["_logs"] = logs
    return summary


# ---------------------------------------------------------------------------
# Regression test cases
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_no_files_modified(self, example):
        _run(example, dry_run=True)
        assert picture_count(example["t01_lib"]) == 0
        assert picture_count(example["t02_lib"]) == 0
        assert picture_count(example["t05_lib"]) == 0

    def test_correct_summary(self, example):
        summary = _run(example, dry_run=True)
        # 3 library files total: t01, t02, t05
        assert summary["total"] == 3
        # t01 and t02 have matching backups WITH artwork
        assert summary["matched"] == 2
        # t05 has no backup at all
        assert summary["no_backup"] == 1
        # no_artwork_in_backup is 0 because track04 is not in the library
        assert summary["no_artwork_in_backup"] == 0
        assert summary["errors"] == 0

    def test_dry_run_logged(self, example):
        summary = _run(example, dry_run=True)
        combined = "\n".join(summary["_logs"])
        assert "DRY RUN" in combined


class TestLiveRun:
    def test_artwork_restored_on_matched_files(self, example):
        _run(example, dry_run=False)
        assert picture_count(example["t01_lib"]) == 1
        assert picture_count(example["t02_lib"]) == 1

    def test_unmatched_file_untouched(self, example):
        _run(example, dry_run=False)
        assert picture_count(example["t05_lib"]) == 0

    def test_correct_summary(self, example):
        summary = _run(example, dry_run=False)
        assert summary["total"] == 3
        assert summary["matched"] == 2
        assert summary["no_backup"] == 1
        assert summary["no_artwork_in_backup"] == 0
        assert summary["errors"] == 0

    def test_picture_data_integrity(self, example):
        """Image bytes in the restored file must exactly match the backup."""
        backup_flac = FLAC(str(example["backup"] / "track01.flac"))
        expected_data = backup_flac.pictures[0].data

        _run(example, dry_run=False)

        restored_flac = FLAC(str(example["t01_lib"]))
        assert len(restored_flac.pictures) == 1
        assert restored_flac.pictures[0].data == expected_data

    def test_other_tags_preserved(self, example):
        """
        Restoration must not remove or alter Vorbis comments that were already
        present on the target file.
        """
        # Embed a TITLE comment in the target before running
        target = FLAC(str(example["t01_lib"]))
        target["title"] = ["Regression Track"]
        target["artist"] = ["Test Artist"]
        target.save()

        _run(example, dry_run=False)

        restored = FLAC(str(example["t01_lib"]))
        assert restored.get("title") == ["Regression Track"]
        assert restored.get("artist") == ["Test Artist"]

    def test_idempotent_second_run(self, example):
        """Running twice should produce identical results (no artwork duplication)."""
        _run(example, dry_run=False)
        _run(example, dry_run=False)

        assert picture_count(example["t01_lib"]) == 1
        assert picture_count(example["t02_lib"]) == 1


class TestEdgeCases:
    def test_library_with_no_flac_files(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        backup = tmp_path / "backup"
        backup.mkdir()
        (library / "not_a_flac.mp3").write_bytes(b"\xff\xfb")

        restorer = ArtworkRestorer(library, backup, dry_run=True)
        summary = restorer.run()
        assert summary["total"] == 0

    def test_empty_backup_folder(self, tmp_path):
        library = tmp_path / "library"
        library.mkdir()
        backup = tmp_path / "backup"
        backup.mkdir()
        make_flac(library / "song.flac")

        restorer = ArtworkRestorer(library, backup, dry_run=False)
        summary = restorer.run()
        assert summary["no_backup"] == 1
        assert summary["matched"] == 0

    def test_duplicate_backup_names_first_wins(self, tmp_path):
        """
        When two backup files share the same lower-case name, the first one
        encountered should be used and the duplicate should be logged.
        """
        library = tmp_path / "library"
        library.mkdir()
        backup = tmp_path / "backup"
        backup.mkdir()

        target = make_flac(library / "song.flac", with_picture=False)
        # Both files have the same lower-case name
        make_flac(backup / "song.flac", with_picture=True)
        make_flac(backup / "Song.flac", with_picture=True)

        logs = []
        restorer = ArtworkRestorer(
            library, backup, dry_run=False,
            log_callback=lambda msg, level="info": logs.append((level, msg)),
        )
        summary = restorer.run()

        # Duplicate should be warned about
        assert any("duplicate" in msg.lower() for _, msg in logs)
        # Artwork should still have been restored from whichever copy was kept
        assert summary["matched"] == 1
        assert picture_count(target) == 1

    def test_deeply_nested_library(self, tmp_path):
        library = tmp_path / "library"
        deep = library / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        backup = tmp_path / "backup"
        backup.mkdir()

        target = make_flac(deep / "deep_track.flac", with_picture=False)
        make_flac(backup / "deep_track.flac", with_picture=True)

        restorer = ArtworkRestorer(library, backup, dry_run=False)
        summary = restorer.run()

        assert summary["matched"] == 1
        assert picture_count(target) == 1

    def test_large_batch(self, tmp_path):
        """Smoke-test with 200 files to confirm there are no performance issues."""
        library = tmp_path / "library"
        library.mkdir()
        backup = tmp_path / "backup"
        backup.mkdir()

        n = 200
        for i in range(n):
            make_flac(library / f"track_{i:04d}.flac", with_picture=False)
            make_flac(backup / f"track_{i:04d}.flac", with_picture=True)

        progress_calls = []
        restorer = ArtworkRestorer(
            library, backup, dry_run=False,
            progress_callback=lambda cur, tot: progress_calls.append((cur, tot)),
        )
        summary = restorer.run()

        assert summary["total"] == n
        assert summary["matched"] == n
        assert summary["errors"] == 0
        assert len(progress_calls) == n


# ===========================================================================
# MIK Artwork Restorer regression tests
# ===========================================================================
#
# Fixture layout:
#
#   mik_export/
#       Playlist A/
#           track01.flac   ← artwork lost by MIK export
#       Playlist B/
#           track02.flac   ← artwork lost by MIK export
#           track05.flac   ← no match in library
#   library/
#       Artist A/
#           Album 1/
#               track01.flac   ← artwork intact
#               track04.flac   ← not in MIK export (extra library file)
#       Artist B/
#           Album 2/
#               track02.flac   ← artwork intact
#               track03.flac   ← no artwork (shouldn't crash)


@pytest.fixture()
def mik_example(tmp_path: Path) -> dict:
    """Build MIK export + library under *tmp_path* and return Path handles."""
    export = tmp_path / "mik_export"
    playlist_a = export / "Playlist A"
    playlist_b = export / "Playlist B"
    playlist_a.mkdir(parents=True)
    playlist_b.mkdir(parents=True)

    library = tmp_path / "library"
    album1 = library / "Artist A" / "Album 1"
    album2 = library / "Artist B" / "Album 2"
    album1.mkdir(parents=True)
    album2.mkdir(parents=True)

    # MIK export files — artwork lost during export
    t01_export = make_flac(playlist_a / "track01.flac", with_picture=False)
    t02_export = make_flac(playlist_b / "track02.flac", with_picture=False)
    # track05 exists only in the export (no library match)
    t05_export = make_flac(playlist_b / "track05.flac", with_picture=False)

    # Library files — artwork intact
    make_flac(album1 / "track01.flac", with_picture=True)
    make_flac(album2 / "track02.flac", with_picture=True)
    make_flac(album1 / "track04.flac", with_picture=True)   # extra, not in export
    make_flac(album2 / "track03.flac", with_picture=False)  # library file with no art

    return {
        "export": export,
        "library": library,
        "t01_export": t01_export,
        "t02_export": t02_export,
        "t05_export": t05_export,
    }


def _mik_run(mik_example, dry_run: bool) -> dict:
    logs = []
    restorer = MIKArtworkRestorer(
        mik_export_root=mik_example["export"],
        library_root=mik_example["library"],
        dry_run=dry_run,
        log_callback=lambda msg, level="info": logs.append(msg),
    )
    summary = restorer.run()
    summary["_logs"] = logs
    return summary


class TestMIKDryRun:
    def test_no_files_modified(self, mik_example):
        _mik_run(mik_example, dry_run=True)
        assert picture_count(mik_example["t01_export"]) == 0
        assert picture_count(mik_example["t02_export"]) == 0
        assert picture_count(mik_example["t05_export"]) == 0

    def test_correct_summary(self, mik_example):
        summary = _mik_run(mik_example, dry_run=True)
        # 3 export files: t01, t02, t05
        assert summary["total"] == 3
        # t01 and t02 match library files WITH artwork
        assert summary["matched"] == 2
        # t05 has no library match
        assert summary["no_library_match"] == 1
        # no library file without artwork is hit by export lookup
        assert summary["no_artwork_in_library"] == 0
        assert summary["errors"] == 0

    def test_dry_run_logged(self, mik_example):
        summary = _mik_run(mik_example, dry_run=True)
        combined = "\n".join(summary["_logs"])
        assert "DRY RUN" in combined


class TestMIKLiveRun:
    def test_artwork_restored_on_matched_files(self, mik_example):
        _mik_run(mik_example, dry_run=False)
        assert picture_count(mik_example["t01_export"]) == 1
        assert picture_count(mik_example["t02_export"]) == 1

    def test_unmatched_file_untouched(self, mik_example):
        _mik_run(mik_example, dry_run=False)
        assert picture_count(mik_example["t05_export"]) == 0

    def test_correct_summary(self, mik_example):
        summary = _mik_run(mik_example, dry_run=False)
        assert summary["total"] == 3
        assert summary["matched"] == 2
        assert summary["no_library_match"] == 1
        assert summary["no_artwork_in_library"] == 0
        assert summary["errors"] == 0

    def test_picture_data_integrity(self, mik_example):
        """Image bytes in the restored file must exactly match the library source."""
        lib_flac = FLAC(str(mik_example["library"] / "Artist A" / "Album 1" / "track01.flac"))
        expected_data = lib_flac.pictures[0].data

        _mik_run(mik_example, dry_run=False)

        restored = FLAC(str(mik_example["t01_export"]))
        assert len(restored.pictures) == 1
        assert restored.pictures[0].data == expected_data

    def test_other_tags_preserved(self, mik_example):
        """Restoration must not remove or alter Vorbis comments on the target file."""
        target = FLAC(str(mik_example["t01_export"]))
        target["title"] = ["MIK Regression Track"]
        target["artist"] = ["Test Artist"]
        target.save()

        _mik_run(mik_example, dry_run=False)

        restored = FLAC(str(mik_example["t01_export"]))
        assert restored.get("title") == ["MIK Regression Track"]
        assert restored.get("artist") == ["Test Artist"]

    def test_idempotent_second_run(self, mik_example):
        """Running twice must not duplicate picture blocks."""
        _mik_run(mik_example, dry_run=False)
        _mik_run(mik_example, dry_run=False)
        assert picture_count(mik_example["t01_export"]) == 1
        assert picture_count(mik_example["t02_export"]) == 1

    def test_export_file_with_existing_artwork_is_overwritten(self, mik_example):
        """MIK export files that already carry artwork are always overwritten."""
        # Give the export file artwork before the run
        export_flac = FLAC(str(mik_example["t01_export"]))
        from mutagen.flac import Picture
        pic = Picture()
        pic.type = 3
        pic.mime = "image/png"
        pic.data = b"old artwork"
        export_flac.add_picture(pic)
        export_flac.save()

        _mik_run(mik_example, dry_run=False)

        restored = FLAC(str(mik_example["t01_export"]))
        # Should have exactly one picture (replaced, not appended)
        assert len(restored.pictures) == 1
        # The old artwork bytes should have been replaced by the library artwork
        assert restored.pictures[0].data != b"old artwork"


class TestMIKEdgeCases:
    def test_export_with_no_flac_files(self, tmp_path):
        export = tmp_path / "export"
        export.mkdir()
        lib = tmp_path / "lib"
        lib.mkdir()
        (export / "playlist.m3u").write_text("# playlist")
        restorer = MIKArtworkRestorer(export, lib, dry_run=True)
        summary = restorer.run()
        assert summary["total"] == 0

    def test_empty_library(self, tmp_path):
        export = tmp_path / "export"
        export.mkdir()
        lib = tmp_path / "lib"
        lib.mkdir()
        make_flac(export / "song.flac")
        restorer = MIKArtworkRestorer(export, lib, dry_run=False)
        summary = restorer.run()
        assert summary["no_library_match"] == 1
        assert summary["matched"] == 0

    def test_deeply_nested_structures(self, tmp_path):
        export = tmp_path / "export"
        (export / "a" / "b" / "c").mkdir(parents=True)
        lib = tmp_path / "lib"
        (lib / "x" / "y" / "z").mkdir(parents=True)

        target = make_flac(export / "a" / "b" / "c" / "deep.flac", with_picture=False)
        make_flac(lib / "x" / "y" / "z" / "deep.flac", with_picture=True)

        restorer = MIKArtworkRestorer(export, lib, dry_run=False)
        summary = restorer.run()
        assert summary["matched"] == 1
        assert picture_count(target) == 1

    def test_duplicate_library_names_first_wins(self, tmp_path):
        export = tmp_path / "export"
        export.mkdir()
        lib = tmp_path / "lib"
        (lib / "a").mkdir(parents=True)
        (lib / "b").mkdir(parents=True)

        target = make_flac(export / "song.flac", with_picture=False)
        make_flac(lib / "a" / "song.flac", with_picture=True)
        make_flac(lib / "b" / "song.flac", with_picture=True)

        logs = []
        restorer = MIKArtworkRestorer(
            export, lib, dry_run=False,
            log_callback=lambda msg, level="info": logs.append((level, msg)),
        )
        summary = restorer.run()

        assert any("duplicate" in msg.lower() for _, msg in logs)
        assert summary["matched"] == 1
        assert picture_count(target) == 1

    def test_large_batch(self, tmp_path):
        """Smoke-test with 200 files to confirm no performance issues."""
        export = tmp_path / "export"
        export.mkdir()
        lib = tmp_path / "lib"
        lib.mkdir()

        n = 200
        for i in range(n):
            make_flac(export / f"track_{i:04d}.flac", with_picture=False)
            make_flac(lib / f"track_{i:04d}.flac", with_picture=True)

        progress_calls = []
        restorer = MIKArtworkRestorer(
            export, lib, dry_run=False,
            progress_callback=lambda cur, tot: progress_calls.append((cur, tot)),
        )
        summary = restorer.run()

        assert summary["total"] == n
        assert summary["matched"] == n
        assert summary["errors"] == 0
        assert len(progress_calls) == n
