"""
Читает data/admins.json — список Discord ID пользователей, которым
разрешено просить бота выполнить модерационное действие (кик/бан/роль).

Файл правится вручную на сервере (см. README, раздел "Модерация").
Пример структуры — в data/admins.example.json.

ВАЖНО: это единственное место, где решается, разрешено ли действие.
Проверка происходит в коде ДО обращения к любой LLM — сама модель
никогда не решает, кому что можно.
"""
import json
import os

_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "admins.json")

_cache = None


def reload():
    global _cache
    if not os.path.exists(_PATH):
        _cache = []
        return _cache
    with open(_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    _cache = [int(uid) for uid in data.get("admin_ids", [])]
    return _cache


def _load():
    global _cache
    if _cache is None:
        reload()
    return _cache


def is_admin(user_id: int) -> bool:
    return user_id in _load()
