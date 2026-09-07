# Vessel server foundation

`schema.sql` описывает структуру PostgreSQL для настоящей версии Vessel.

Таблицы:

- `profiles` — пользователи и их статусы;
- `servers` — серверы Vessel;
- `server_members` — участники и роли;
- `channels` — текстовые и голосовые каналы;
- `messages` — сообщения с историей и временем редактирования.

## Edge Functions

Версионируемые исходники функций лежат в `server/functions/`.

- `transfer-server-ownership` — JWT-защищённая серверная граница для передачи владения сервером. Функция проверяет пользователя по access token и только затем вызывает service-role RPC, где повторно проверяется текущий владелец и членство нового владельца.

Service-role key никогда не должен попадать во frontend, GitHub Actions logs или клиентские `.env` файлы.

## Security

Клиент работает через publishable key и RLS. Привилегированные операции должны выполняться только через JWT-защищённые Edge Functions или ограниченные RPC, недоступные `anon`/`authenticated` напрямую без необходимых серверных проверок.
