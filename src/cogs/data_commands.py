import io
import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands, Embed, Color
import aiosqlite
from matplotlib import pyplot as plt

from .utils import *


class DataCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="view_settings", description="View gather settings in this channel")
    async def view_settings(self, interaction: discord.Interaction):
        return

    @app_commands.command(name="gather_graph", description="View gathers vs hour graph for this channel")
    @app_commands.describe(
        emoji="Emoji to show reaction data for",
        user="User/role to filter by. Defaults to everyone.",
        start_date="Start date (YYYY-MM-DD) to get data for. Gets all data by default.",
        end_date="End date (YYYY-MM-DD) to get data for. Gets all data by default."
    )
    async def gather_graph(self, interaction: discord.Interaction, emoji: str, user: str, start_date: str | None = None, end_date: str | None = None):
        await interaction.response.defer(ephemeral=False)

        channel_id = getattr(interaction.channel, 'id', interaction.channel_id)
        channel_name = getattr(interaction.channel, 'name', str(interaction.channel))
        users = get_users_by_role(user)

        async with aiosqlite.connect(db_path) as connection:
            async with connection.execute(
                "SELECT timestamp FROM data WHERE channel_id = ? AND emoji = ? AND user in ?",
                (channel_id, emoji, users)
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await interaction.followup.send("No data found for this channel and emoji.")
            return

        hours = range(24)
        counts = [0] * 24

        if start_date:
            start_date = datetime.datetime.fromisoformat(start_date).date()
        else:
            start_date = datetime.datetime.fromtimestamp(rows[0][0], tz=ZoneInfo("America/New_York")).date()
        

        if end_date:
            end_date = datetime.datetime.fromisoformat(end_date).date()
        else:
            end_date = datetime.datetime.fromtimestamp(rows[-1][0], tz=ZoneInfo("America/New_York")).date()

        days = (end_date - start_date).days + 1

        for row in rows:
            d = datetime.datetime.fromtimestamp(row[0], tz=ZoneInfo("America/New_York"))
            if d.date() >= start_date and d.date() <= end_date:
                counts[d.hour] += 1

        averages = [count / days for count in counts]


        plt.figure(figsize=(6, 4), facecolor=plot_color_palette['background_color'])
        ax = plt.gca()
        ax.set_facecolor(plot_color_palette['axis_color'])

        plt.bar(hours, counts, color=plot_color_palette['object_color'])
        plt.title(f'Average Reaction Count from {start_date.isoformat()} to {end_date.isoformat()}')
        plt.xlabel('Hour [Eastern Time]')
        plt.ylabel('Average Reaction Count')
        plt.xticks(hours[::2], [f'{str(h*2)}:00' for h in range(12)])
        plt.xticks(rotation=60)

        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        plt.close()

        discord_file = discord.File(fp=buffer, filename="reactions_graph.png")

        await interaction.followup.send(
            file=discord_file
        )

        return

async def setup(bot: commands.Bot):
    await bot.add_cog(DataCommands(bot))