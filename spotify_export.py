import os
from datetime import datetime
from urllib.parse import urlencode

import requests

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
APP_PORT = os.getenv("APP_PORT", "5000")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", f"http://127.0.0.1:{APP_PORT}/spotify/callback")

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_SCOPES = "playlist-modify-public playlist-modify-private user-read-private"


class SpotifyApiError(RuntimeError):
    def __init__(self, message, status_code=None, method=None, path=None):
        super().__init__(message)
        self.status_code = status_code
        self.method = method
        self.path = path


def is_spotify_configured():
    return bool(SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET)


def build_spotify_auth_url(state):
    if not is_spotify_configured():
        raise RuntimeError("Spotify integration is not configured.")
    query = urlencode(
        {
            "client_id": SPOTIFY_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": SPOTIFY_REDIRECT_URI,
            "scope": SPOTIFY_SCOPES,
            "state": state,
            "show_dialog": "true",
        }
    )
    return f"{SPOTIFY_AUTH_URL}?{query}"


def exchange_code_for_token(code):
    if not is_spotify_configured():
        raise RuntimeError("Spotify integration is not configured.")

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": SPOTIFY_REDIRECT_URI,
        },
        auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
        timeout=15,
    )
    if response.status_code >= 400:
        detail = response.json().get("error_description") if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise RuntimeError(detail or "Could not exchange Spotify auth code.")
    return response.json()


def refresh_access_token(refresh_token):
    if not is_spotify_configured():
        raise RuntimeError("Spotify integration is not configured.")
    if not refresh_token:
        raise RuntimeError("Missing Spotify refresh token.")

    response = requests.post(
        SPOTIFY_TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=(SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET),
        timeout=15,
    )
    if response.status_code >= 400:
        detail = response.json().get("error_description") if response.headers.get("content-type", "").startswith("application/json") else response.text
        raise RuntimeError(detail or "Could not refresh Spotify token.")
    return response.json()


def _spotify_error_message(response):
    fallback = f"Spotify API error ({response.status_code})."
    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        return response.text.strip() or fallback

    try:
        payload = response.json()
    except ValueError:
        return fallback

    err = payload.get("error")
    if isinstance(err, dict):
        message = err.get("message") or err.get("reason")
        status = err.get("status")
        if message:
            return f"{message} (Spotify {status or response.status_code})"
    elif isinstance(err, str):
        return err

    message = payload.get("error_description") or payload.get("message")
    if message:
        return message
    return fallback


def _raise_spotify_error(response, method, path):
    message = _spotify_error_message(response)
    status_code = response.status_code
    raise SpotifyApiError(
        f"{message} ({method} {path})",
        status_code=status_code,
        method=method,
        path=path,
    )


def _spotify_get(access_token, path, params=None):
    response = requests.get(
        f"{SPOTIFY_API_BASE}{path}",
        params=params or {},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if response.status_code >= 400:
        _raise_spotify_error(response, "GET", path)
    return response.json()


def _spotify_post(access_token, path, body):
    response = requests.post(
        f"{SPOTIFY_API_BASE}{path}",
        json=body,
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        timeout=15,
    )
    if response.status_code >= 400:
        _raise_spotify_error(response, "POST", path)
    return response.json() if response.text else {}


def _search_track_uri(access_token, track_name, artist):
    query = f'track:"{track_name}" artist:"{artist}"'
    data = _spotify_get(
        access_token,
        "/search",
        {"q": query, "type": "track", "limit": 1},
    )
    items = data.get("tracks", {}).get("items", [])
    if not items:
        return None
    return items[0].get("uri")


def _create_playlist(access_token, playlist_name):
    me = _spotify_get(access_token, "/me")
    user_id = me.get("id")
    if not user_id:
        raise RuntimeError("Could not resolve Spotify user.")

    now = datetime.utcnow().strftime("%Y-%m-%d")
    created = _spotify_post(
        access_token,
        f"/users/{user_id}/playlists",
        {
            "name": f"{playlist_name} (Moodwave)",
            "description": f"Exported from Moodwave on {now}",
            "public": False,
        },
    )
    return created.get("id"), created.get("external_urls", {}).get("spotify")


def _add_tracks(access_token, playlist_id, uris):
    if not uris:
        return
    chunk_size = 100
    for start in range(0, len(uris), chunk_size):
        _spotify_post(
            access_token,
            f"/playlists/{playlist_id}/tracks",
            {"uris": uris[start : start + chunk_size]},
        )


def export_playlist_to_spotify(access_token, playlist_name, tracks):
    playlist_id, playlist_url = _create_playlist(access_token, playlist_name)

    uris = []
    misses = 0
    for track in tracks or []:
        uri = _search_track_uri(access_token, track.get("name", ""), track.get("artist", ""))
        if uri:
            uris.append(uri)
        else:
            misses += 1

    _add_tracks(access_token, playlist_id, uris)
    return {
        "spotify_playlist_id": playlist_id,
        "spotify_playlist_url": playlist_url,
        "matched_tracks": len(uris),
        "unmatched_tracks": misses,
    }
