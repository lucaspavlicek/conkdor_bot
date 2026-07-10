import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands, Embed, Color
import aiosqlite
from matplotlib import pyplot as plt

from .utils import *


class MiscCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="next_00", description="View the next hour (:00) in major time zones.")
    async def next_00(self, interaction: discord.Interaction):
        now = datetime.datetime.now(tz=ZoneInfo('America/New_York'))
        next = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)

        embed = Embed(
            title="Next hour (:00) in major time zones",
            color=Color.pink()
        )
        embed.add_field(
            name="Eastern Time:",
            value=f"```{next.strftime('%I:%M %p')} / {next.strftime('%H:%M %Z')}```",
            inline=False
        )
        embed.add_field(
            name="Central European Time:",
            value=f"```{next.astimezone(ZoneInfo('Europe/Paris')).strftime('%I:%M %p')} / {next.astimezone(ZoneInfo('Europe/Paris')).strftime('%H:%M %Z')}```",
            inline=False
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(MiscCommands(bot))