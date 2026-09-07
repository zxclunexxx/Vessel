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

- Commit: `2bb0a6d8cd277cea0ed3fa1e876fda7085310501`
- Release Gate run: `34159153052`
- Fast Gate: verified green
- Web build/deploy: verified green
- Android debug APK: verified green and artifact uploaded
- Windows portable EXE: verified green and artifact uploaded
- Friends / DM / realtime resilience: merged
- Voice / calls / reconnect / TURN-ready transport architecture: merged
- UI Batch 1 liquid-glass foundation: merged as PR #5
- Auth email rate-limit resilience + production SMTP guide: merged as PR #6
- Live Supabase `rtc-config`: ACTIVE and JWT-protected; real TURN relay still requires external TURN infrastructure and server-side secrets.

## Current sprint

Branch: `autonomous/ui-messaging-social-batch`

UI Batch 2 deepens the visual system without changing database access or social authorization rules:

1. Upgrade Direct Message rows into compact identity cards with avatars, presence dots, status copy, selected-state depth and unread glow.
2. Add loading skeletons and a designed empty state for the DM list.
3. Turn the Friends page into a Vessel Social hub with ambient glass hero, friend/incoming/outgoing counters and a premium add-friend action.
4. Restyle friends into floating glass cards with online/away/DND/offline presence indicators.
5. Give incoming requests a warm signal accent and outgoing requests a violet pending accent.
6. Standardize friend message/call/accept/remove controls as compact interactive action buttons.
7. Add designed social loading skeletons and a first-use empty state.
8. Give messages semantic `mine` styling while preserving existing mutation permissions and security checks.
9. Improve message hover depth, avatar treatment, hidden-until-hover actions and attachment chips.
10. Enhance the composer with a restrained ambient focus glow and gradient send control.
11. Keep all animations transform/opacity-oriented and disable repeating social/unread animations under `prefers-reduced-motion`.
12. Extend the centralized Fast Gate from 29 to 30 checks with `ui_messaging_social_smoke_check.py`.

## Current sprint verification

- Autonomous visual migration: passed.
- Generated runtime/UI is present in `src/main.js` and `src/style.css`.
- `VESSEL_UI_MESSAGING_SOCIAL_V1` is isolated on top of the existing visual foundation.
- 30-check Fast Gate smoke suite: passed on sprint HEAD before this status-only commit.
- JavaScript syntax: passed.
- Dependency audit: passed.
- Production build: passed.
- No SQL, RLS or Supabase schema changes are part of this batch.
- A final Fast Gate on the status-updated sprint HEAD is required before PR.
- After PR Fast Gate, squash-merge and run exactly one Release Gate for Web, Android APK and Windows EXE.

## Next UI batches

1. Voice + Calls: participant cards, speaking indicators, audio/video stages, reconnect banners and floating call controls.
2. Motion + Polish: transitions, microinteractions, ambient motion, modal/toast polish, mobile refinement, reduced-motion validation and performance cleanup.

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
