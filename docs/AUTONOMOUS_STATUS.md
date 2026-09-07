# Vessel autonomous status

Updated: 2026-09-07

## Current runtime

Vessel is running on the authenticated Supabase-backed runtime rather than the old local demo. Mark/Liza/default-message placeholders and fake local runtime data are removed. Runtime smoke checks reject known demo placeholders and blocking browser `prompt()`, `confirm()` and `alert()` flows.

Verified features in code/database:

- Supabase Auth session bootstrap, login/logout and profile loading;
- registration creates the real profile only; it no longer creates the legacy `Мой Vessel` demo/bootstrap server;
- real server memberships, text/voice channels and member roster;
- server create/join/leave/delete, invitation redemption, roles and member removal;
- friend search, requests, accept/decline/cancel, removal and reciprocal pending-request protection;
- direct-message history based on real conversations rather than the current friend list;
- historical DMs remain readable to their participants after unfriend, while new messages/calls are disabled until friendship is restored;
- realtime refresh for social state, DM threads/messages, server memberships, channels, channel messages, profile changes and server rename/icon changes;
- private attachments opened with short-lived signed URLs;
- audio/video DM calling with decline/busy/hangup, mic/camera controls and unanswered-call timeout;
- WebRTC voice rooms with presence/signaling and room switching;
- native Vessel dialogs/toasts, message search, notifications and emoji picker;
- responsive mobile channel drawer;
- latest 100 channel/DM messages loaded in chronological order;
- user-controlled text escaped before insertion into the large HTML template.

## Database and RLS verification

Public Vessel tables keep RLS enabled. Policies continue to enforce participant/friend/server-membership ownership rules instead of widening access to make features work.

Hardening completed on 2026-09-07:

- `friend_requests.sender_id`, `receiver_id` and row identity are immutable to browser clients; authenticated clients can update only `status` and `updated_at`;
- `servers` browser updates are limited to `name` and `icon`;
- `channels` browser updates are limited to `name`, `kind` and `position`;
- `server_members` browser updates are limited to `role`;
- `notifications` browser updates are limited to `read_at`;
- anonymous direct table privileges were removed from the server/channel/member/notification surfaces used only by authenticated runtime;
- untouched auto-generated `Мой Vessel` bootstrap servers were removed, while user-created/used servers were preserved;
- the live `handle_new_user()` trigger now creates only a profile, so future registrations start cleanly with an empty server list.

The live Supabase Security Advisor currently reports only the account-level warning that leaked-password protection is disabled. No RLS policy was weakened during these fixes.

## Build / CI state

Main continues to run the Vessel Quality Gate plus Web, Android APK and Windows EXE workflows on changes. Database changes in this sprint are checked in as migrations under `server/migrations/` so the repository records the live hardening.

## Remaining highest-value work

1. Broader two-client/browser/device verification of friend, realtime DM, attachment and membership race conditions.
2. Call signaling hardening: Realtime Broadcast sender identity is still client-supplied. Move toward a server-verifiable friendship-scoped signaling design.
3. TURN relay support for dependable WebRTC across restrictive NAT/firewall combinations; TURN credentials must never be committed.
4. Voice-channel reconnect/presence testing across abrupt tab/app closes and network loss.
5. Mobile/desktop native permission and lifecycle verification for microphone, camera, background/foreground and app close.
6. Enable Supabase leaked-password protection in Auth settings when account-level configuration is available.

## Repository cleanup

`scripts/autonomous_patch.py` remains the guarded patch path and `scripts/runtime_smoke_check.py` remains the authenticated runtime gate. New database changes should remain mirrored in `server/migrations/` and the schema snapshot should be refreshed by the normal guarded schema-sync path.
