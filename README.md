# spotify-playlist-dedup

Find duplicate tracks in a Spotify playlist and remove them, keeping one copy.

Spotify gives a different track ID to the same recording when it appears on an
album vs a single. This tool groups by ISRC first, then by normalized
title + artists + duration, so those cases are detected.

## Setup

1. Create an app at https://developer.spotify.com/dashboard
   - Redirect URI: `http://localhost:8888/callback`
2. Copy env file and fill it:

```powershell
Copy-Item .env.example .env
```

Required scopes: `playlist-read-private playlist-modify-private playlist-modify-public`.

3. Install:

```powershell
pip install -r requirements.txt
```

## Usage

Dry-run (default, safe, writes a backup JSON):

```powershell
python -m spotify_dedup --playlist <playlist-id-or-url>
```

Delete duplicates (keeps earliest added):

```powershell
python -m spotify_dedup --playlist <playlist-id-or-url> --apply --yes
```

Options:

- `--tolerance-ms 2500` duration tolerance for fuzzy matching
- `--market ES` optional market code
- `--backup backup.json` custom backup path

Removal uses `uri + positions` in batches of 100, so only duplicate
occurrences are deleted. A full `backup-<id>-<timestamp>.json` is always written.

## How detection works

1. Same ISRC (case-insensitive) -> same group.
2. Else same normalized title + sorted artists + duration within tolerance.
3. Keeper is the earliest `added_at` / lowest position.

## Tests

```powershell
python -m pytest -q
```
