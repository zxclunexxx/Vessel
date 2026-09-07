# Vessel release readiness

## Current development mode

Vessel uses batched autonomous sprint branches instead of treating every small fix as a release.

- Development branches: `autonomous/**`
- Every sprint commit: `Vessel Fast Gate`
- Pull requests to `main`: `Vessel Fast Gate`
- Merge/push to `main`: `Vessel Release Gate`
- Release Gate runs Fast Gate first, then Web, Android APK, and Windows EXE in parallel.
- Autonomous patching is restricted to `autonomous/**` and never force-pushes.
- Historical patch migrations are not replayed; only patch migrations added relative to `main` are applied in a sprint.
- Generated runtime changes must pass the centralized Fast Gate suite before the bot commit is pushed.

## Last known stable main

- Commit: `7e6207f62cad3a15c99136c925d392a3d4cc4e52`
- Release Gate run: `34157439474`
- Fast Gate: verified green
- Web build/deploy: verified green
- Android debug APK: verified green and artifact uploaded
- Windows portable EXE: verified green and artifact uploaded
- Friends / DM / realtime resilience: merged
- Voice / calls / reconnect / TURN-ready transport architecture: merged
- UI Batch 1 liquid-glass foundation: merged as PR #5
- Live Supabase `rtc-config`: ACTIVE and JWT-protected; real TURN relay still requires external TURN infrastructure and server-side secrets.

## Current sprint

Branch: `autonomous/auth-email-resilience-batch`

This focused auth batch addresses Supabase email quota failures before UI Batch 2:

1. Translate Supabase Auth failures into stable Russian Vessel messages instead of exposing raw backend error strings.
2. Recognize `over_email_send_rate_limit` / `email rate limit` explicitly.
3. Apply a local registration cooldown after email quota or generic Auth 429 failures so repeated clicks do not hammer Auth endpoints.
4. Keep login available while signup is cooling down.
5. Restore the signup button automatically with a visible countdown.
6. Preserve email confirmation rather than weakening account security to bypass delivery limits.
7. Document a production custom-SMTP architecture in `docs/AUTH_EMAIL_SMTP.md`.
8. Keep SMTP credentials exclusively in protected Supabase/provider configuration; never in frontend code, GitHub, APK or EXE.
9. Require SPF, DKIM and DMARC/domain setup for production sending.
10. Extend the centralized Fast Gate from 28 to 29 checks with `auth_email_resilience_smoke_check.py`.

## Current sprint verification

- Autonomous auth migration: passed.
- Generated auth runtime is present in `src/main.js` under `VESSEL_AUTH_EMAIL_RESILIENCE_V1`.
- 29-check Fast Gate smoke suite: passed.
- JavaScript syntax: passed.
- Dependency audit: passed.
- Production build: passed.
- PR Fast Gate is required before merge.
- After merge, exactly one Release Gate must verify Web, Android APK and Windows EXE.

## Next UI batches

1. Messaging + Social: friend cards, DM rows, message grouping, composer polish, loading/empty/error states.
2. Voice + Calls: participant cards, speaking indicators, audio/video stages, reconnect banners and floating call controls.
3. Motion + Polish: transitions, microinteractions, ambient motion, mobile refinement, reduced-motion validation and performance cleanup.

## Known blockers / external dependencies

- Production auth email still requires an external SMTP provider account/domain and its SMTP credentials configured in Supabase. Those secrets must not be committed to Vessel.
- The built-in Supabase Auth email sender is suitable only for limited testing and can return `email rate limit exceeded` under repeated signup/recovery traffic.
- Actual TURN relay traffic requires external TURN infrastructure plus Edge Function secrets `TURN_URLS` and `TURN_SHARED_SECRET` (optional `TURN_TTL_SECONDS` / `STUN_URLS`).
- No TURN secret or long-lived TURN credential may be committed to the repository or embedded in browser code.
- Supabase Leaked Password Protection is an account/project Auth setting rather than an application-code patch; enabling it must not expose any secrets.

## Safety invariants

- Never expose service-role keys, secret keys, SMTP passwords, TURN shared secrets, TURN credentials, or private tokens in client code, logs, commits, or artifacts.
- Keep email confirmations enabled for production accounts.
- Keep `rtc-config` JWT-protected and authenticated; it does not need service-role access.
- Do not weaken RLS to make a client flow work.
- Do not force-push.
- Do not bypass Fast Gate or Release Gate after relevant changes.
