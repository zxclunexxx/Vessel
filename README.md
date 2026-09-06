# Vessel

Vessel — собственный мессенджер в стиле Discord с web-, Android- и Windows-версиями.

## Текущее состояние

Основной runtime Vessel работает поверх Supabase Auth, PostgreSQL/RLS, Realtime и Storage. Старые локальные demo/fake-данные больше не используются как authenticated runtime: пользователи, друзья, серверы, каналы, сообщения и участники загружаются из реальной БД.

Последний этап стабилизации включает:

- регистрация, вход, восстановление сессии и выход через Supabase Auth;
- синхронизация смены аккаунта и logout/login между вкладками с очисткой старых Realtime/WebRTC-состояний;
- профили и их realtime-обновление;
- поиск пользователей, входящие/исходящие заявки в друзья, принятие, отклонение, отмена и повторная отправка после завершённой заявки;
- двусторонние friendship-связи и удаление из друзей;
- личные сообщения, список старых DM-тредов и realtime-обновление;
- сообщения и вложения привязаны к исходному DM/каналу даже если пользователь переключился в другой чат во время асинхронной отправки;
- приватные вложения через Supabase Storage с удалением неотправленных файлов при ошибке записи сообщения;
- создание, переименование и удаление серверов и каналов, приглашения, участники и роли;
- RLS ограничивает операции владельцами/участниками и не расширяется ради удобства клиента;
- аудио- и видеозвонки WebRTC: invite/accept/decline/busy, hangup, mic/camera, ICE и очистка media state;
- голосовые каналы через Supabase Realtime Presence/Broadcast с восстановлением realtime-состояния и отключением при потере membership/удалении комнаты;
- production build проверяется перед автоматическим commit автономных патчей;
- GitHub Actions собирает web, Android APK и Windows EXE.

## Безопасность

Все основные пользовательские таблицы в `public` работают с включённым Row Level Security. Клиент использует только publishable Supabase key; service-role secret не хранится в браузерном коде.

`public.vessel_dm_threads()` намеренно остаётся узким `SECURITY DEFINER` RPC для обнаружения собственных старых DM-тредов после удаления пользователя из друзей. Выполнение для `anon/public` запрещено, вызов доступен только authenticated-пользователям, функция фильтрует сообщения через `auth.uid()` и возвращает только безопасные поля профиля без email.

В Supabase Auth остаётся отдельное предупреждение Security Advisor: **Leaked Password Protection Disabled**. Это настройка Auth проекта и включается в Supabase Dashboard; RLS ради её обхода не меняется.

## Возможности

- Supabase Auth: регистрация, вход, сессии и logout;
- профили и статусы;
- серверы, участники, роли и приглашения;
- текстовые и голосовые каналы;
- поиск пользователей и друзья;
- личные сообщения и realtime;
- приватные вложения;
- уведомления;
- аудио- и видеозвонки WebRTC;
- управление микрофоном и камерой;
- web / Android APK / Windows EXE.

## Запуск

```bash
npm install
npm run dev
```

Сервер API для legacy/local разработки запускается отдельно командой `npm run server`. Основной authenticated web-клиент использует Supabase напрямую для данных, Auth, Realtime и Storage.

## Android APK

Проект подготовлен для Android через Capacitor.

```bash
npm install
npm run android:apk
```

Автоматическая сборка запускается в GitHub Actions после обновлений `main`. Артефакт workflow `Build Vessel Android APK` называется `Vessel-debug-apk`.

## Windows EXE

Портативная Windows-версия собирается workflow `Build Vessel Windows EXE`. Артефакт называется `Vessel-windows-exe`; после распаковки запускается `Vessel.exe`.

## Веб-версия

Веб-версия публикуется workflow `Deploy Vessel Web` и доступна по адресу:

`https://zxclunexxx.github.io/Vessel/`

## Структура

- `src/` — основной интерфейс и authenticated runtime Vessel;
- `server/` — SQL bootstrap, миграции и legacy/local API;
- `scripts/` — идемпотентные maintenance-патчи и проверки автономной разработки;
- `electron/` — desktop entrypoint;
- `index.html` — точка входа приложения;
- `capacitor.config.json` — Android-конфигурация;
- `.github/workflows/` — quality gate, web, APK, EXE и автономный maintenance CI.
