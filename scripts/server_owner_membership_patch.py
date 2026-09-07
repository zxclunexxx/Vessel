from pathlib import Path

path = Path('server/schema.sql')
schema = path.read_text(encoding='utf-8')

old = '''create policy "members can leave or owners can remove" on public.server_members for delete to authenticated using(
  user_id=(select auth.uid()) or exists(select 1 from public.servers s where s.id=server_members.server_id and s.owner_id=(select auth.uid()) and server_members.user_id<>s.owner_id)
);'''
new = '''create policy "members can leave or owners can remove" on public.server_members for delete to authenticated using(
  (
    user_id=(select auth.uid())
    and not exists(
      select 1 from public.servers s
      where s.id=server_members.server_id and s.owner_id=(select auth.uid())
    )
  )
  or exists(
    select 1 from public.servers s
    where s.id=server_members.server_id
      and s.owner_id=(select auth.uid())
      and server_members.user_id<>s.owner_id
  )
);'''

if new in schema:
    print('Server owner membership delete guard already present')
elif old in schema:
    path.write_text(schema.replace(old, new, 1), encoding='utf-8')
    print('Protected server owner membership from direct deletion')
else:
    raise SystemExit('Server membership delete policy shape changed; inspect before patching')
