# Teto Bot — голосовой Discord-бот

Discord-бот, который распознаёт голосовые сообщения и текст с упоминанием
бота, отвечает голосом через Fish Audio TTS, умеет пинговать людей/роли по
имени и (для доверенных админов) выполнять модерацию сервера — по просьбе,
через отдельную LLM-классификацию команд.

## Почему голосовые сообщения, а не прослушивание voice-канала

Изначально планировалось, что бот сам слушает голосовой канал и реагирует на
триггер-фразу («тето ответь» и т.п.). Но с марта 2026 Discord сделал
end-to-end шифрование (протокол **DAVE**) обязательным для всех голосовых
звонков, и **приём голоса** в py-cord (версия 2.8.1 на момент написания)
оказался полностью нерабочим — не только из-за незавершённой поддержки
DAVE, но и из-за внутреннего бага самой библиотеки (`AttributeError:
'WaveSink' object has no attribute '__sink_listeners__'` — воспроизводится
даже на встроенных синках, то есть проблема не в нашем коде, а в текущем
релизе py-cord).

Поэтому вместо приёма голоса из voice-канала используется официальная фича
Discord — **голосовые сообщения** (та самая "волна" с иконкой микрофона в
чате) или обычные аудио-вложения. Это работает через давно стабильный API
вложений (`message.attachments`), никак не связанный с proблемным приёмом
голоса из voice-каналов, поэтому не зависит от состояния DAVE-поддержки в
py-cord.

**Отправка** голоса в voice-канал (TTS-ответ) работает нормально — ломается
только приём, поэтому бот всё ещё может зайти в канал командой `/join` и
отвечать там голосом.

## Структура проекта

```
teto-bot/
├── main.py                       # точка входа
├── config.py                     # env-переменные, лимит памяти, модели
├── data/
│   ├── aliases.example.json      # пример базы пингов (скопировать в aliases.json)
│   └── admins.example.json       # пример списка админов (скопировать в admins.json)
├── cogs/
│   ├── voice_commands.py         # /join, /leave — вход/выход из voice-канала (для озвучки ответа)
│   └── voice_message_listener.py # приём сообщений, разветвление на модерацию/разговор
├── services/
│   ├── stt_service.py            # Groq Whisper — речь в текст
│   ├── llm_service.py            # Groq LLM (персона Тето) + память + function calling для пинга
│   ├── tts_service.py            # Fish Audio SDK — текст в речь
│   ├── action_classifier.py      # вторая LLM — классифицирует команды модерации
│   ├── alias_service.py          # чтение data/aliases.json
│   ├── permission_service.py     # чтение data/admins.json — кому разрешена модерация
│   └── trigger_detector.py       # НЕ используется сейчас (заготовка на будущее)
├── memory/
│   └── conversation_store.py     # история диалога, лимит 8 сообщений на текстовый канал
└── utils/
    └── audio_utils.py            # конвертация аудио в WAV (ffmpeg), проигрывание TTS-ответа в voice-канале
```

## 1. Локальная установка и тест (Ubuntu)

```bash
cd /run/media/yuzuha/YD/discord_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo apt install ffmpeg -y   # если ещё не установлен
```

Скопируй `.env.example` в `.env` и заполни реальными значениями:

```bash
cp .env.example .env
nano .env
```

