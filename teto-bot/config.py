"""
Центральная конфигурация бота.
Все "магические числа" и настраиваемые параметры собраны здесь,
чтобы не искать их по всему коду.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Discord ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# --- Groq (STT + LLM) ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")

# --- Fish Audio (TTS) ---
FISH_AUDIO_API_KEY = os.getenv("FISH_AUDIO_API_KEY")
FISH_AUDIO_REFERENCE_ID = os.getenv("FISH_AUDIO_REFERENCE_ID")
# s2.1-pro-free — бесплатная модель Fish Audio (без лимита по объёму,
# доступна минимум до 31.08.2026 по Fair Use Policy). Не требует баланса.
FISH_AUDIO_MODEL = os.getenv("FISH_AUDIO_MODEL", "s2.1-pro-free")

# --- Память диалога ---
MEMORY_LIMIT = 8  # хранится последние N сообщений (user+assistant вместе)

# --- Триггер-фразы (НЕ используются в текущей push-to-talk версии) ---
# Изначально задумывались для постоянного прослушивания канала, но из-за
# незавершённой поддержки Discord DAVE в py-cord сейчас вместо них
# используются явные команды /talk и /stop (см. cogs/voice_listener.py).
# Оставлено в конфиге на случай, если для этого захочется вернуться
# к постоянному прослушиванию, когда библиотека это починит.
# Пишем в нижнем регистре, без знаков препинания — сравнение тоже
# нормализует текст перед проверкой.
TRIGGER_PHRASES = [
    "тето ответь",
    "тэто ответь",
    "teto answer",
    "テト 答えてください",
    "テト、答えてください",
]

# Порог нечёткого совпадения (0-100). STT иногда искажает фразу,
# поэтому сравниваем не строго, а с допуском.
TRIGGER_FUZZY_THRESHOLD = 78

# --- VAD / нарезка речи на утерансы ---
# Через сколько миллисекунд тишины считаем, что человек закончил фразу
SILENCE_TIMEOUT_MS = 700
# Минимальная длительность речи, чтобы не гонять STT на случайный шум
MIN_UTTERANCE_MS = 300

# --- Персона Тето для системного промпта LLM ---
SYSTEM_PROMPT = (
    "Ты — Тето (Kasane Teto), дружелюбный голосовой ассистент на Discord-сервере. "
    "Отвечай кратко и по делу (2-4 предложения), твой ответ будет озвучен голосом, "
    "поэтому избегай списков, markdown и длинных технических простыней текста."
)
