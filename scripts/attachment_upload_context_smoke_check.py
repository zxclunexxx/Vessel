from pathlib import Path

schema = Path('server/schema.sql').read_text(encoding='utf-8')
migration = Path('server/migrations/20260907_harden_attachment_upload_context.sql').read_text(encoding='utf-8')
main = Path('src/main.js').read_text(encoding='utf-8')

schema_required = [
    'create or replace function private.can_upload_vessel_file(object_name text)',
    "parts[1]<>uid::text",
    "parts[2]='dm'",
    'f.user_id=uid and f.friend_id=peer_uuid',
    "parts[2]='channel'",
    "c.kind='text'",
    'private.can_upload_vessel_file(name)',
    'revoke all on function private.can_upload_vessel_file(text) from public,anon;',
]
for marker in schema_required:
    if marker not in schema:
        raise SystemExit(f'Bootstrap attachment upload context guard missing: {marker}')

migration_required = [
    'create or replace function private.can_upload_vessel_file(object_name text)',
    "where f.user_id=uid and f.friend_id=peer_uuid",
    "and c.kind='text'",
    'drop policy if exists "users upload vessel files" on storage.objects;',
    "with check(bucket_id='vessel-files' and private.can_upload_vessel_file(name));",
]
for marker in migration_required:
    if marker not in migration:
        raise SystemExit(f'Attachment upload context migration missing: {marker}')

client_required = [
    "if(!/^(dm|channel)\\/[^/]+$/.test(storageContext))",
    'const objectPath=`${user.id}/${storageContext}/${crypto.randomUUID()}-${safeName}`;',
    "supabase.storage.from('vessel-files').upload(objectPath,file",
]
for marker in client_required:
    if marker not in main:
        raise SystemExit(f'Attachment client context guard missing: {marker}')

legacy = "with check(bucket_id='vessel-files' and (storage.foldername(name))[1]=(select auth.uid())::text);"
if legacy in schema:
    raise SystemExit('Legacy owner-prefix-only storage upload policy remains')

print('Vessel attachment upload context security smoke check passed')
