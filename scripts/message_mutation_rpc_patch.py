from pathlib import Path

schema_path = Path('server/schema.sql')
schema = schema_path.read_text(encoding='utf-8')

required_rpc = 'create or replace function public.vessel_dm_threads()'
old_filter = """    where auth.uid() is not null
      and (dm.sender_id = auth.uid() or dm.receiver_id = auth.uid())
"""
new_filter = """    where auth.uid() is not null
      and dm.deleted_at is null
      and (dm.sender_id = auth.uid() or dm.receiver_id = auth.uid())
"""

if required_rpc not in schema:
    print('DM thread RPC is not present yet; message_mutation_patch.py will create it')
    raise SystemExit(0)

if 'dm.deleted_at is null' in schema:
    print('DM thread RPC deleted-message filter already applied; nothing to change')
    raise SystemExit(0)

if old_filter not in schema:
    raise SystemExit('DM thread RPC exists but its participant filter has unexpected drift')

schema = schema.replace(old_filter, new_filter, 1)
schema_path.write_text(schema, encoding='utf-8')
print('Updated existing DM thread RPC to exclude deleted messages')
