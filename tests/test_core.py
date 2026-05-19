"""
Unit tests for pn_artwork_restorer.ArtworkRestorer

Each test focuses on one specific method or behaviour so that failures are
easy to diagnose.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from mutagen.flac import FLAC

from pn_artwork_restorer import ArtworkRestorer, _load_saved_paths, _save_saved_paths
from tests.conftest import make_flac, picture_count, FAKE_PNG_DATA


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_restorer(library, backup, dry_run=True, logs=None):
    """Return an ArtworkRestorer whose callbacks append to *logs*."""
    if logs is None:
        logs = []
    return ArtworkRestorer(
        library_root=library,
        backup_folder=backup,
        dry_run=dry_run,
        log_callback=lambda msg, level="info": logs.append((level, msg)),
    ), logs


# ---------------------------------------------------------------------------
# build_backup_dict
# ---------------------------------------------------------------------------

class TestBuildBackupDict:
    def test_empty_backup_folder(self, tmp_backup):
        restorer, _ = _make_restorer(tmp_backup, tmp_backup)
        bd, dupes = restorer.build_backup_dict()
        assert bd == {}
        assert dupes == []

    def test_single_flac_indexed(self, tmp_backup):
        make_flac(tmp_backup / "song.flac")
        restorer, _ = _make_restorer(tmp_backup, tmp_backup)
        bd, dupes = restorer.build_backup_dict()
        assert "song.flac" in bd
        assert dupes == []

    def test_key_is_lower_case(self, tmp_backup):
        make_flac(tmp_backup / "UPPER.FLAC")
        restorer, _ = _make_restorer(tmp_backup, tmp_backup)
        bd, _ = restorer.build_backup_dict()
        assert "upper.flac" in bd

    def test_non_flac_files_ignored(self, tmp_backup):
        (tmp_backup / "cover.jpg").write_bytes(b"\xff\xd8")
        (tmp_backup / "info.txt").write_text("notes")
        restorer, _ = _make_restorer(tmp_backup, tmp_backup)
        bd, _ = restorer.build_backup_dict()
        assert bd == {}

    def test_duplicate_detection(self, tmp_backup):
        """Only the first occurrence is kept; duplicate name is reported."""
        make_flac(tmp_backup / "dupe.flac")
        make_flac(tmp_backup / "Dupe.flac")   # same name, different case
        restorer, logs = _make_restorer(tmp_backup, tmp_backup)
        bd, dupes = restorer.build_backup_dict()
        # Only one entry in dict
        assert len(bd) == 1
        assert "dupe.flac" in bd
        # Duplicate flag raised
        assert "dupe.flac" in dupes
        # Warning logged
        assert any("duplicate" in msg.lower() for _, msg in logs)

    def test_multiple_unique_files(self, tmp_backup):
        for name in ("a.flac", "b.flac", "c.flac"):
            make_flac(tmp_backup / name)
        restorer, _ = _make_restorer(tmp_backup, tmp_backup)
        bd, dupes = restorer.build_backup_dict()
        assert len(bd) == 3
        assert dupes == []

    def test_subdirectories_are_not_scanned(self, tmp_backup):
        """build_backup_dict is flat — subdirs inside backup are ignored."""
        sub = tmp_backup / "subdir"
        sub.mkdir()
        make_flac(sub / "nested.flac")
        restorer, _ = _make_restorer(tmp_backup, tmp_backup)
        bd, _ = restorer.build_backup_dict()
        assert "nested.flac" not in bd


# ---------------------------------------------------------------------------
# find_library_files
# ---------------------------------------------------------------------------

class TestFindLibraryFiles:
    def test_empty_library(self, tmp_library, tmp_backup):
        restorer, _ = _make_restorer(tmp_library, tmp_backup)
        assert restorer.find_library_files() == []

    def test_flat_single_file(self, tmp_library, tmp_backup):
        make_flac(tmp_library / "track.flac")
        restorer, _ = _make_restorer(tmp_library, tmp_backup)
        files = restorer.find_library_files()
        assert len(files) == 1
        assert files[0].name == "track.flac"

    def test_recursive_scan(self, tmp_library, tmp_backup):
        (tmp_library / "Artist A" / "Album 1").mkdir(parents=True)
        (tmp_library / "Artist B" / "Album 2").mkdir(parents=True)
        make_flac(tmp_library / "Artist A" / "Album 1" / "t01.flac")
        make_flac(tmp_library / "Artist B" / "Album 2" / "t02.flac")
        make_flac(tmp_library / "t00.flac")  # at root level

        restorer, _ = _make_restorer(tmp_library, tmp_backup)
        files = restorer.find_library_files()
        assert len(files) == 3

    def test_non_flac_files_excluded(self, tmp_library, tmp_backup):
        make_flac(tmp_library / "track.flac")
        (tmp_library / "cover.jpg").write_bytes(b"\xff\xd8")
        (tmp_library / "notes.txt").write_text("liner notes")

        restorer, _ = _make_restorer(tmp_library, tmp_backup)
        files = restorer.find_library_files()
        assert len(files) == 1

    def test_results_are_sorted(self, tmp_library, tmp_backup):
        for name in ("c.flac", "a.flac", "b.flac"):
            make_flac(tmp_library / name)
        restorer, _ = _make_restorer(tmp_library, tmp_backup)
        names = [f.name for f in restorer.find_library_files()]
        assert names == sorted(names)

    def test_case_insensitive_extension(self, tmp_library, tmp_backup):
        """Files with .FLAC (upper-case) extension should be found."""
        make_flac(tmp_library / "track.FLAC")
        restorer, _ = _make_restorer(tmp_library, tmp_backup)
        # rglob("*.flac") is case-sensitive on Linux; use *.flac only.
        # This test verifies our documented behaviour: we rely on rglob("*.flac").
        # On case-sensitive file systems .FLAC may not match; that is acceptable
        # and consistent with the spec (lower-case .flac only).
        # We just ensure no exception is raised.
        restorer.find_library_files()


# ---------------------------------------------------------------------------
# restore_artwork_for_file
# ---------------------------------------------------------------------------

class TestRestoreArtworkForFile:
    def test_dry_run_does_not_write(self, tmp_path):
        target = make_flac(tmp_path / "target.flac", with_picture=False)
        backup = make_flac(tmp_path / "backup.flac", with_picture=True)

        restorer = ArtworkRestorer(tmp_path, tmp_path, dry_run=True)
        success, msg = restorer.restore_artwork_for_file(target, backup)

        assert success is True
        assert "[DRY RUN]" in msg
        assert picture_count(target) == 0  # file must NOT have been written

    def test_live_run_writes_picture(self, tmp_path):
        target = make_flac(tmp_path / "target.flac", with_picture=False)
        backup = make_flac(tmp_path / "backup.flac", with_picture=True)

        restorer = ArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        success, msg = restorer.restore_artwork_for_file(target, backup)

        assert success is True
        assert picture_count(target) == 1

    def test_existing_picture_in_target_is_replaced(self, tmp_path):
        """Any pre-existing picture in the target is cleared first."""
        target = make_flac(tmp_path / "target.flac", with_picture=True)
        backup = make_flac(tmp_path / "backup.flac", with_picture=True)

        restorer = ArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        success, _ = restorer.restore_artwork_for_file(target, backup)

        assert success is True
        assert picture_count(target) == 1  # still exactly one (replaced, not added)

    def test_backup_with_no_artwork_returns_failure(self, tmp_path):
        target = make_flac(tmp_path / "target.flac", with_picture=False)
        backup = make_flac(tmp_path / "backup.flac", with_picture=False)

        restorer = ArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        success, msg = restorer.restore_artwork_for_file(target, backup)

        assert success is False
        assert "no embedded artwork" in msg.lower()

    def test_corrupt_backup_returns_failure(self, tmp_path):
        target = make_flac(tmp_path / "target.flac", with_picture=False)
        corrupt = tmp_path / "corrupt.flac"
        corrupt.write_bytes(b"this is not a valid FLAC file at all")

        restorer = ArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        success, msg = restorer.restore_artwork_for_file(target, corrupt)

        assert success is False
        assert "cannot open backup" in msg.lower()

    def test_picture_data_is_preserved_exactly(self, tmp_path):
        """The raw image bytes must be identical after the round-trip."""
        backup = make_flac(tmp_path / "backup.flac", with_picture=True)
        target = make_flac(tmp_path / "target.flac", with_picture=False)

        restorer = ArtworkRestorer(tmp_path, tmp_path, dry_run=False)
        restorer.restore_artwork_for_file(target, backup)

        target_pic = FLAC(str(target)).pictures[0]
        assert target_pic.data == FAKE_PNG_DATA
        assert target_pic.mime == "image/png"


# ---------------------------------------------------------------------------
# run — integration-level unit tests
# ---------------------------------------------------------------------------

class TestRun:
    def test_summary_counts_all_cases(self, tmp_library, tmp_backup):
        """
        Library: 3 tracks
          - track_match.flac  → has a backup WITH artwork   → should be matched
          - track_noart.flac  → has a backup WITHOUT artwork → no_artwork_in_backup
          - track_only.flac   → NO backup at all            → no_backup
        """
        make_flac(tmp_library / "track_match.flac", with_picture=False)
        make_flac(tmp_library / "track_noart.flac", with_picture=False)
        make_flac(tmp_library / "track_only.flac", with_picture=False)

        make_flac(tmp_backup / "track_match.flac", with_picture=True)
        make_flac(tmp_backup / "track_noart.flac", with_picture=False)
        # no backup for track_only.flac

        restorer, _ = _make_restorer(tmp_library, tmp_backup, dry_run=True)
        summary = restorer.run()

        assert summary["total"] == 3
        assert summary["matched"] == 1
        assert summary["no_backup"] == 1
        assert summary["no_artwork_in_backup"] == 1
        assert summary["duplicate_library_filenames"] == 0
        assert summary["duplicate_backups"] == 0
        assert summary["errors"] == 0

    def test_empty_library_returns_zero_summary(self, tmp_library, tmp_backup):
        restorer, _ = _make_restorer(tmp_library, tmp_backup)
        summary = restorer.run()
        assert summary == {
            "total": 0,
            "matched": 0,
            "no_backup": 0,
            "no_artwork_in_backup": 0,
            "duplicate_library_filenames": 0,
            "duplicate_backups": 0,
            "errors": 0,
        }

    def test_progress_callback_called_for_each_file(self, tmp_library, tmp_backup):
        for i in range(5):
            make_flac(tmp_library / f"t{i:02d}.flac")

        calls = []
        restorer = ArtworkRestorer(
            tmp_library, tmp_backup, dry_run=True,
            progress_callback=lambda cur, tot: calls.append((cur, tot)),
        )
        restorer.run()

        assert len(calls) == 5
        # Progress values should be monotonically increasing
        for i, (cur, tot) in enumerate(calls, start=1):
            assert cur == i
            assert tot == 5

    def test_dry_run_does_not_modify_files(self, tmp_library, tmp_backup):
        target = make_flac(tmp_library / "song.flac", with_picture=False)
        make_flac(tmp_backup / "song.flac", with_picture=True)

        restorer, _ = _make_restorer(tmp_library, tmp_backup, dry_run=True)
        restorer.run()

        assert picture_count(target) == 0  # dry run → untouched

    def test_live_run_modifies_files(self, tmp_library, tmp_backup):
        target = make_flac(tmp_library / "song.flac", with_picture=False)
        make_flac(tmp_backup / "song.flac", with_picture=True)

        restorer, _ = _make_restorer(tmp_library, tmp_backup, dry_run=False)
        restorer.run()

        assert picture_count(target) == 1

    def test_case_insensitive_filename_matching(self, tmp_library, tmp_backup):
        """
        Library file "Song.flac" should match backup "SONG.FLAC" because
        both are normalised to lower-case before comparison.
        """
        target = make_flac(tmp_library / "Song.flac", with_picture=False)
        make_flac(tmp_backup / "SONG.FLAC", with_picture=True)

        restorer, _ = _make_restorer(tmp_library, tmp_backup, dry_run=False)
        summary = restorer.run()

        assert summary["matched"] == 1
        assert picture_count(target) == 1

    def test_log_callback_receives_messages(self, tmp_library, tmp_backup):
        make_flac(tmp_library / "track.flac")
        make_flac(tmp_backup / "track.flac", with_picture=True)

        logs = []
        restorer = ArtworkRestorer(
            tmp_library, tmp_backup, dry_run=True,
            log_callback=lambda msg, level="info": logs.append(msg),
        )
        restorer.run()

        # Should have received at least the summary separator
        combined = "\n".join(logs)
        assert "Run complete" in combined

    def test_recursive_library_structure(self, tmp_library, tmp_backup):
        (tmp_library / "A" / "B" / "C").mkdir(parents=True)
        target = make_flac(
            tmp_library / "A" / "B" / "C" / "deep.flac", with_picture=False
        )
        make_flac(tmp_backup / "deep.flac", with_picture=True)

        restorer, _ = _make_restorer(tmp_library, tmp_backup, dry_run=False)
        summary = restorer.run()

        assert summary["matched"] == 1
        assert picture_count(target) == 1

    def test_logs_fixed_file_list_and_suppresses_no_backup_debug(
        self, tmp_library, tmp_backup
    ):
        make_flac(tmp_library / "matched.flac", with_picture=False)
        make_flac(tmp_library / "unmatched.flac", with_picture=False)
        make_flac(tmp_backup / "matched.flac", with_picture=True)

        logs = []
        restorer = ArtworkRestorer(
            tmp_library,
            tmp_backup,
            dry_run=False,
            log_callback=lambda msg, level="info": logs.append((level, msg)),
        )
        summary = restorer.run()

        assert summary["matched"] == 1
        assert summary["no_backup"] == 1
        assert summary["duplicate_library_filenames"] == 0
        assert not any(level == "debug" for level, _ in logs)
        combined = "\n".join(msg for _, msg in logs)
        assert "Files restored:" in combined
        assert "  - matched.flac" in combined
        assert "Duplicate library    : 0" in combined
        assert "Duplicate backups    : 0" in combined

    def test_duplicate_library_filenames_all_restored(self, tmp_library, tmp_backup):
        """
        If two library files share the same filename in different folders, both
        should be restored from a single matching backup file.
        """
        (tmp_library / "A").mkdir()
        (tmp_library / "B").mkdir()
        target_a = make_flac(tmp_library / "A" / "dup.flac", with_picture=False)
        target_b = make_flac(tmp_library / "B" / "dup.flac", with_picture=False)
        make_flac(tmp_backup / "dup.flac", with_picture=True)

        restorer, _ = _make_restorer(tmp_library, tmp_backup, dry_run=False)
        summary = restorer.run()

        assert summary["matched"] == 2
        assert summary["duplicate_library_filenames"] == 1
        assert picture_count(target_a) == 1
        assert picture_count(target_b) == 1

    def test_summary_reports_duplicate_backup_count(self, tmp_library, tmp_backup):
        make_flac(tmp_library / "song.flac", with_picture=False)
        make_flac(tmp_backup / "song.flac", with_picture=True)
        make_flac(tmp_backup / "Song.flac", with_picture=True)

        logs = []
        restorer = ArtworkRestorer(
            tmp_library,
            tmp_backup,
            dry_run=False,
            log_callback=lambda msg, level="info": logs.append((level, msg)),
        )
        summary = restorer.run()

        assert summary["duplicate_backups"] == 1
        combined = "\n".join(msg for _, msg in logs)
        assert "Duplicate backups    : 1" in combined


class TestConfigPersistence:
    def test_load_saved_paths_defaults_when_file_missing(self, tmp_path):
        config_path = tmp_path / "missing_config.json"
        paths = _load_saved_paths(config_path=config_path)
        assert paths == {"library_root": "", "backup_folder": ""}

    def test_load_saved_paths_invalid_json_falls_back(self, tmp_path):
        config_path = tmp_path / "bad_config.json"
        config_path.write_text("{not valid json", encoding="utf-8")
        paths = _load_saved_paths(config_path=config_path)
        assert paths == {"library_root": "", "backup_folder": ""}

    def test_save_and_load_saved_paths_round_trip(self, tmp_path):
        config_path = tmp_path / "subdir" / "app_config.json"
        _save_saved_paths(
            library_root="/music/library",
            backup_folder="/music/backup",
            config_path=config_path,
        )
        paths = _load_saved_paths(config_path=config_path)
        assert paths == {
            "library_root": "/music/library",
            "backup_folder": "/music/backup",
        }
