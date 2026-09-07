# Vessel Auth Email / SMTP production setup

Vessel uses Supabase Auth for email/password accounts. Email confirmation remains enabled; the production fix for `email rate limit exceeded` is to use a dedicated SMTP provider instead of relying on Supabase's built-in trial sender.

## Production architecture

1. Browser code calls Supabase Auth with the public project key only.
2. Supabase Auth sends confirmation/recovery messages through a dedicated SMTP provider.
3. SMTP credentials live only in Supabase project configuration under `Authentication > Emails > SMTP Settings`.
4. Vessel frontend, GitHub Actions, APK/EXE bundles and repository files must never contain SMTP credentials.
5. Keep подтверждение email enabled for account security.

Supported provider choices include Resend, Postmark, Brevo, SendGrid and AWS SES. Choose one provider and use a dedicated transactional sender such as `Vessel <no-reply@auth.example.com>` rather than a personal mailbox.

## Required provider-side setup

- Verify the sending domain.
- Publish the provider's SPF record.
- Publish the provider's DKIM records.
- Add a DMARC policy and monitor delivery/reputation.
- Disable marketing/link-tracking features for authentication mail when the provider recommends it.
- Use a dedicated auth sender/domain when possible.

## Supabase configuration

Open the Vessel project and configure the provider in `Authentication > Emails > SMTP Settings` using the host, port, username, sender and password supplied by the SMTP provider.

Security rule: **никогда не хранить SMTP-пароль в `src/`, `.env` фронтенда, GitHub, APK/EXE или документации.** Enter it only into the protected Supabase SMTP settings UI (or an equivalent secret-management path).

After custom SMTP is working, review `Authentication > Rate Limits`. Start conservatively, test delivery and increase limits only for expected real traffic. Custom SMTP removes the very small built-in Supabase email quota, but the provider will still enforce its own limits and reputation rules.

## Abuse protection

Before public launch:

- enable CAPTCHA on signup/sign-in/password-reset flows;
- keep per-client anti-spam/cooldown behavior in Vessel;
- avoid disabling email confirmation to work around rate limits;
- monitor rejected/bounced mail with the SMTP provider;
- keep recovery and confirmation templates short and transactional.

## Test checklist

After SMTP credentials are configured:

1. Register a fresh address.
2. Confirm the email arrives with Vessel sender branding.
3. Open the confirmation link and verify login succeeds.
4. Test password recovery.
5. Repeat with several test users without hitting the old built-in email quota.
6. Confirm no SMTP secret appears in browser DevTools, built assets, APK/EXE or GitHub.
7. Verify incorrect credentials, unconfirmed email and rate-limit errors show localized Vessel messages instead of raw Supabase text.

## Current external dependency

The repository is SMTP-ready, but actual outbound production mail still requires a provider account/domain and its SMTP credentials. Those values are intentionally not committed to Vessel.
