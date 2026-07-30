"""
Обработка обращений к Тето: голосовые сообщения и текст с упоминанием бота.

Два способа обратиться к боту в текстовом канале:
  1. Голосовое сообщение (или любой аудио-файл) — бот скачивает вложение,
     распознаёт речь (Groq Whisper), дальше как в пункте 2.
  2. Обычный текст с упоминанием бота (@リアルテト твой вопрос) — текст
     берётся напрямую, без STT.

В обоих случаях дальше: LLM (Groq) с памятью до 8 сообщений на канал →
Fish Audio TTS → если бот подключён к voice-каналу на сервере — ответ
проигрывается там, иначе прикрепляется mp3-файлом в тот же текстовый канал.

Почему не приём голоса из voice-канала напрямую: см. README, раздел
"Почему голосовые сообщения, а не прослушивание voice-канала".
"""
import asyncio
import io

import discord
from discord.ext import commands

from services import stt_service, llm_service, tts_service
from utils import audio_utils

AUDIO_EXTENSIONS = (".ogg", ".mp3", ".wav", ".m4a", ".webm", ".oga")


def _is_audio_attachment(attachment: discord.Attachment) -> bool:
    if attachment.content_type and attachment.content_type.startswith("audio/"):
        return True
    return attachment.filename.lower().endswith(AUDIO_EXTENSIONS)


class VoiceMessageListener(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        audio_attachments = [a for a in message.attachments if _is_audio_attachment(a)]

        if audio_attachments:
            await self._handle_voice_message(message, audio_attachments[0])
            return

        if self.bot.user in message.mentions:
            text = message.content
            for mention in (f"<@{self.bot.user.id}>", f"<@!{self.bot.user.id}>"):
                text = text.replace(mention, "")
            text = text.strip()

            if not text:
                await message.reply("Слушаю! Напиши вопрос вместе с упоминанием меня 🎤")
                return

            await self._handle_question(message, text)

    async def _handle_voice_message(self, message: discord.Message, attachment: discord.Attachment):
        async with message.channel.typing():
            try:
                raw_bytes = await attachment.read()
                wav_bytes = await asyncio.to_thread(audio_utils.convert_to_wav_bytes, raw_bytes)
                text = await asyncio.to_thread(stt_service.transcribe, wav_bytes)
            except Exception as e:
                await message.reply(f"Не смогла обработать голосовое сообщение: {e}")
                return

            if not text:
                await message.reply("Не удалось распознать речь в этом сообщении 😔 Попробуй ещё раз.")
                return

            await message.reply(f"Расслышала: *{text}*")
            await self._handle_question(message, text, already_typing=True)

    async def _handle_question(self, message: discord.Message, text: str, already_typing: bool = False):
        async def _process():
            try:
                answer = await asyncio.to_thread(llm_service.ask, message.channel.id, text)
            except Exception as e:
                await message.channel.send(f"Ошибка при обращении к LLM (Groq): {e}")
                return

            try:
                audio_bytes = await asyncio.to_thread(tts_service.synthesize, answer)
            except Exception as e:
                await message.channel.send(f"Ошибка при обращении к TTS (Fish Audio): {e}\n\nОтвет текстом: {answer}")
                return

            voice_client = discord.utils.get(self.bot.voice_clients, guild=message.guild)
            if voice_client and voice_client.is_connected():
                audio_utils.play_bytes_in_voice(voice_client, audio_bytes)
                await message.channel.send(f"🗣️ {answer}")
            else:
                await message.channel.send(
                    content=f"🗣️ {answer}",
                    file=discord.File(io.BytesIO(audio_bytes), filename="teto_answer.mp3"),
                )

        if already_typing:
            await _process()
        else:
            async with message.channel.typing():
                await _process()


def setup(bot: discord.Bot):
    bot.add_cog(VoiceMessageListener(bot))
