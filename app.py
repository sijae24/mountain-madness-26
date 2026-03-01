import os
import secrets
import time
from urllib.parse import urlencode

from flask import Flask, jsonify, redirect, request, send_from_directory, session

from db import (
    add_recent_play,
    add_track_to_playlist,
    cache_tracks,
    clear_recent_tracks,
    create_playlist,
    delete_playlist,
    get_liked_tracks,
    get_playlist_tracks,
    get_recent_tracks,
    init_db,
    list_playlists,
    toggle_like,
)
from spotify import get_recommendations, search_tracks
from spotify_export import (
    SpotifyApiError,
    build_spotify_auth_url,
    exchange_code_for_token,
    export_playlist_to_spotify,
    is_spotify_configured,
    refresh_access_token,
)

app = Flask(__name__, static_folder=".", template_folder=".")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-change-this-key")
init_db()

SPOTIFY_TOKEN_SESSION_KEY = "spotify_token"
SPOTIFY_STATE_SESSION_KEY = "spotify_oauth_state"
SPOTIFY_PENDING_PLAYLIST_KEY = "spotify_pending_playlist_id"


def _json_error(message, status=400):
    return jsonify({"error": message}), status


def _track_from_body(data):
    if not data or "track" not in data:
        raise ValueError("Request must include a track object.")
    return data["track"]


def _token_expired(token_data):
    if not token_data:
        return True
    return token_data.get("expires_at", 0) <= int(time.time()) + 30


def _set_spotify_token(token_payload):
    if not token_payload:
        return
    current = session.get(SPOTIFY_TOKEN_SESSION_KEY, {})
    refresh_token = token_payload.get("refresh_token") or current.get("refresh_token")
    session[SPOTIFY_TOKEN_SESSION_KEY] = {
        "access_token": token_payload.get("access_token"),
        "refresh_token": refresh_token,
        "expires_at": int(time.time()) + int(token_payload.get("expires_in", 3600)),
    }


def _get_spotify_access_token():
    token_data = session.get(SPOTIFY_TOKEN_SESSION_KEY)
    if not token_data:
        return None
    if not _token_expired(token_data):
        return token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        return None
    refreshed = refresh_access_token(refresh_token)
    _set_spotify_token(refreshed)
    return session.get(SPOTIFY_TOKEN_SESSION_KEY, {}).get("access_token")


def _redirect_with_query(params):
    return redirect("/?" + urlencode(params))


def _export_playlist_with_spotify_token(playlist_id):
    playlist = get_playlist_tracks(playlist_id)
    if not playlist:
        raise ValueError("Playlist not found.")

    access_token = _get_spotify_access_token()
    if not access_token:
        raise PermissionError("Please connect Spotify first.")

    result = export_playlist_to_spotify(
        access_token=access_token,
        playlist_name=playlist["name"],
        tracks=playlist.get("tracks", []),
    )
    result["playlist_name"] = playlist["name"]
    return result


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/style.css")
def css():
    return send_from_directory(".", "style.css")


@app.route("/app.js")
def js():
    return send_from_directory(".", "app.js")


@app.route("/recommend", methods=["POST"])
def recommend():
    data = request.get_json(force=True, silent=True)
    if not data or not data.get("text", "").strip():
        return _json_error("Please provide a non-empty text field.", 400)
    try:
        result = get_recommendations(data["text"].strip())
        cache_tracks(result.get("tracks", []))
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Error in /recommend")
        return _json_error(str(exc), 500)


@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"query": "", "tracks": []})
    try:
        tracks = search_tracks(query, limit=15)
        cache_tracks(tracks)
        return jsonify({"query": query, "tracks": tracks})
    except Exception as exc:
        app.logger.exception("Error in /search")
        return _json_error(str(exc), 500)


@app.route("/api/bootstrap", methods=["GET"])
def bootstrap():
    try:
        return jsonify(
            {
                "liked_tracks": get_liked_tracks(),
                "recent_tracks": get_recent_tracks(limit=10),
                "playlists": list_playlists(),
            }
        )
    except Exception as exc:
        app.logger.exception("Error in /api/bootstrap")
        return _json_error(str(exc), 500)


