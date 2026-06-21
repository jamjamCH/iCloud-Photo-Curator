"""Unit tests for pure / side-effect-free logic in icloud_photo_curator_mcp.

These tests never touch iCloud, the filesystem (beyond a tmp dir), or a
real keyring.  They mock the `mcp` package so the module can be imported
without a running MCP server.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

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

class _FakeImage:
    def __init__(self, path=None, data=None, format=None) -> None:
        self.path = path
        self.data = data
        self.format = format

_mcp_fastmcp_stub.FastMCP = _FakeFastMCP
_mcp_fastmcp_stub.Image = _FakeImage
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
    _metadata_only_analysis,
    _normalize_action,
    _parse_env_value,
    _reverse_geocode,
    _safe_name,
    _to_float,
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
        action = self._action("add_to_existing_album", "Travel", confidence=0.3)
        result = _normalize_action(action, self._existing)
        assert result["type"] == "needs_review"

    def test_high_confidence_add_existing_passes(self):
        action = self._action("add_to_existing_album", "Travel", confidence=0.9)
        result = _normalize_action(action, self._existing)
        assert result["type"] == "add_to_existing_album"
        assert result["album_name"] == "Travel"

    def test_add_to_unknown_album_becomes_needs_review(self):
        action = self._action("add_to_existing_album", "Nonexistent", confidence=0.9)
        result = _normalize_action(action, self._existing)
        assert result["type"] == "needs_review"

    def test_create_album_passes(self):
        action = self._action("create_album", "Weddings", confidence=0.85)
        result = _normalize_action(action, self._existing)
        assert result["type"] == "create_album"

    def test_skip_passes(self):
        result = _normalize_action(self._action("skip", confidence=0.95), self._existing)
        assert result["type"] == "skip"

    def test_unknown_action_type_becomes_needs_review(self):
        action = self._action("delete_everything", confidence=0.99)
        result = _normalize_action(action, self._existing)
        assert result["type"] == "needs_review"

    def test_missing_primary_action_becomes_needs_review(self):
        result = _normalize_action({}, self._existing)
        assert result["type"] == "needs_review"

    def test_confidence_threshold_boundary(self, monkeypatch):
        monkeypatch.setenv("ICLOUD_PHOTO_CURATOR_MIN_CONFIDENCE", "0.80")
        below = _normalize_action(
            self._action("create_album", "X", confidence=0.79), self._existing
        )
        assert below["type"] == "needs_review"
        above = _normalize_action(
            self._action("create_album", "X", confidence=0.80), self._existing
        )
        assert above["type"] == "create_album"


# ---------------------------------------------------------------------------
# _to_float
# ---------------------------------------------------------------------------

class TestToFloat:
    def test_none(self):
        assert _to_float(None) is None

    def test_int(self):
        assert _to_float(3) == 3.0

    def test_numeric_string(self):
        assert _to_float("48.85") == 48.85

    def test_garbage(self):
        assert _to_float("not-a-number") is None


# ---------------------------------------------------------------------------
# _reverse_geocode
# ---------------------------------------------------------------------------

class TestReverseGeocode:
    def test_no_coordinates_returns_none(self):
        assert _reverse_geocode(None, None) is None
        assert _reverse_geocode(48.85, None) is None

    def test_missing_library_returns_hint(self, monkeypatch):
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "reverse_geocode":
                raise ModuleNotFoundError("No module named 'reverse_geocode'")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        # Use coordinates unlikely to be cached by other tests.
        result = _reverse_geocode(12.3456, 65.4321)
        assert result is not None
        assert result.get("available") is False
        assert "hint" in result

    def test_resolves_known_city_when_available(self):
        pytest.importorskip("reverse_geocode")
        result = _reverse_geocode(48.8584, 2.2945)  # Eiffel Tower
        assert result is not None
        assert result.get("available") is True
        assert result.get("country_code") == "FR"
        assert result.get("label")


# ---------------------------------------------------------------------------
# _metadata_only_analysis location handling
# ---------------------------------------------------------------------------

class TestLocationAnalysis:
    def test_screenshot_filename_suggests_album(self):
        meta = {"filename": "Screenshot 2024.png", "media": {}, "gps": {}}
        analysis = _metadata_only_analysis(meta, ["Screenshots"])
        assert analysis["primary_action"]["album_name"] == "Screenshots"

    def test_resolved_location_creates_place_album(self):
        meta = {
            "filename": "img.jpg",
            "media": {},
            "gps": {"latitude": 1.0, "longitude": 2.0},
            "location": {
                "available": True,
                "city": "Paris",
                "country": "France",
                "label": "Paris, France",
            },
        }
        analysis = _metadata_only_analysis(meta, [])
        names = [s["name"] for s in analysis["new_album_suggestions"]]
        assert "Paris" in names

    def test_unavailable_geocoder_falls_back_to_review(self):
        meta = {
            "filename": "img.jpg",
            "media": {},
            "gps": {"latitude": 1.0, "longitude": 2.0},
            "location": {"available": False, "hint": "install it"},
        }
        analysis = _metadata_only_analysis(meta, [])
        names = [s["name"] for s in analysis["new_album_suggestions"]]
        assert "Location Review" in names
