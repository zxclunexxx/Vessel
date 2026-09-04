# Vessel

Vessel — собственный мессенджер в стиле Discord.

## Возможности прототипа

- регистрация и вход через Supabase Auth;
- профили пользователей;
- серверы и текстовые/голосовые каналы;
- личные сообщения;
- локальная история и вложения;
- realtime-сообщения;
- управление микрофоном и камерой.

## Запуск

```bash
npm install
npm run dev
```

Сервер API запускается отдельно командой `npm run server`.

## Android APK

Проект подготовлен для Android через Capacitor.

Сборка локально:

```bash
npm install
npm run android:apk
```

Автоматическая сборка запускается в GitHub Actions после каждого обновления
ветки `main`. Готовый тестовый файл находится в запуске workflow
`Build Vessel Android APK` в разделе **Artifacts** под именем `Vessel-debug-apk`.

## Структура

- `src/` — интерфейс Vessel;
- `server/` — API, realtime и SQL-схема;
- `index.html` — точка входа приложения.
- `capacitor.config.json` — настройки Android-приложения;
- `.github/workflows/android-apk.yml` — автоматическая сборка APK.
