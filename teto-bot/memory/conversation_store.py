"""
In-memory хранилище истории диалога.

Ключ — id голосового канала (int), значение — deque с последними
config.MEMORY_LIMIT сообщениями в формате {"role": ..., "content": ...},
готовом для передачи в LLM API.

Важно: это хранилище живёт только пока работает процесс бота.
Если нужно переживать перезапуски — замени на Redis/SQLite (структура
интерфейса ниже это позволяет сделать без изменений в остальном коде).
"""
from collections import deque

from config import MEMORY_LIMIT

_store: dict[int, deque] = {}


def get_history(channel_id: int) -> list[dict]:
    return list(_store.get(channel_id, deque()))


def add_message(channel_id: int, role: str, content: str) -> None:
    if channel_id not in _store:
        _store[channel_id] = deque(maxlen=MEMORY_LIMIT)
    _store[channel_id].append({"role": role, "content": content})


def clear_history(channel_id: int) -> None:
    _store.pop(channel_id, None)
