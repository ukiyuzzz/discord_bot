"""
Определяет, просит ли админ выполнить модерационное действие, и с какими
параметрами — но НЕ выполняет его сам. Реальное исполнение (кик/бан/роль)
делает cogs/voice_message_listener.py — так сама LLM не имеет прямого
доступа к Discord API, только классифицирует намерение.

Используется отдельная, более быстрая/дешёвая модель (ACTION_LLM_MODEL),
чтобы не грузить основную персону Тето инструкциями про модерацию.

ВАЖНО: этот классификатор вызывается ТОЛЬКО если автор сообщения уже
прошёл проверку services/permission_service.is_admin() — сама LLM
никогда не участвует в решении "можно ли этому человеку".
"""
import json

from groq import Groq

from config import GROQ_API_KEY, ACTION_LLM_MODEL

_client = Groq(api_key=GROQ_API_KEY)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "kick_from_voice",
            "description": "Отключить пользователя от голосового канала (пользователь остаётся на сервере)",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_name": {"type": "string", "description": "Имя/ник упомянутого пользователя, как оно написано в сообщении"}
                },
                "required": ["target_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kick_from_server",
            "description": "Выгнать пользователя с сервера без бана (сможет вернуться по новому инвайту)",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_name": {"type": "string"},
                    "reason": {"type": "string", "description": "Причина, если указана в сообщении"},
                },
                "required": ["target_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ban_member",
            "description": "Забанить пользователя на сервере (не сможет вернуться по инвайту)",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_name": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["target_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_and_assign_role",
            "description": "Создать новую роль без особых прав и выдать её пользователю",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_name": {"type": "string"},
                    "role_name": {"type": "string", "description": "Название новой роли"},
                },
                "required": ["target_name", "role_name"],
            },
        },
    },
]

SYSTEM_PROMPT = (
    "Ты классификатор команд модерации Discord-сервера. Тебе дают сообщение "
    "от администратора сервера. Если это явная просьба выполнить модерационное "
    "действие (отключить от войса, кикнуть с сервера, забанить, выдать роль) — "
    "вызови СООТВЕТСТВУЮЩУЮ функцию с извлечёнными параметрами. Если сообщение "
    "не является явной командой модерации (обычный вопрос, разговор, "
    "неоднозначная фраза) — не вызывай никакую функцию."
)


def classify(text: str):
    """
    Возвращает (action_name, args_dict), если распознана явная команда
    модерации, иначе (None, None).
    """
    response = _client.chat.completions.create(
        model=ACTION_LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        tools=TOOLS,
        tool_choice="auto",
        temperature=0,
        max_tokens=200,
    )
    message = response.choices[0].message

    if not message.tool_calls:
        return None, None

    call = message.tool_calls[0]
    args = json.loads(call.function.arguments)
    return call.function.name, args
