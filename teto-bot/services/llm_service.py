"""
Запрос к LLM (через Groq) с учётом истории диалога (память на N сообщений).
"""
from groq import Groq

from config import GROQ_API_KEY, GROQ_LLM_MODEL, SYSTEM_PROMPT
from memory import conversation_store

_client = Groq(api_key=GROQ_API_KEY)


def ask(channel_id: int, question: str) -> str:
    """
    channel_id: используется как ключ для истории диалога (у каждого
                голосового канала — своя память).
    question: текст вопроса пользователя (уже без триггер-фразы).
    Возвращает текст ответа и сам сохраняет обмен в память.
    """
    history = conversation_store.get_history(channel_id)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": question})

    response = _client.chat.completions.create(
        model=GROQ_LLM_MODEL,
        messages=messages,
        temperature=0.7,
        max_tokens=300,
    )
    answer = response.choices[0].message.content.strip()

    conversation_store.add_message(channel_id, "user", question)
    conversation_store.add_message(channel_id, "assistant", answer)

    return answer