@app.route("/api/liked", methods=["GET"])
def liked_tracks():
    try:
        return jsonify({"tracks": get_liked_tracks()})
    except Exception as exc:
        app.logger.exception("Error in /api/liked")
        return _json_error(str(exc), 500)


@app.route("/api/liked/toggle", methods=["POST"])
def toggle_liked_track():
    data = request.get_json(force=True, silent=True)
    try:
        track = _track_from_body(data)
        liked = toggle_like(track)
        tracks = get_liked_tracks()
        return jsonify({"liked": liked, "tracks": tracks})
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except Exception as exc:
        app.logger.exception("Error in /api/liked/toggle")
        return _json_error(str(exc), 500)


@app.route("/api/recent", methods=["GET", "POST", "DELETE"])
def recent_tracks():
    if request.method == "GET":
        try:
            return jsonify({"tracks": get_recent_tracks(limit=10)})
        except Exception as exc:
            app.logger.exception("Error in GET /api/recent")
            return _json_error(str(exc), 500)

    if request.method == "DELETE":
        try:
            clear_recent_tracks()
            return jsonify({"ok": True, "tracks": []})
        except Exception as exc:
            app.logger.exception("Error in DELETE /api/recent")
            return _json_error(str(exc), 500)

    data = request.get_json(force=True, silent=True)
    try:
        track = _track_from_body(data)
        add_recent_play(track)
        return jsonify({"ok": True})
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except Exception as exc:
        app.logger.exception("Error in POST /api/recent")
        return _json_error(str(exc), 500)


@app.route("/api/recent/clear", methods=["POST"])
def clear_recent_tracks_route():
    try:
        clear_recent_tracks()
        return jsonify({"ok": True, "tracks": []})
    except Exception as exc:
        app.logger.exception("Error in POST /api/recent/clear")
        return _json_error(str(exc), 500)


@app.route("/api/playlists", methods=["GET", "POST"])
def playlists():
    if request.method == "GET":
        try:
            return jsonify({"playlists": list_playlists()})
        except Exception as exc:
            app.logger.exception("Error in GET /api/playlists")
            return _json_error(str(exc), 500)

    data = request.get_json(force=True, silent=True)
    try:
        created = create_playlist((data or {}).get("name", ""))
        return jsonify({"playlist": created, "playlists": list_playlists()})
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except Exception as exc:
        app.logger.exception("Error in POST /api/playlists")
        return _json_error(str(exc), 500)


@app.route("/api/playlists/<int:playlist_id>", methods=["GET", "DELETE"])
def playlist_tracks(playlist_id):
    if request.method == "DELETE":
        try:
            deleted = delete_playlist(playlist_id)
            if not deleted:
                return _json_error("Playlist not found.", 404)
            return jsonify({"deleted": True, "playlists": list_playlists()})
        except Exception as exc:
            app.logger.exception("Error in DELETE /api/playlists/<id>")
            return _json_error(str(exc), 500)

    try:
        result = get_playlist_tracks(playlist_id)
        if not result:
            return _json_error("Playlist not found.", 404)
        return jsonify(result)
    except Exception as exc:
        app.logger.exception("Error in GET /api/playlists/<id>")
        return _json_error(str(exc), 500)


@app.route("/api/playlists/<int:playlist_id>/delete", methods=["POST"])
def delete_playlist_route(playlist_id):
    try:
        deleted = delete_playlist(playlist_id)
        if not deleted:
            return _json_error("Playlist not found.", 404)
        return jsonify({"deleted": True, "playlists": list_playlists()})
    except Exception as exc:
        app.logger.exception("Error in POST /api/playlists/<id>/delete")
        return _json_error(str(exc), 500)


