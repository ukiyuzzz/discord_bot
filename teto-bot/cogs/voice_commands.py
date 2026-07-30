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

    @discord.slash_command(name="join", description="Тето заходит в твой голосовой канал")
    async def join(self, ctx: discord.ApplicationContext):
        # Discord даёт только 3 секунды на первый ответ на interaction.
        # Подключение к voice-каналу может занять дольше — поэтому сразу
        # "откладываем" ответ (defer), а реальный текст отправляем позже
        # через ctx.respond(), у которого после defer() лимита в 3 секунды уже нет.
        await ctx.defer()

        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.respond("Зайди сначала в голосовой канал, а потом позови меня 🎤")
            return

        channel = ctx.author.voice.channel

        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()

        await ctx.respond(
            f"Зашла в **{channel.name}**! Пришли голосовое сообщение в любой текстовый канал — отвечу здесь голосом."
        )

    @discord.slash_command(name="leave", description="Тето выходит из голосового канала")
    async def leave(self, ctx: discord.ApplicationContext):
        await ctx.defer()

        if ctx.voice_client is None:
            await ctx.respond("Я и так не в голосовом канале.")
            return

        channel_id = ctx.voice_client.channel.id
        await ctx.voice_client.disconnect()
        conversation_store.clear_history(channel_id)
        await ctx.respond("Вышла из канала, до встречи! 👋")


def setup(bot: discord.Bot):
    bot.add_cog(VoiceCommands(bot))
