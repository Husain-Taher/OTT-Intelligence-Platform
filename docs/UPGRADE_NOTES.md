# OTT Intelligence: upgrade notes

## What changed
| Area | Before | Now |
|---|---|---|
| Frontends | Two (a 125 KB static page on :8000 and a Next.js app) that had drifted apart | One: the Next.js app. Old page kept in `services/intelligence-core/legacy/` for reference, no longer served |
| Login | Hand-rolled SHA-256 passwords, secret key in source, a seeded account with a known password; every route trusted a `user_id` sent by the browser | Auth0. FastAPI verifies the RS256 access token (issuer, audience, expiry) and uses its `sub` as the user. Next.js proxies `/api/ott/*` and attaches the token server-side |
| Mood | The home-page mood buttons were ignored; mood was never stored | Mood re-lights the whole UI, is sent with every reaction, and is learned per user (genre affinities per mood) |
| New users | Silently given a pre-baked "cerebral sci-fi" taste (Nolan, Villeneuve) | Blank profile, built by a 3-step onboarding and their own reactions |
| Profile numbers | Hard-coded (94% alignment, 48.5 h watched, fixed directors) | Computed from real events |
| Modal match score | Always "92%" | Real score, hidden when unknown |

## The experience
- **Marquee** (signed out): working mood dimmer; the room changes colour before sign-in.
- **Curtain** opens once per session after sign-in.
- **Onboarding**: pick your usual seat, react to an 8-title reel, light your first mood.
- **Mood Studio**: dimmer, genre chips for that mood, runtime, familiar-to-adventurous slider, free text, projector countdown, reveal with reasons and meters, "This fits tonight" / Save / Show me another, intermission picks.
- **Lobby**: same catalogue re-ranked by the lit mood (`/v1/discover?mood=`).
- **My Ticket**: real stats, "how well we know your taste", a per-mood map of what you reach for, recent nights, your saved reel.
- A mood chip in the top bar changes the mood from any screen.

## Run it locally
```bash
# API
cd services/intelligence-core
pip install -r requirements.txt
cp .env.example .env            # fill AUTH0_DOMAIN / AUTH0_AUDIENCE
uvicorn app.main:app --port 8000

# Web
cd apps/web
npm install
cp .env.local.example .env.local   # fill the Auth0 values
npm run dev                         # http://localhost:3000
```
Your existing database keeps working: new tables are created on startup.

## Auth0 setup (about 10 minutes)
1. **Applications > APIs > Create API**. Identifier = `https://ott-intelligence-api` (any URL-style id). This value is `AUTH0_AUDIENCE` in *both* env files.
2. **Applications > Create Application > Regular Web Application**. Copy Domain, Client ID, Client Secret into `.env.local`.
3. In that application's settings: Allowed Callback URLs `http://localhost:3000/api/auth/callback`, Allowed Logout URLs `http://localhost:3000`, Allowed Web Origins `http://localhost:3000`.
4. `AUTH0_SECRET` = output of `openssl rand -hex 32`.
5. For production add your real domain to those URLs and set `AUTH0_BASE_URL` and `CORS_ORIGINS`.

### UI work without Auth0
Set `AUTH_DISABLED=true` for FastAPI, and `AUTH_DISABLED=true` plus `NEXT_PUBLIC_AUTH_DISABLED=true` for Next.js (dev server only). Everything runs as `default_user`. Both sides refuse to start with this flag in production.

## Tests
`pytest tests/test_auth_and_moods.py` runs offline (forged RSA tokens, no Auth0 tenant). It checks that bad audience, issuer, expiry and signature are rejected, spoofed user ids are ignored, users are isolated, and reactions in a mood change that mood's profile. The older scripts in `tests/` call a live server; start it with `AUTH_DISABLED=true` first.

## Do this now
- **Rotate your TMDB API key and read token.** The uploaded zip contained `.env` with real values. `.gitignore` covers it, but anything shared as a zip should be treated as exposed. Keep `.venv/` (500 MB) out of zips too.
- `.babelrc` was removed from `apps/web`; it forced Next.js onto the slower Babel compiler.

## Known limits and next steps
- SQLite is fine for development; move to Postgres before real users.
- Per-mood ranking rules are still hand-written multipliers in `ranker.py`; the learned per-mood genre blend (max 45%, after 3 reactions) sits on top of them.
- The catalogue is 121 titles; the mood experience improves a lot with a bigger one (`run_seed.py` / TMDB ingestion).
- `TasteUniverseView` and `NaturalSearchView` were re-themed through the shared palette but not redesigned.
