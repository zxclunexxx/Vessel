# Vessel autonomous status

Updated: 2026-09-05

## Current verified runtime

Latest validated application commit: `ce2cccd70946bb12449d239f989ee0265fdd468a`.

This runtime is no longer the old local demo. Authenticated mode is backed by Supabase Auth and database records. The old Mark/Liza/default-message placeholders and fake local servers/channels are removed, and runtime smoke checks now fail if prototype browser `prompt()`, `confirm()` or `alert()` flows return.

Verified features in code/database:

- Supabase session bootstrap and profile loading;
- automatic real profile + starter server creation after signup;
- real server memberships, text/voice channels and member roster;
- server create/join/leave/delete, invitation redemption, roles and member removal;
- friend search, requests, accept/decline, reciprocal friendships and removal;
- direct messages restricted by RLS to friends;
- realtime refresh for social state, DMs, server memberships, channels and channel messages;
- private attachments opened with short-lived signed URLs;
- audio/video DM calling with decline/busy/hangup, mic/camera controls and a 30-second unanswered-call timeout;
- WebRTC voice rooms with presence/signaling and room switching;
- native Vessel dialogs/toasts, message search, notifications and emoji picker;
- responsive mobile channel drawer;
- latest 100 channel/DM messages loaded in chronological order;
- user-controlled text escaped before insertion into the large HTML template.

## Automated verification

The autonomous patch workflow validates generated application changes with:

1. JavaScript syntax check;
2. dependency install;
3. production Vite build;
4. commit only after validation;
5. explicit dispatch of Quality Gate, Web deploy, Android APK and Windows EXE workflows.

For `ce2cccd70946bb12449d239f989ee0265fdd468a` the following completed successfully:

- Vessel Quality Gate;
- GitHub Pages web deployment;
- Android APK build;
- Windows EXE build.

The runtime smoke checker additionally bans known demo placeholders and blocking prototype dialogs and requires the current authenticated social/server/call/mobile primitives to exist.

## Database verification

A rollback-only Supabase smoke test with two temporary users verified:

- 2 auth users produced 2 profiles;
- 2 starter servers were created;
- both owners received owner memberships;
- 4 default channels were created (text + voice for each starter server);
- accepting one friend request created both reciprocal friendship rows;
- the receiver received a notification;
- an authenticated friend could insert/read a DM under RLS;
- a non-friend DM insert was correctly rejected by RLS.

The transaction was rolled back. Production user/profile/message counts remained zero after the test; no test accounts or messages were retained.

Supabase Security Advisor is clean. Foreign-key indexes and several RLS policies were also optimized during this sprint.

## Remaining true end-to-end verification

The production Supabase project currently has no real users. Therefore browser-level A ↔ B verification of signup, friend search, DM realtime, WebRTC calls and voice-room media still requires two genuine accounts to exist. The database-side flow has been smoke-tested without persisting fake production users.

WebRTC currently uses STUN only. A TURN relay will eventually be needed for reliable calls across restrictive NAT/firewall combinations.

## Repository cleanup

Old one-off maintenance/social-upgrade workflows and their patch scripts were removed so they cannot accidentally re-apply obsolete prototype transforms. `scripts/autonomous_patch.py` is the active guarded patch path and `scripts/runtime_smoke_check.py` is the authenticated runtime gate.
