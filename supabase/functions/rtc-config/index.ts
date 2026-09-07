import { createClient } from 'npm:@supabase/supabase-js@2';

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json', 'Cache-Control': 'no-store' } });

const DEFAULT_STUN_URLS = ['stun:stun.l.google.com:19302', 'stun:stun1.l.google.com:19302'];
const splitUrls = (value: string | undefined, allowed: RegExp) =>
  String(value || '')
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter((item) => allowed.test(item))
    .slice(0, 8);

const base64 = (bytes: Uint8Array) => {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
};

async function createTurnCredential(secret: string, username: string) {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-1' },
    false,
    ['sign'],
  );
  const signature = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(username));
  return base64(new Uint8Array(signature));
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors });
  if (req.method !== 'POST') return json({ error: 'Method not allowed' }, 405);

  try {
    const authHeader = req.headers.get('Authorization');
    if (!authHeader) return json({ error: 'Unauthorized' }, 401);

    const url = Deno.env.get('SUPABASE_URL')!;
    const anon = Deno.env.get('SUPABASE_ANON_KEY')!;
    const userClient = createClient(url, anon, { global: { headers: { Authorization: authHeader } } });
    const { data: { user }, error } = await userClient.auth.getUser();
    if (error || !user) return json({ error: 'Unauthorized' }, 401);

    const configuredStun = splitUrls(Deno.env.get('STUN_URLS'), /^stuns?:/i);
    const stunUrls = configuredStun.length ? configuredStun : DEFAULT_STUN_URLS;
    const iceServers: Array<Record<string, unknown>> = [{ urls: stunUrls }];

    const turnUrls = splitUrls(Deno.env.get('TURN_URLS'), /^turns?:/i);
    const turnSecret = String(Deno.env.get('TURN_SHARED_SECRET') || '').trim();
    let expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString();
    let relayEnabled = false;

    if (turnUrls.length && turnSecret) {
      const rawTtl = Number(Deno.env.get('TURN_TTL_SECONDS') || 3600);
      const ttlSeconds = Number.isFinite(rawTtl) ? Math.min(Math.max(Math.floor(rawTtl), 300), 86400) : 3600;
      const expirySeconds = Math.floor(Date.now() / 1000) + ttlSeconds;
      const username = `${expirySeconds}:${user.id}`;
      const credential = await createTurnCredential(turnSecret, username);
      iceServers.push({ urls: turnUrls, username, credential });
      expiresAt = new Date(expirySeconds * 1000).toISOString();
      relayEnabled = true;
    }

    return json({
      iceServers,
      expires_at: expiresAt,
      relay_enabled: relayEnabled,
    });
  } catch (error) {
    console.error('RTC config failed', error);
    return json({ error: 'Unable to create RTC configuration' }, 500);
  }
});
