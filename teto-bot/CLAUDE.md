# Teto Bot — контекст проекта

Discord-бот-ассистент "Тето" (Kasane Teto). Отвечает голосом на голосовые
сообщения и текст с упоминанием, умеет пинговать людей/роли по имени и
(для доверенных админов) выполнять модерацию сервера. Python, py-cord,
Groq (STT + LLM), Fish Audio (TTS).

Владелец пишет на русском, комментарии в коде и README — тоже на русском.
Сохранять этот стиль при дальнейшей работе.

## Стек

- **Discord**: py-cord (`py-cord[voice]`, форк discord.py — extras `[voice]`
  обязателен, иначе упадёт на `MissingVoiceDependenciesError`)
- **STT**: Groq Whisper API (`whisper-large-v3-turbo`)
- **LLM (персона Тето)**: Groq (`llama-3.3-70b-versatile`) с function calling
- **LLM (классификатор модерации)**: Groq (`llama-3.1-8b-instant`), отдельная
  модель, чтобы не грузить персону Тето инструкциями про модерацию
- **TTS**: Fish Audio SDK (`fish-audio-sdk`), бесплатная модель `s2.1-pro-free`
- **Хранилище**: обычные JSON-файлы в `data/` (не БД) — осознанный выбор,
  владелец предпочитает ручное редактирование через SSH
- **Хостинг**: VPS (Ubuntu) через systemd-сервис

## Структура

```
teto-bot/
├── main.py                       # точка входа, регистрирует cogs, читает DISCORD_TOKEN
├── config.py                     # все env-переменные, системный промпт, лимит памяти
├── requirements.txt
├── .env / .env.example           # секреты (.env в .gitignore)
├── data/
│   ├── aliases.example.json      # шаблон; реальный aliases.json — тоже в .gitignore
│   └── admins.example.json       # шаблон; реальный admins.json — тоже в .gitignore
├── cogs/
│   ├── voice_commands.py         # /join, /leave (только для озвучки в voice-канале)
│   └── voice_message_listener.py # ГЛАВНЫЙ файл оркестрации: on_message, вся логика ветвления
├── services/
│   ├── stt_service.py            # Groq Whisper: bytes(wav) -> text
│   ├── llm_service.py            # персона Тето + function calling ping_contact + память
│   ├── tts_service.py            # Fish Audio: text -> mp3 bytes
│   ├── action_classifier.py      # классификатор команд модерации (function calling, без исполнения)
│   ├── alias_service.py          # читает data/aliases.json, резолвит имя -> "<@id>"/"<@&id>"
│   ├── permission_service.py     # читает data/admins.json, is_admin(user_id)
│   └── trigger_detector.py       # НЕ используется, задел на будущее (см. "История решений")
├── memory/
│   └── conversation_store.py     # in-memory история диалога, deque(maxlen=8) на channel_id
└── utils/
    └── audio_utils.py            # ffmpeg-конвертация в WAV, проигрывание TTS-ответа в voice-канале
```

## Как работает пайплайн (`cogs/voice_message_listener.py`)

Единая точка входа — `on_message`. Два способа обратиться к боту:

1. **Голосовое сообщение / аудио-вложение** в любом текстовом канале →
   скачивается → `audio_utils.convert_to_wav_bytes` (ffmpeg) →
   `stt_service.transcribe` → текст.
2. **Текст с упоминанием бота** (`@リアルテト вопрос`) → упоминание
   вырезается из текста напрямую.

Дальше единый `_handle_incoming_text`:
- Если `permission_service.is_admin(author.id)` — сначала пробуем
  `action_classifier.classify(text)` (вторая LLM). Если она вернула
  действие — резолвим цель (`_resolve_target`: сначала явные `@упоминания`
  в сообщении, потом `alias_service` по имени) и выполняем
  (`kick_from_voice` / `kick_from_server` / `ban_member` /
  `create_and_assign_role`), отвечаем результатом, **выходим**.
- Иначе (или если классификатор не нашёл действие) — обычный разговор:
  `llm_service.ask(channel_id, text, author_display_name)` → при желании
  модель вызывает `ping_contact` (function calling) → `alias_service`
  резолвит точный ID → ответ → `tts_service.synthesize` → проигрывается в
  voice-канале, если бот там (`/join`), иначе прикрепляется mp3-файлом.

