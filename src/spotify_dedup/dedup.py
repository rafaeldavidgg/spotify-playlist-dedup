"""Pure duplicate detection logic (no network).

Grouping strategy (in order):
1. Same Spotify track ID -> same group (covered by fuzzy too).
2. Same ISRC (case-insensitive) -> same recording even if IDs differ
   (album vs single case from the request).
3. Fuzzy fallback: normalized title + sorted artists + duration tolerance.
"""
from __future__ import annotations

import re
import unicodedata


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def normalize_title(title: str) -> str:
    """Normalize a track title for fuzzy comparison."""
    s = (title or "").lower().strip()
    s = _strip_accents(s)
    # Drop "feat/ft/featuring ..." tails.
    s = re.sub(r"\s*(feat\.?|ft\.?|featuring)\s+.+$", "", s)
    # Drop trailing " - live/remaster/acoustic/..." markers.
    s = re.sub(
        r"\s*-\s*(live|remaster.*|acoustic|version|edit|radio.*|single.*|deluxe.*)$",
        "",
        s,
    )
    # Drop any parenthetical/bracket content like "(Remastered 2015)".
    s = re.sub(r"\s*[\(\[].*?[\)\]]", "", s)
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_artists(artists: list[str]) -> list[str]:
    """Lowercase, accent-strip and sort artist names."""
    cleaned = [_strip_accents((a or "").lower().strip()) for a in (artists or [])]
    cleaned = [re.sub(r"\s+", " ", a).strip() for a in cleaned if a]
    return sorted(cleaned)


def _sort_key(track: dict):
    return (track.get("added_at") or "", track.get("position", 0))


def find_duplicate_groups(
    tracks: list[dict], duration_tolerance_ms: int = 2500
) -> list[dict]:
    """Group tracks that are the same recording.

    Each track dict needs: position, id, uri, name, artists,
    duration_ms, isrc (optional), added_at (optional).
    Returns [{"key":..., "keeper": track, "duplicates": [track, ...]}]
    keeping the earliest added_at/position.
    """
    groups: list[dict] = []

    for track in tracks:
        norm_t = normalize_title(track.get("name", ""))
        norm_a = tuple(normalize_artists(track.get("artists", [])))
        isrc = (track.get("isrc") or "").strip().upper() or None
        try:
            duration = int(track.get("duration_ms") or 0)
        except (TypeError, ValueError):
            duration = 0

        matched = None
        for group in groups:
            # 1) Same ISRC wins, even with different IDs.
            if isrc and group["isrc"] and isrc == group["isrc"]:
                matched = group
                break
            # 2) Fuzzy: same normalized title + artists + duration close.
            if (
                norm_t
                and norm_t == group["norm_title"]
                and norm_a == group["norm_artists"]
            ):
                if any(
                    abs(duration - d) <= duration_tolerance_ms
                    for d in group["durations"]
                ):
                    matched = group
                    break

        if matched is None:
            groups.append(
                {
                    "isrc": isrc,
                    "norm_title": norm_t,
                    "norm_artists": norm_a,
                    "durations": [duration],
                    "members": [track],
                }
            )
        else:
            matched["members"].append(track)
            matched["durations"].append(duration)
            # If this member brings an ISRC, adopt it for future matches.
            if isrc and not matched["isrc"]:
                matched["isrc"] = isrc

    result = []
    for group in groups:
        if len(group["members"]) < 2:
            continue
        ordered = sorted(group["members"], key=_sort_key)
        keeper, duplicates = ordered[0], sorted(ordered[1:], key=lambda t: t.get("position", 0))
        result.append(
            {
                "key": group["isrc"] or f"{group['norm_title']}::{'+'.join(group['norm_artists'])}",
                "keeper": keeper,
                "duplicates": duplicates,
            }
        )

    result.sort(key=lambda g: g["keeper"].get("position", 0))
    return result
