from pathlib import Path

text = Path('server/schema.sql').read_text(encoding='utf-8')
start = text.find('create or replace function public.handle_new_user()')
end = text.find('-- Every real server receives its owner membership', start)
if start < 0 or end < 0:
    raise SystemExit('handle_new_user bootstrap function not found')
block = text[start:end]
if 'insert into public.profiles' not in block:
    raise SystemExit('handle_new_user no longer creates profile')
if 'insert into public.servers' in block:
    raise SystemExit('Fresh bootstrap still creates an implicit starter server')
if 'Profile is created from a real Auth user; servers are explicit user actions.' not in text:
    raise SystemExit('Explicit server bootstrap contract marker missing')
print('Fresh bootstrap server behavior matches production')
