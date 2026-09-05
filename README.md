# Vessel

Vessel — собственный мессенджер в стиле Discord.

## Текущее состояние

Проект постепенно переводится с прототипных локальных данных на реальный authenticated runtime поверх Supabase. В `main` уже используются настоящая Supabase-сессия, профили, серверы/участники/каналы из БД, друзья и заявки, личные сообщения и WebRTC-звонки. Демо-пользователи и стартовые сообщения не используются в authenticated-режиме.

Последний этап стабилизации включает:

- серверы и каналы загружаются из Supabase без локальных fake/fallback-каналов;
- новые серверы полагаются на DB-trigger для владельца и стартовых каналов;
- создание каналов выполняется только владельцем и синхронизируется обратно из БД;
- заявки в друзья можно принять или отклонить;
- отправка DM разрешена RLS только между друзьями;
- вложения поддерживаются и в каналах, и в личных сообщениях;
- composer скрывается в голосовом канале;
- internal Supabase trigger-функции и RLS проходят Security Advisor без замечаний.

## Возможности

- регистрация, вход, восстановление сессии и выход через Supabase Auth;
- профили пользователей;
- серверы, участники и текстовые/голосовые каналы;
- друзья и заявки в друзья;
- личные сообщения и realtime;
- загрузка вложений;
- уведомления;
- аудио- и видеозвонки WebRTC;
- управление микрофоном и камерой.

## Запуск

```bash
npm install
npm run dev
```

Сервер API для legacy/local разработки запускается отдельно командой `npm run server`. Веб-клиент с authenticated runtime использует Supabase напрямую для основных данных.

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

- `src/` — интерфейс Vessel;
- `server/` — legacy/local API и SQL-материалы;
- `scripts/` — проверяемые maintenance-патчи для автономной разработки;
- `electron/` — desktop entrypoint;
- `index.html` — точка входа приложения;
- `capacitor.config.json` — Android-конфигурация;
- `.github/workflows/` — web/APK/EXE и maintenance CI.
