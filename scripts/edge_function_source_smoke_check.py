from pathlib import Path

schema = Path('server/schema.sql').read_text(encoding='utf-8')
functions = {
    'join-server': ('vessel_redeem_server_invite',),
    'search-user': ('vessel_find_profile_exact',),
    'transfer-server-ownership': ('vessel_transfer_server_ownership',),
}
for slug, rpc_names in functions.items():
    path = Path('server/functions') / slug / 'index.ts'
    if not path.exists():
        raise SystemExit(f'Missing versioned Edge Function source: {slug}')
    text = path.read_text(encoding='utf-8')
    required = [
        "req.headers.get('Authorization')",
        'userClient.auth.getUser()',
        "Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')",
        'persistSession: false',
        'autoRefreshToken: false',
    ] + list(rpc_names)
    missing = [marker for marker in required if marker not in text]
    if missing:
        raise SystemExit(f'{slug} missing security markers: ' + ', '.join(missing))

schema_requirements = [
    'revoke all on function public.vessel_redeem_server_invite(text,uuid) from public,anon,authenticated;',
    'grant execute on function public.vessel_redeem_server_invite(text,uuid) to service_role;',
    'revoke all on function public.vessel_find_profile_exact(text) from public,anon,authenticated;',
    'grant execute on function public.vessel_find_profile_exact(text) to service_role;',
    'revoke all on function public.vessel_transfer_server_ownership(uuid,uuid,uuid) from public,anon,authenticated;',
    'grant execute on function public.vessel_transfer_server_ownership(uuid,uuid,uuid) to service_role;',
]
missing_schema = [marker for marker in schema_requirements if marker not in schema]
if missing_schema:
    raise SystemExit('Missing service-role RPC grants: ' + ', '.join(missing_schema))

print('Privileged Edge Function sources and RPC boundaries are versioned')