## Модель безопасности (важно не сломать при доработках)

- **Проверка прав на модерацию — всегда в коде, до вызова любой LLM.**
  `permission_service.is_admin()` вызывается первым; если автор не админ,
  `action_classifier` вообще не вызывается для этого сообщения.
- **Резолвинг цели действия никогда не доверяется свободному тексту LLM.**
  Только явные Discord-упоминания (`message.mentions`) или точное
  совпадение имени в `data/aliases.json`. LLM не может "угадать" ID.
- **`ping_contact` тоже не позволяет LLM писать ID сама** — она вызывает
  функцию по имени, реальный ID подставляет `alias_service` из файла.
- **`everyone`/`here` жёстко заблокированы** в `alias_service.get_mention`
  на уровне кода — не пройдут, даже если их вписать в `aliases.json`.
- **Роли создаются без прав** (`discord.Permissions.none()`) — модерация
  не может выдать себе/кому-то реальные привилегии сервера.
- `data/aliases.json` и `data/admins.json` — НЕ в git (только `.example.json`
  версии), правятся вручную на сервере, требуют перезапуска бота.

## История решений (важный контекст, чтобы не наступить на те же грабли)

1. **Изначальный план** — бот сам слушает голосовой канал (voice receive)
   и реагирует на триггер-фразу ("тето ответь"). **Отказались**: с марта
   2026 Discord сделал E2EE (протокол DAVE) обязательным, а py-cord
   2.8.1 не может стабильно принимать голос — падает даже на встроенных
   синках (`AttributeError: '...' object has no attribute
   '__sink_listeners__'`, баг незавершённой переделки библиотеки под DAVE).
2. **Второй план** — push-to-talk (`/talk` + `/stop` через
   `start_recording`/`WaveSink`). **Тоже отказались** — та же самая
   ошибка `__sink_listeners__` воспроизводится и на встроенных синках,
   значит проблема не в нашем коде, а в самой библиотеке.
3. **Текущее решение** — голосовые сообщения Discord как вложения
   (`message.attachments`) — стабильный API, не завязан на voice receive.
   `config.TRIGGER_PHRASES` и `services/trigger_detector.py` остались в
   коде неиспользуемыми — заготовка на случай, если py-cord всё же
   починит поддержку DAVE и захочется вернуться к автослушиванию.
4. **Fish Audio 402 Payment Required** — решилось явным указанием
   бесплатной модели `s2.1-pro-free` вторым позиционным аргументом в
   `session.tts(request, "s2.1-pro-free")` — SDK по умолчанию, видимо,
   пытался использовать платную модель.
5. **Пинги через LLM** — сознательно НЕ дали модели самой писать
   `<@id>` в тексте (риск галлюцинации ID) — только function calling
   с резолвом на нашей стороне.
6. **БД для алиасов/админов** — сознательно НЕ SQLite и НЕ slash-команды,
   а простые JSON-файлы + ручное редактирование через SSH — так предпочёл
   владелец (проще, не нужно городить команды администрирования).

## Известные ограничения / места для будущей доработки

- Список конкретных пунктов и деталей — см. README.md, раздел
  "Известные ограничения текущей версии".
- Классификатор модерации может неверно интерпретировать двусмысленные
  фразы — сейчас без подтверждения перед выполнением (осознанный выбор
  владельца: "если админ попросил — делаем сразу").
- Память диалога (`conversation_store`) — только in-memory, сбрасывается
  при перезапуске бота. Не проблема при текущем масштабе использования.
- `data/aliases.json` и `data/admins.json` читаются один раз при старте,
  live-reload не реализован (перезапуск через `systemctl restart teto-bot`).

## Деплой

VPS (Ubuntu), путь на сервере обычно `~/discord_bot/teto-bot` (репозиторий
`discord_bot` клонирован целиком, бот — в подпапке `teto-bot`). Управляется
через systemd unit `teto-bot.service` (`ExecStart=.../venv/bin/python3
main.py`, `EnvironmentFile=.../.env`). Подробная пошаговая инструкция —
в README.md, разделы 1–3.

Локальная машина владельца: Ubuntu, путь проекта
`/run/media/yuzuha/YD/discord_bot`.
