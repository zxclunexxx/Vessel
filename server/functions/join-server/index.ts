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
    const code = String(body?.code || '').trim().toUpperCase();
    if (!/^VSL-[A-Z0-9-]{4,40}$/.test(code)) return json({ error: 'Неверный формат кода приглашения.' }, 400);

    const admin = createClient(url, service, { auth: { persistSession: false, autoRefreshToken: false } });
    const { data, error } = await admin.rpc('vessel_redeem_server_invite', { invite_code: code, target_user: user.id });
    if (error) {
      console.error('Invite redemption RPC failed', error);
      return json({ error: 'Не удалось вступить в сервер.' }, 500);
    }
    if (!data?.ok) {
      const reason = data?.reason;
      if (reason === 'not_found') return json({ error: 'Код приглашения не найден.' }, 404);
      if (reason === 'expired') return json({ error: 'Срок действия приглашения истёк.' }, 410);
      if (reason === 'used_up') return json({ error: 'Приглашение больше недействительно.' }, 410);
      return json({ error: 'Не удалось вступить в сервер.' }, 400);
    }
    return json({ ok: true, server_id: data.server_id, already_member: !!data.already_member });
  } catch (error) {
    console.error(error);
    return json({ error: 'Не удалось вступить в сервер.' }, 500);
  }
});
