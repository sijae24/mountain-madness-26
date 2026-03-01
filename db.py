import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "moodwave.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _track_key(name, artist):
    return f"{(name or '').strip().lower()}::{(artist or '').strip().lower()}"


def normalize_track(track):
    return {
        "name": (track or {}).get("name", "").strip(),
        "artist": (track or {}).get("artist", "").strip(),
        "preview_url": (track or {}).get("preview_url"),
        "album_cover": (track or {}).get("album_cover"),
        "lastfm_url": (track or {}).get("lastfm_url") or (track or {}).get("spotify_url"),
        "spotify_url": (track or {}).get("spotify_url") or (track or {}).get("lastfm_url"),
    }


def _serialize_track_row(row):
    return {
        "name": row["name"],
        "artist": row["artist"],
        "preview_url": row["preview_url"],
        "album_cover": row["album_cover"],
        "lastfm_url": row["lastfm_url"],
        "spotify_url": row["spotify_url"],
    }


def _upsert_track(conn, track):
    normalized = normalize_track(track)
    if not normalized["name"] or not normalized["artist"]:
        raise ValueError("Track must include both name and artist.")
    key = _track_key(normalized["name"], normalized["artist"])
    conn.execute(
        """
        INSERT INTO tracks (
            track_key, name, artist, preview_url, album_cover, lastfm_url, spotify_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(track_key) DO UPDATE SET
            preview_url = excluded.preview_url,
            album_cover = excluded.album_cover,
            lastfm_url = excluded.lastfm_url,
            spotify_url = excluded.spotify_url,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            key,
            normalized["name"],
            normalized["artist"],
            normalized["preview_url"],
            normalized["album_cover"],
            normalized["lastfm_url"],
            normalized["spotify_url"],
        ),
    )
    return key


def init_db():
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS tracks (
                track_key TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                artist TEXT NOT NULL,
                preview_url TEXT,
                album_cover TEXT,
                lastfm_url TEXT,
                spotify_url TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS liked_songs (
                track_key TEXT PRIMARY KEY,
                liked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(track_key) REFERENCES tracks(track_key) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS recent_plays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_key TEXT NOT NULL,
                played_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(track_key) REFERENCES tracks(track_key) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS playlist_tracks (
                playlist_id INTEGER NOT NULL,
                track_key TEXT NOT NULL,
                added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (playlist_id, track_key),
                FOREIGN KEY(playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
                FOREIGN KEY(track_key) REFERENCES tracks(track_key) ON DELETE CASCADE
            );
            """
        )


def cache_tracks(tracks):
    with _connect() as conn:
        for track in tracks or []:
            try:
                _upsert_track(conn, track)
            except ValueError:
                continue


def get_liked_tracks():
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT t.*
            FROM liked_songs ls
            JOIN tracks t ON t.track_key = ls.track_key
            ORDER BY ls.liked_at DESC
            """
        ).fetchall()
        return [_serialize_track_row(row) for row in rows]


def toggle_like(track):
    with _connect() as conn:
        key = _upsert_track(conn, track)
        exists = conn.execute(
            "SELECT 1 FROM liked_songs WHERE track_key = ?", (key,)
        ).fetchone()
        if exists:
            conn.execute("DELETE FROM liked_songs WHERE track_key = ?", (key,))
            return False
        conn.execute("INSERT INTO liked_songs (track_key) VALUES (?)", (key,))
        return True


def add_recent_play(track, max_entries=25):
    with _connect() as conn:
        key = _upsert_track(conn, track)
        conn.execute("INSERT INTO recent_plays (track_key) VALUES (?)", (key,))
        conn.execute(
            """
            DELETE FROM recent_plays
            WHERE track_key = ?
              AND id NOT IN (
                SELECT id
                FROM recent_plays
                WHERE track_key = ?
                ORDER BY played_at DESC, id DESC
                LIMIT 1
              )
            """,
            (key, key),
        )
        conn.execute(
            """
            DELETE FROM recent_plays
            WHERE id NOT IN (
              SELECT id
              FROM recent_plays
              ORDER BY played_at DESC, id DESC
              LIMIT ?
            )
            """,
            (max_entries,),
        )


def get_recent_tracks(limit=10):
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT t.*
            FROM recent_plays rp
            JOIN tracks t ON t.track_key = rp.track_key
            ORDER BY rp.played_at DESC, rp.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [_serialize_track_row(row) for row in rows]


def clear_recent_tracks():
    with _connect() as conn:
        conn.execute("DELETE FROM recent_plays")


def list_playlists():
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT p.id, p.name, p.created_at, COUNT(pt.track_key) AS track_count
            FROM playlists p
            LEFT JOIN playlist_tracks pt ON pt.playlist_id = p.id
            GROUP BY p.id
            ORDER BY p.created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def create_playlist(name):
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Playlist name cannot be empty.")

    with _connect() as conn:
        existing = conn.execute(
            "SELECT id, name FROM playlists WHERE lower(name) = lower(?)",
            (clean_name,),
        ).fetchone()
        if existing:
            return {"id": existing["id"], "name": existing["name"], "created": False}

        cursor = conn.execute("INSERT INTO playlists (name) VALUES (?)", (clean_name,))
        return {"id": cursor.lastrowid, "name": clean_name, "created": True}


def get_playlist_tracks(playlist_id):
    with _connect() as conn:
        playlist = conn.execute(
            "SELECT id, name FROM playlists WHERE id = ?", (playlist_id,)
        ).fetchone()
        if not playlist:
            return None

        rows = conn.execute(
            """
            SELECT t.*
            FROM playlist_tracks pt
            JOIN tracks t ON t.track_key = pt.track_key
            WHERE pt.playlist_id = ?
            ORDER BY pt.added_at DESC
            """,
            (playlist_id,),
        ).fetchall()
        return {
            "id": playlist["id"],
            "name": playlist["name"],
            "tracks": [_serialize_track_row(row) for row in rows],
        }


def add_track_to_playlist(playlist_id, track):
    with _connect() as conn:
        key = _upsert_track(conn, track)
        exists = conn.execute(
            "SELECT id FROM playlists WHERE id = ?", (playlist_id,)
        ).fetchone()
        if not exists:
            raise ValueError("Playlist not found.")

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO playlist_tracks (playlist_id, track_key)
            VALUES (?, ?)
            """,
            (playlist_id, key),
        )
        return cursor.rowcount > 0


def delete_playlist(playlist_id):
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        return cursor.rowcount > 0
