"""Tests for pure duplicate detection (no network)."""
from spotify_dedup.dedup import normalize_title, normalize_artists, find_duplicate_groups


def make_track(pos, tid, name, artists, duration_ms, isrc=None, added_at=None):
    return {
        "position": pos,
        "id": tid,
        "uri": f"spotify:track:{tid}",
        "name": name,
        "artists": artists,
        "duration_ms": duration_ms,
        "isrc": isrc,
        "added_at": added_at or f"2024-01-01T00:00:{pos:02d}Z",
    }


def test_normalize_strips_remaster_live_feat():
    assert normalize_title("Yellow (Remastered 2015)") == "yellow"
    assert normalize_title("Yellow - Live") == "yellow"
    assert normalize_title("Yellow feat. Beyonce") == "yellow"
    assert normalize_title("  HÉROES  ") == "heroes"


def test_normalize_artists_sorted_lower():
    assert normalize_artists(["Coldplay", "BTS"]) == ["bts", "coldplay"]


def test_exact_id_duplicates_grouped():
    tracks = [
        make_track(0, "abc", "Yellow", ["Coldplay"], 266000),
        make_track(5, "abc", "Yellow", ["Coldplay"], 266000),
    ]
    groups = find_duplicate_groups(tracks)
    assert len(groups) == 1
    assert groups[0]["keeper"]["position"] == 0
    assert [d["position"] for d in groups[0]["duplicates"]] == [5]


def test_same_song_album_vs_single_via_isrc():
    # Same recording, different Spotify IDs (album vs single)
    tracks = [
        make_track(0, "id_album", "Yellow", ["Coldplay"], 266000, isrc="GBAYE0000123"),
        make_track(3, "id_single", "Yellow", ["Coldplay"], 266200, isrc="gbaye0000123"),
    ]
    groups = find_duplicate_groups(tracks)
    assert len(groups) == 1
    assert groups[0]["keeper"]["position"] == 0


def test_fuzzy_title_artists_duration_without_isrc():
    tracks = [
        make_track(0, "id1", "Yellow", ["Coldplay"], 266000),
        make_track(2, "id2", "yellow (Remastered)", ["coldplay"], 267500),
    ]
    groups = find_duplicate_groups(tracks, duration_tolerance_ms=2500)
    assert len(groups) == 1


def test_different_songs_not_grouped():
    tracks = [
        make_track(0, "id1", "Yellow", ["Coldplay"], 266000),
        make_track(1, "id2", "Viva La Vida", ["Coldplay"], 242000),
    ]
    assert find_duplicate_groups(tracks) == []


def test_keeps_earliest_added():
    tracks = [
        make_track(4, "x", "Song", ["A"], 200000, added_at="2024-02-01T00:00:00Z"),
        make_track(1, "y", "Song", ["A"], 200100, added_at="2024-01-01T00:00:00Z"),
    ]
    groups = find_duplicate_groups(tracks)
    assert groups[0]["keeper"]["position"] == 1


def test_tolerance_boundary_exact_vs_over():
    base0 = make_track(0, "i0", "Yellow", ["Coldplay"], 266000)
    base1 = make_track(1, "i1", "Yellow", ["Coldplay"], 268500)
    assert len(find_duplicate_groups([base0, base1], duration_tolerance_ms=2500)) == 1
    over = make_track(1, "i1", "Yellow", ["Coldplay"], 268501)
    assert find_duplicate_groups([base0, over], duration_tolerance_ms=2500) == []


def test_live_variant_groups_and_diff_artist_does_not():
    tracks = [
        make_track(0, "x0", "Yellow", ["Coldplay"], 266000),
        make_track(1, "x1", "Yellow - Live", ["Coldplay"], 266000),
    ]
    assert len(find_duplicate_groups(tracks)) == 1
    other = [
        make_track(0, "x0", "Yellow", ["Coldplay"], 266000),
        make_track(1, "x1", "Yellow", ["BTS"], 266000),
    ]
    assert find_duplicate_groups(other) == []
