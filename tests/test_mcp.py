"""Unit tests for pure / side-effect-free logic in icloud_photo_curator_mcp.

These tests never touch iCloud, the filesystem (beyond a tmp dir), or a
real keyring.  They mock the `mcp` package so the module can be imported
without a running MCP server.
"""
from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Stub the mcp package so the module can be imported without the real server.
# ---------------------------------------------------------------------------
_mcp_stub = types.ModuleType("mcp")
_mcp_server_stub = types.ModuleType("mcp.server")
_mcp_fastmcp_stub = types.ModuleType("mcp.server.fastmcp")

class _FakeFastMCP:
    def __init__(self, name: str) -> None:
        self.name = name

    def tool(self):
        def decorator(fn):
            return fn
        return decorator

    def run(self):
        pass

_mcp_fastmcp_stub.FastMCP = _FakeFastMCP
_mcp_stub.server = _mcp_server_stub
_mcp_server_stub.fastmcp = _mcp_fastmcp_stub

for _name, _mod in [
    ("mcp", _mcp_stub),
    ("mcp.server", _mcp_server_stub),
    ("mcp.server.fastmcp", _mcp_fastmcp_stub),
]:
    sys.modules.setdefault(_name, _mod)

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from icloud_photo_curator_mcp import (  # noqa: E402
    SAFE_WRITE_CONFIRMATION,
    WRITE_RISK_ACKNOWLEDGEMENT,
    _hash,
    _normalize_action,
    _parse_env_value,
    _safe_name,
    _write_guard,
)


# ---------------------------------------------------------------------------
# _write_guard
# ---------------------------------------------------------------------------

class TestWriteGuard:
    def test_dry_run_always_passes(self):
        assert _write_guard(dry_run=True) is None

    def test_dry_run_ignores_bad_confirmation(self):
        assert _write_guard(confirmation="wrong", dry_run=True) is None

    def test_live_blocked_when_writes_disabled(self, monkeypatch):
        monkeypatch.delenv("ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES", raising=False)
        result = _write_guard(
            confirmation=SAFE_WRITE_CONFIRMATION,
            risk_acknowledgement=WRITE_RISK_ACKNOWLEDGEMENT,
            dry_run=False,
        )
        assert result is not None
        assert result["allowed"] is False
        assert "required_env" in result

    def test_live_blocked_wrong_confirmation(self, monkeypatch):
        monkeypatch.setenv("ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES", "true")
        result = _write_guard(
            confirmation="not the right phrase",
            risk_acknowledgement=WRITE_RISK_ACKNOWLEDGEMENT,
            dry_run=False,
        )
        assert result is not None
        assert result["allowed"] is False
        assert result["required_confirmation"] == SAFE_WRITE_CONFIRMATION

    def test_live_blocked_wrong_acknowledgement(self, monkeypatch):
        monkeypatch.setenv("ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES", "true")
        result = _write_guard(
            confirmation=SAFE_WRITE_CONFIRMATION,
            risk_acknowledgement="nope",
            dry_run=False,
        )
        assert result is not None
        assert result["allowed"] is False
        assert result["required_acknowledgement"] == WRITE_RISK_ACKNOWLEDGEMENT

    def test_live_allowed_with_correct_phrases(self, monkeypatch):
        monkeypatch.setenv("ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES", "true")
        result = _write_guard(
            confirmation=SAFE_WRITE_CONFIRMATION,
            risk_acknowledgement=WRITE_RISK_ACKNOWLEDGEMENT,
            dry_run=False,
        )
        assert result is None

    def test_live_blocked_empty_strings(self, monkeypatch):
        monkeypatch.setenv("ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES", "true")
        result = _write_guard(confirmation="", risk_acknowledgement="", dry_run=False)
        assert result is not None
        assert result["allowed"] is False

    def test_env_value_true_only(self, monkeypatch):
        for bad in ("1", "yes", "True", "TRUE", " true"):
            monkeypatch.setenv("ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES", bad)
            result = _write_guard(
                confirmation=SAFE_WRITE_CONFIRMATION,
                risk_acknowledgement=WRITE_RISK_ACKNOWLEDGEMENT,
                dry_run=False,
            )
            assert result is not None, f"Expected blocked for env value '{bad}'"


