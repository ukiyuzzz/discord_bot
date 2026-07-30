"""
Распознавание речи через Groq Whisper API.

Принимает сырые аудио-байты (WAV, 16-bit PCM) и возвращает распознанный текст.
"""
import io

from groq import Groq

from config import GROQ_API_KEY, GROQ_STT_MODEL

_client = Groq(api_key=GROQ_API_KEY)


def transcribe(wav_bytes: bytes, language_hint: str | None = None) -> str:
    """
    wav_bytes: содержимое WAV-файла целиком (с заголовком).
    language_hint: код языка ('ru', 'en', 'ja') если известен — ускоряет
                   и повышает точность распознавания. Можно не указывать,
                   Whisper сам определит язык.
    """
    audio_file = io.BytesIO(wav_bytes)
    audio_file.name = "utterance.wav"  # Groq SDK ждёт атрибут .name для определения формата

    kwargs = {
        "file": audio_file,
        "model": GROQ_STT_MODEL,
        "response_format": "text",
    }
    if language_hint:
        kwargs["language"] = language_hint

    result = _client.audio.transcriptions.create(**kwargs)

    # В зависимости от response_format SDK может вернуть строку или объект с .text
    if isinstance(result, str):
        return result.strip()
    return getattr(result, "text", "").strip()
