-- Run this in Supabase SQL editor before enabling USE_SUPABASE.

create extension if not exists pgcrypto;

create table if not exists public.tracks (
  track_key text primary key,
  name text not null,
  artist text not null,
  preview_url text,
  album_cover text,
  lastfm_url text,
  spotify_url text,
  updated_at timestamptz not null default now()
);

create table if not exists public.liked_songs (
  user_id uuid not null references auth.users(id) on delete cascade,
  track_key text not null references public.tracks(track_key) on delete cascade,
  liked_at timestamptz not null default now(),
  primary key (user_id, track_key)
);

create table if not exists public.recent_plays (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  track_key text not null references public.tracks(track_key) on delete cascade,
  played_at timestamptz not null default now()
);

create unique index if not exists recent_plays_user_track_unique
  on public.recent_plays(user_id, track_key);

create table if not exists public.playlists (
  id bigint generated always as identity primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now()
);

create unique index if not exists playlists_user_lower_name_unique
  on public.playlists(user_id, lower(name));

create table if not exists public.playlist_tracks (
  playlist_id bigint not null references public.playlists(id) on delete cascade,
  track_key text not null references public.tracks(track_key) on delete cascade,
  added_at timestamptz not null default now(),
  primary key (playlist_id, track_key)
);

create index if not exists playlist_tracks_playlist_id_idx
  on public.playlist_tracks(playlist_id);

create index if not exists recent_plays_user_played_at_idx
  on public.recent_plays(user_id, played_at desc, id desc);

create index if not exists liked_songs_user_liked_at_idx
  on public.liked_songs(user_id, liked_at desc);

alter table public.tracks enable row level security;
alter table public.liked_songs enable row level security;
alter table public.recent_plays enable row level security;
alter table public.playlists enable row level security;
alter table public.playlist_tracks enable row level security;

drop policy if exists "tracks read all" on public.tracks;
create policy "tracks read all"
  on public.tracks
  for select
  to authenticated
  using (true);

drop policy if exists "tracks service write" on public.tracks;
create policy "tracks service write"
  on public.tracks
  for all
  to service_role
  using (true)
  with check (true);

drop policy if exists "liked owner" on public.liked_songs;
create policy "liked owner"
  on public.liked_songs
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "recent owner" on public.recent_plays;
create policy "recent owner"
  on public.recent_plays
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "playlists owner" on public.playlists;
create policy "playlists owner"
  on public.playlists
  for all
  to authenticated
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "playlist_tracks owner" on public.playlist_tracks;
create policy "playlist_tracks owner"
  on public.playlist_tracks
  for all
  to authenticated
  using (
    exists (
      select 1
      from public.playlists p
      where p.id = playlist_id
        and p.user_id = auth.uid()
    )
  )
  with check (
    exists (
      select 1
      from public.playlists p
      where p.id = playlist_id
        and p.user_id = auth.uid()
    )
  );
