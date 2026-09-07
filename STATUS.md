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

- Commit: `f4f741941ceaf8a9d9a6dfbd833904ebe3708e12`
- Release Gate run: `34154604758`
- Fast Gate: verified green
- Web build/deploy: verified green
- Android debug APK: verified green and artifact uploaded
- Windows portable EXE: verified green and artifact uploaded
- Friends → DM → Realtime resilience batch: merged as PR #3

## Current sprint

Branch: `autonomous/voice-turn-ready-batch`

The current batch hardens voice rooms and direct calls as one transport/recovery unit:

1. Fetch authenticated RTC configuration through the `rtc-config` Edge Function.
2. Keep browser code free of TURN shared secrets and long-lived TURN credentials.
3. Generate short-lived coturn REST credentials when `TURN_URLS` and `TURN_SHARED_SECRET` are configured server-side.
4. Fall back safely to STUN when TURN is not configured or RTC configuration cannot be fetched.
5. Refresh ephemeral RTC configuration before ICE restarts.
6. Attempt voice-peer ICE restart before destroying and recreating the peer connection.
7. Use session-scoped exponential reconnect for call inbox and active call signaling.
8. Accelerate RTC recovery when the browser reports that network connectivity returned.
9. Cancel voice/call reconnect timers and cached RTC configuration on authenticated-session reset.
10. Cover the batch with the dedicated `voice_turn_ready_smoke_check.py` in the centralized Fast Gate suite.

## Current sprint verification

- Staging commit: `e02b1cb808205a8db8014bcb7a4f8a097708c11f`
- Verified generated runtime commit: `e61f91bcb3fffbb89e7c35e149a56d7cb115cfca`
- Autonomous migration application: passed
- Generated Fast Gate suite: passed
- JavaScript syntax: passed
- Dependency audit: passed
- Production build: passed
- A normal Fast Gate is required on the final sprint HEAD before opening the PR.

## Known blockers / external dependencies

- The application is TURN-ready, but actual relay traffic requires external TURN infrastructure plus Edge Function secrets `TURN_URLS` and `TURN_SHARED_SECRET` (optional `TURN_TTL_SECONDS` / `STUN_URLS`).
- No TURN secret or long-lived TURN credential may be committed to the repository or embedded in browser code.
- Supabase Leaked Password Protection is an account/project Auth setting rather than an application-code patch; enabling it must not expose any secrets.

## Safety invariants

- Never expose service-role keys, secret keys, TURN shared secrets, TURN credentials, or private tokens in client code, logs, commits, or artifacts.
- Keep `rtc-config` JWT-protected and authenticated; it does not need service-role access.
- Do not weaken RLS to make a client flow work.
- Do not force-push.
- Do not bypass Fast Gate or Release Gate after relevant changes.
