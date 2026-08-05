import re

_TIMEOUT_MARKERS = ("тайм-аут", "мут", "timeout")

_DURATION_PATTERNS = [
    (re.compile(r"(?P<value>\d+)\s*(?:минут|минута|минуты|мин|m)\b", re.I), 60),
    (re.compile(r"(?P<value>\d+)\s*(?:час|часа|часов|h)\b", re.I), 3600),
    (re.compile(r"(?P<value>\d+)\s*(?:день|дня|дней|d)\b", re.I), 86400),
]


def parse_timeout_request(text: str):
    """Разбирает текст админ-команды и возвращает (target_name, duration_seconds)."""
    lower_text = text.lower()
    if not any(marker in lower_text for marker in _TIMEOUT_MARKERS):
        return None, None

    target_name = None
    mention_match = re.search(r"@([^\s@]+)", text)
    if mention_match:
        target_name = mention_match.group(1).strip(" ,.:;")

    if target_name is None:
        patterns = (
            re.compile(r"(?:отправь|выдай|запрети)\s+([^\s,.:;]+?)(?:\s+в\s+)?(?:тайм-аут|мут)", re.I),
            re.compile(r"(?:тайм-аут|мут|timeout)\s+(?:для\s+)?([^\s,.:;]+)", re.I),
        )
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                target_name = match.group(1).strip(" ,.:;")
                break

    duration_seconds = None
    for pattern, multiplier in _DURATION_PATTERNS:
        match = pattern.search(text)
        if match:
            duration_seconds = int(match.group("value")) * multiplier
            break

    return target_name, duration_seconds
