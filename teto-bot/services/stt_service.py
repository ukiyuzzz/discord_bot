"""
Распознавание речи через Groq Whisper API.

Принимает сырые аудио-байты (WAV, 16-bit PCM) и возвращает распознанный текст.
"""
import io

try:
    from groq import Groq
except Exception as exc:  # pragma: no cover - зависит от окружения
    Groq = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from config import GROQ_API_KEY, GROQ_STT_MODEL

_client = None


def _get_client():
    global _client
    if _client is None:
        if Groq is None:
            raise RuntimeError(f"Не удалось импортировать Groq-клиент: {_IMPORT_ERROR}") from _IMPORT_ERROR
        try:
            _client = Groq(api_key=GROQ_API_KEY)
        except Exception as exc:
            raise RuntimeError(f"Не удалось инициализировать Groq-клиент: {exc}") from exc
    return _client


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

    result = _get_client().audio.transcriptions.create(**kwargs)

    # В зависимости от response_format SDK может вернуть строку или объект с .text
    if isinstance(result, str):
        return result.strip()
    return getattr(result, "text", "").strip()
