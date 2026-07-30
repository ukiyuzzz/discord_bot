"""
Синтез речи через официальный fish-audio-sdk.

Используем бесплатную модель s2.1-pro-free (без списания платного баланса,
доступна без ограничения по объёму до 31 августа 2026 по Fair Use Policy —
см. https://fish.audio/blog/s2-1-pro-free-api/).

Документация: https://docs.fish.audio
"""
from fish_audio_sdk import Session, TTSRequest

from config import FISH_AUDIO_API_KEY, FISH_AUDIO_REFERENCE_ID, FISH_AUDIO_MODEL

_session = Session(FISH_AUDIO_API_KEY)


def synthesize(text: str) -> bytes:
    """
    Возвращает mp3-байты синтезированной речи голосом Тето
    (reference_id задаётся в .env как FISH_AUDIO_REFERENCE_ID).
    """
    chunks = []
    request = TTSRequest(text=text, reference_id=FISH_AUDIO_REFERENCE_ID)
    # Второй позиционный аргумент — backend/модель. s2.1-pro-free — бесплатная.
    for chunk in _session.tts(request, FISH_AUDIO_MODEL):
        chunks.append(chunk)
    return b"".join(chunks)
