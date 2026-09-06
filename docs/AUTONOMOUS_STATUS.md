# Vessel autonomous status

Updated: 2026-09-06

## Current verified runtime

Latest application commit validated by the autonomous production-build path: `962941d102323fa478262914002e6207a572a0bd`.

Vessel is running on the authenticated Supabase-backed runtime rather than the old local demo. Mark/Liza/default-message placeholders and fake local servers/channels are removed. Runtime smoke checks reject known demo placeholders and blocking browser `prompt()`, `confirm()` and `alert()` flows.

Verified features in code/database:

- Supabase Auth session bootstrap and profile loading;
- automatic real profile + starter server creation after signup;
- real server memberships, text/voice channels and member roster;
- server create/join/leave/delete, invitation redemption, roles and member removal;
- friend search, requests, accept/decline, removal and database-level protection against reciprocal pending-request races;
- direct-message history based on real conversations rather than the current friend list;
- historical DMs remain readable to their participants after unfriend, while new messages/calls are disabled until friendship is restored;
- realtime refresh for social state, DM threads/messages, server memberships, channels, channel messages, profile changes and server rename/icon changes;
- private attachments opened with short-lived signed URLs;
- audio/video DM calling with decline/busy/hangup, mic/camera controls and a 30-second unanswered-call timeout;
- WebRTC voice rooms with presence/signaling and room switching;
- native Vessel dialogs/toasts, message search, notifications and emoji picker;
- responsive mobile channel drawer;
- latest 100 channel/DM messages loaded in chronological order;
- user-controlled text escaped before insertion into the large HTML template;
- profile writes use the database-confirmed result and report duplicate usernames clearly.

## Automated verification

The autonomous patch workflow is idempotent and validates generated application/schema changes with:

1. patch application;
2. JavaScript syntax check;
3. dependency install;
4. production Vite build;
5. commit only after validation;
6. explicit dispatch of Quality Gate, Web deploy, Android APK and Windows EXE workflows.

For `962941d102323fa478262914002e6207a572a0bd`, the autonomous production build completed successfully and the Vessel Quality Gate also completed successfully, including the authenticated runtime smoke check, JavaScript syntax check and production build. Web/APK/EXE distributable workflows were dispatched for the same commit.

## Database and RLS verification

Public Vessel tables keep RLS enabled. Existing policies continue to enforce participant/friend/server-membership ownership rules instead of widening access to make features work.

Additional hardening completed in this sprint:

- a symmetric partial unique index prevents two opposite pending friend requests for the same pair;
- `vessel_dm_threads()` returns only the safe peer fields needed for conversation discovery and scopes results to `auth.uid()`;
- anonymous EXECUTE permission on that SECURITY DEFINER RPC is explicitly revoked;
- the checked-in `server/schema.sql` snapshot is updated by the same verified autonomous path as application changes.

The latest Security Advisor check no longer reports anonymous access to `vessel_dm_threads()`. Its remaining function warning is the intentional authenticated EXECUTE permission needed by signed-in clients. Supabase Auth leaked-password protection is still disabled and should be enabled as an account-level hardening step.

## Remaining true end-to-end work

The production project now contains real application data, so database-backed social and DM flows are no longer purely prototype paths. The next highest-value work is broader two-client/browser/device verification of realtime edge cases and call lifecycle behavior.

WebRTC currently uses a public STUN server only. A TURN relay is still required for dependable calls/voice across restrictive NAT and firewall combinations; TURN credentials must not be hard-coded or committed.

Call signaling currently uses Supabase Realtime Broadcast. Busy/decline/hangup/reconnect cleanup exists, but sender identity in Broadcast payloads is still client-supplied. Further hardening should move call authorization/signaling toward a server-verifiable, friendship-scoped design rather than trusting payload identity.

## Repository cleanup

Old one-off maintenance/social-upgrade workflows and obsolete prototype patch paths are not used for current changes. `scripts/autonomous_patch.py` is the active guarded patch path and `scripts/runtime_smoke_check.py` is the authenticated runtime gate.
