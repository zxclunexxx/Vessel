import { createClient } from 'npm:@supabase/supabase-js@2';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } });

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
  if (req.method !== 'POST') return json({ error: 'Method not allowed' }, 405);
  try {
    const authHeader = req.headers.get('Authorization');
    if (!authHeader) return json({ error: 'Unauthorized' }, 401);
    const url = Deno.env.get('SUPABASE_URL')!;
    const anon = Deno.env.get('SUPABASE_ANON_KEY')!;
    const service = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const userClient = createClient(url, anon, { global: { headers: { Authorization: authHeader } } });
    const { data: { user }, error: userError } = await userClient.auth.getUser();
    if (userError || !user) return json({ error: 'Unauthorized' }, 401);

    const body = await req.json().catch(() => ({}));
    const username = String(body?.username || '').trim();
    if (username.length < 2 || username.length > 64) return json({ user: null });

    const admin = createClient(url, service, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data, error } = await admin.rpc('vessel_find_profile_exact', { search_username: username });
    if (error) {
      console.error('Exact profile search RPC failed', error);
      return json({ error: 'Не удалось выполнить поиск.' }, 500);
    }
    const profile = Array.isArray(data) ? data[0] : null;
    if (!profile) return json({ user: null });
    if (profile.id === user.id) return json({ user: { ...profile, self: true } });
    return json({ user: profile });
  } catch (error) {
    console.error(error);
    return json({ error: 'Не удалось выполнить поиск.' }, 500);
  }
});
