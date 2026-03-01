import os
import random

import requests
from dotenv import load_dotenv

from emotion import get_emotion_data

load_dotenv()

LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")
LASTFM_BASE_URL = "https://ws.audioscrobbler.com/2.0/"
ITUNES_SEARCH_URL = "https://itunes.apple.com/search"


def _get_json(url, params):
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return {}


def _extract_lastfm_image(images):
    if not isinstance(images, list):
        return None
    for img in reversed(images):
        src = (img or {}).get("#text", "").strip()
        if src:
            return src
    return None


def _get_itunes_track_data(track_name, artist):
    data = _get_json(
        ITUNES_SEARCH_URL,
        {
            "term": f"{track_name} {artist}",
            "media": "music",
            "entity": "song",
            "limit": 1,
        },
    )
    results = data.get("results", [])
    if not results:
        return {"preview_url": None, "album_cover": None}
    first = results[0]
    return {
        "preview_url": first.get("previewUrl"),
        "album_cover": first.get("artworkUrl100"),
    }


def _format_track(track_name, artist, lastfm_url=None, lastfm_cover=None):
    itunes_data = _get_itunes_track_data(track_name, artist)
    return {
        "name": track_name,
        "artist": artist,
        "lastfm_url": lastfm_url,
        # Backward-compatibility with existing frontend key.
        "spotify_url": lastfm_url,
        "preview_url": itunes_data["preview_url"],
        "album_cover": itunes_data["album_cover"] or lastfm_cover,
    }


def get_top_artists_for_tag(tag):
    page = random.randint(1, 10)
    data = _get_json(
        LASTFM_BASE_URL,
        {
            "method": "tag.gettopartists",
            "tag": tag,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "page": page,
            "limit": 20,
        },
    )
    artists = data.get("topartists", {}).get("artist", [])
    return [a["name"] for a in artists if a.get("name")]


def get_top_track_for_artist(artist):
    data = _get_json(
        LASTFM_BASE_URL,
        {
            "method": "artist.gettoptracks",
            "artist": artist,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": 5,
        },
    )
    tracks = data.get("toptracks", {}).get("track", [])
    if not tracks:
        return None

    shuffled_tracks = tracks[:]
    random.shuffle(shuffled_tracks)
    fallback = None

    for track in shuffled_tracks:
        track_name = track.get("name")
        if not track_name:
            continue

        formatted = _format_track(
            track_name=track_name,
            artist=artist,
            lastfm_url=track.get("url"),
            lastfm_cover=_extract_lastfm_image(track.get("image")),
        )
        if formatted["preview_url"]:
            return formatted
        if fallback is None:
            fallback = formatted

    return fallback


def search_tracks(query, limit=15):
    query = (query or "").strip()
    if not query:
        return []

    data = _get_json(
        LASTFM_BASE_URL,
        {
            "method": "track.search",
            "track": query,
            "api_key": LASTFM_API_KEY,
            "format": "json",
            "limit": max(limit * 2, 20),
        },
    )
    matches = data.get("results", {}).get("trackmatches", {}).get("track", [])
    if isinstance(matches, dict):
        matches = [matches]

    with_preview = []
    without_preview = []
    seen = set()

    for track in matches:
        name = track.get("name", "").strip()
        artist = track.get("artist", "").strip()
        if not name or not artist:
            continue
        key = f"{name.lower()}::{artist.lower()}"
        if key in seen:
            continue
        seen.add(key)

        formatted = _format_track(
            track_name=name,
            artist=artist,
            lastfm_url=track.get("url"),
            lastfm_cover=_extract_lastfm_image(track.get("image")),
        )
        if formatted["preview_url"]:
            with_preview.append(formatted)
        else:
            without_preview.append(formatted)

        if len(with_preview) >= limit:
            break

    combined = with_preview + without_preview
    return combined[:limit]


def get_recommendations(text):
    emotion_data = get_emotion_data(text)
    emotion = emotion_data["emotion"]
    tag = emotion_data["tag"]

    artists = get_top_artists_for_tag(tag)
    if not artists:
        return {"emotion": emotion, "tag": tag, "tracks": []}

    # Aim for a fuller playlist instead of only a few tracks.
    target_tracks = 10
    selected_artists = random.sample(artists, min(len(artists), 20))
    tracks = []
    seen = set()

    for artist in selected_artists:
        track = get_top_track_for_artist(artist)
        if track:
            key = f"{track.get('name', '').lower()}::{track.get('artist', '').lower()}"
            if key in seen:
                continue
            seen.add(key)
            tracks.append(track)
            if len(tracks) >= target_tracks:
                break

    return {"emotion": emotion, "tag": tag, "tracks": tracks}
        
