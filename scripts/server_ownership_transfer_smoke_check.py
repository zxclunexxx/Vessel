from pathlib import Path

schema = Path('server/schema.sql').read_text(encoding='utf-8')
main = Path('src/main.js').read_text(encoding='utf-8')
edge = Path('supabase/functions/transfer-server-ownership/index.ts').read_text(encoding='utf-8')

schema_markers = [
    'create or replace function public.vessel_transfer_server_ownership(target_server uuid, target_owner uuid, actor_user uuid)',
    "set search_path='pg_catalog','public'",
    'for update;',
    'current_owner<>actor_user',
    'where sm.server_id=target_server and sm.user_id=target_owner',
    "when user_id=target_owner then 'owner'",
    "when user_id=current_owner then 'member'",
    'update public.servers',
    'where id=target_server and owner_id=current_owner',
    'revoke all on function public.vessel_transfer_server_ownership(uuid,uuid,uuid) from public,anon,authenticated;',
    'grant execute on function public.vessel_transfer_server_ownership(uuid,uuid,uuid) to service_role;',
]
for marker in schema_markers:
    if marker not in schema:
        raise SystemExit(f'missing ownership transfer schema marker: {marker}')

if 'vessel_transfer_server_ownership(uuid,uuid) to authenticated' in schema:
    raise SystemExit('legacy authenticated ownership transfer RPC grant remains')

ui_markers = [
    'Передать владение сервером',
    "supabase.functions.invoke('transfer-server-ownership'",
    'body:{server_id:serverId,target_owner:memberId}',
    'Ты перестанешь быть владельцем и станешь обычным участником.',
    'window.__vesselServersLoaded=false',
    'syncSupabaseServers(user)',
]
for marker in ui_markers:
    if marker not in main:
        raise SystemExit(f'missing ownership transfer UI marker: {marker}')

edge_markers = [
    "userClient.auth.getUser()",
    "admin.rpc('vessel_transfer_server_ownership'",
    'target_server: serverId',
    'target_owner: targetOwner',
    'actor_user: user.id',
]
for marker in edge_markers:
    if marker not in edge:
        raise SystemExit(f'missing ownership Edge Function marker: {marker}')

# Direct server UPDATE remains unable to assign owner_id to another user.
if 'create policy "owners can update servers" on public.servers for update to authenticated using(owner_id=(select auth.uid())) with check(owner_id=(select auth.uid()));' not in schema:
    raise SystemExit('direct server update policy no longer pins owner_id to the authenticated owner')

print('Server ownership transfer smoke check passed')
