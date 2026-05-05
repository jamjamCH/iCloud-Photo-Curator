from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import icloud_photo_curator_mcp as curator  # noqa: E402

ENV_KEYS = {
    "ICLOUD_PHOTO_CURATOR_APPLE_ID",
    "ICLOUD_PHOTO_CURATOR_REGION",
    "ICLOUD_PHOTO_CURATOR_STATE_DIR",
}
DEFAULT_CONFIG_DIR = Path.home() / ".icloud-photo-curator"
DEFAULT_ENV_PATH = DEFAULT_CONFIG_DIR / ".env"


def _print(data: Any) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _read_env_file(path: Path = DEFAULT_ENV_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if key in ENV_KEYS:
            values[key] = value
    return values


def _quote_env_value(value: str) -> str:
    escaped = value.replace('"', '\\"')
    return f'"{escaped}"'


def _write_env_file(values: dict[str, str], path: Path = DEFAULT_ENV_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_values = {key: value for key, value in values.items() if key in ENV_KEYS and value}
    lines = [
        "# iCloud Photo Curator local config",
        "# Do not store passwords in this file. Passwords belong in Windows Keyring.",
    ]
    for key in [
        "ICLOUD_PHOTO_CURATOR_APPLE_ID",
        "ICLOUD_PHOTO_CURATOR_REGION",
        "ICLOUD_PHOTO_CURATOR_STATE_DIR",
    ]:
        if key in safe_values:
            lines.append(f"{key}={_quote_env_value(safe_values[key])}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _config_value(key: str, default: str | None = None) -> str | None:
    return os.getenv(key) or _read_env_file().get(key) or default


def _connect(args: argparse.Namespace) -> dict[str, Any]:
    username = args.username or _config_value("ICLOUD_PHOTO_CURATOR_APPLE_ID")
    password = os.getenv("ICLOUD_PHOTO_CURATOR_PASSWORD")
    region = args.region or _config_value("ICLOUD_PHOTO_CURATOR_REGION", "global")

    if not username:
        username = input("Apple ID email: ").strip()
    if not username:
        _print({"logged_in": False, "error": "Apple ID is required."})
        return
    if args.ask_password and not password:
        password = getpass.getpass("iCloud password: ")

    result = curator.connect_icloud(username=username, password=password, region=region)
    if result.get("auth", {}).get("requires_2fa") and args.two_factor_code:
        result["two_factor"] = curator.validate_2fa_code(args.two_factor_code)
    return result


def _print_2fa_next_step(connection: dict[str, Any]) -> None:
    _print({**connection, "next_step": "Run login or retry with --two-factor-code 123456."})


def cmd_setup(args: argparse.Namespace) -> None:
    _print(curator.setup_check())


def cmd_login(args: argparse.Namespace) -> None:
    from icloudpy.utils import store_password_in_keyring

    current = _read_env_file()
    username = args.username or os.getenv("ICLOUD_PHOTO_CURATOR_APPLE_ID") or current.get(
        "ICLOUD_PHOTO_CURATOR_APPLE_ID"
    )
    if not username:
        username = input("Apple ID email: ").strip()

    region = args.region or os.getenv("ICLOUD_PHOTO_CURATOR_REGION") or current.get(
        "ICLOUD_PHOTO_CURATOR_REGION"
    )
    if not region:
        typed_region = input("Region [global/china] (default global): ").strip().lower()
        region = typed_region or "global"
    if region not in {"global", "china"}:
        _print({"logged_in": False, "error": "Region must be 'global' or 'china'."})
        return

    state_dir = (
        args.state_dir
        or os.getenv("ICLOUD_PHOTO_CURATOR_STATE_DIR")
        or current.get("ICLOUD_PHOTO_CURATOR_STATE_DIR")
        or str(DEFAULT_CONFIG_DIR)
    )

    _write_env_file(
        {
            "ICLOUD_PHOTO_CURATOR_APPLE_ID": username,
            "ICLOUD_PHOTO_CURATOR_REGION": region,
            "ICLOUD_PHOTO_CURATOR_STATE_DIR": state_dir,
        }
    )
    curator._reload_local_env()

    password = getpass.getpass("iCloud password (stored in Windows Keyring, not .env): ")
    if not password:
        _print({"logged_in": False, "error": "Password is required and was not stored."})
        return
    store_password_in_keyring(username, password)

    result = curator.connect_icloud(username=username, password=password, region=region)
    two_factor = None
    if result.get("auth", {}).get("requires_2fa"):
        code = args.two_factor_code or input("Apple 2FA code: ").strip()
        two_factor = curator.validate_2fa_code(code)

    setup = curator.setup_check()
    _print(
        {
            "logged_in": bool(result.get("connected")),
            "auth": (two_factor or result).get("auth", result.get("auth")),
            "two_factor_validated": None if two_factor is None else bool(two_factor.get("validated")),
            "env_path": setup.get("env_path"),
            "env_exists": setup.get("env_exists"),
            "apple_id_configured": setup.get("apple_id_configured"),
            "region": setup.get("region"),
            "session_dir": setup.get("session_dir"),
            "keyring_password_available": setup.get("keyring_password_available"),
            "password_saved_to_env": False,
        }
    )


def cmd_connect(args: argparse.Namespace) -> None:
    _print(_connect(args))


def cmd_albums(args: argparse.Namespace) -> None:
    connection = _connect(args)
    if not connection.get("connected"):
        _print(connection)
        return
    if connection.get("auth", {}).get("requires_2fa") and not args.two_factor_code:
        _print_2fa_next_step(connection)
        return
    _print(curator.list_albums(include_counts=args.counts, max_albums=args.max_albums))


def cmd_scan(args: argparse.Namespace) -> None:
    connection = _connect(args)
    if not connection.get("connected"):
        _print(connection)
        return
    if connection.get("auth", {}).get("requires_2fa") and not args.two_factor_code:
        _print_2fa_next_step(connection)
        return
    _print(
        curator.scan_album(
            album_name=args.album,
            limit=args.limit,
            skip=args.skip,
            include_versions=args.include_versions,
        )
    )


def cmd_curate(args: argparse.Namespace) -> None:
    connection = _connect(args)
    if not connection.get("connected"):
        _print(connection)
        return
    if connection.get("auth", {}).get("requires_2fa") and not args.two_factor_code:
        _print_2fa_next_step(connection)
        return
    _print(
        curator.curate_batch(
            album_name=args.album,
            limit=args.limit,
            skip=args.skip,
            version=args.version,
            existing_albums_limit=args.existing_albums_limit,
        )
    )


def cmd_prepare(args: argparse.Namespace) -> None:
    connection = _connect(args)
    if not connection.get("connected"):
        _print(connection)
        return
    if connection.get("auth", {}).get("requires_2fa") and not args.two_factor_code:
        _print_2fa_next_step(connection)
        return
    _print(
        curator.prepare_batch_for_codex(
            album_name=args.album,
            limit=args.limit,
            skip=args.skip,
            version=args.version,
            existing_albums_limit=args.existing_albums_limit,
        )
    )


def cmd_review(args: argparse.Namespace) -> None:
    _print(curator.review_proposals(status=args.status, limit=args.limit))


def cmd_rules(args: argparse.Namespace) -> None:
    if args.set_file:
        rules = Path(args.set_file).expanduser().read_text(encoding="utf-8")
        _print(curator.save_curation_rules(rules, append=args.append))
        return
    if args.add:
        _print(curator.save_curation_rules(args.add, append=True))
        return
    _print(curator.get_curation_rules())


def cmd_write_capabilities(args: argparse.Namespace) -> None:
    _print(curator.write_capabilities())


def _ensure_connected_for_command(args: argparse.Namespace) -> bool:
    connection = _connect(args)
    if not connection.get("connected"):
        _print(connection)
        return False
    if connection.get("auth", {}).get("requires_2fa") and not args.two_factor_code:
        _print_2fa_next_step(connection)
        return False
    return True


def cmd_create_album(args: argparse.Namespace) -> None:
    if not _ensure_connected_for_command(args):
        return
    _print(
        curator.create_album(
            album_name=args.album,
            dry_run=not args.execute,
            confirmation=args.confirmation,
            risk_acknowledgement=args.risk_acknowledgement,
        )
    )


def cmd_add_photo(args: argparse.Namespace) -> None:
    if not _ensure_connected_for_command(args):
        return
    _print(
        curator.add_photo_to_album(
            album_name=args.album,
            asset_id=args.asset_id,
            source_album=args.source_album,
            dry_run=not args.execute,
            confirmation=args.confirmation,
            risk_acknowledgement=args.risk_acknowledgement,
        )
    )


def cmd_apply_proposals(args: argparse.Namespace) -> None:
    if not _ensure_connected_for_command(args):
        return
    _print(
        curator.apply_proposals(
            proposal_ids=args.proposal_ids,
            dry_run=not args.execute,
            confirmation=args.confirmation,
            risk_acknowledgement=args.risk_acknowledgement,
        )
    )


def add_auth_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--username", help="Apple ID email. Prefer env var ICLOUD_PHOTO_CURATOR_APPLE_ID.")
    parser.add_argument("--ask-password", action="store_true", help="Prompt for password if ICLOUD_PHOTO_CURATOR_PASSWORD is not set.")
    parser.add_argument("--two-factor-code", help="Apple 2FA code shown on your trusted device.")
    parser.add_argument("--region", choices=["global", "china"])


def add_write_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--execute", action="store_true", help="Apply live iCloud album changes. Default is dry-run.")
    parser.add_argument("--confirmation", default="", help="Required exact confirmation phrase for --execute.")
    parser.add_argument("--risk-acknowledgement", default="", help="Required exact risk acknowledgement phrase for --execute.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Try the iCloud Photo Curator without an MCP client.")
    sub = parser.add_subparsers(required=True)

    setup = sub.add_parser("setup", help="Run local dependency/config self-check.")
    setup.set_defaults(func=cmd_setup)

    login = sub.add_parser("login", help="Configure .env, store password in Windows Keyring, and trust the session.")
    add_auth_args(login)
    login.add_argument("--state-dir", help="State/cache/session directory. Defaults to ~/.icloud-photo-curator.")
    login.set_defaults(func=cmd_login)

    connect = sub.add_parser("connect", help="Test iCloud login and 2FA state.")
    add_auth_args(connect)
    connect.set_defaults(func=cmd_connect)

    albums = sub.add_parser("albums", help="List existing iCloud Photos albums.")
    add_auth_args(albums)
    albums.add_argument("--counts", action="store_true", help="Also ask iCloud for album counts.")
    albums.add_argument("--max-albums", type=int, default=100)
    albums.set_defaults(func=cmd_albums)

    scan = sub.add_parser("scan", help="Scan metadata from a small album batch.")
    add_auth_args(scan)
    scan.add_argument("--album", default="All Photos")
    scan.add_argument("--limit", type=int, default=5)
    scan.add_argument("--skip", type=int, default=0)
    scan.add_argument("--include-versions", action="store_true")
    scan.set_defaults(func=cmd_scan)

    prepare = sub.add_parser("prepare", help="Cache a small batch for Codex-native image review.")
    add_auth_args(prepare)
    prepare.add_argument("--album", default="All Photos")
    prepare.add_argument("--limit", type=int, default=3)
    prepare.add_argument("--skip", type=int, default=0)
    prepare.add_argument("--version", default="thumb", choices=["thumb", "medium", "full", "large"])
    prepare.add_argument("--existing-albums-limit", type=int, default=200)
    prepare.set_defaults(func=cmd_prepare)

    curate = sub.add_parser("curate", help="Legacy metadata-only batch proposal helper.")
    add_auth_args(curate)
    curate.add_argument("--album", default="All Photos")
    curate.add_argument("--limit", type=int, default=3)
    curate.add_argument("--skip", type=int, default=0)
    curate.add_argument("--version", default="thumb", choices=["thumb", "medium", "full", "large"])
    curate.add_argument("--existing-albums-limit", type=int, default=200)
    curate.set_defaults(func=cmd_curate)

    review = sub.add_parser("review", help="Review locally saved proposals.")
    review.add_argument("--status", default="proposed")
    review.add_argument("--limit", type=int, default=20)
    review.set_defaults(func=cmd_review)

    rules = sub.add_parser("rules", help="Show or update local curation rules.")
    rules.add_argument("--set-file", help="Replace rules with markdown from this file.")
    rules.add_argument("--add", help="Append one rule or markdown snippet.")
    rules.add_argument("--append", action="store_true", help="Append --set-file content instead of replacing.")
    rules.set_defaults(func=cmd_rules)

    writes = sub.add_parser("write-capabilities", help="Show experimental write support and required safeguards.")
    writes.set_defaults(func=cmd_write_capabilities)

    create_album = sub.add_parser("create-album", help="Dry-run or create one iCloud Photos album.")
    add_auth_args(create_album)
    add_write_args(create_album)
    create_album.add_argument("--album", required=True, help="Album name to create.")
    create_album.set_defaults(func=cmd_create_album)

    add_photo = sub.add_parser("add-photo", help="Dry-run or add one photo to an existing album.")
    add_auth_args(add_photo)
    add_write_args(add_photo)
    add_photo.add_argument("--album", required=True, help="Destination album name.")
    add_photo.add_argument("--asset-id", required=True, help="Asset ID from scan/prepare output.")
    add_photo.add_argument("--source-album", default="All Photos", help="Album used to locate the source asset.")
    add_photo.set_defaults(func=cmd_add_photo)

    apply = sub.add_parser("apply-proposals", help="Dry-run or apply approved local proposals.")
    add_auth_args(apply)
    add_write_args(apply)
    apply.add_argument("proposal_ids", nargs="+", help="Approved proposal IDs to apply.")
    apply.set_defaults(func=cmd_apply_proposals)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
