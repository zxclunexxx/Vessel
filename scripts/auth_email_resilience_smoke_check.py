from pathlib import Path

main = Path('src/main.js').read_text(encoding='utf-8')
doc = Path('docs/AUTH_EMAIL_SMTP.md').read_text(encoding='utf-8') if Path('docs/AUTH_EMAIL_SMTP.md').is_file() else ''

required = [
    '/* VESSEL_AUTH_EMAIL_RESILIENCE_V1 */',
    "code==='over_email_send_rate_limit'",
    "message.includes('email rate limit')",
    'signupEmailCooldownUntil',
    'remainingSignupEmailCooldownSeconds()',
    'refreshAuthSubmitAvailability(form)',
    "submit.textContent=`Повторить через ${remaining} с`;",
    "vesselNotice(feedback.message,'error');",
    "if(mode==='signup')refreshAuthSubmitAvailability(form);",
    'refreshAuthSubmitAvailability(authForm);',
]
missing=[item for item in required if item not in main]
if missing:
    raise SystemExit('Missing auth email resilience behavior: '+', '.join(missing))

forbidden = [
    "vesselNotice(error?.message || 'Не удалось выполнить авторизацию.','error');",
    'SUPABASE_SERVICE_ROLE_KEY',
    'SMTP_PASSWORD=',
]
violations=[item for item in forbidden if item in main]
if violations:
    raise SystemExit('Unsafe/legacy auth behavior remains: '+', '.join(violations))

if not doc:
    raise SystemExit('Missing docs/AUTH_EMAIL_SMTP.md')
for marker in [
    'Authentication > Emails > SMTP Settings',
    'SPF',
    'DKIM',
    'DMARC',
    'никогда не хранить SMTP-пароль',
    'подтверждение email',
]:
    if marker not in doc:
        raise SystemExit('SMTP production guide is missing marker: '+marker)

if 'smtp_pass:' in doc.lower() or 'smtp_password=' in doc.lower():
    raise SystemExit('SMTP guide must not contain credential-shaped secret examples')

print('Vessel auth email resilience smoke check passed')
