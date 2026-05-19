"""
Shared pytest fixtures and helpers for the PN Artwork Restorer test suite.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from mutagen.flac import FLAC, Picture


# ---------------------------------------------------------------------------
# Minimal valid FLAC binary (44100 Hz, 16-bit, mono, 0 samples, no audio)
# ---------------------------------------------------------------------------
# Layout: "fLaC" magic (4) + STREAMINFO block header (4) + STREAMINFO data (34)
# STREAMINFO packed field: sample_rate=44100, channels=1, bps=16, total_samples=0
MINIMAL_FLAC_BYTES: bytes = bytes([
    0x66, 0x4C, 0x61, 0x43,  # "fLaC"
    0x80, 0x00, 0x00, 0x22,  # last-block flag | type=STREAMINFO, length=34
    # STREAMINFO (34 bytes)
    0x10, 0x00,              # min_blocksize = 4096
    0x10, 0x00,              # max_blocksize = 4096
    0x00, 0x00, 0x00,        # min_framesize = 0
    0x00, 0x00, 0x00,        # max_framesize = 0
    # Packed: sample_rate(20 b)=44100, channels(3 b)=0→1ch, bps(5 b)=15→16bit,
    #         total_samples(36 b)=0
    0x0A, 0xC4, 0x40, 0xF0, 0x00, 0x00, 0x00, 0x00,
    # MD5 signature (16 bytes, all zero for silent file)
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
])

# Minimal fake PNG header + padding — mutagen stores picture data as raw bytes
# and never validates the image content, so this is sufficient for tests.
FAKE_PNG_DATA: bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def make_flac(path: Path, with_picture: bool = False) -> Path:
    """
    Write a minimal FLAC file to *path*.

    If *with_picture* is True, embed one fake cover-art PICTURE block.
    Returns *path* for convenience.
    """
    path.write_bytes(MINIMAL_FLAC_BYTES)
    if with_picture:
        flac = FLAC(str(path))
        pic = Picture()
        pic.type = 3          # PictureType.COVER_FRONT
        pic.mime = "image/png"
        pic.width = 1
        pic.height = 1
        pic.depth = 8
        pic.data = FAKE_PNG_DATA
        flac.add_picture(pic)
        flac.save()
    return path


def picture_count(path: Path) -> int:
    """Return the number of PICTURE blocks embedded in the FLAC at *path*."""
    return len(FLAC(str(path)).pictures)


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_library(tmp_path: Path) -> Path:
    """Empty temporary library root directory."""
    lib = tmp_path / "library"
    lib.mkdir()
    return lib


@pytest.fixture()
def tmp_backup(tmp_path: Path) -> Path:
    """Empty temporary (flat) backup directory."""
    bak = tmp_path / "pn_backups"
    bak.mkdir()
    return bak
