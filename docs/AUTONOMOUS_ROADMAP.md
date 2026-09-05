# Vessel — автономная дорожная карта

Цель: довести Vessel из прототипа до цельного рабочего MVP без демо-заглушек в реальном режиме.

## Критические проблемы, подтверждённые 2026-09-05

- реальный режим смешан с localStorage/demo-данными;
- регистрация при ошибке Supabase молча создаёт локального псевдопользователя;
- в auth.users и profiles нет реальных пользователей, поэтому друзья/DM физически не могли работать;
- стартовые сообщения Марка/Лизы/«Ты» до сих пор загружаются как defaultMessages;
- каналы частично живут в localStorage и частично в Supabase;
- звонки имеют неполный lifecycle/cleanup, из-за чего hang-up может не срабатывать;
- интерфейс не различает loading / empty / error состояния достаточно явно;
- основной runtime собран в одном большом src/main.js и требует постепенной декомпозиции.

## P0 — единая аутентификация и состояние

Definition of Done:
- Supabase Auth — единственный источник истины для реального пользователя;
- приложение стартует через getSession/onAuthStateChange;
- signUp/signIn ошибки показываются пользователю и никогда не превращаются в demo/local user;
- если signUp требует подтверждения почты, показывается отдельное состояние ожидания подтверждения;
- logout делает Supabase signOut и очищает только UI-кэш;
- устаревшие vesselUser/vesselToken больше не дают доступ в реальный интерфейс;
- demo mode, если сохраняется, полностью изолирован и явно помечен как demo.

## P0 — убрать все fake runtime data

Definition of Done:
- нет defaultMessages Марк/Лиза/Ты в authenticated mode;
- нет fake servers/channels/member lists в authenticated mode;
- пустая база = корректный empty state, а не заполненный фейковый Discord-подобный экран;
- localStorage используется только для UI preferences/cache, не как база продукта.

## P0 — друзья

Definition of Done:
- поиск пользователя по username работает только для authenticated session;
- нельзя добавить себя;
- нельзя создать дублирующую или встречную pending-заявку;
- входящие и исходящие заявки имеют понятные состояния;
- принять/отклонить/отменить заявку можно без перезагрузки;
- friendship создаётся атомарно на стороне БД;
- список друзей обновляется realtime;
- удаление из друзей работает безопасно.

## P0 — Direct Messages

Definition of Done:
- DM доступен только между допустимыми пользователями согласно продуктовой политике;
- список диалогов строится из реальных данных, а не только из friends;
- история сообщений загружается стабильно;
- отправка/получение realtime работает в двух вкладках/аккаунтах;
- сообщения не дублируются;
- есть loading/error/empty states;
- вложения в DM либо поддерживаются полноценно, либо UI не обещает их поддержку.

## P0 — звонки

Definition of Done:
- audio call: initiate → ring → accept/reject → connected → hang up;
- video call проходит тот же lifecycle;
- hang-up работает у инициатора и получателя;
- remote bye закрывает звонок у второго участника;
- busy state обрабатывается;
- mic/camera toggle отражают реальное состояние track.enabled;
- все media tracks и RTCPeerConnection закрываются при завершении;
- повторный звонок после завершения работает без reload;
- уход со страницы/смена аккаунта очищает звонок;
- таймаут неотвеченного звонка не оставляет UI в вечном состоянии.

## P1 — серверы и каналы

Definition of Done:
- список серверов берётся из Supabase;
- создание сервера создаёт owner membership и минимум один реальный текстовый канал транзакционно;
- join by invite работает и обновляет UI;
- invite usage/expiry учитываются атомарно;
- текстовые/голосовые каналы создаются только при достаточной роли;
- переключение каналов не переносит сообщения предыдущего канала;
- удаление/переименование каналов и сервера доступны владельцу;
- роли owner/admin/member соблюдаются в UI и RLS.

## P1 — участники и presence

Definition of Done:
- sidebar участников показывает реальный roster;
- online/offline не хардкодится;
- presence обновляется realtime;
- owner/admin/member отображаются корректно;
- текущий пользователь не дублируется.

## P1 — сообщения каналов

Definition of Done:
- отправка идёт только в выбранный реальный channel_id;
- realtime подписка фильтруется/обрабатывается без дублей;
- профиль автора подтягивается корректно;
- сообщения не сохраняются одновременно в Supabase + локальный Express fallback;
- локальный http://localhost:8080 не используется веб-версией GitHub Pages.

## P1 — UI/UX

Definition of Done:
- desktop layout устойчив при 1366/1440/1920 px;
- mobile layout пригоден для Android;
- модалки, dropdown, context actions не строятся через prompt()/alert() для основных сценариев;
- кнопки имеют disabled/loading states;
- ошибки показываются inline/toast;
- пустые состояния не выглядят как сломанная загрузка;
- звонок имеет отдельную понятную панель состояния.

## P1 — архитектура

Definition of Done:
- постепенно разделить main.js на auth/data/realtime/calls/ui модули;
- единый app state вместо десятков window.__vessel* flags;
- cleanup subscriptions при logout/unmount;
- централизованная обработка ошибок;
- не хранить секретные ключи в клиенте; publishable key допустим.

## P1 — база и безопасность

Definition of Done:
- RLS включён на всех exposed tables;
- policies не содержат tautology/IDOR;
- SECURITY DEFINER функции не доступны как публичные RPC без необходимости;
- server membership, friendships, invites и notifications проверены security advisor;
- индексы добавлены для основных realtime/query путей;
- migrations отражают реальное состояние production schema.

## P2 — автоматические тесты и CI

Definition of Done:
- npm build обязателен для каждого изменения;
- smoke test загружает веб-приложение без runtime console errors;
- auth test проверяет отсутствие silent demo fallback;
- UI tests проверяют empty states;
- при доступной тестовой auth-среде — 2-user E2E: friend request → accept → DM → call signaling;
- web deploy, APK и EXE workflows остаются зелёными;
- failing workflow автоматически разбирается по logs перед следующим изменением.

## P2 — релизы

Definition of Done:
- web: стабильная GitHub Pages версия;
- Android: устанавливаемый debug/release APK с корректным appId/icon/name;
- Windows: запускаемый portable EXE;
- README содержит понятные инструкции и ограничения;
- перед релизом выполняется финальный regression checklist.

## Правила автономной работы

1. Сначала чинить P0, потом P1/P2.
2. Не маскировать ошибки фейковыми данными.
3. После DDL/RLS — Supabase Security Advisor.
4. После frontend change — build/web workflow.
5. После platform change — соответствующий APK/EXE workflow.
6. Не создавать платные ресурсы и не выполнять необратимые destructive операции без явного решения пользователя.
7. Если задача не заблокирована внешним секретом/стоимостью/необратимым продуктовым решением — продолжать автономно.
