import { createClient } from 'npm:@supabase/supabase-js@2';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } });
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

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
    const serverId = String(body?.server_id || '').trim();
    const targetOwner = String(body?.target_owner || '').trim();
    if (!UUID_RE.test(serverId) || !UUID_RE.test(targetOwner)) return json({ error: 'Некорректные данные сервера или пользователя.' }, 400);

    const admin = createClient(url, service, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data, error } = await admin.rpc('vessel_transfer_server_ownership', {
      target_server: serverId,
      target_owner: targetOwner,
      actor_user: user.id,
    });
    if (error) {
      console.error('Ownership transfer RPC failed', error.code, error.message);
      if (error.code === '42501') return json({ error: 'Передача владельца запрещена.' }, 403);
      if (error.code === 'P0002') return json({ error: 'Сервер не найден.' }, 404);
      return json({ error: 'Не удалось передать сервер.' }, 500);
    }
    if (!data?.ok) return json({ error: 'Не удалось передать сервер.' }, 400);
    return json({ ok: true, server_id: data.server_id, owner_id: data.owner_id, already_owner: !!data.already_owner });
  } catch (error) {
    console.error('Ownership transfer failed', error);
    return json({ error: 'Не удалось передать сервер.' }, 500);
  }
});
