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

- Commit: `d1c4d0899fa182e780e3fae06e2827cefdedee83`
- Release Gate run: `34164260211`
- Fast Gate: verified green with 33 smoke checks
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
- Full QA & Release Hardening: merged as PR #10
- Live Supabase `rtc-config`: ACTIVE and JWT-protected; real TURN relay still requires external TURN infrastructure and server-side secrets.

## Current sprint

Branch: `autonomous/release-candidate-integrity`

Release Candidate Integrity turns artifact assumptions into explicit, machine-readable release facts without changing application authorization or backend data access:

1. Pin the browser Supabase SDK to an exact semantic version instead of the floating `@2` CDN range.
2. Add SHA-256 generation for the Android APK artifact.
3. Add Android artifact metadata that explicitly records `build_variant=debug`, Android debug signing, and `production_ready=false`.
4. Add SHA-256 generation for the Windows portable EXE.
5. Inspect Windows Authenticode status during CI and record it in artifact metadata.
6. Derive the Windows `production_ready` field from actual Authenticode validation instead of assuming a successful build is a signed release.
7. Package integrity/signing metadata together with each APK/EXE artifact.
8. Extend the centralized Fast Gate from 33 to 34 checks with `release_candidate_integrity_smoke_check.py`.

## Release Candidate artifact audit

The artifacts from Release Gate `34164260211` were downloaded and inspected directly:

- `app-debug.apk` is a valid Android APK, contains an APK signing block and the expected Capacitor/Vessel web payload.
- APK SHA-256: `1e6c7005fcb9a9970224c8176d8b24c72950db0f7059280518636a32a0b7dcd4`.
- APK signer is `CN=Android Debug, O=Android, C=US`; this is a debug/test certificate, not a production distribution identity.
- `Vessel 0.1.0.exe` is a valid Windows PE GUI executable packaged as a Nullsoft Installer self-extracting archive.
- EXE SHA-256: `048ced0101d7ab5222617e70ac4c0860387f3f4387b5364d287606df2d177621`.
- The current EXE has no PE Security Directory / Authenticode signature, so it must not be described as a signed production binary.
- The deployed GitHub Pages artifact contains `index.html`, one JS bundle and one CSS bundle.
- The Pages JS/CSS bundles are byte-for-byte identical to the JS/CSS bundles embedded in the APK, confirming the web and Android clients were built from the same release payload.

## Remaining release QA / external validation

- Real two-account end-to-end interaction still needs an actual two-session/device pass for friend request/accept/remove, DM send/read/reload, server membership/channel flows and realtime convergence.
- Physical APK/EXE installation and microphone/camera permission behavior still need device-level validation.
- A production Android release requires a private release keystore/certificate. The current APK is deliberately identified as debug and must not be represented as store/production signed.
- A production Windows release requires an Authenticode code-signing certificate. The current EXE is unsigned and must not be represented as a signed installer/executable.
- Actual TURN relay traffic cannot be claimed as tested until external TURN infrastructure and server-side credentials are available.
- Automated browser/device navigation is constrained in the current execution environment, so responsive runtime behavior still needs a real browser/device pass even though static/runtime smoke coverage is green.

## Known blockers / external dependencies

- Production auth email still requires an external SMTP provider account/domain and its SMTP credentials configured in Supabase. Those secrets must not be committed to Vessel.
- The built-in Supabase Auth email sender is suitable only for limited testing and can return `email rate limit exceeded` under repeated signup/recovery traffic.
- Actual TURN relay traffic requires external TURN infrastructure plus Edge Function secrets `TURN_URLS` and `TURN_SHARED_SECRET` (optional `TURN_TTL_SECONDS` / `STUN_URLS`).
- Android production signing requires a private keystore and passwords stored as repository/environment secrets, never committed to source.
- Windows production signing requires a code-signing certificate/private key stored as repository/environment secrets or a secure external signing service.
- No TURN secret, release signing private key, SMTP password, service-role key, or long-lived credential may be committed to the repository or embedded in client code.
- Supabase Leaked Password Protection is an account/project Auth setting rather than an application-code patch; enabling it must not expose any secrets.

## Safety invariants

- Never expose service-role keys, secret keys, SMTP passwords, TURN shared secrets, TURN credentials, release signing private keys, or private tokens in client code, logs, commits, or artifacts.
- Keep email confirmations enabled for production accounts.
- Keep `rtc-config` JWT-protected and authenticated; it does not need service-role access.
- Do not weaken RLS to make a client flow work.
- Do not force-push.
- Do not bypass Fast Gate or Release Gate after relevant changes.