Понадобится:
- `DISCORD_TOKEN` — токен бота из [Discord Developer Portal](https://discord.com/developers/applications).
  **Важно:** в настройках бота включи Privileged Gateway Intents → `Message Content Intent`.
  При приглашении бота на сервер (OAuth2 → URL Generator) отметь scope `bot` и
  `applications.commands`, из permissions — минимум `Connect`, `Speak`, `Use Voice Activity`.
- `GROQ_API_KEY` — с console.groq.com.
- `FISH_AUDIO_API_KEY` и `FISH_AUDIO_REFERENCE_ID` — у тебя уже есть, `reference_id` это id голосовой модели Тето в твоём аккаунте Fish Audio.

Запуск:
```bash
python3 main.py
```

Проверка: пришли голосовое сообщение (или аудио-файл) в любой текстовый
канал, где есть бот — он должен прислать текстом, что расслышал, а затем
ответить голосом (файлом в чат, либо в voice-канале, если вызывал `/join`).

## Пинги по имени

Бот может упоминать людей и роли по имени в своих ответах (например,
«позови Святослава» → в ответе появится настоящий `<@741544905234579456>`).

1. Скопируй пример и заполни реальными ID:
```bash
cp data/aliases.example.json data/aliases.json
nano data/aliases.json
```
2. Формат:
```json
{
  "users": {
    "Святослав": "741544905234579456"
  },
  "roles": {
    "роль играющих мальчиков": "1477712062154014815"
  }
}
```
Discord ID можно скопировать, включив режим разработчика (Настройки →
Расширенные → Режим разработчика), затем ПКМ по пользователю/роли → «Копировать ID».

3. **Изменения требуют перезапуска бота** (`systemctl restart teto-bot` на VPS) —
файл читается один раз при старте.

Имена `everyone`/`here` заблокированы на уровне кода и не сработают, даже
если их вписать в файл вручную — это защита от случайного/намеренного
пинга всего сервера.

## Модерация (только для админов)

Доверенные пользователи могут попросить бота отключить кого-то от войса,
выгнать с сервера, забанить или выдать роль — просто написав это боту
текстом (с упоминанием) или голосовым сообщением.

1. Скопируй пример и впиши ID тех, кому доверяешь:
```bash
cp data/admins.example.json data/admins.json
nano data/admins.json
```
```json
{
  "admin_ids": [
    "741544905234579456"
  ]
}
```
2. **Изменения требуют перезапуска бота**, как и с алиасами.

Как это работает: если автор сообщения есть в `admins.json`, бот сначала
прогоняет текст через отдельную, более быструю LLM-модель
(`services/action_classifier.py`), которая определяет — это команда
модерации или обычный разговор. Проверка прав всегда происходит в коде
**до** обращения к любой LLM — модель никогда не решает, кому что можно.

**Важно про указание цели**: надёжнее всего явно упомянуть человека
(`@ник`) в той же фразе — тогда бот берёт точный ID напрямую от Discord.
Если просто назвать имя текстом («кикни Святослава») — бот попробует найти
это имя в `data/aliases.json`; если имени там нет, бот попросит уточнить.

**Права бота на сервере**, необходимые для модерации: `Kick Members`,
`Ban Members`, `Manage Roles`, `Move Members` — выдай их через роль бота
в настройках сервера. Для выдачи ролей роль бота должна стоять **выше**
любой роли, которую он создаёт/выдаёт, в списке ролей сервера (Настройки
сервера → Роли — перетащить роль бота повыше).

## 2. Загрузка на GitHub (приватный репозиторий)

```bash
cd /run/media/yuzuha/YD/discord_bot
git init
git add .
git commit -m "Initial commit: Teto voice bot"
```

Создай приватный репозиторий на github.com (без README/gitignore — они уже есть локально),
затем:

```bash
git remote add origin git@github.com:ТВОЙ_ЮЗЕРНЕЙМ/teto-bot.git
git branch -M main
git push -u origin main
```

`.env` в репозиторий не попадёт — он в `.gitignore`.

## 3. Деплой на VPS

```bash
ssh root@ТВОЙ_IP
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git ffmpeg

git clone git@github.com:ТВОЙ_ЮЗЕРНЕЙМ/teto-bot.git
# если репозиторий приватный и нет SSH-ключа на VPS — склонируй по HTTPS
# с personal access token, либо сгенерируй ключ на VPS и добавь в GitHub Deploy Keys

cd teto-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
nano .env   # вставь те же значения, что и локально
```

Постоянная работа через systemd:

```bash
nano /etc/systemd/system/teto-bot.service
```

```ini
[Unit]
Description=Teto Discord Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/teto-bot
ExecStart=/root/teto-bot/venv/bin/python3 main.py
Restart=always
RestartSec=5
EnvironmentFile=/root/teto-bot/.env

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable teto-bot
systemctl start teto-bot
systemctl status teto-bot      # проверить статус
journalctl -u teto-bot -f      # логи в реальном времени
```

Обновление кода в будущем:
```bash
cd teto-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart teto-bot
```

## Известные ограничения текущей версии (для этапа тестов)

- **Discord Intents**: обработка сообщений требует `Message Content Intent`,
  включённого и в Developer Portal, и в коде (`main.py`, уже включено).
  Без него `on_message` не будет видеть вложения от обычных пользователей.
- **Формат аудио**: конвертация идёт через `ffmpeg` (`utils/audio_utils.py`),
  он должен быть установлен в системе (уже указано в разделе установки).
  Если ffmpeg не найден — увидишь ошибку `[Errno 2] No such file or directory: 'ffmpeg'`.
- **Только первое аудио-вложение в сообщении** обрабатывается, если их
  несколько — остальные игнорируются (осознанное упрощение).
- **Многоязычность**: Whisper сам определяет язык, но если бот будет часто
  путать русский/английский/японский — можно зафиксировать `language_hint`
  в `stt_service.transcribe()` под нужды конкретного сервера.
- **Голосовой канал нужен только для озвучки, не для приёма**: `/join`
  подключает бота, чтобы TTS-ответ звучал в канале для всех — но сам вопрос
  всё равно нужно присылать голосовым сообщением в текстовый канал, а не
  проговаривать вслух в voice-канале (бот его не услышит).
- **Пинги работают только по зарегистрированным именам**: если имени/роли
  нет в `data/aliases.json`, бот не сможет его упомянуть (и не будет
  пытаться угадать) — это осознанное ограничение ради безопасности.
- **Действия модерации выполняются сразу**, без переспроса подтверждения —
  если это окажется неудобным на практике (например, случайные срабатывания
  классификатора на двусмысленные фразы), можно добавить шаг подтверждения
  в `cogs/voice_message_listener.py` (`_try_handle_admin_action`).
- **Список админов и алиасов читается один раз при старте бота** — любые
  правки `data/admins.json`/`data/aliases.json` требуют перезапуска
  (`systemctl restart teto-bot`).
- **Если в будущем приём голоса из voice-канала починят в py-cord** —
  `config.py` и `services/trigger_detector.py` содержат неиспользуемые
  сейчас заготовки (триггер-фразы, нечёткий поиск) на случай возврата к
  автоматическому прослушиванию.
