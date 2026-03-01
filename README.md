# Moodwave

Mood-based song discovery app with:
- Last.fm + iTunes track search and previews
- likes, recents, playlists
- Spotify playlist export
- optional Supabase multi-user mode

## Run Locally

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create/update `.env`:
```env
FLASK_SECRET_KEY=replace-with-a-long-random-secret
APP_PORT=5001

GEMINI_API_KEY=...
LASTFM_API_KEY=...

SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://127.0.0.1:5001/spotify/callback

USE_SUPABASE=false
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
```

3. Start app:
```bash
python3 app.py
```

4. Open:
`http://127.0.0.1:5001`

## Enable Supabase Multi-User Mode

1. Create Supabase project.
2. Run [`supabase_schema.sql`](/Users/karan/Downloads/new_project/mountain-madness-26/supabase_schema.sql) in Supabase SQL Editor.
3. Set `.env`:
```env
USE_SUPABASE=true
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
```
4. Restart app.
5. Use top-right `Sign In` button in UI.

When Supabase is enabled, likes/recent/playlists are scoped per authenticated user.


## Security Notes

- Never commit `.env`.
- Rotate secrets immediately if exposed.
- `SUPABASE_SERVICE_ROLE_KEY` must stay server-side only.
