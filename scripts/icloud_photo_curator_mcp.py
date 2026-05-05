from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError as exc:  # pragma: no cover - dependency bootstrap path
    if "--self-test" in sys.argv:
        print("Missing dependency: install requirements.txt before running the MCP server.")
        sys.exit(1)
    raise exc

mcp = FastMCP("icloud-photo-curator")

_api: Any | None = None

SAFE_WRITE_CONFIRMATION = "I understand this will change my iCloud Photos albums"
CODEX_REVIEW_MODE = "codex-native"
WRITE_RISK_ACKNOWLEDGEMENT = (
    "I understand iCloud album writes are experimental and I am responsible for the changes"
)
SUPPORTED_CONFIG_KEYS = {
    "ICLOUD_PHOTO_CURATOR_APPLE_ID",
    "ICLOUD_PHOTO_CURATOR_REGION",
    "ICLOUD_PHOTO_CURATOR_STATE_DIR",
}
DEFAULT_CONFIG_DIR = Path.home() / ".icloud-photo-curator"
DEFAULT_ENV_PATH = DEFAULT_CONFIG_DIR / ".env"
_dotenv_values: dict[str, str] = {}

DEFAULT_CURATION_RULES = """# iCloud Photo Curator Rules

These are personal sorting rules for the AI client.

## Default behavior

- Ask before doing anything beyond a small scan.
- Prefer existing albums when the fit is clear.
- Create new album suggestions only when no existing album fits.
- Mark uncertain cases as needs_review.
- Use thumb or medium previews unless the user explicitly asks for originals.

## Album style

- Keep album names short and human-readable.
- Avoid duplicate albums with near-identical names.
- Do not infer real names for people from faces.

## Confidence

- High confidence: safe to propose directly.
- Medium confidence: propose with a reason.
- Low confidence: mark needs_review.
"""


