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

- Commit: `b285fc4ba9f01a03ee3e7bc1355e2330473ea4bc`
- Release Gate run: `34161499648`
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
- Live Supabase `rtc-config`: ACTIVE and JWT-protected; real TURN relay still requires external TURN infrastructure and server-side secrets.

## Current sprint

Branch: `autonomous/ui-motion-polish-batch`

UI Batch 4 Motion + Polish unifies Vessel interaction behavior without changing data access, authorization or RTC transport:

1. Add context-aware transitions for channel, DM, Friends and RTC scene changes while avoiding animation on ordinary realtime rerenders.
2. Add transform/opacity entrance motion to headers, content panes, composer and call/voice stages.
3. Standardize hover and press feedback across primary actions, dialogs, attachments, social controls, call controls and utility buttons.
4. Restrict hover-only effects to fine-pointer devices so touch interfaces do not retain sticky hover states.
5. Upgrade modal presentation with a consistent glass highlight, backdrop entrance and spring-like card entrance.
6. Present standard modals as bottom sheets on small mobile screens while leaving the dedicated incoming-call animation isolated.
7. Replace overlapping notices with an accessible stacked toast system supporting info, success and error tones, manual dismiss and a lifetime indicator.
8. Add a real mobile channel-drawer scrim that closes the drawer on tap and keeps body/drawer state synchronized across rerenders.
9. Add safe-area spacing, `100dvh` sizing and larger mobile touch targets.
10. Reduce expensive blur levels on small screens and add paint containment to expensive visual cards/tiles for a lighter rendering budget.
11. Keep new animation transform/opacity oriented and disable Batch 4 motion under `prefers-reduced-motion`.
12. Preserve the exact verified call ICE-recovery markers and all earlier UI batch markers.
13. Extend the centralized Fast Gate from 31 to 32 checks with `ui_motion_polish_smoke_check.py`.

## Current sprint verification

- Autonomous Motion + Polish migration: passed.
- Generated runtime is present in `src/main.js` under `VESSEL_UI_MOTION_POLISH_V1`.
- Generated visual layer is present in `src/style.css` under `VESSEL_UI_MOTION_POLISH_V1`.
- Existing 31 regression checks continue to pass, including social UI, voice/calls UI, voice reconnect, TURN-ready transport, call ICE restart and call-session cleanup.
- Dedicated Motion + Polish regression check passes as part of the 32-check Fast Gate.
- Pre-status sprint HEAD `7bd51edf33bddb73354444481aeec974aabaf618`: Fast Gate success.
- JavaScript syntax: passed.
- Locked dependency install: passed.
- Dependency audit: passed.
- Production build: passed.
- No SQL, RLS, Supabase schema, policy, authentication or authorization changes are part of this batch.
- A final Fast Gate on this status-updated sprint HEAD is required before PR.
- After PR Fast Gate, squash-merge and run exactly one Release Gate for Web, Android APK and Windows EXE.

## Next stage

Full QA and release hardening: two-account social/DM flows, channel/server lifecycle, call/voice recovery, responsive/device validation, artifact installation checks, accessibility pass and final production-readiness cleanup.

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
