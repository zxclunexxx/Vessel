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

- Commit: `a65d0f499f8519dd1c787fa5fbe3f133c7ac6668`
- Release Gate run: `34162533485`
- Fast Gate: verified green
- Web build/deploy: verified green
- Android debug APK: verified green and artifact uploaded
- Windows portable EXE: verified green and artifact uploaded
- Friends / DM / realtime resilience: merged
- Voice / calls / reconnect / TURN-ready transport architecture: merged
- UI Batch 1 liquid-glass foundation: merged as PR #5
- Auth email rate-limit resilience + production SMTP guide: merged as PR #6
- UI Batch 2 Messaging + Social: merged as PR #7
- UI Batch 3 Voice + Calls: merged as PR #8
- UI Batch 4 Motion + Polish: merged as PR #9
- Live Supabase `rtc-config`: ACTIVE and JWT-protected; real TURN relay still requires external TURN infrastructure and server-side secrets.

## Current sprint

Branch: `autonomous/full-qa-hardening`

Full QA & Release Hardening focuses on defects that appear at lifecycle, mobile, accessibility and release boundaries without changing backend authorization:

1. Correct offline presence copy so `offline` / `не в сети` no longer renders as `В сети`.
2. Harden logout, account-switch and failed-auth cleanup by stopping Web Audio speaking meters, call-duration UI timers and the RTC visual runtime ticker.
3. Upgrade custom prompt/choice/confirm dialogs with `role=dialog`, `aria-modal`, universal Escape close, initial focus and focus restoration.
4. Apply the same Escape, outside-click and focus-return lifecycle to the profile settings modal.
5. Route channel/notification mobile navigation through one drawer-close function so the scrim and `body.mobile-drawer-open` state cannot remain stale after navigation.
6. Clear drawer body/scrim state at render boundaries because render reconstructs the shell and implicitly closes the drawer.
7. Replace the permanent global 500 ms RTC polling loop with a dynamic ticker that only exists while call/voice/reconnect runtime is active.
8. Remove duplicate render cleanup introduced while hardening the drawer lifecycle.
9. Preserve Electron release security invariants: context isolation, disabled Node integration, sandboxing, HTTPS-only external navigation and explicit permission handlers.
10. Extend the centralized Fast Gate from 32 to 33 checks with `full_qa_hardening_smoke_check.py`.

## Current sprint verification

- First hardening batch: Fast Gate run `34163602290` passed with 33 checks, JavaScript syntax, locked dependency install, dependency audit and production build.
- Interaction/performance generated runtime: autonomous verifier run `34163819717` passed before bot commit.
- Final cleanup generated runtime: autonomous verifier run `34163968391` passed before bot commit `c2f35168d8fe631c1ebf2259a24d4afc3e528980`.
- Dedicated hardening regression coverage checks runtime cleanup, dialog accessibility, mobile drawer lifecycle, idle RTC polling removal and Electron security invariants.
- Existing social, DM, server, attachment, notification, voice reconnect, TURN-ready, call ICE restart, call-session cleanup and all four UI batch regression checks remain in the same Fast Gate suite.
- No SQL, RLS, Supabase schema, policy, authentication or authorization changes are part of this sprint.
- No service-role key, SMTP password, TURN shared secret or long-lived TURN credential is present in client runtime.
- A final Fast Gate on the status-updated sprint HEAD is required before PR.
- After PR Fast Gate, squash-merge and run exactly one Release Gate for Web, Android APK and Windows EXE.

## Remaining release QA / external validation

- Real two-account end-to-end interaction still needs an actual two-session/device pass for friend request/accept/remove, DM send/read/reload, server membership/channel flows and realtime convergence.
- Physical APK/EXE installation and microphone/camera permission behavior still need device-level validation after the final Release Gate artifacts are produced.
- Actual TURN relay traffic cannot be claimed as tested until external TURN infrastructure and server-side credentials are available.
- The web entrypoint still loads Supabase JS from a major-version CDN URL (`@supabase/supabase-js@2`); bundling or exact pin/SRI is a remaining supply-chain hardening follow-up and has not been changed in this sprint.

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
