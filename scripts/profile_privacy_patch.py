from pathlib import Path

main_path = Path('src/main.js')
schema_path = Path('server/schema.sql')
text = main_path.read_text(encoding='utf-8')
schema = schema_path.read_text(encoding='utf-8')
changed = False


def replace_main_once(old, new, label):
    global text, changed
    if new in text:
        return
    if old not in text:
        raise SystemExit(f'{label} anchor not found')
    text = text.replace(old, new, 1)
    changed = True


# Email belongs to Supabase Auth. The public profile row should only carry social/display data.
replace_main_once(
    "const {data: profile, error: profileError} = await supabase.from('profiles').select('id,username,email,status,avatar_color').eq('id', authUser.id).maybeSingle();",
    "const {data: profile, error: profileError} = await supabase.from('profiles').select('id,username,status,avatar_color').eq('id', authUser.id).maybeSingle();",
    'profile bootstrap email select',
)
replace_main_once(
    "    email: profile?.email || authUser.email || '',",
    "    email: authUser.email || '',",
    'profile bootstrap auth email',
)

# Explicit column grants complement RLS: related users may read display fields, but never email.
privileges = """

-- Column-level profile privacy --------------------------------------------------
-- RLS controls which profile rows an authenticated user may see. Column grants additionally
-- ensure related users cannot query private Auth-facing fields such as email from those rows.
revoke all on table public.profiles from anon, authenticated;
grant select (id, username, avatar_color, status, created_at) on table public.profiles to authenticated;
grant update (username, avatar_color, status) on table public.profiles to authenticated;
"""
marker = 'grant select (id, username, avatar_color, status, created_at) on table public.profiles to authenticated;'
if marker not in schema:
    rls_anchor = "alter table public.notifications enable row level security;\n"
    if rls_anchor not in schema:
        raise SystemExit('profile privilege schema anchor not found')
    schema = schema.replace(rls_anchor, rls_anchor + privileges, 1)
    changed = True

for required in [
    ".select('id,username,status,avatar_color').eq('id', authUser.id).maybeSingle()",
    "email: authUser.email || ''",
]:
    if required not in text:
        raise SystemExit(f'missing profile privacy marker: {required}')
for required in [
    'revoke all on table public.profiles from anon, authenticated;',
    marker,
    'grant update (username, avatar_color, status) on table public.profiles to authenticated;',
]:
    if required not in schema:
        raise SystemExit(f'missing profile privilege marker: {required}')

if changed:
    main_path.write_text(text, encoding='utf-8')
    schema_path.write_text(schema, encoding='utf-8')
    print('Applied Vessel profile email privacy hardening')
else:
    print('Vessel profile email privacy hardening already applied; nothing to change')
