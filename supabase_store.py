import os
from collections import Counter

import requests


SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY") or ""


def is_configured():
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def public_config():
    return {
        "enabled": is_configured() and bool(SUPABASE_ANON_KEY),
        "url": SUPABASE_URL if is_configured() else "",
        "anon_key": SUPABASE_ANON_KEY if SUPABASE_ANON_KEY else "",
    }


def _rest_headers(prefer=None):
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _rest_request(method, path, params=None, payload=None, prefer=None):
    if not is_configured():
        raise RuntimeError("Supabase is not configured.")

    response = requests.request(
        method=method,
        url=f"{SUPABASE_URL}/rest/v1/{path}",
        params=params or {},
        json=payload,
        headers=_rest_headers(prefer=prefer),
        timeout=20,
    )

    if response.status_code >= 400:
        text = response.text.strip() or f"Supabase REST error ({response.status_code})."
        raise RuntimeError(text)

    if not response.text:
        return []
    try:
        return response.json()
    except ValueError:
        return []


def resolve_user_from_access_token(access_token):
    token = (access_token or "").strip()
    if not token or not is_configured():
        return None

    api_key = SUPABASE_ANON_KEY or SUPABASE_SERVICE_ROLE_KEY
    response = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "apikey": api_key,
            "Authorization": f"Bearer {token}",
        },
        timeout=20,
    )
    if response.status_code >= 400:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    user_id = payload.get("id")
    if not user_id:
        return None
    return {"id": user_id, "email": payload.get("email")}


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
        "name": row.get("name"),
        "artist": row.get("artist"),
        "preview_url": row.get("preview_url"),
        "album_cover": row.get("album_cover"),
        "lastfm_url": row.get("lastfm_url"),
        "spotify_url": row.get("spotify_url"),
    }


def _require_user_id(user_id):
    clean = (user_id or "").strip()
    if not clean:
        raise PermissionError("Sign in required.")
    return clean


def _pg_quote(value):
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def _text_in(values):
    return f"({','.join(_pg_quote(v) for v in values)})"


def _int_in(values):
    return f"({','.join(str(int(v)) for v in values)})"


