"""
Обработка обращений к Тето: голосовые сообщения и текст с упоминанием бота.

Два способа обратиться к боту в текстовом канале:
  1. Голосовое сообщение (или любой аудио-файл) — бот скачивает вложение,
     распознаёт речь (Groq Whisper).
  2. Обычный текст с упоминанием бота (@リアルテト твой вопрос) — текст
     берётся напрямую, без STT.

Дальше сообщение разветвляется:
  - Если автор — админ (services/permission_service.is_admin) И текст
    похож на команду модерации (services/action_classifier), бот выполняет
    её (кик/бан/роль) и отвечает результатом. Прав на это НЕ решает LLM —
    только код (см. permission_service).
  - Иначе — обычный разговор: LLM (Groq) с памятью на канал → Fish Audio
    TTS → ответ голосом (в voice-канале либо файлом в текстовом).
"""
import asyncio
import io

import discord
from discord.ext import commands

from services import stt_service, llm_service, tts_service, action_classifier, permission_service, alias_service
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

            await self._handle_incoming_text(message, text)

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
            await self._handle_incoming_text(message, text, already_typing=True)

    async def _handle_incoming_text(self, message: discord.Message, text: str, already_typing: bool = False):
        async def _process():
            # Модерация проверяется ДО любого обращения к LLM-персоне —
            # и только если автор есть в списке админов (код, не LLM, решает это).
            if permission_service.is_admin(message.author.id):
                handled = await self._try_handle_admin_action(message, text)
                if handled:
                    return

            await self._handle_conversation(message, text)

        if already_typing:
            await _process()
        else:
            async with message.channel.typing():
                await _process()

    async def _try_handle_admin_action(self, message: discord.Message, text: str) -> bool:
        try:
            action_name, args = await asyncio.to_thread(action_classifier.classify, text)
        except Exception as e:
            await message.channel.send(f"Ошибка классификатора модерации (Groq): {e}")
            return True

        if action_name is None:
            return False

        target_name = args.get("target_name", "")
        try:
            target = self._resolve_target(message, target_name)
        except Exception as e:
            await message.channel.send(f"Ошибка при поиске цели «{target_name}»: {e}")
            return True

        if target is None:
            await message.channel.send(
                f"Не смогла понять, кого ты имеешь в виду под «{target_name}» — "
                f"упомяни человека напрямую (@ник) или добавь его в data/aliases.json."
            )
            return True

        try:
            if action_name == "kick_from_voice":
                if target.voice and target.voice.channel:
                    await target.move_to(None)
                    await message.channel.send(f"Отключила {target.mention} от голосового канала.")
                else:
                    await message.channel.send(f"{target.mention} сейчас не в голосовом канале.")

            elif action_name == "kick_from_server":
                reason = args.get("reason") or "Без указанной причины"
                await target.kick(reason=reason)
                await message.channel.send(f"Выгнала {target.display_name} с сервера. Причина: {reason}")

            elif action_name == "ban_member":
                reason = args.get("reason") or "Без указанной причины"
                await target.ban(reason=reason)
                await message.channel.send(f"Забанила {target.display_name}. Причина: {reason}")

            elif action_name == "create_and_assign_role":
                role_name = args.get("role_name") or "Новая роль"
                role = await message.guild.create_role(name=role_name, permissions=discord.Permissions.none())
                await target.add_roles(role)
                await message.channel.send(f"Создала роль «{role_name}» и выдала её {target.mention}.")

            print(f"[Модерация] {message.author} запросил '{action_name}' над {target} в #{message.channel}")

        except discord.Forbidden:
            await message.channel.send(
                "Не хватает прав на это действие — проверь, что роль бота выше роли цели "
                "и что у бота включены нужные права (Kick/Ban Members, Manage Roles, Move Members)."
            )
        except Exception as e:
            await message.channel.send(f"Ошибка при выполнении действия: {e}")

        return True

    def _resolve_target(self, message: discord.Message, target_name: str):
        # 1. Явное @упоминание в сообщении — самый надёжный источник, им и пользуемся.
        # Упоминание самого бота (которым его вызвали) целью быть не может.
        mentions = [m for m in message.mentions if m.id != self.bot.user.id]
        if mentions:
            return mentions[0]
        # 2. Иначе пробуем найти по имени в базе алиасов (только зарегистрированные записи).
        mention = alias_service.get_mention(target_name)
        if mention and mention.startswith("<@") and not mention.startswith("<@&"):
            user_id = int(mention.strip("<@!>"))
            return message.guild.get_member(user_id)
        return None

    async def _handle_conversation(self, message: discord.Message, text: str):
        try:
            answer = await asyncio.to_thread(
                llm_service.ask, message.channel.id, text, message.author.display_name
            )
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


def setup(bot: discord.Bot):
    bot.add_cog(VoiceMessageListener(bot))
