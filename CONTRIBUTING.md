# Contributing to iCloud Photo Curator

Thank you for your interest in contributing.

## Before You Start

This project uses private iCloud CloudKit endpoints via `icloudpy`. If you plan
to work on write features, test only against disposable test albums in a
non-primary iCloud account.

## Setup

```bash
python scripts/bootstrap.py
```

Install dev dependencies:

```bash
.venv/Scripts/python.exe -m pip install -e ".[dev]"   # Windows
.venv/bin/python -m pip install -e ".[dev]"            # macOS / Linux
```

## Running Tests

```bash
.venv/Scripts/python.exe -m pytest   # Windows
.venv/bin/python -m pytest           # macOS / Linux
```

All tests are pure unit tests — no iCloud account or network access needed.

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
.venv/Scripts/python.exe -m ruff check scripts/ tests/
.venv/Scripts/python.exe -m ruff format scripts/ tests/
```

CI will reject PRs that fail Ruff checks.

## Pull Request Guidelines

- Keep PRs focused: one fix or feature per PR.
- Add or update tests for any changed logic.
- Do not add new write operations without updating `write_capabilities` and `docs/security.md`.
- Never commit credentials, `.env` files, session cookies, or cached photos.
- Run the test suite locally before opening a PR.

## Safety Rules for Contributors

The write adapter uses private Apple CloudKit mutations. Any change to
`create_album`, `add_photo_to_album`, or `apply_proposals` must:

1. Keep `dry_run=True` as the default.
2. Preserve the `_write_guard()` check with both confirmation strings.
3. Never add photo deletion, album deletion, or album renaming.

## Reporting Bugs

Open an issue on GitHub. Include your OS, Python version, and the output of:

```bash
python scripts/try_curator.py setup
```

Do **not** include your Apple ID, passwords, or session files in issues.
