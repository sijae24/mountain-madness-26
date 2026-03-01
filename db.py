import os

from local_store import (
    add_recent_play as _local_add_recent_play,
    add_track_to_playlist as _local_add_track_to_playlist,
    cache_tracks as _local_cache_tracks,
    clear_recent_tracks as _local_clear_recent_tracks,
    create_playlist as _local_create_playlist,
    delete_playlist as _local_delete_playlist,
    get_liked_tracks as _local_get_liked_tracks,
    get_playlist_tracks as _local_get_playlist_tracks,
    get_recent_tracks as _local_get_recent_tracks,
    init_db as _local_init_db,
    list_playlists as _local_list_playlists,
    toggle_like as _local_toggle_like,
)
from supabase_store import (
    add_recent_play as _sb_add_recent_play,
    add_track_to_playlist as _sb_add_track_to_playlist,
    cache_tracks as _sb_cache_tracks,
    clear_recent_tracks as _sb_clear_recent_tracks,
    create_playlist as _sb_create_playlist,
    delete_playlist as _sb_delete_playlist,
    get_liked_tracks as _sb_get_liked_tracks,
    get_playlist_tracks as _sb_get_playlist_tracks,
    get_recent_tracks as _sb_get_recent_tracks,
    is_configured as _sb_is_configured,
    list_playlists as _sb_list_playlists,
    public_config as _sb_public_config,
    resolve_user_from_access_token as _sb_resolve_user_from_access_token,
    toggle_like as _sb_toggle_like,
)


def is_supabase_mode():
    explicit = (os.getenv("USE_SUPABASE") or "").strip().lower()
    if explicit in {"1", "true", "yes", "on"}:
        return True
    if explicit in {"0", "false", "no", "off"}:
        return False
    return _sb_is_configured()


def supabase_public_config():
    return _sb_public_config()


def resolve_user_from_access_token(access_token):
    if not is_supabase_mode():
        return None
    return _sb_resolve_user_from_access_token(access_token)


def init_db():
    if is_supabase_mode():
        return None
    return _local_init_db()


def cache_tracks(tracks):
    if is_supabase_mode():
        return _sb_cache_tracks(tracks)
    return _local_cache_tracks(tracks)


def get_liked_tracks(user_id=None):
    if is_supabase_mode():
        return _sb_get_liked_tracks(user_id=user_id)
    return _local_get_liked_tracks()


def toggle_like(track, user_id=None):
    if is_supabase_mode():
        return _sb_toggle_like(track, user_id=user_id)
    return _local_toggle_like(track)


def add_recent_play(track, user_id=None, max_entries=25):
    if is_supabase_mode():
        return _sb_add_recent_play(track, user_id=user_id, max_entries=max_entries)
    return _local_add_recent_play(track, max_entries=max_entries)


def get_recent_tracks(limit=10, user_id=None):
    if is_supabase_mode():
        return _sb_get_recent_tracks(limit=limit, user_id=user_id)
    return _local_get_recent_tracks(limit=limit)


def clear_recent_tracks(user_id=None):
    if is_supabase_mode():
        return _sb_clear_recent_tracks(user_id=user_id)
    return _local_clear_recent_tracks()


def list_playlists(user_id=None):
    if is_supabase_mode():
        return _sb_list_playlists(user_id=user_id)
    return _local_list_playlists()


def create_playlist(name, user_id=None):
    if is_supabase_mode():
        return _sb_create_playlist(name, user_id=user_id)
    return _local_create_playlist(name)


def get_playlist_tracks(playlist_id, user_id=None):
    if is_supabase_mode():
        return _sb_get_playlist_tracks(playlist_id, user_id=user_id)
    return _local_get_playlist_tracks(playlist_id)


def add_track_to_playlist(playlist_id, track, user_id=None):
    if is_supabase_mode():
        return _sb_add_track_to_playlist(playlist_id, track, user_id=user_id)
    return _local_add_track_to_playlist(playlist_id, track)


def delete_playlist(playlist_id, user_id=None):
    if is_supabase_mode():
        return _sb_delete_playlist(playlist_id, user_id=user_id)
    return _local_delete_playlist(playlist_id)