def _parse_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _load_local_env(path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key in SUPPORTED_CONFIG_KEYS:
            values[key] = _parse_env_value(value)
    return values


def _reload_local_env() -> dict[str, str]:
    global _dotenv_values
    _dotenv_values = _load_local_env()
    return _dotenv_values


def _config_value(key: str, default: str | None = None) -> str | None:
    return os.getenv(key) or _dotenv_values.get(key) or default


_reload_local_env()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_dir() -> Path:
    configured = _config_value("ICLOUD_PHOTO_CURATOR_STATE_DIR", "~/.icloud-photo-curator")
    path = Path(configured).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    (path / "cache").mkdir(parents=True, exist_ok=True)
    (path / "session").mkdir(parents=True, exist_ok=True)
    return path


def _db_path() -> Path:
    return _state_dir() / "curator.sqlite"


def _rules_path() -> Path:
    return _state_dir() / "rules.md"


def _read_curation_rules() -> str:
    path = _rules_path()
    if not path.exists():
        path.write_text(DEFAULT_CURATION_RULES, encoding="utf-8")
    return path.read_text(encoding="utf-8")


def _write_curation_rules(rules_markdown: str) -> Path:
    path = _rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rules_markdown.strip() + "\n", encoding="utf-8")
    return path


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(_db_path())
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS proposals (
            id TEXT PRIMARY KEY,
            asset_id TEXT NOT NULL,
            source_album TEXT NOT NULL,
            action_json TEXT NOT NULL,
            analysis_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS scans (
            id TEXT PRIMARY KEY,
            source_album TEXT NOT NULL,
            limit_count INTEGER NOT NULL,
            skip_count INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            summary_json TEXT NOT NULL
        )
        """
    )
    con.commit()
    return con


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def _compact_error(exc: BaseException) -> dict[str, str]:
    return {"type": type(exc).__name__, "message": str(exc)}


def _safe_name(value: str | None, fallback: str = "asset") -> str:
    value = value or fallback
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._")
    return value[:120] or fallback


def _hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]


def _field(fields: dict[str, Any], name: str, default: Any = None) -> Any:
    item = fields.get(name)
    if not isinstance(item, dict):
        return default
    return item.get("value", default)


def _first_field(records: list[dict[str, Any]], names: list[str], default: Any = None) -> Any:
    for record in records:
        fields = record.get("fields", {}) if isinstance(record, dict) else {}
        for name in names:
            value = _field(fields, name, None)
            if value is not None:
                return value
    return default


def _decode_b64_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return base64.b64decode(value).decode("utf-8")
    except Exception:
        return None


def _import_icloudpy() -> Any:
    try:
        from icloudpy import ICloudPyService
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "icloudpy is not installed. Run: python -m pip install -r requirements.txt"
        ) from exc
    return ICloudPyService


def _keyring_password_available(username: str | None = None) -> bool:
    username = username or _config_value("ICLOUD_PHOTO_CURATOR_APPLE_ID")
    if not username:
        return False
    try:
        from icloudpy.utils import password_exists_in_keyring
    except ModuleNotFoundError:
        return False
    try:
        return bool(password_exists_in_keyring(username))
    except Exception:
        return False


def _require_api() -> Any:
    if _api is None:
        raise RuntimeError(
            "No iCloud session is active. Call connect_icloud first, or run try_curator.py login "
            "to configure Apple ID, Keyring password, and trusted session cookies."
        )
    return _api


def _auth_state(api: Any) -> dict[str, Any]:
    return {
        "requires_2fa": bool(getattr(api, "requires_2fa", False)),
        "requires_2sa": bool(getattr(api, "requires_2sa", False)),
        "trusted_session": not bool(getattr(api, "requires_2fa", False))
        and not bool(getattr(api, "requires_2sa", False)),
    }


def _connect(
    username: str | None = None, password: str | None = None, region: str | None = None
) -> Any:
    global _api
    _reload_local_env()
    username = username or _config_value("ICLOUD_PHOTO_CURATOR_APPLE_ID")
    password = password or os.getenv("ICLOUD_PHOTO_CURATOR_PASSWORD")
    region = region or _config_value("ICLOUD_PHOTO_CURATOR_REGION", "global")
    if not username:
        raise RuntimeError(
            "Missing Apple ID. Pass username to connect_icloud or set "
            "ICLOUD_PHOTO_CURATOR_APPLE_ID."
        )

    service_cls = _import_icloudpy()
    kwargs: dict[str, Any] = {"cookie_directory": str(_state_dir() / "session")}
    if region.lower() == "china":
        kwargs.update(
            {
                "home_endpoint": "https://www.icloud.com.cn",
                "setup_endpoint": "https://setup.icloud.com.cn/setup/ws/1",
            }
        )

    if password:
        _api = service_cls(username, password, **kwargs)
    else:
        _api = service_cls(username, **kwargs)
    return _api


def _album_by_name(api: Any, album_name: str = "All Photos") -> Any:
    normalized = (album_name or "All Photos").strip()
    if normalized.lower() in {"all", "all photos", "photos"}:
        return api.photos.all
    albums = api.photos.albums
    if normalized not in albums:
        available = sorted(albums.keys())[:50]
        raise KeyError(f"Album '{normalized}' not found. First available albums: {available}")
    return albums[normalized]


def _write_enabled() -> bool:
    return os.getenv("ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES") == "true"


def _write_guard(
    confirmation: str = "",
    risk_acknowledgement: str = "",
    dry_run: bool = True,
) -> dict[str, Any] | None:
    if dry_run:
        return None
    if not _write_enabled():
        return {
            "allowed": False,
            "reason": "Experimental writes are disabled.",
            "required_env": "ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true",
        }
    if confirmation != SAFE_WRITE_CONFIRMATION:
        return {
            "allowed": False,
            "reason": "Confirmation phrase did not match.",
            "required_confirmation": SAFE_WRITE_CONFIRMATION,
        }
    if risk_acknowledgement != WRITE_RISK_ACKNOWLEDGEMENT:
        return {
            "allowed": False,
            "reason": "Risk acknowledgement did not match.",
            "required_acknowledgement": WRITE_RISK_ACKNOWLEDGEMENT,
        }
    return None


def _modify_records(api: Any, operations: list[dict[str, Any]], desired_keys: list[str]) -> dict[str, Any]:
    endpoint = api.photos._service_endpoint
    params = api.photos.params
    from urllib.parse import urlencode

    url = f"{endpoint}/records/modify?{urlencode(params)}"
    body = {
        "operations": operations,
        "zoneID": api.photos.zone_id,
        "desiredKeys": desired_keys,
        "atomic": True,
    }
    response = api.photos.session.post(
        url,
        data=json.dumps(body),
        headers={"Content-type": "text/plain"},
    )
    try:
        payload = response.json()
    except Exception:
        payload = {"text": response.text}
    return {"status_code": response.status_code, "response": payload, "request_body": body}


def _modify_succeeded(result: dict[str, Any]) -> bool:
    response = result.get("response")
    has_errors = isinstance(response, dict) and bool(response.get("hasErrors"))
    return int(result.get("status_code", 500)) < 400 and not has_errors


def _album_desired_keys() -> list[str]:
    return [
        "albumType",
        "albumNameEnc",
        "name",
        "position",
        "sortType",
        "sortTypeExt",
        "sortAscending",
        "parentId",
        "isDeleted",
        "isExpunged",
        "dateExpunged",
        "remappedRef",
        "recordName",
        "recordType",
        "recordChangeTag",
    ]


def _relation_desired_keys() -> list[str]:
    return [
        "containerId",
        "itemId",
        "position",
        "parentId",
        "isKeyAsset",
        "isDeleted",
        "isExpunged",
        "recordName",
        "recordType",
        "recordChangeTag",
    ]


def _new_record_name(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex.upper()}"


def _album_create_operation(album_name: str) -> dict[str, Any]:
    encoded_name = base64.b64encode(album_name.encode("utf-8")).decode("ascii")
    return {
        "operationType": "create",
        "record": {
            "recordName": _new_record_name("album"),
            "recordType": "CPLAlbum",
            "recordChangeTag": None,
            "fields": {
                "albumType": {"value": 0},
                "albumNameEnc": {"value": encoded_name},
                "name": {"value": album_name},
                "position": {"value": int(time.time() * 1000)},
                "sortType": {"value": 0},
                "sortTypeExt": {"value": 0},
                "sortAscending": {"value": 1},
                "parentId": {"value": "----Root-Folder----"},
                "isDeleted": {"value": 0},
                "isExpunged": {"value": 0},
            },
        },
    }


def _relation_create_operation(album_id: str, asset_record_name: str) -> dict[str, Any]:
    return {
        "operationType": "create",
        "record": {
            "recordName": _new_record_name("relation"),
            "recordType": "CPLContainerRelation",
            "recordChangeTag": None,
            "fields": {
                "containerId": {"value": album_id},
                "itemId": {"value": asset_record_name},
                "parentId": {"value": album_id},
                "position": {"value": int(time.time() * 1000)},
                "isKeyAsset": {"value": 0},
                "isDeleted": {"value": 0},
                "isExpunged": {"value": 0},
            },
        },
    }


def _album_id(api: Any, album_name: str) -> str:
    album = _album_by_name(api, album_name)
    album_id = getattr(album, "folder_id", None)
    if not album_id:
        raise ValueError(f"Album '{album_name}' is not a writable user album.")
    return album_id


def _add_photo_to_album_id(
    api: Any,
    album_name: str,
    album_id: str,
    asset_id: str,
    source_album: str,
    dry_run: bool,
    confirmation: str,
    risk_acknowledgement: str,
) -> dict[str, Any]:
    asset = _find_asset(source_album, asset_id, max_scan=100_000)
    asset_record = getattr(asset, "_asset_record", {}) or {}
    asset_record_name = asset_record.get("recordName")
    if not asset_record_name:
        raise ValueError(f"Could not resolve asset record for '{asset_id}'.")

    operation = _relation_create_operation(album_id, asset_record_name)
    plan = {
        "operation": "add_photo_to_album",
        "album_name": album_name,
        "album_id": album_id,
        "asset_id": asset_id,
        "asset_record_name": asset_record_name,
        "relation_record_name": operation["record"]["recordName"],
    }
    guard = _write_guard(confirmation, risk_acknowledgement, dry_run=dry_run)
    if guard:
        return {"added": False, "dry_run": dry_run, "plan": plan, "guard": guard}
    if dry_run:
        return {"added": False, "dry_run": True, "plan": plan}

    result = _modify_records(api, [operation], _relation_desired_keys())
    return {
        "added": _modify_succeeded(result),
        "dry_run": False,
        "album_name": album_name,
        "asset_id": asset_id,
        "result": result["response"],
    }


def _asset_metadata(asset: Any, include_versions: bool = False) -> dict[str, Any]:
    master_record = getattr(asset, "_master_record", {}) or {}
    asset_record = getattr(asset, "_asset_record", {}) or {}
    records = [asset_record, master_record]
    master_fields = master_record.get("fields", {}) if isinstance(master_record, dict) else {}

    def safe_attr(name: str) -> Any:
        try:
            return getattr(asset, name)
        except Exception:
            return None

    caption = _decode_b64_text(_first_field(records, ["captionEnc", "extendedDescEnc"]))
    metadata: dict[str, Any] = {
        "asset_id": safe_attr("id") or master_record.get("recordName"),
        "asset_record_name": asset_record.get("recordName"),
        "master_record_name": master_record.get("recordName"),
        "filename": safe_attr("filename"),
        "size_bytes": safe_attr("size"),
        "dimensions": safe_attr("dimensions"),
        "created": safe_attr("created"),
        "asset_date": safe_attr("asset_date"),
        "added_date": safe_attr("added_date"),
        "gps": {
            "latitude": _first_field(records, ["locationLatitude", "latitude"]),
            "longitude": _first_field(records, ["locationLongitude", "longitude"]),
        },
        "flags": {
            "favorite": _first_field(records, ["isFavorite"], False),
            "hidden": _first_field(records, ["isHidden"], False),
            "deleted": _first_field(records, ["isDeleted"], False),
            "expunged": _first_field(records, ["isExpunged"], False),
        },
        "media": {
            "duration": _first_field(records, ["duration"]),
            "item_type": _first_field(records, ["itemType"]),
            "data_class_type": _first_field(records, ["dataClassType"]),
            "asset_subtype": _first_field(records, ["assetSubtype", "assetSubtypeV2"]),
            "original_file_type": _field(master_fields, "resOriginalFileType"),
        },
        "caption": caption,
    }

    if include_versions:
        try:
            versions = asset.versions
        except Exception:
            versions = {}
        metadata["versions"] = {
            name: {
                "filename": version.get("filename"),
                "width": version.get("width"),
                "height": version.get("height"),
                "size": version.get("size"),
                "type": version.get("type"),
                "has_download_url": bool(version.get("url")),
            }
            for name, version in versions.items()
        }

    return _jsonable(metadata)


def _iter_album_assets(album: Any, skip: int = 0, limit: int = 25):
    yielded = 0
    for index, asset in enumerate(album):
        if index < skip:
            continue
        if yielded >= limit:
            break
        yielded += 1
        yield index, asset


def _find_asset(album_name: str, asset_id: str, max_scan: int = 100_000) -> Any:
    api = _require_api()
    album = _album_by_name(api, album_name)
    for index, asset in enumerate(album):
        if index >= max_scan:
            break
        if getattr(asset, "id", None) == asset_id:
            return asset
    raise KeyError(f"Asset '{asset_id}' was not found in album '{album_name}' within {max_scan} items.")


def _content_type_for(path: Path, fallback: str | None = None) -> str:
    if fallback:
        return fallback.split(";")[0]
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    if suffix == ".heic":
        return "image/heic"
    if suffix in {".mov", ".mp4"}:
        return "video/mp4"
    return "application/octet-stream"


def _download_version(asset: Any, version: str = "thumb") -> dict[str, Any]:
    version = version or "thumb"
    try:
        versions = asset.versions
    except Exception as exc:
        raise RuntimeError(f"Could not read available asset versions: {exc}") from exc
    if version not in versions:
        available = sorted(versions.keys())
        raise KeyError(f"Version '{version}' not available. Available versions: {available}")

    response = asset.download(version, timeout=90)
    if response is None:
        raise RuntimeError(f"icloudpy returned no response for version '{version}'.")

    filename = versions[version].get("filename") or getattr(asset, "filename", None) or "asset"
    suffix = Path(filename).suffix or ".bin"
    asset_id = getattr(asset, "id", "unknown")
    cache_path = _state_dir() / "cache" / f"{_hash(asset_id)}_{version}_{_safe_name(filename)}"
    if not cache_path.suffix:
        cache_path = cache_path.with_suffix(suffix)

    bytes_written = 0
    with response:
        with cache_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)
                    bytes_written += len(chunk)

    return {
        "asset_id": asset_id,
        "version": version,
        "path": str(cache_path),
        "bytes_written": bytes_written,
        "content_type": _content_type_for(cache_path, response.headers.get("Content-Type")),
        "cached_at": _now(),
    }


def _existing_album_names(api: Any, limit: int = 200) -> list[str]:
    albums = sorted(str(name) for name in api.photos.albums.keys())
    return albums[: max(0, limit)]


def _metadata_only_analysis(metadata: dict[str, Any], existing_albums: list[str]) -> dict[str, Any]:
    filename = (metadata.get("filename") or "").lower()
    media = metadata.get("media") or {}
    gps = metadata.get("gps") or {}
    labels: list[str] = []
    suggested_existing: list[dict[str, Any]] = []
    new_album_suggestions: list[dict[str, Any]] = []

    def match_album(candidates: list[str], confidence: float, reason: str) -> None:
        lower_map = {album.lower(): album for album in existing_albums}
        for candidate in candidates:
            for lower, original in lower_map.items():
                if candidate in lower:
                    suggested_existing.append(
                        {"name": original, "confidence": confidence, "reason": reason}
                    )
                    return

    if "screenshot" in filename or "screen shot" in filename:
        labels.append("screenshot")
        match_album(["screenshot", "screenshots"], 0.86, "Filename looks like a screenshot.")
        if not suggested_existing:
            new_album_suggestions.append(
                {"name": "Screenshots", "confidence": 0.72, "reason": "Filename looks like a screenshot."}
            )

    if media.get("duration"):
        labels.append("video")
        match_album(["video", "videos"], 0.8, "Asset has a duration field.")
        if not suggested_existing:
            new_album_suggestions.append(
                {"name": "Videos", "confidence": 0.65, "reason": "Asset has a duration field."}
            )

    if gps.get("latitude") is not None and gps.get("longitude") is not None:
        labels.append("gps-tagged")
        new_album_suggestions.append(
            {
                "name": "Location Review",
                "confidence": 0.5,
                "reason": "GPS coordinates exist, but no reverse geocoder is configured yet.",
            }
        )

    if suggested_existing:
        primary = {
            "type": "add_to_existing_album",
            "album_name": suggested_existing[0]["name"],
            "confidence": suggested_existing[0]["confidence"],
            "reason": suggested_existing[0]["reason"],
        }
    elif new_album_suggestions:
        primary = {
            "type": "create_album",
            "album_name": new_album_suggestions[0]["name"],
            "confidence": new_album_suggestions[0]["confidence"],
            "reason": new_album_suggestions[0]["reason"],
        }
    else:
        primary = {
            "type": "needs_review",
            "album_name": None,
            "confidence": 0.2,
            "reason": "No vision model is configured and metadata alone is not enough.",
        }

    return {
        "mode": "metadata_only",
        "visual_summary": None,
        "content_labels": labels,
        "recommended_existing_albums": suggested_existing,
        "new_album_suggestions": new_album_suggestions,
        "primary_action": primary,
        "privacy_note": "No external vision API was called by the MCP server.",
    }


def _analysis_prompt(metadata: dict[str, Any], existing_albums: list[str]) -> str:
    return json.dumps(
        {
            "task": "Classify this iCloud photo for album organization.",
            "rules": [
                "Use visual content, filename, dates, GPS fields, and existing album names.",
                "Do not identify people by real name, celebrity, or biometric identity.",
                "Prefer adding to an existing album when it is clearly appropriate.",
                "Suggest a new album only when no existing album fits well.",
                "Use conservative confidence. Use needs_review below 0.7 confidence.",
                "Return strict JSON only, with no markdown.",
            ],
            "metadata": metadata,
            "existing_albums": existing_albums,
            "expected_json_shape": {
                "visual_summary": "short description",
                "content_labels": ["food", "travel", "screenshot", "document", "portrait"],
                "people_description": "generic description without identity, or null",
                "event_or_context": "inferred context or null",
                "gps_or_place_use": "how GPS influenced the recommendation or null",
                "recommended_existing_albums": [
                    {"name": "album name", "confidence": 0.0, "reason": "why"}
                ],
                "new_album_suggestions": [
                    {"name": "album name", "confidence": 0.0, "reason": "why"}
                ],
                "primary_action": {
                    "type": "add_to_existing_album | create_album | skip | needs_review",
                    "album_name": "target album or null",
                    "confidence": 0.0,
                    "reason": "why",
                },
            },
        },
        ensure_ascii=True,
    )


def _analyze_image(
    image_path: Path, metadata: dict[str, Any], existing_albums: list[str]
) -> dict[str, Any]:
    analysis = _metadata_only_analysis(metadata, existing_albums)
    analysis["mode"] = CODEX_REVIEW_MODE
    analysis["local_image_path"] = str(image_path)
    analysis["codex_instruction"] = (
        "Use prepare_photo_for_codex or prepare_batch_for_codex, inspect the returned "
        "local image path with Codex's native image understanding, then call "
        "save_codex_proposal with the album decision."
    )
    return analysis


def _normalize_action(analysis: dict[str, Any], existing_albums: list[str]) -> dict[str, Any]:
    primary = analysis.get("primary_action") or {}
    action_type = str(primary.get("type") or "needs_review")
    album_name = primary.get("album_name")
    confidence = float(primary.get("confidence") or 0.0)
    reason = primary.get("reason") or "No reason provided."

    if confidence < float(os.getenv("ICLOUD_PHOTO_CURATOR_MIN_CONFIDENCE", "0.70")):
        return {
            "type": "needs_review",
            "album_name": album_name,
            "confidence": confidence,
            "reason": f"Below confidence threshold: {reason}",
        }

    if action_type == "add_to_existing_album" and album_name not in existing_albums:
        return {
            "type": "needs_review",
            "album_name": album_name,
            "confidence": confidence,
            "reason": "Model selected an existing album name that was not in the scanned album list.",
        }

    if action_type not in {"add_to_existing_album", "create_album", "skip", "needs_review"}:
        action_type = "needs_review"

    return {
        "type": action_type,
        "album_name": album_name,
        "confidence": confidence,
        "reason": reason,
    }


def _save_proposal(
    source_album: str, metadata: dict[str, Any], analysis: dict[str, Any], action: dict[str, Any]
) -> str:
    seed = f"{metadata.get('asset_id')}:{source_album}:{json.dumps(action, sort_keys=True)}:{time.time()}"
    proposal_id = _hash(seed)
    with _db() as con:
        con.execute(
            """
            INSERT INTO proposals (
                id, asset_id, source_album, action_json, analysis_json, metadata_json,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'proposed', ?, ?)
            """,
            (
                proposal_id,
                metadata.get("asset_id"),
                source_album,
                json.dumps(_jsonable(action), ensure_ascii=True),
                json.dumps(_jsonable(analysis), ensure_ascii=True),
                json.dumps(_jsonable(metadata), ensure_ascii=True),
                _now(),
                _now(),
            ),
        )
        con.commit()
    return proposal_id


@mcp.tool()
def setup_check() -> dict[str, Any]:
    """Check local dependencies, configuration, and safety mode for this MCP server."""
    _reload_local_env()
    apple_id = _config_value("ICLOUD_PHOTO_CURATOR_APPLE_ID")
    region = _config_value("ICLOUD_PHOTO_CURATOR_REGION", "global")
    state_dir = _state_dir()
    checks: dict[str, Any] = {
        "env_path": str(DEFAULT_ENV_PATH),
        "env_exists": DEFAULT_ENV_PATH.exists(),
        "state_dir": str(state_dir),
        "session_dir": str(state_dir / "session"),
        "rules_path": str(_rules_path()),
        "rules_exists": _rules_path().exists(),
        "codex_native_ai_mode": True,
        "external_openai_api_required": False,
        "apple_id_configured": bool(apple_id),
        "region": region,
        "env_password_configured": bool(os.getenv("ICLOUD_PHOTO_CURATOR_PASSWORD")),
        "keyring_password_available": _keyring_password_available(apple_id),
        "writes_enabled": os.getenv("ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES") == "true",
        "writes_env_location": "real environment variable only; not loaded from .env",
        "safe_write_confirmation": SAFE_WRITE_CONFIRMATION,
        "write_risk_acknowledgement": WRITE_RISK_ACKNOWLEDGEMENT,
    }
    for package, import_name in {
        "mcp": "mcp",
        "icloudpy": "icloudpy",
        "keyring": "keyring",
    }.items():
        try:
            __import__(import_name)
            checks[f"{package}_installed"] = True
        except ModuleNotFoundError:
            checks[f"{package}_installed"] = False
    return checks


@mcp.tool()
def curation_workflow_guide() -> dict[str, Any]:
    """Return the required user-facing workflow questions and available operating modes."""
    return {
        "required_first_question": (
            "Should I only scan, scan and make proposals, or apply already approved proposals?"
        ),
        "modes": [
            {
                "id": "scan_only",
                "label": "Scan only",
                "description": "Read albums and metadata. Do not cache image previews unless requested.",
                "icloud_writes": False,
            },
            {
                "id": "scan_and_propose",
                "label": "Scan and propose",
                "description": "Read metadata, cache small previews, inspect them, and save local proposals.",
                "icloud_writes": False,
            },
            {
                "id": "apply_approved",
                "label": "Apply approved proposals",
                "description": "Apply already approved proposals through the experimental gated write adapter.",
                "icloud_writes": "experimental_gated",
                "default_mode": "dry_run",
                "required_confirmation": SAFE_WRITE_CONFIRMATION,
                "required_acknowledgement": WRITE_RISK_ACKNOWLEDGEMENT,
            },
        ],
        "required_scope_questions": [
            "Which source album should be scanned?",
            "How many photos should be processed in this batch?",
            "Which preview size should be used: thumb or medium?",
            "Should existing albums be preferred over new albums?",
            "Are there personal sorting rules to add or update first?",
        ],
        "safety_rules": [
            "Never delete photos.",
            "Do not apply writes unless the write adapter reports support and the user explicitly confirms.",
            "Use small batches first.",
            "Mark uncertain cases as needs_review.",
        ],
    }


@mcp.tool()
def get_curation_rules() -> dict[str, Any]:
    """Read the user's local curation rules for album decisions."""
    rules = _read_curation_rules()
    return {
        "rules_path": str(_rules_path()),
        "rules_markdown": rules,
        "note": "These rules are local user preferences and should guide scan/proposal decisions.",
    }


@mcp.tool()
def save_curation_rules(rules_markdown: str, append: bool = False) -> dict[str, Any]:
    """Create or update the user's local curation rules. This does not change iCloud."""
    if append and _rules_path().exists():
        current = _read_curation_rules().rstrip()
        rules_markdown = current + "\n\n" + rules_markdown.strip()
    path = _write_curation_rules(rules_markdown)
    return {
        "saved": True,
        "rules_path": str(path),
        "write_status": "local_rules_only",
    }


@mcp.tool()
def connect_icloud(
    username: str | None = None, password: str | None = None, region: str | None = None
) -> dict[str, Any]:
    """Create an iCloud session. Prefer env vars or keyring over passing passwords in chat."""
    try:
        api = _connect(username=username, password=password, region=region)
        return {"connected": True, "auth": _auth_state(api)}
    except Exception as exc:
        return {"connected": False, "error": _compact_error(exc)}


@mcp.tool()
def validate_2fa_code(code: str) -> dict[str, Any]:
    """Validate an iCloud 2FA code for the active session."""
    try:
        api = _require_api()
        result = api.validate_2fa_code(code)
        trust_result = None
        if hasattr(api, "trust_session"):
            trust_result = api.trust_session()
        return {"validated": bool(result), "trust_result": trust_result, "auth": _auth_state(api)}
    except Exception as exc:
        return {"validated": False, "error": _compact_error(exc)}


@mcp.tool()
def list_albums(include_counts: bool = False, max_albums: int = 300) -> dict[str, Any]:
    """List iCloud Photos albums, optionally with item counts."""
    try:
        api = _require_api()
        albums = []
        for index, (name, album) in enumerate(api.photos.albums.items()):
            if index >= max_albums:
                break
            item: dict[str, Any] = {"name": name}
            if include_counts:
                try:
                    item["count"] = len(album)
                except Exception as exc:
                    item["count_error"] = _compact_error(exc)
            albums.append(item)
        return {"albums": albums, "truncated": len(albums) >= max_albums}
    except Exception as exc:
        return {"albums": [], "error": _compact_error(exc)}


@mcp.tool()
def scan_album(
    album_name: str = "All Photos", limit: int = 25, skip: int = 0, include_versions: bool = False
) -> dict[str, Any]:
    """Read a batch of photo metadata from an iCloud album without downloading originals."""
    try:
        api = _require_api()
        album = _album_by_name(api, album_name)
        limit = max(1, min(int(limit), 250))
        skip = max(0, int(skip))
        assets = [
            _asset_metadata(asset, include_versions=include_versions)
            for _, asset in _iter_album_assets(album, skip=skip, limit=limit)
        ]
        return {
            "album_name": album_name,
            "skip": skip,
            "limit": limit,
            "returned": len(assets),
            "assets": assets,
        }
    except Exception as exc:
        return {"album_name": album_name, "assets": [], "error": _compact_error(exc)}


@mcp.tool()
def download_photo_version(
    album_name: str, asset_id: str, version: str = "thumb", max_scan: int = 100_000
) -> dict[str, Any]:
    """Download a small iCloud photo version, usually thumb or medium, into the local cache."""
    try:
        asset = _find_asset(album_name=album_name, asset_id=asset_id, max_scan=max_scan)
        result = _download_version(asset, version=version)
        result["metadata"] = _asset_metadata(asset, include_versions=True)
        return result
    except Exception as exc:
        return {"asset_id": asset_id, "version": version, "error": _compact_error(exc)}


@mcp.tool()
def prepare_photo_for_codex(
    album_name: str,
    asset_id: str,
    version: str = "medium",
    existing_albums_limit: int = 200,
    max_scan: int = 100_000,
) -> dict[str, Any]:
    """Prepare one photo for Codex-native visual review without using an external API."""
    try:
        api = _require_api()
        asset = _find_asset(album_name=album_name, asset_id=asset_id, max_scan=max_scan)
        metadata = _asset_metadata(asset, include_versions=True)
        download = _download_version(asset, version=version)
        return {
            "mode": CODEX_REVIEW_MODE,
            "asset_id": asset_id,
            "source_album": album_name,
            "local_image_path": download["path"],
            "download": download,
            "metadata": metadata,
            "existing_albums": _existing_album_names(api, limit=existing_albums_limit),
            "curation_rules": _read_curation_rules(),
            "next_step": (
                "Codex should inspect local_image_path with native image understanding, "
                "combine that with metadata/GPS/existing_albums, then call save_codex_proposal."
            ),
            "write_status": "not_applied",
        }
    except Exception as exc:
        return {"asset_id": asset_id, "album_name": album_name, "error": _compact_error(exc)}


@mcp.tool()
def prepare_batch_for_codex(
    album_name: str = "All Photos",
    limit: int = 5,
    skip: int = 0,
    version: str = "thumb",
    existing_albums_limit: int = 200,
) -> dict[str, Any]:
    """Prepare a small batch of cached images and metadata for Codex-native review."""
    try:
        api = _require_api()
        album = _album_by_name(api, album_name)
        limit = max(1, min(int(limit), 25))
        skip = max(0, int(skip))
        items: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for index, asset in _iter_album_assets(album, skip=skip, limit=limit):
            metadata = _asset_metadata(asset, include_versions=True)
            try:
                download = _download_version(asset, version=version)
                items.append(
                    {
                        "album_index": index,
                        "asset_id": metadata.get("asset_id"),
                        "filename": metadata.get("filename"),
                        "local_image_path": download["path"],
                        "download": download,
                        "metadata": metadata,
                    }
                )
            except Exception as exc:
                errors.append(
                    {
                        "album_index": index,
                        "asset_id": metadata.get("asset_id"),
                        "filename": metadata.get("filename"),
                        "error": _compact_error(exc),
                    }
                )

        return {
            "mode": CODEX_REVIEW_MODE,
            "source_album": album_name,
            "skip": skip,
            "limit": limit,
            "version": version,
            "items": items,
            "errors": errors,
            "existing_albums": _existing_album_names(api, limit=existing_albums_limit),
            "curation_rules": _read_curation_rules(),
            "next_step": (
                "Codex should inspect each local_image_path, decide whether to add to an "
                "existing album, create a new album, skip, or mark needs_review, then call "
                "save_codex_proposal for each decision."
            ),
            "write_status": "not_applied",
        }
    except Exception as exc:
        return {"album_name": album_name, "items": [], "error": _compact_error(exc)}


@mcp.tool()
def save_codex_proposal(
    source_album: str,
    asset_id: str,
    action_type: str,
    album_name: str | None = None,
    confidence: float = 0.0,
    reason: str = "",
    visual_summary: str = "",
    content_labels: list[str] | None = None,
    rule_matches: list[str] | None = None,
) -> dict[str, Any]:
    """Save a Codex-made album decision locally without changing iCloud."""
    if action_type not in {"add_to_existing_album", "create_album", "skip", "needs_review"}:
        return {
            "saved": False,
            "error": "action_type must be add_to_existing_album, create_album, skip, or needs_review",
        }

    metadata = {"asset_id": asset_id}
    try:
        asset = _find_asset(source_album, asset_id, max_scan=100_000)
        metadata = _asset_metadata(asset, include_versions=True)
    except Exception:
        # Saving the human/Codex decision is still useful even if the asset lookup expired.
        pass

    analysis = {
        "mode": CODEX_REVIEW_MODE,
        "visual_summary": visual_summary,
        "content_labels": content_labels or [],
        "rule_matches": rule_matches or [],
        "primary_action": {
            "type": action_type,
            "album_name": album_name,
            "confidence": confidence,
            "reason": reason,
        },
    }
    action = {
        "type": action_type,
        "album_name": album_name,
        "confidence": confidence,
        "reason": reason,
    }
    proposal_id = _save_proposal(source_album, metadata, analysis, action)
    return {
        "saved": True,
        "proposal_id": proposal_id,
        "asset_id": asset_id,
        "action": action,
        "write_status": "not_applied",
    }


@mcp.tool()
def analyze_photo(
    album_name: str,
    asset_id: str,
    version: str = "medium",
    existing_albums_limit: int = 200,
    max_scan: int = 100_000,
) -> dict[str, Any]:
    """Analyze one photo version with a vision model and return album recommendations."""
    try:
        api = _require_api()
        asset = _find_asset(album_name=album_name, asset_id=asset_id, max_scan=max_scan)
        metadata = _asset_metadata(asset, include_versions=True)
        download = _download_version(asset, version=version)
        existing_albums = _existing_album_names(api, limit=existing_albums_limit)
        analysis = _analyze_image(Path(download["path"]), metadata, existing_albums)
        action = _normalize_action(analysis, existing_albums)
        return {
            "asset_id": asset_id,
            "album_name": album_name,
            "metadata": metadata,
            "download": download,
            "analysis": analysis,
            "proposed_action": action,
            "write_status": "not_applied",
        }
    except Exception as exc:
        return {"asset_id": asset_id, "album_name": album_name, "error": _compact_error(exc)}


@mcp.tool()
def curate_batch(
    album_name: str = "All Photos",
    limit: int = 10,
    skip: int = 0,
    version: str = "medium",
    existing_albums_limit: int = 200,
) -> dict[str, Any]:
    """Analyze a small iCloud Photos batch and store proposed album actions for review."""
    try:
        api = _require_api()
        album = _album_by_name(api, album_name)
        existing_albums = _existing_album_names(api, limit=existing_albums_limit)
        limit = max(1, min(int(limit), 50))
        skip = max(0, int(skip))
        proposals: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for index, asset in _iter_album_assets(album, skip=skip, limit=limit):
            metadata = _asset_metadata(asset, include_versions=True)
            try:
                download = _download_version(asset, version=version)
                analysis = _analyze_image(Path(download["path"]), metadata, existing_albums)
                action = _normalize_action(analysis, existing_albums)
                proposal_id = _save_proposal(album_name, metadata, analysis, action)
                proposals.append(
                    {
                        "proposal_id": proposal_id,
                        "album_index": index,
                        "asset_id": metadata.get("asset_id"),
                        "filename": metadata.get("filename"),
                        "action": action,
                        "analysis_summary": {
                            "mode": analysis.get("mode"),
                            "visual_summary": analysis.get("visual_summary"),
                            "labels": analysis.get("content_labels"),
                        },
                    }
                )
            except Exception as exc:
                errors.append(
                    {
                        "album_index": index,
                        "asset_id": metadata.get("asset_id"),
                        "filename": metadata.get("filename"),
                        "error": _compact_error(exc),
                    }
                )

        scan_id = _hash(f"{album_name}:{skip}:{limit}:{time.time()}")
        summary = {
            "scan_id": scan_id,
            "album_name": album_name,
            "skip": skip,
            "limit": limit,
            "version": version,
            "proposal_count": len(proposals),
            "error_count": len(errors),
        }
        with _db() as con:
            con.execute(
                "INSERT INTO scans (id, source_album, limit_count, skip_count, created_at, summary_json) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (scan_id, album_name, limit, skip, _now(), json.dumps(summary, ensure_ascii=True)),
            )
            con.commit()

        return {**summary, "proposals": proposals, "errors": errors, "write_status": "not_applied"}
    except Exception as exc:
        return {"album_name": album_name, "proposals": [], "error": _compact_error(exc)}


@mcp.tool()
def review_proposals(status: str = "proposed", limit: int = 50) -> dict[str, Any]:
    """Review stored album action proposals from previous curate_batch runs."""
    limit = max(1, min(int(limit), 200))
    with _db() as con:
        rows = con.execute(
            """
            SELECT id, asset_id, source_album, action_json, analysis_json, metadata_json,
                   status, created_at, updated_at
            FROM proposals
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (status, limit),
        ).fetchall()
    proposals = []
    for row in rows:
        proposals.append(
            {
                "proposal_id": row[0],
                "asset_id": row[1],
                "source_album": row[2],
                "action": json.loads(row[3]),
                "analysis": json.loads(row[4]),
                "metadata": json.loads(row[5]),
                "status": row[6],
                "created_at": row[7],
                "updated_at": row[8],
            }
        )
    return {"status": status, "returned": len(proposals), "proposals": proposals}


@mcp.tool()
def mark_proposals_reviewed(proposal_ids: list[str], decision: str = "approved") -> dict[str, Any]:
    """Mark proposals as approved, rejected, or needs_review locally. This does not change iCloud."""
    allowed = {"approved", "rejected", "needs_review", "proposed"}
    if decision not in allowed:
        return {"updated": 0, "error": f"decision must be one of {sorted(allowed)}"}
    with _db() as con:
        count = 0
        for proposal_id in proposal_ids:
            cur = con.execute(
                "UPDATE proposals SET status = ?, updated_at = ? WHERE id = ?",
                (decision, _now(), proposal_id),
            )
            count += cur.rowcount
        con.commit()
    return {"updated": count, "decision": decision, "write_status": "not_applied"}


@mcp.tool()
def write_capabilities() -> dict[str, Any]:
    """Show experimental iCloud write capabilities and required confirmations."""
    return {
        "experimental_writes_enabled": _write_enabled(),
        "supported_operations": [
            "create_album",
            "add_photo_to_album",
            "apply_approved_proposals",
        ],
        "unsupported_operations": [
            "delete_photo",
            "remove_photo_from_album",
            "rename_album",
            "delete_album",
        ],
        "default_mode": "dry_run",
        "required_env": "ICLOUD_PHOTO_CURATOR_ENABLE_EXPERIMENTAL_WRITES=true",
        "required_env_location": "real environment variable; not ~/.icloud-photo-curator/.env",
        "required_confirmation": SAFE_WRITE_CONFIRMATION,
        "required_acknowledgement": WRITE_RISK_ACKNOWLEDGEMENT,
        "warning": (
            "These operations use private iCloud Photos CloudKit record mutations. "
            "Test with disposable albums before applying to a real library."
        ),
    }


@mcp.tool()
def create_album(
    album_name: str,
    dry_run: bool = True,
    confirmation: str = "",
    risk_acknowledgement: str = "",
) -> dict[str, Any]:
    """Create a user album in iCloud Photos. Defaults to dry-run."""
    try:
        api = _require_api()
        if album_name in api.photos.albums:
            return {
                "created": False,
                "dry_run": dry_run,
                "album_name": album_name,
                "reason": "Album already exists.",
                "album_id": _album_id(api, album_name),
            }
        operation = _album_create_operation(album_name)
        plan = {
            "operation": "create_album",
            "album_name": album_name,
            "record_name": operation["record"]["recordName"],
            "record_type": "CPLAlbum",
        }
        guard = _write_guard(confirmation, risk_acknowledgement, dry_run=dry_run)
        if guard:
            return {"created": False, "dry_run": dry_run, "plan": plan, "guard": guard}
        if dry_run:
            return {"created": False, "dry_run": True, "plan": plan}

        result = _modify_records(api, [operation], _album_desired_keys())
        if hasattr(api.photos, "_albums"):
            api.photos._albums = None
        return {
            "created": _modify_succeeded(result),
            "dry_run": False,
            "album_name": album_name,
            "album_id": operation["record"]["recordName"],
            "result": result["response"],
        }
    except Exception as exc:
        return {"created": False, "album_name": album_name, "error": _compact_error(exc)}


@mcp.tool()
def add_photo_to_album(
    album_name: str,
    asset_id: str,
    source_album: str = "All Photos",
    dry_run: bool = True,
    confirmation: str = "",
    risk_acknowledgement: str = "",
) -> dict[str, Any]:
    """Add one photo asset to an existing iCloud Photos user album. Defaults to dry-run."""
    try:
        api = _require_api()
        album_id = _album_id(api, album_name)
        return _add_photo_to_album_id(
            api,
            album_name=album_name,
            album_id=album_id,
            asset_id=asset_id,
            source_album=source_album,
            dry_run=dry_run,
            confirmation=confirmation,
            risk_acknowledgement=risk_acknowledgement,
        )
    except Exception as exc:
        return {
            "added": False,
            "album_name": album_name,
            "asset_id": asset_id,
            "error": _compact_error(exc),
        }


@mcp.tool()
def apply_proposals(
    proposal_ids: list[str],
    dry_run: bool = True,
    confirmation: str = "",
    risk_acknowledgement: str = "",
) -> dict[str, Any]:
    """Apply approved proposals to iCloud albums. Defaults to dry-run."""
    guard = _write_guard(confirmation, risk_acknowledgement, dry_run=dry_run)
    if guard:
        return {"applied": False, "dry_run": dry_run, "proposal_ids": proposal_ids, "guard": guard}

    with _db() as con:
        rows = con.execute(
            """
            SELECT id, asset_id, source_album, action_json, status
            FROM proposals
            WHERE id IN ({})
            """.format(",".join("?" for _ in proposal_ids)),
            proposal_ids,
        ).fetchall() if proposal_ids else []

    plans: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    created_album_ids: dict[str, str] = {}
    try:
        api = _require_api()
    except Exception as exc:
        return {"applied": False, "dry_run": dry_run, "proposal_ids": proposal_ids, "error": _compact_error(exc)}

    for proposal_id, asset_id, source_album, action_json, status in rows:
        action = json.loads(action_json)
        action_type = action.get("type")
        album_name = action.get("album_name")
        if status != "approved":
            results.append(
                {
                    "proposal_id": proposal_id,
                    "applied": False,
                    "reason": f"Proposal status is '{status}', not 'approved'.",
                }
            )
            continue
        if action_type in {"skip", "needs_review"}:
            results.append({"proposal_id": proposal_id, "applied": False, "reason": action_type})
            continue
        if not album_name:
            results.append({"proposal_id": proposal_id, "applied": False, "reason": "Missing album_name."})
            continue

        album_id = created_album_ids.get(album_name)
        if action_type == "create_album":
            if album_id:
                plans.append(
                    {
                        "proposal_id": proposal_id,
                        "step": "create_album",
                        "result": {
                            "created": False,
                            "dry_run": dry_run,
                            "album_name": album_name,
                            "album_id": album_id,
                            "reason": "Album already planned or created in this run.",
                        },
                    }
                )
            else:
                try:
                    album_id = _album_id(api, album_name)
                    plans.append(
                        {
                            "proposal_id": proposal_id,
                            "step": "create_album",
                            "result": {
                                "created": False,
                                "dry_run": dry_run,
                                "album_name": album_name,
                                "album_id": album_id,
                                "reason": "Album already exists.",
                            },
                        }
                    )
                except Exception:
                    created = create_album(
                        album_name,
                        dry_run=dry_run,
                        confirmation=confirmation,
                        risk_acknowledgement=risk_acknowledgement,
                    )
                    plans.append({"proposal_id": proposal_id, "step": "create_album", "result": created})
                    if dry_run:
                        album_id = (created.get("plan") or {}).get("record_name")
                    elif created.get("created") or created.get("album_id"):
                        album_id = created.get("album_id")
                    if not album_id:
                        results.append(
                            {
                                "proposal_id": proposal_id,
                                "applied": False,
                                "dry_run": dry_run,
                                "album_name": album_name,
                                "asset_id": asset_id,
                                "reason": "Album could not be created or planned.",
                            }
                        )
                        continue
                    created_album_ids[album_name] = album_id
        elif action_type == "add_to_existing_album":
            try:
                album_id = album_id or _album_id(api, album_name)
            except Exception as exc:
                results.append(
                    {
                        "proposal_id": proposal_id,
                        "applied": False,
                        "dry_run": dry_run,
                        "album_name": album_name,
                        "asset_id": asset_id,
                        "reason": _compact_error(exc),
                    }
                )
                continue
        else:
            results.append(
                {
                    "proposal_id": proposal_id,
                    "applied": False,
                    "dry_run": dry_run,
                    "reason": f"Unsupported action type '{action_type}'.",
                }
            )
            continue

        try:
            add_result = _add_photo_to_album_id(
                api,
                album_name=album_name,
                album_id=album_id,
                asset_id=asset_id,
                source_album=source_album,
                dry_run=dry_run,
                confirmation=confirmation,
                risk_acknowledgement=risk_acknowledgement,
            )
        except Exception as exc:
            add_result = {
                "added": False,
                "dry_run": dry_run,
                "album_name": album_name,
                "asset_id": asset_id,
                "error": _compact_error(exc),
            }
        plans.append({"proposal_id": proposal_id, "step": "add_photo_to_album", "result": add_result})
        item = {
            "proposal_id": proposal_id,
            "applied": bool(add_result.get("added")),
            "dry_run": dry_run,
            "album_name": album_name,
            "asset_id": asset_id,
        }
        if add_result.get("error"):
            item["error"] = add_result["error"]
        if add_result.get("guard"):
            item["guard"] = add_result["guard"]
        results.append(item)

    apply_targets = [item for item in results if "applied" in item]
    return {
        "applied": (not dry_run) and bool(apply_targets) and all(item.get("applied") for item in apply_targets),
        "dry_run": dry_run,
        "proposal_count": len(rows),
        "plans": plans,
        "results": results,
        "warning": "Experimental iCloud write path. Test with disposable albums first.",
    }


@mcp.tool()
def export_proposals(path: str | None = None, status: str = "proposed") -> dict[str, Any]:
    """Export stored proposals to JSON for manual review or backup."""
    target = Path(path).expanduser() if path else _state_dir() / f"proposals_{status}.json"
    data = review_proposals(status=status, limit=200)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
    return {"path": str(target), "status": status, "count": data.get("returned", 0)}


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        print(json.dumps(setup_check(), indent=2, ensure_ascii=True))
    else:
        mcp.run()
