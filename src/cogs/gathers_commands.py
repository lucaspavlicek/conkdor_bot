import datetime
from zoneinfo import ZoneInfo

import discord
from discord import channel
from discord.ext import commands
from discord import app_commands, Embed, Color
from pathlib import Path
import aiosqlite

from .utils import *


class GathersCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def create_embed(
        self,
        channel_id: int,
        start_val: int,
        end_val: int,
        message_val: str | None
    ):
        embed=Embed(title=f'Gather settings for <#{channel_id}>', color=Color.pink())
        embed.add_field(name='Start Time:', value=create_timestamp(start_val), inline=False)
        embed.add_field(name='End Time:', value=create_timestamp(end_val), inline=False)
        embed.add_field(name='Message:', value=message_val if message_val is not None else "None", inline=False)
        embed.add_field(name='Resets at:', value=create_timestamp((end_val+1)%24), inline=False)

        return embed

    @app_commands.command(name="setup_gathers", description="Setup gathers in the current channel")
    @app_commands.describe(start_time="First gather time of the day. Default 12:00 Eastern.")
    @app_commands.choices(start_time=time_choices)
    @app_commands.describe(end_time="Last gather time of the day. Default 00:00 Eastern.")
    @app_commands.choices(end_time=time_choices)
    @app_commands.describe(message="Message when gathers reset. No message by default.")
    async def setup_gathers(
        self,
        interaction: discord.Interaction,
        start_time: str = time_choices[12].value,
        end_time: str = time_choices[0].value,
        message: str | None = None
    ):
        await interaction.response.defer(ephemeral=False)

        # Prepare values
        channel_id = getattr(interaction.channel, 'id', interaction.channel_id)
        channel_name = getattr(interaction.channel, 'name', str(interaction.channel))
        guild_discord_id = interaction.guild_id
        start_val = int(getattr(start_time, "value", start_time))
        end_val = int(getattr(end_time, "value", end_time))
        message_val = message if message is not None else None

        sql = '''
        INSERT INTO gather_channels (id, name, guild_id, start_time, end_time, message)
        VALUES (?, ?, (SELECT id FROM guilds WHERE id = ?), ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            start_time = excluded.start_time,
            end_time = excluded.end_time,
            message = excluded.message
        ;'''

        try:
            async with aiosqlite.connect(db_path) as connection:
                await connection.execute(sql, (channel_id, channel_name, guild_discord_id, start_val, end_val, message_val))
                await connection.commit()

            embed = self.create_embed(channel_id, start_val, end_val, message_val)
            await interaction.followup.send(embed=embed, ephemeral=False)
        except Exception as exc:
            await interaction.followup.send(f"Failed to save gather channel: {exc}", ephemeral=False)


    @app_commands.command(name="view_settings", description="View gather settings in this channel")
    async def view_settings(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        channel_id = getattr(interaction.channel, 'id', interaction.channel_id)

        try:
            async with aiosqlite.connect(db_path) as connection:
                async with connection.execute(
                    'SELECT start_time, end_time, message FROM gather_channels WHERE id = ?',
                    (channel_id,)
                ) as cursor:
                    row = await cursor.fetchone()

            if not row:
                await interaction.followup.send("No gather settings found for this channel. You can set them up using `/setup_gathers`.")
                return

            start_val, end_val, message_val = row
            embed = self.create_embed(channel_id, start_val, end_val, message_val)
            await interaction.followup.send(embed=embed, ephemeral=False)
        except Exception as exc:
            await interaction.followup.send(f"Failed to fetch settings: {exc}", ephemeral=False)

    @app_commands.command(name="find_gather_channels", description="List the channels which have gathers setup in this server")
    async def find_gather_channels(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        guild_id = getattr(interaction.guild, 'id', interaction.guild_id)

        try:
            async with aiosqlite.connect(db_path) as connection:
                async with connection.execute(
                    'SELECT id FROM gather_channels WHERE guild_id = ?',
                    (guild_id,)
                ) as cursor:
                    rows = await cursor.fetchall()

            if not rows:
                await interaction.followup.send("No gather channels found in this server. You can set one up using `/setup_gathers` in a chosen channel.")
                return


            embed=Embed(title=f'Gather channels in {interaction.guild.name}', color=Color.pink())
            channels_str = ""

            for row in rows:
                channel_id = row[0]
                channels_str += f"- <#{channel_id}>\n"

            embed.description = channels_str
            await interaction.followup.send(embed=embed, ephemeral=False)
        except Exception as exc:
            await interaction.followup.send(f"Failed to fetch gather channels: {exc}", ephemeral=False)


    @app_commands.command(name="manual_reset", description="Manually reset gathers in this channel right now")
    async def manual_reset(self, interaction: discord.Interaction):
        channel_id = getattr(interaction.channel, 'id', interaction.channel_id)

        await reset_gathers(self.bot, channel_id)


    @app_commands.command(name="remove_gathers", description="Stop resetting gathers in this channel")
    async def remove_gathers(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)

        channel_id = getattr(interaction.channel, 'id', interaction.channel_id)

        try:
            async with aiosqlite.connect(db_path) as connection:
                async with connection.execute(
                    'DELETE FROM gather_channels WHERE id = ?', 
                    (channel_id,)
                ) as cursor:
                    await connection.commit()
                    
                    if cursor.rowcount == 0:
                        await interaction.followup.send("No gathers are setup for this channel.")
                    else:
                        await interaction.followup.send("Gather settings successfully removed. Conkdor will stop resetting this channel.")
        except Exception as exc:
            await interaction.followup.send(f"Failed to remove gather channel: {exc}", ephemeral=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(GathersCommands(bot))