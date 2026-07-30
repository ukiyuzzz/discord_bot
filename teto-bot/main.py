"""
Точка входа бота Тето.
Запуск: python3 main.py (или через systemd-сервис на VPS).
"""
import discord

from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = discord.Bot(intents=intents)

bot.load_extension("cogs.voice_commands")
bot.load_extension("cogs.voice_message_listener")


@bot.event
async def on_ready():
    print(f"Тето на связи! Вошла как {bot.user} (id={bot.user.id})")


if __name__ == "__main__":
    if not DISCORD_TOKEN:
        raise RuntimeError("DISCORD_TOKEN не найден — проверь файл .env")
    bot.run(DISCORD_TOKEN)
