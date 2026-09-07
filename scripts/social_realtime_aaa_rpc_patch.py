from pathlib import Path

path = Path('server/schema.sql')
text = path.read_text(encoding='utf-8')
start = text.find('create or replace function public.vessel_dm_threads()')
if start < 0:
    raise SystemExit('vessel_dm_threads bootstrap RPC not found')
end_marker = 'grant execute on function public.vessel_dm_threads() to authenticated;'
end = text.find(end_marker, start)
if end < 0:
    raise SystemExit('vessel_dm_threads authenticated grant not found')
end += len(end_marker)
block = text[start:end]

if 'security definer' in block.lower():
    raise SystemExit('vessel_dm_threads must never be SECURITY DEFINER')
if 'security invoker' not in block.lower():
    raise SystemExit('vessel_dm_threads must remain SECURITY INVOKER')

changed = False
if "set search_path='pg_catalog','public'" not in block:
    if 'set search_path = public' not in block:
        raise SystemExit('unexpected vessel_dm_threads search_path')
    block = block.replace('set search_path = public', "set search_path='pg_catalog','public'", 1)
    changed = True

combined = 'revoke all on function public.vessel_dm_threads() from public,anon;'
if combined not in block:
    split = 'revoke all on function public.vessel_dm_threads() from public;\nrevoke execute on function public.vessel_dm_threads() from anon;'
    if split not in block:
        raise SystemExit('unexpected vessel_dm_threads revoke grants')
    block = block.replace(split, combined, 1)
    changed = True

if changed:
    text = text[:start] + block + text[end:]
    path.write_text(text, encoding='utf-8')
    print('Aligned bootstrap DM-thread RPC with production security settings')
else:
    print('Bootstrap DM-thread RPC security already aligned')
