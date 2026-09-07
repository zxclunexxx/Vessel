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

- Commit: `327527a8b8707b88297ff526c413d9f90ec03d31`
- Release Gate run: `34159920341`
- Fast Gate: verified green
- Web build/deploy: verified green
- Android debug APK: verified green and artifact uploaded
- Windows portable EXE: verified green and artifact uploaded
- Friends / DM / realtime resilience: merged
- Voice / calls / reconnect / TURN-ready transport architecture: merged
- UI Batch 1 liquid-glass foundation: merged as PR #5
- Auth email rate-limit resilience + production SMTP guide: merged as PR #6
- UI Batch 2 Messaging + Social: merged as PR #7
- Live Supabase `rtc-config`: ACTIVE and JWT-protected; real TURN relay still requires external TURN infrastructure and server-side secrets.

## Current sprint

Branch: `autonomous/ui-voice-calls-batch-v2`

UI Batch 3 redesigns Voice + Calls while preserving the verified WebRTC signaling, ICE recovery and authorization boundaries:

1. Replace the old inline call controls with dedicated immersive audio-call, video-call and voice-room stages.
2. Add a floating glass control dock while preserving the existing call/voice action IDs and handlers.
3. Add a focused audio-call scene with participant avatar, ambient orbits, waveform motion and self microphone state.
4. Add a full central video-call stage with a large remote video tile, participant fallback and mirrored local preview with camera-off fallback.
5. Add a live call duration timer and connection-state labels for calling, connecting, connected and reconnecting states.
6. Surface reconnect banners by observing the existing call/voice recovery state instead of modifying the verified recovery state machine.
7. Upgrade voice rooms with participant cards, empty state, join/leave controls and dedicated microphone/deafen treatment.
8. Add client-side speaking detection with Web Audio `AnalyserNode`; active speakers receive presence glow and level animation without recording or uploading analyser data.
9. Redesign the incoming-call modal with call type, animated orbit/wave treatment and preserved accept/reject actions.
10. Add mobile layouts and `prefers-reduced-motion` fallbacks for stage, speaking, incoming-call and reconnect motion.
11. Preserve the single `#join-voice` source-control invariant used by the existing voice-controls regression guard.
12. Keep the exact verified call ICE-restart handler markers unchanged.
13. Extend the centralized Fast Gate from 30 to 31 checks with `ui_voice_calls_smoke_check.py`.

## Current sprint verification

- Autonomous runtime migration: passed.
- Autonomous style migration: passed.
- Generated Voice + Calls runtime is present in `src/main.js` under `VESSEL_UI_VOICE_CALLS_V1`.
- Generated Voice + Calls visual layer is present in `src/style.css` under `VESSEL_UI_VOICE_CALLS_V1`.
- Existing 30 regression checks continue to pass, including voice controls, voice peer reconnect, TURN-ready transport, call ICE restart and call-session cleanup.
- Dedicated Voice + Calls visual regression check passes as part of the 31-check Fast Gate.
- Final pre-status sprint HEAD `503a6aa11d66f5b4df8307ee2544a2f226c80519`: Fast Gate success.
- JavaScript syntax: passed.
- Dependency audit: passed.
- Production build: passed.
- No SQL, RLS, Supabase schema or policy changes are part of this batch.
- A final Fast Gate on this status-updated sprint HEAD is required before PR.
- After PR Fast Gate, squash-merge and run exactly one Release Gate for Web, Android APK and Windows EXE.

## Next UI batch

Motion + Polish: transitions, microinteractions, ambient motion, modal/toast polish, mobile refinement, reduced-motion validation and performance cleanup.

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
