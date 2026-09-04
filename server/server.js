import http from 'node:http';
import crypto from 'node:crypto';

const messages = [];
const users = new Map();
const clients = new Set();
const json = (res, code, data) => { res.writeHead(code, {'Content-Type':'application/json','Access-Control-Allow-Origin':'*'}); res.end(JSON.stringify(data)); };
const server = http.createServer((req, res) => {
  if (req.method === 'OPTIONS') { res.writeHead(204, {'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'Content-Type'}); return res.end(); }
  if (req.url === '/api/messages' && req.method === 'GET') return json(res, 200, messages);
  if ((req.url === '/api/auth/register' || req.url === '/api/auth/login') && req.method === 'POST') { let body=''; req.on('data',c=>body+=c); req.on('end',()=>{ try { const data=JSON.parse(body); const key=(data.email||'').toLowerCase(); if(!key||!data.password) return json(res,400,{error:'Email and password required'}); if(req.url.endsWith('register') && users.has(key)) return json(res,409,{error:'User already exists'}); const hash=crypto.scryptSync(data.password,'vessel-salt',64).toString('hex'); if(req.url.endsWith('login') && (!users.has(key)||users.get(key).hash!==hash)) return json(res,401,{error:'Invalid credentials'}); const user=users.get(key)||{name:data.name||key.split('@')[0],email:key,hash}; users.set(key,{...user,hash}); json(res,200,{token:crypto.randomBytes(24).toString('hex'),user:{name:user.name,email:user.email}}); } catch { json(res,400,{error:'Invalid JSON'}); } }); return; }
  if (req.url === '/api/messages' && req.method === 'POST') { let body=''; req.on('data', c=>body+=c); req.on('end',()=>{ try { const message={id:Date.now().toString(),...JSON.parse(body),created_at:new Date().toISOString()}; messages.push(message); clients.forEach(c=>c.write(`data: ${JSON.stringify(message)}\n\n`)); json(res,201,message); } catch { json(res,400,{error:'Invalid JSON'}); } }); return; }
  if (req.url === '/api/events') { res.writeHead(200, {'Content-Type':'text/event-stream','Cache-Control':'no-cache','Connection':'keep-alive','Access-Control-Allow-Origin':'*'}); res.write(': connected\n\n'); clients.add(res); req.on('close',()=>clients.delete(res)); return; }
  json(res,404,{error:'Not found'});
});
server.listen(8080,()=>console.log('Vessel server listening on http://localhost:8080'));
