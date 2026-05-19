# Example Folder Structure

This directory contains a small illustrative file tree that mirrors a real-world
setup.  The actual `.flac` files are **not** committed — they are generated
automatically by the test suite via `tests/conftest.py`.

```
example/
├── library/
│   ├── Artist A/
│   │   └── Album 1/
│   │       └── track01.flac   ← processed by Platinum Notes (artwork lost)
│   └── Artist B/
│       └── Album 2/
│           └── track02.flac   ← processed by Platinum Notes (artwork lost)
└── pn_backups/
    ├── track01.flac            ← original backup with artwork intact
    ├── track02.flac            ← original backup with artwork intact
    └── track03.flac            ← backup with no matching library file
```

The test suite (`tests/test_regression.py`) creates temporary copies of this
structure and verifies end-to-end that artwork is correctly restored.
