# Moodwave

## Supabase Multi-User Setup

1. Create a Supabase project.
2. Run [`supabase_schema.sql`](/Users/karan/Downloads/new_project/mountain-madness-26/supabase_schema.sql) in the Supabase SQL editor.
3. In `.env`, set:
   - `USE_SUPABASE=true`
   - `SUPABASE_URL=...`
   - `SUPABASE_ANON_KEY=...`
   - `SUPABASE_SERVICE_ROLE_KEY=...`
4. Restart Flask (`python3 app.py`).
5. Open the app and use the top-right `Sign In` button.

## Notes

- In Supabase mode, likes, recents, and playlists are scoped per authenticated user.
- If `USE_SUPABASE=false`, the app falls back to local SQLite.
