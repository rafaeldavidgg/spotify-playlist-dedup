"""Tests for Spotify removal planning (no network, fake client)."""
from spotify_dedup.dedup import find_duplicate_groups
from spotify_dedup.spotify import (
    build_removal_plan,
    parse_playlist_id,
    remove_with_plan,
)


def _mk(pos, tid="abc"):
    return {
        "position": pos,
        "id": tid,
        "uri": f"spotify:track:{tid}",
        "name": "Yellow",
        "artists": ["Coldplay"],
        "duration_ms": 266000,
        "isrc": None,
        "added_at": f"2024-01-01T00:00:{pos:02d}Z",
    }


def test_removal_plan_keeps_keeper_uses_sorted_positions():
    groups = find_duplicate_groups([_mk(0), _mk(7), _mk(5)])
    assert groups[0]["keeper"]["position"] == 0
    assert build_removal_plan(groups) == [
        {"uri": "spotify:track:abc", "positions": [5, 7]}
    ]


def test_parse_playlist_id_variants():
    assert (
        parse_playlist_id("https://open.spotify.com/playlist/abc123?si=x")
        == "abc123"
    )
    assert parse_playlist_id("spotify:playlist:abc123") == "abc123"
    assert parse_playlist_id("abc123") == "abc123"


def test_remove_with_plan_batches_100():
    class Fake:
        def __init__(self):
            self.calls = []

        def playlist_remove_specific_occurrences_of_items(self, pid, chunk):
            self.calls.append(list(chunk))

    fake = Fake()
    plan = [{"uri": f"u{i}", "positions": [i]} for i in range(250)]
    assert remove_with_plan(fake, "pid", plan) == 250
    assert [len(c) for c in fake.calls] == [100, 100, 50]
