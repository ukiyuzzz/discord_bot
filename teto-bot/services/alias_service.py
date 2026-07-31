"""
Читает data/aliases.json — соответствия "имя" → Discord-упоминание.

Файл правится вручную на сервере (см. README, раздел "Пинги по имени").
Пример структуры — в data/aliases.example.json.

Специально сделано через простой JSON-файл, а не БД/slash-команды — чтобы
администратор мог сам контролировать список без дополнительных прав в боте.
"""
import json
import os

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "aliases.json")

# Эти "имена" никогда нельзя резолвить, даже если их случайно/намеренно
# впишут в aliases.json — иначе через безобидный на вид пинг можно
# устроить рассылку всему серверу.
_FORBIDDEN_NAMES = {"everyone", "here", "@everyone", "@here"}

_cache = None


def reload():
    global _cache
    if not os.path.exists(_PATH):
        _cache = {"users": {}, "roles": {}}
        return _cache
    with open(_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("users", {})
    data.setdefault("roles", {})
    _cache = data
    return _cache


def _load():
    global _cache
    if _cache is None:
        reload()
    return _cache


def get_mention(name: str) -> str | None:
    """
    Ищет имя (регистронезависимо) сначала среди пользователей, потом среди
    ролей. Возвращает готовую строку упоминания ("<@id>" или "<@&id>")
    либо None, если имя не найдено или запрещено.
    """
    name_lower = name.strip().lower()
    if name_lower in _FORBIDDEN_NAMES:
        return None

    data = _load()

    for alias, discord_id in data["users"].items():
        if alias.strip().lower() == name_lower:
            return f"<@{discord_id}>"

    for alias, discord_id in data["roles"].items():
        if alias.strip().lower() == name_lower:
            return f"<@&{discord_id}>"

    return None
