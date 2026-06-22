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


async def setup(bot: commands.Bot):
    await bot.add_cog(MiscCommands(bot))