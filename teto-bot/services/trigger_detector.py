"""
Проверка: содержит ли распознанный текст одну из триггер-фраз.

STT не идеален (особенно на смеси языков), поэтому сравниваем не строго,
а через rapidfuzz.partial_ratio с порогом из config.TRIGGER_FUZZY_THRESHOLD.
"""
import re
from difflib import SequenceMatcher

from rapidfuzz import fuzz

from config import TRIGGER_PHRASES, TRIGGER_FUZZY_THRESHOLD


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\sа-яёa-zぁ-んァ-ヶー一-龯]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def detect_trigger(text: str):
    """
    Возвращает (True, question) если триггер найден, иначе (False, None).

    question — это часть текста ПОСЛЕ триггер-фразы (если она есть),
    иначе весь текст (например, если человек сказал только "тето ответь"
    в одном чанке, а вопрос будет в следующем — это уже логика вызывающего
    кода в voice_listener.py).
    """
    normalized = _normalize(text)
    if not normalized:
        return False, None

    best_score = 0
    best_phrase = None
    for phrase in TRIGGER_PHRASES:
        score = fuzz.partial_ratio(_normalize(phrase), normalized)
        if score > best_score:
            best_score = score
            best_phrase = phrase

    if best_score < TRIGGER_FUZZY_THRESHOLD:
        return False, None

    # Пытаемся найти позицию совпадения, чтобы отрезать вопрос от триггера.
    # Это эвристика: точную границу fuzzy-match не даёт, поэтому берём
    # самый длинный совпадающий блок и всё, что идёт после него.
    matcher = SequenceMatcher(None, _normalize(best_phrase), normalized)
    match = matcher.find_longest_match(0, len(_normalize(best_phrase)), 0, len(normalized))
    tail = normalized[match.b + match.size:].strip()

    return True, tail if tail else None