def _upsert_track(track):
    normalized = normalize_track(track)
    if not normalized["name"] or not normalized["artist"]:
        raise ValueError("Track must include both name and artist.")

    key = _track_key(normalized["name"], normalized["artist"])
    payload = {
        "track_key": key,
        "name": normalized["name"],
        "artist": normalized["artist"],
        "preview_url": normalized["preview_url"],
        "album_cover": normalized["album_cover"],
        "lastfm_url": normalized["lastfm_url"],
        "spotify_url": normalized["spotify_url"],
    }
    _rest_request(
        "POST",
        "tracks",
        params={"on_conflict": "track_key"},
        payload=payload,
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return key


def _fetch_tracks_by_keys(keys):
    if not keys:
        return {}
    rows = _rest_request(
        "GET",
        "tracks",
        params={
            "select": "track_key,name,artist,preview_url,album_cover,lastfm_url,spotify_url",
            "track_key": f"in.{_text_in(keys)}",
        },
    )
    return {row["track_key"]: _serialize_track_row(row) for row in rows}


def init_db():
    return None


def cache_tracks(tracks):
    for track in tracks or []:
        try:
            _upsert_track(track)
        except ValueError:
            continue


def get_liked_tracks(user_id=None):
    uid = _require_user_id(user_id)
    likes = _rest_request(
        "GET",
        "liked_songs",
        params={
            "select": "track_key,liked_at",
            "user_id": f"eq.{uid}",
            "order": "liked_at.desc",
        },
    )
    keys = [row["track_key"] for row in likes]
    track_map = _fetch_tracks_by_keys(keys)
    return [track_map[key] for key in keys if key in track_map]


def toggle_like(track, user_id=None):
    uid = _require_user_id(user_id)
    key = _upsert_track(track)

    existing = _rest_request(
        "GET",
        "liked_songs",
        params={
            "select": "track_key",
            "user_id": f"eq.{uid}",
            "track_key": f"eq.{key}",
            "limit": 1,
        },
    )
    if existing:
        _rest_request(
            "DELETE",
            "liked_songs",
            params={"user_id": f"eq.{uid}", "track_key": f"eq.{key}"},
        )
        return False

    _rest_request(
        "POST",
        "liked_songs",
        payload={"user_id": uid, "track_key": key},
        prefer="return=minimal",
    )
    return True


def add_recent_play(track, user_id=None, max_entries=25):
    uid = _require_user_id(user_id)
    key = _upsert_track(track)

    _rest_request(
        "DELETE",
        "recent_plays",
        params={"user_id": f"eq.{uid}", "track_key": f"eq.{key}"},
    )
    _rest_request(
        "POST",
        "recent_plays",
        payload={"user_id": uid, "track_key": key},
        prefer="return=minimal",
    )

    extras = _rest_request(
        "GET",
        "recent_plays",
        params={
            "select": "id",
            "user_id": f"eq.{uid}",
            "order": "played_at.desc,id.desc",
            "offset": max_entries,
            "limit": 1000,
        },
    )
    extra_ids = [row["id"] for row in extras]
    if extra_ids:
        _rest_request(
            "DELETE",
            "recent_plays",
            params={"id": f"in.{_int_in(extra_ids)}"},
        )


def get_recent_tracks(limit=10, user_id=None):
    uid = _require_user_id(user_id)
    rows = _rest_request(
        "GET",
        "recent_plays",
        params={
            "select": "track_key",
            "user_id": f"eq.{uid}",
            "order": "played_at.desc,id.desc",
            "limit": limit,
        },
    )
    keys = [row["track_key"] for row in rows]
    track_map = _fetch_tracks_by_keys(list(dict.fromkeys(keys)))
    return [track_map[key] for key in keys if key in track_map]


def clear_recent_tracks(user_id=None):
    uid = _require_user_id(user_id)
    _rest_request("DELETE", "recent_plays", params={"user_id": f"eq.{uid}"})


def list_playlists(user_id=None):
    uid = _require_user_id(user_id)
    playlists = _rest_request(
        "GET",
        "playlists",
        params={
            "select": "id,name,created_at",
            "user_id": f"eq.{uid}",
            "order": "created_at.desc,id.desc",
        },
    )
    if not playlists:
        return []

    ids = [row["id"] for row in playlists]
    tracks = _rest_request(
        "GET",
        "playlist_tracks",
        params={
            "select": "playlist_id",
            "playlist_id": f"in.{_int_in(ids)}",
        },
    )
    counts = Counter(row["playlist_id"] for row in tracks)

    out = []
    for row in playlists:
        out.append(
            {
                "id": row["id"],
                "name": row["name"],
                "created_at": row.get("created_at"),
                "track_count": counts.get(row["id"], 0),
            }
        )
    return out


def create_playlist(name, user_id=None):
    uid = _require_user_id(user_id)
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("Playlist name cannot be empty.")

    existing = _rest_request(
        "GET",
        "playlists",
        params={
            "select": "id,name",
            "user_id": f"eq.{uid}",
        },
    )
    for row in existing:
        if (row.get("name") or "").strip().lower() == clean_name.lower():
            return {"id": row["id"], "name": row["name"], "created": False}

    created = _rest_request(
        "POST",
        "playlists",
        payload={"user_id": uid, "name": clean_name},
        prefer="return=representation",
    )
    if not created:
        raise RuntimeError("Could not create playlist.")
    row = created[0]
    return {"id": row["id"], "name": row["name"], "created": True}


def get_playlist_tracks(playlist_id, user_id=None):
    uid = _require_user_id(user_id)
    playlist_rows = _rest_request(
        "GET",
        "playlists",
        params={
            "select": "id,name",
            "id": f"eq.{int(playlist_id)}",
            "user_id": f"eq.{uid}",
            "limit": 1,
        },
    )
    if not playlist_rows:
        return None
    playlist = playlist_rows[0]

    rows = _rest_request(
        "GET",
        "playlist_tracks",
        params={
            "select": "track_key",
            "playlist_id": f"eq.{int(playlist_id)}",
            "order": "added_at.desc",
        },
    )
    keys = [row["track_key"] for row in rows]
    track_map = _fetch_tracks_by_keys(list(dict.fromkeys(keys)))
    tracks = [track_map[key] for key in keys if key in track_map]
    return {"id": playlist["id"], "name": playlist["name"], "tracks": tracks}


def add_track_to_playlist(playlist_id, track, user_id=None):
    uid = _require_user_id(user_id)
    pid = int(playlist_id)
    exists = _rest_request(
        "GET",
        "playlists",
        params={
            "select": "id",
            "id": f"eq.{pid}",
            "user_id": f"eq.{uid}",
            "limit": 1,
        },
    )
    if not exists:
        raise ValueError("Playlist not found.")

    key = _upsert_track(track)
    existing = _rest_request(
        "GET",
        "playlist_tracks",
        params={
            "select": "playlist_id,track_key",
            "playlist_id": f"eq.{pid}",
            "track_key": f"eq.{key}",
            "limit": 1,
        },
    )
    if existing:
        return False

    _rest_request(
        "POST",
        "playlist_tracks",
        payload={"playlist_id": pid, "track_key": key},
        prefer="return=minimal",
    )
    return True


def delete_playlist(playlist_id, user_id=None):
    uid = _require_user_id(user_id)
    deleted = _rest_request(
        "DELETE",
        "playlists",
        params={"id": f"eq.{int(playlist_id)}", "user_id": f"eq.{uid}"},
        prefer="return=representation",
    )
    return bool(deleted)
