# Vessel release readiness

## Current development mode

Vessel uses batched autonomous sprint branches instead of treating every small fix as a release.

- Development branches: `autonomous/**`
- Every sprint commit: `Vessel Fast Gate`
- Pull requests to `main`: `Vessel Fast Gate`
- Merge/push to `main`: `Vessel Release Gate`
- Release Gate runs Fast Gate first, then Web, Android APK, and Windows EXE in parallel.
- Autonomous patching is restricted to `autonomous/**` and never force-pushes.

## Last known stable main

- Commit: `72a407597bee3b390f3c279a0527cedc511f6ecb`
- Quality Gate: previously verified green
- Web: previously verified green
- Android APK: previously verified green
- Windows EXE: previously verified green

## Current sprint priorities

1. Stabilize autonomous patch pipeline and direct-call ICE reconnect.
2. Verify friends, DM lifecycle, and private Realtime behavior between real accounts.
3. Harden calls/voice reconnect and keep the transport TURN-ready without embedding credentials.
4. Run mobile and desktop reliability passes.
5. Final RLS/security and UX QA.
6. Merge a verified batch to `main` and require the full Release Gate.

## Known blockers / external dependencies

- Production TURN requires external TURN infrastructure and credentials. The code should remain configurable and credential-free in the repository.
- Supabase Leaked Password Protection is an account/project Auth setting rather than an application-code patch; enabling it must not expose any secrets.

## Safety invariants

- Never expose service-role keys, secret keys, TURN credentials, or private tokens in client code, logs, commits, or artifacts.
- Do not weaken RLS to make a client flow work.
- Do not force-push.
- Do not bypass Fast Gate or Release Gate after relevant changes.
