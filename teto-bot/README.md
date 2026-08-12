# Teto Bot — голосовой Discord-бот

Discord-бот, который распознаёт голосовые сообщения и текст с упоминанием бота, отвечает голосом через Fish Audio TTS, умеет пинговать людей/роли по имени и (для доверенных админов) выполнять модерацию сервера.

## Почему голосовые сообщения, а не прослушивание voice-канала

Изначально планировалось, что бот сам слушает голосовой канал и реагирует на триггер-фразу. Но с марта 2026 Discord сделал end-to-end шифрование (протокол **DAVE**) обязательным для всех голосовых звонков, и **приём голоса** в py-cord (версия 2.8.1 на момент написания) оказался полностью нерабочим — не только из-за незавершённой поддержки DAVE, но и из-за внутреннего бага самой библиотеки.

Поэтому вместо приёма голоса из voice-канала используется официальная фича Discord — **голосовые сообщения** (та самая "волна" с иконкой микрофона в чате) или обычные аудио-вложения. Это работает через давно стабильный API вложений, не связанный с проблемным приёмом голоса из voice-каналов.

**Отправка** голоса в voice-канал (TTS-ответ) работает нормально, поэтому бот может зайти в канал командой `/join` и отвечать там голосом.

## Выбор библиотек

- **py-cord** — интегрированная работа с Discord API, поддержка слэш-команд и voice-каналов
- **Groq Whisper** — быстрое распознавание речи (STT) с поддержкой множества языков
- **Groq LLM** — обработка текста и генерация ответов п��рсонажа Тето
- **Fish Audio SDK** — синтез речи (TTS) на основе предварительно обученной модели голоса
- **ffmpeg** — универсальная конвертация аудиоформатов для совместимости с Discord

## Структура проекта

```
teto-bot/
├── main.py                       # точка входа
├── config.py                     # env-переменные, лимит памяти, модели
├── data/
│   ├── aliases.example.json      # пример базы пингов
│   └── admins.example.json       # пример списка админов
├── cogs/
│   ├── voice_commands.py         # /join, /leave — вход/выход из voice-канала
│   └── voice_message_listener.py # приём сообщений, разветвление
├── services/
│   ├── stt_service.py            # Groq Whisper — речь в текст
│   ├── llm_service.py            # Groq LLM + память + function calling
│   ├── tts_service.py            # Fish Audio SDK — текст в речь
│   ├── action_classifier.py      # классифицирует команды модерации
│   ├── alias_service.py          # чтение aliases.json
│   ├── permission_service.py     # чтение admins.json
│   └── trigger_detector.py       # заготовка на будущее
├── memory/
│   └── conversation_store.py     # история диалога (лимит 8 сообщений)
└── utils/
    └── audio_utils.py            # конвертация и проигрывание аудио
```

## Установка

### Требования

- Python 3.8 или выше
- ffmpeg (для конвертации аудио)

### Локальная установка

1. Клонируй репозиторий:
```bash
git clone https://github.com/ukiyuzzz/discord_bot.git
cd discord_bot/teto-bot
```

2. Создай виртуальное окружение:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# или
venv\Scripts\activate     # Windows
```

3. Установи зависимости:
```bash
pip install -r requirements.txt
```

4. Установи ffmpeg (если не установлен):
```bash
# Linux (Ubuntu/Debian)
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg
```

### Конфигураци��

1. Скопируй `.env.example` в `.env` и заполни значения:
```bash
cp .env.example .env
```

Понадобятся:
- **DISCORD_TOKEN** — токен бота из [Discord Developer Portal](https://discord.com/developers/applications)
  - Включи `Message Content Intent` в интентах
  - При приглашении бота на сервер используй scope `bot` и `applications.commands`
  - Минимальные права: `Connect`, `Speak`, `Use Voice Activity`
- **GROQ_API_KEY** — API ключ с [console.groq.com](https://console.groq.com)
- **FISH_AUDIO_API_KEY** и **FISH_AUDIO_REFERENCE_ID** — ключ и ID голосовой модели из Fish Audio

2. Настрой пинги по именам (опционально):
```bash
cp data/aliases.example.json data/aliases.json
nano data/aliases.json
```

Формат:
```json
{
  "users": {
    "Имя": "Discord_ID"
  },
  "roles": {
    "Название роли": "Discord_Role_ID"
  }
}
```

3. Включи модерацию для админов (опционально):
```bash
cp data/admins.example.json data/admins.json
nano data/admins.json
```

Формат:
```json
{
  "admin_ids": [
    "Discord_ID"
  ]
}
```

### Запуск

```bash
python3 main.py
```

Проверка: отправь голосовое сообщение (или аудиофайл) в текстовый канал, где есть бот — он должен распознать текст и ответить голосом.

## Известные ограничения

- Обработка требует включённого `Message Content Intent` в Discord Developer Portal
- Конвертация аудио происходит через ffmpeg (должен быть установлен в системе)
- Обрабатывается только первое аудио-вложение в сообщении
- Язык автоматически определяется Whisper (можно зафиксировать под конкретный сервер)
- Пинги работают только по зарегистрированным именам в `data/aliases.json`
- Список админов и алиасов читается при старте бота (изменения требуют перезапуска)