# ---------------------------------------------------------------------------
# _parse_env_value
# ---------------------------------------------------------------------------

class TestParseEnvValue:
    def test_strips_whitespace(self):
        assert _parse_env_value("  hello  ") == "hello"

    def test_strips_double_quotes(self):
        assert _parse_env_value('"value"') == "value"

    def test_strips_single_quotes(self):
        assert _parse_env_value("'value'") == "value"

    def test_no_quotes_unchanged(self):
        assert _parse_env_value("plain") == "plain"

    def test_mismatched_quotes_unchanged(self):
        assert _parse_env_value("'mixed\"") == "'mixed\""

    def test_empty_string(self):
        assert _parse_env_value("") == ""

    def test_only_quotes(self):
        assert _parse_env_value('""') == ""


# ---------------------------------------------------------------------------
# _safe_name
# ---------------------------------------------------------------------------

class TestSafeName:
    def test_replaces_spaces(self):
        result = _safe_name("my photo.jpg")
        assert " " not in result

    def test_replaces_special_chars(self):
        result = _safe_name("photo@2024!.jpg")
        assert "@" not in result
        assert "!" not in result

    def test_allows_dots_hyphens_underscores(self):
        result = _safe_name("photo_file-name.jpg")
        assert result == "photo_file-name.jpg"

    def test_truncates_at_120(self):
        long_name = "a" * 200
        assert len(_safe_name(long_name)) <= 120

    def test_none_uses_fallback(self):
        assert _safe_name(None) == "asset"

    def test_empty_string_uses_fallback(self):
        assert _safe_name("") == "asset"

    def test_custom_fallback(self):
        assert _safe_name("", fallback="photo") == "photo"


# ---------------------------------------------------------------------------
# _hash
# ---------------------------------------------------------------------------

class TestHash:
    def test_deterministic(self):
        assert _hash("hello") == _hash("hello")

    def test_different_inputs_differ(self):
        assert _hash("foo") != _hash("bar")

    def test_length_16(self):
        assert len(_hash("anything")) == 16

    def test_hex_chars_only(self):
        result = _hash("test value")
        assert all(c in "0123456789abcdef" for c in result)


# ---------------------------------------------------------------------------
# _normalize_action
# ---------------------------------------------------------------------------

class TestNormalizeAction:
    _existing = ["Travel", "Screenshots", "Family"]

    def _action(self, action_type, album=None, confidence=0.9, reason="ok"):
        return {
            "primary_action": {
                "type": action_type,
                "album_name": album,
                "confidence": confidence,
                "reason": reason,
            }
        }

    def test_low_confidence_becomes_needs_review(self):
        result = _normalize_action(self._action("add_to_existing_album", "Travel", confidence=0.3), self._existing)
        assert result["type"] == "needs_review"

    def test_high_confidence_add_existing_passes(self):
        result = _normalize_action(self._action("add_to_existing_album", "Travel", confidence=0.9), self._existing)
        assert result["type"] == "add_to_existing_album"
        assert result["album_name"] == "Travel"

    def test_add_to_unknown_album_becomes_needs_review(self):
        result = _normalize_action(self._action("add_to_existing_album", "Nonexistent", confidence=0.9), self._existing)
        assert result["type"] == "needs_review"

    def test_create_album_passes(self):
        result = _normalize_action(self._action("create_album", "Weddings", confidence=0.85), self._existing)
        assert result["type"] == "create_album"

    def test_skip_passes(self):
        result = _normalize_action(self._action("skip", confidence=0.95), self._existing)
        assert result["type"] == "skip"

    def test_unknown_action_type_becomes_needs_review(self):
        result = _normalize_action(self._action("delete_everything", confidence=0.99), self._existing)
        assert result["type"] == "needs_review"

    def test_missing_primary_action_becomes_needs_review(self):
        result = _normalize_action({}, self._existing)
        assert result["type"] == "needs_review"

    def test_confidence_threshold_boundary(self, monkeypatch):
        monkeypatch.setenv("ICLOUD_PHOTO_CURATOR_MIN_CONFIDENCE", "0.80")
        below = _normalize_action(self._action("create_album", "X", confidence=0.79), self._existing)
        assert below["type"] == "needs_review"
        above = _normalize_action(self._action("create_album", "X", confidence=0.80), self._existing)
        assert above["type"] == "create_album"
