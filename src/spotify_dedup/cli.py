"""CLI: list duplicates (default) or delete with --apply."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from .dedup import find_duplicate_groups
from .spotify import (
    build_removal_plan,
    fetch_all_playlist_tracks,
    get_spotify_client,
    parse_playlist_id,
    remove_with_plan,
)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Find and remove duplicate tracks in a Spotify playlist."
    )
    p.add_argument("--playlist", required=True, help="Playlist ID, URL or URI")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete duplicates. Without it, only dry-run.",
    )
    p.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompt when using --apply.",
    )
    p.add_argument(
        "--tolerance-ms",
        type=int,
        default=2500,
        help="Duration tolerance for fuzzy matching (default 2500).",
    )
    p.add_argument(
        "--market",
        default="from_token",
        help="Market code, e.g. ES, or from_token (default) to use your account country.",
    )
    p.add_argument(
        "--backup",
        default="",
        help="Backup JSON path. Defaults to backup-<id>-<ts>.json.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    playlist_id = parse_playlist_id(args.playlist)

    sp = get_spotify_client()
    print(f"Fetching playlist {playlist_id} ...")
    tracks = fetch_all_playlist_tracks(sp, playlist_id, market=args.market)
    print(f"Total tracks: {len(tracks)}")
    unplayable = sum(1 for t in tracks if t.get("unplayable"))
    if unplayable:
        print(
            f"Warning: {unplayable}/{len(tracks)} tracks came back empty "
            f"(market={args.market}). If everything is empty, retry with "
            f"--market ES (or your country) or --market from_token."
        )

    groups = find_duplicate_groups(tracks, duration_tolerance_ms=args.tolerance_ms)
    dup_count = sum(len(g["duplicates"]) for g in groups)
    print(f"Duplicate groups: {len(groups)} / tracks to remove: {dup_count}")

    for group in groups:
        keeper = group["keeper"]
        keep_label = f"{keeper['name']} — {', '.join(keeper['artists'])}"
        print(f"\nKEEP #{keeper['position']}: {keep_label}")
        for dup in group["duplicates"]:
            dup_label = f"{dup['name']} — {', '.join(dup['artists'])} [{dup.get('album','')}]"
            print(f"  DUP  #{dup['position']}: {dup_label} isrc={dup.get('isrc','')}")

    backup_path = args.backup or (
        f"backup-{playlist_id}-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
    )
    with open(backup_path, "w", encoding="utf-8") as fh:
        json.dump({"playlist_id": playlist_id, "tracks": tracks}, fh, ensure_ascii=False, indent=2)
    print(f"\nBackup saved to {backup_path}")

    if not groups:
        print("No duplicates found. Nothing to do.")
        return 0

    if not args.apply:
        print("\nDry-run only. Re-run with --apply --yes to delete.")
        return 0

    plan = build_removal_plan(groups)
    if not args.yes:
        answer = input(f"Delete {dup_count} duplicates? Type DELETE to confirm: ")
        if answer.strip() != "DELETE":
            print("Aborted.")
            return 1

    removed = remove_with_plan(sp, playlist_id, plan)
    print(f"Removed {removed} duplicate occurrences. Keeper copies were kept.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
