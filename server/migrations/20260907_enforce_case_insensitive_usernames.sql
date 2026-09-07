-- Friend search is case-insensitive, so usernames must be unique under the same normalization.
create unique index if not exists profiles_username_lower_unique
on public.profiles (lower(btrim(username)));
