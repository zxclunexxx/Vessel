from pathlib import Path

schema = Path('server/schema.sql').read_text(encoding='utf-8')
main = Path('src/main.js').read_text(encoding='utf-8')

schema_markers = [
    'create or replace function public.vessel_transfer_server_ownership',
    "set search_path='pg_catalog','public'",
    'for update;',
    'current_owner<>(select auth.uid())',
    'where sm.server_id=target_server and sm.user_id=target_owner',
    "when user_id=target_owner then 'owner'",
    "when user_id=current_owner then 'member'",
    'update public.servers',
    'where id=target_server and owner_id=current_owner',
    'grant execute on function public.vessel_transfer_server_ownership(uuid,uuid) to authenticated,service_role;',
]
for marker in schema_markers:
    if marker not in schema:
        raise SystemExit(f'missing ownership transfer schema marker: {marker}')

ui_markers = [
    'Передать владение сервером',
    "supabase.rpc('vessel_transfer_server_ownership'",
    'target_server:serverId,target_owner:memberId',
    'Ты перестанешь быть владельцем и станешь обычным участником.',
    'window.__vesselServersLoaded=false',
    'syncSupabaseServers(user)',
]
for marker in ui_markers:
    if marker not in main:
        raise SystemExit(f'missing ownership transfer UI marker: {marker}')

# Ownership must not be changed through an ordinary browser UPDATE policy.
if 'create policy "owners can update servers" on public.servers for update to authenticated using(owner_id=(select auth.uid())) with check(owner_id=(select auth.uid()));' not in schema:
    raise SystemExit('direct server update policy no longer pins owner_id to the authenticated owner')

print('Server ownership transfer smoke check passed')
