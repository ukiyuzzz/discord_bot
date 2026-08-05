"""
Синтез речи через официальный fish-audio-sdk.

Используем бесплатную модель s2.1-pro-free (без списания платного баланса,
доступна без ограничения по объёму до 31 августа 2026 по Fair Use Policy —
см. https://fish.audio/blog/s2-1-pro-free-api/).

Документация: https://docs.fish.audio
"""
try:
    from fish_audio_sdk import Session, TTSRequest
except Exception as exc:  # pragma: no cover - зависит от окружении
    Session = None
    TTSRequest = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from config import FISH_AUDIO_API_KEY, FISH_AUDIO_REFERENCE_ID, FISH_AUDIO_MODEL

_session = None


def _get_session():
    global _session
    if _session is None:
        if Session is None or TTSRequest is None:
            raise RuntimeError(f"Не удалось импортировать Fish Audio SDK: {_IMPORT_ERROR}") from _IMPORT_ERROR
        try:
            _session = Session(FISH_AUDIO_API_KEY)
        except Exception as exc:
            raise RuntimeError(f"Не удалось инициализировать Fish Audio SDK: {exc}") from exc
    return _session


def synthesize(text: str) -> bytes:
    """
    Возвращает mp3-байты синтезированной речи голосом Тето
    (reference_id задаётся в .env как FISH_AUDIO_REFERENCE_ID).
    """
    chunks = []
    session = _get_session()
    request = TTSRequest(text=text, reference_id=FISH_AUDIO_REFERENCE_ID)
    # Второй позиционный аргумент — backend/модель. s2.1-pro-free — бесплатная.
    for chunk in session.tts(request, FISH_AUDIO_MODEL):
        chunks.append(chunk)
    return b"".join(chunks)
