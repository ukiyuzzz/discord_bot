"""
Запрос к основной LLM (персона Тето) с учётом истории диалога и
возможностью пинговать людей/роли через function calling.

Function calling нужен, чтобы модель не пыталась сама "придумать" Discord ID
(риск галлюцинации) — вместо этого она вызывает ping_contact(name), а точный
ID подставляет наш код из services/alias_service.py.
"""
import json

try:
    from groq import Groq
except Exception as exc:  # pragma: no cover - зависит от окружения
    Groq = None
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None

from config import GROQ_API_KEY, GROQ_LLM_MODEL, SYSTEM_PROMPT
from memory import conversation_store
from services import alias_service

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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ping_contact",
            "description": (
                "Получить Discord-упоминание (пинг) человека или роли по имени "
                "из базы известных контактов сервера. Используй только если "
                "тебя явно просят кого-то позвать/упомянуть/пингануть."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Имя человека или название роли, как оно упомянуто в сообщении"}
                },
                "required": ["name"],
            },
        },
    }
]


def ask(channel_id: int, question: str, author_name: str | None = None) -> str:
    """
    channel_id: ключ истории диалога (память на канал).
    question: текст вопроса пользователя.
    author_name: отображаемое имя автора — добавляется в сообщение, чтобы
                 модель понимала, кто именно сейчас пишет (полезно в общих
                 каналах с несколькими собеседниками).
    """
    history = conversation_store.get_history(channel_id)

    user_content = f"От {author_name}: {question}" if author_name else question

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_content})

    # Модель может звать ping_contact не за один раз (например, если просят
    # пингануть сразу нескольких людей) — поэтому крутим цикл вызовов, а не
    # один раунд, и на КАЖДОМ запросе передаём tools, иначе Groq падает с
    # "Tool choice is none, but model called a tool", если модель решит
    # позвать инструмент ещё раз на "финальном" шаге.
    message = None
    for _ in range(5):  # защита от зацикливания
        response = _get_client().chat.completions.create(
            model=GROQ_LLM_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=300,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            break

        assistant_msg = {
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        }
        messages.append(assistant_msg)

        for tc in message.tool_calls:
            if tc.function.name == "ping_contact":
                args = json.loads(tc.function.arguments)
                mention = alias_service.get_mention(args.get("name", ""))
                result = mention if mention else "Контакт с таким именем не найден в базе"
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    answer = (message.content or "").strip()

    # В память кладём вопрос с именем автора — так и в истории видно, кто говорил
    conversation_store.add_message(channel_id, "user", user_content)
    conversation_store.add_message(channel_id, "assistant", answer)

    return answer
