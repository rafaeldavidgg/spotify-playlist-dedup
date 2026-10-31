"""Spotify API helpers (network boundary, kept thin)."""
from __future__ import annotations

import os

SCOPE = "playlist-read-private playlist-modify-private playlist-modify-public"


def parse_playlist_id(playlist: str) -> str:
    """Accept a raw ID, URL or URI and return the ID."""
    s = (playlist or "").strip()
    if "open.spotify.com/playlist/" in s:
        s = s.split("open.spotify.com/playlist/")[1].split("?")[0].split("/")[0]
    if s.startswith("spotify:playlist:"):
        s = s.split(":")[-1]
    return s


def get_spotify_client():
    """Create an authenticated Spotipy client from env vars."""
    from dotenv import load_dotenv

    load_dotenv()
    client_id = os.getenv("SPOTIFY_CLIENT_ID", "")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET. "
            "Copy .env.example to .env first."
        )
    from spotipy import Spotify
    from spotipy.oauth2 import SpotifyOAuth

    auth = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=SCOPE,
        open_browser=True,
    )
    return Spotify(auth_manager=auth)


def fetch_all_playlist_tracks(sp, playlist_id: str, market: str | None = None) -> list[dict]:
    """Fetch every track in a playlist, handling pagination (limit 50)."""
    tracks: list[dict] = []
    limit, offset = 50, 0
    position = 0
    while True:
        page = sp.playlist_items(
            playlist_id,
            limit=limit,
            offset=offset,
            additional_types=("track",),
            market=market,
        )
        items = page.get("items", []) if isinstance(page, dict) else []
        if not items:
            break
        for item in items:
            tr = (item or {}).get("track") or {}
            if tr.get("type") not in (None, "track"):
                position += 1
                continue
            if not tr.get("id"):
                # Local file or unavailable: keep placeholder so positions stay right.
                tracks.append(
                    {
                        "position": position,
                        "id": "",
                        "uri": tr.get("uri", ""),
                        "name": tr.get("name", ""),
                        "artists": [],
                        "duration_ms": tr.get("duration_ms", 0),
                        "isrc": "",
                        "album": "",
                        "added_at": (item or {}).get("added_at", ""),
                        "unplayable": True,
                    }
                )
                position += 1
                continue
            artists = [a.get("name", "") for a in tr.get("artists", [])]
            tracks.append(
                {
                    "position": position,
                    "id": tr.get("id", ""),
                    "uri": tr.get("uri", ""),
                    "name": tr.get("name", ""),
                    "artists": artists,
                    "duration_ms": tr.get("duration_ms", 0),
                    "isrc": (tr.get("external_ids") or {}).get("isrc", ""),
                    "album": (tr.get("album") or {}).get("name", ""),
                    "added_at": (item or {}).get("added_at", ""),
                }
            )
            position += 1
        if page.get("next") is None:
            break
        offset += limit
    return tracks


def build_removal_plan(groups: list[dict]) -> list[dict]:
    """Build Spotify removal payload using specific positions.

    Using uri+positions removes only the duplicate occurrences,
    keeping the first one. Without positions Spotify would delete all.
    """
    plan: list[dict] = []
    for group in groups:
        by_uri: dict[str, list[int]] = {}
        for dup in group["duplicates"]:
            by_uri.setdefault(dup["uri"], []).append(dup["position"])
        for uri, positions in by_uri.items():
            plan.append({"uri": uri, "positions": sorted(positions)})
    return plan


def remove_with_plan(sp, playlist_id: str, plan: list[dict], batch: int = 100) -> int:
    """Execute removal in batches of <=100. Returns removed count."""
    removed = 0
    for i in range(0, len(plan), batch):
        chunk = plan[i : i + batch]
        sp.playlist_remove_specific_occurrences_of_items(playlist_id, chunk)
        removed += sum(len(c["positions"]) for c in chunk)
    return removed
