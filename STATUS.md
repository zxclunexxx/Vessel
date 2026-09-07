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

- Commit: `45bec0de790de2b5e6493f632ad674728a4a05c2`
- Release Gate run: `34155608303`
- Fast Gate: verified green
- Web build/deploy: verified green
- Android debug APK: verified green and artifact uploaded
- Windows portable EXE: verified green and artifact uploaded
- Friends / DM / realtime resilience: merged
- Voice / calls / reconnect / TURN-ready transport architecture: merged
- Live Supabase `rtc-config`: ACTIVE and JWT-protected; real TURN relay still requires external TURN infrastructure and server-side secrets.

## Current sprint

Branch: `autonomous/ui-foundation-shell-batch`

UI Batch 1 establishes the Vessel visual identity without rewriting authenticated runtime behavior:

1. Dark futuristic liquid-glass design tokens and shared visual constants.
2. Ambient cyan/violet/magenta background lighting with a subtle texture layer.
3. Floating glass shell surfaces for server rail, navigation, workspace and members.
4. Server rail with soft lift/glow states and a luminous selected indicator.
5. Channel navigation with clearer hierarchy, active rail and premium hover states.
6. User card moved visually into the lower navigation flow as a compact dock.
7. Workspace header/action controls, chat surface and composer aligned to the new identity.
8. Auth, dialogs and toasts aligned to the same glass system.
9. Responsive/mobile drawer behavior preserved.
10. Keyboard `:focus-visible` feedback and `prefers-reduced-motion` support.
11. Visual rules documented in `docs/UI_VISUAL_SYSTEM.md`.
12. Dedicated `ui_foundation_shell_smoke_check.py` extends the centralized Fast Gate to 28 checks.

## Current sprint verification

- Functional JavaScript runtime is unchanged by UI Batch 1.
- Generated `src/style.css` foundation is present as an isolated `VESSEL_UI_FOUNDATION_SHELL_V1` override layer.
- Autonomous migration application: passed.
- Fast Gate smoke suite: passed.
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

- Actual TURN relay traffic requires external TURN infrastructure plus Edge Function secrets `TURN_URLS` and `TURN_SHARED_SECRET` (optional `TURN_TTL_SECONDS` / `STUN_URLS`).
- No TURN secret or long-lived TURN credential may be committed to the repository or embedded in browser code.
- Supabase Leaked Password Protection is an account/project Auth setting rather than an application-code patch; enabling it must not expose any secrets.

## Safety invariants

- Never expose service-role keys, secret keys, TURN shared secrets, TURN credentials, or private tokens in client code, logs, commits, or artifacts.
- Keep `rtc-config` JWT-protected and authenticated; it does not need service-role access.
- Do not weaken RLS to make a client flow work.
- Do not force-push.
- Do not bypass Fast Gate or Release Gate after relevant changes.