@app.route("/api/playlists/<int:playlist_id>/export/spotify", methods=["POST"])
def export_playlist_spotify(playlist_id):
    if not is_spotify_configured():
        return _json_error(
            "Spotify is not configured. Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.",
            400,
        )

    access_token = _get_spotify_access_token()
    if not access_token:
        return (
            jsonify(
                {
                    "error": "Connect Spotify to export playlists.",
                    "requires_auth": True,
                    "auth_url": f"/spotify/login?playlist_id={playlist_id}",
                }
            ),
            401,
        )

    try:
        result = _export_playlist_with_spotify_token(playlist_id)
        return jsonify(result)
    except ValueError as exc:
        return _json_error(str(exc), 404)
    except PermissionError as exc:
        return _json_error(str(exc), 401)
    except SpotifyApiError as exc:
        message = str(exc)
        lower = message.lower()
        status = exc.status_code or 500

        # If token scopes are stale, force reconnect to refresh consent.
        if status == 403 and "insufficient client scope" in lower:
            session.pop(SPOTIFY_TOKEN_SESSION_KEY, None)
            return (
                jsonify(
                    {
                        "error": (
                            "Spotify token is missing required scopes. "
                            "Reconnect Spotify and try export again."
                        ),
                        "requires_auth": True,
                        "auth_url": f"/spotify/login?playlist_id={playlist_id}",
                    }
                ),
                401,
            )

        if status == 403:
            message = (
                "Spotify denied playlist export (403). "
                "If your app is in Spotify Development mode, add your account "
                "under Dashboard -> Users and access, then reconnect and retry. "
                f"Details: {exc}"
            )
        return _json_error(message, status if 400 <= status < 600 else 500)
    except Exception as exc:
        app.logger.exception("Error in /api/playlists/<id>/export/spotify")
        return _json_error(str(exc), 500)


@app.route("/spotify/login", methods=["GET"])
def spotify_login():
    if not is_spotify_configured():
        return _redirect_with_query(
            {
                "spotify_export": "error",
                "message": "Spotify credentials are not configured on the server.",
            }
        )

    playlist_id = request.args.get("playlist_id", "").strip()
    if playlist_id:
        session[SPOTIFY_PENDING_PLAYLIST_KEY] = playlist_id

    state = secrets.token_urlsafe(24)
    session[SPOTIFY_STATE_SESSION_KEY] = state
    return redirect(build_spotify_auth_url(state))


@app.route("/spotify/callback", methods=["GET"])
def spotify_callback():
    error = request.args.get("error")
    if error:
        return _redirect_with_query({"spotify_export": "error", "message": f"Spotify auth error: {error}"})

    incoming_state = request.args.get("state")
    expected_state = session.pop(SPOTIFY_STATE_SESSION_KEY, None)
    if not incoming_state or incoming_state != expected_state:
        return _redirect_with_query({"spotify_export": "error", "message": "Invalid Spotify auth state."})

    code = request.args.get("code")
    if not code:
        return _redirect_with_query({"spotify_export": "error", "message": "Missing Spotify auth code."})

    try:
        token_payload = exchange_code_for_token(code)
        _set_spotify_token(token_payload)
    except Exception as exc:
        return _redirect_with_query({"spotify_export": "error", "message": str(exc)})

    pending_playlist_id = session.pop(SPOTIFY_PENDING_PLAYLIST_KEY, None)
    if not pending_playlist_id:
        return _redirect_with_query({"spotify_export": "connected"})

    try:
        result = _export_playlist_with_spotify_token(int(pending_playlist_id))
        return _redirect_with_query(
            {
                "spotify_export": "success",
                "name": result.get("playlist_name", ""),
                "url": result.get("spotify_playlist_url", ""),
                "matched": result.get("matched_tracks", 0),
                "missed": result.get("unmatched_tracks", 0),
            }
        )
    except Exception as exc:
        return _redirect_with_query({"spotify_export": "error", "message": str(exc)})


@app.route("/api/playlists/<int:playlist_id>/tracks", methods=["POST"])
def add_playlist_track(playlist_id):
    data = request.get_json(force=True, silent=True)
    try:
        track = _track_from_body(data)
        added = add_track_to_playlist(playlist_id, track)
        return jsonify({"added": added})
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except Exception as exc:
        app.logger.exception("Error in POST /api/playlists/<id>/tracks")
        return _json_error(str(exc), 500)


if __name__ == "__main__":
    app_port = int(os.getenv("APP_PORT", "5000"))
    app.run(debug=True, use_reloader=False, port=app_port)
