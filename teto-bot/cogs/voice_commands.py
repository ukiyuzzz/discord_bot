"""
Команды управления присутствием бота в голосовом канале.

/join  — бот заходит в voice-канал того, кто вызвал команду.
         Если пользователь не в голосовом канале — бот сообщает об этом.
/leave — бот выходит из голосового канала.
"""
import discord
from discord.ext import commands

from memory import conversation_store


class VoiceCommands(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    async def _reply(self, ctx: discord.ApplicationContext, content: str):
        try:
            await ctx.followup.send(content)
        except Exception:
            await ctx.respond(content)

    @discord.slash_command(name="join", description="Тето заходит в твой голосовой канал")
    async def join(self, ctx: discord.ApplicationContext):
        # Discord даёт только 3 секунды на первый ответ на interaction.
        # Подключение к voice-каналу может занять дольше — поэтому сразу
        # "откладываем" ответ (defer), а реальный текст отправляем позже
        # через followup.send, который корректно работает после defer().
        await ctx.defer()

        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await self._reply(ctx, "Зайди сначала в голосовой канал, а потом позови меня 🎤")
            return

        channel = ctx.author.voice.channel

        try:
            if ctx.voice_client is not None:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()
        except Exception as exc:
            await self._reply(ctx, f"Не смогла зайти в канал: {exc}")
            return

        await self._reply(
            ctx,
            f"Зашла в **{channel.name}**! Пришли голосовое сообщение в любой текстовый канал — отвечу здесь голосом.",
        )

    @discord.slash_command(name="leave", description="Тето выходит из голосового канала")
    async def leave(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        if ctx.voice_client is None:
            await self._reply(ctx, "Я и так не в голосовом канале.")
            return

        channel_id = ctx.voice_client.channel.id
        try:
            await ctx.voice_client.disconnect()
        except Exception as exc:
            await self._reply(ctx, f"Не смогла выйти из канала: {exc}")
            return

        conversation_store.clear_history(channel_id)
        await self._reply(ctx, "Вышла из канала, до встречи! 👋")


def setup(bot: discord.Bot):
    bot.add_cog(VoiceCommands(bot))
