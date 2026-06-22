from discord.ext import commands
from pathlib import Path
import aiosqlite

from .utils import *


class GuildEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def add_guild_to_table(self, guild):
        async with aiosqlite.connect(db_path) as connection:
            await connection.execute(
                '''
                INSERT INTO guilds (id, name)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET name = excluded.name
                ''',
                (guild.id, guild.name),
            )
            await connection.commit()

    async def remove_guild_from_table(self, guild_name):
        async with aiosqlite.connect(db_path) as connection:
            await connection.execute(
                'DELETE FROM guilds WHERE name = ?',
                (guild_name,),
            )
            await connection.commit()

    @commands.Cog.listener()
    async def on_ready(self):

        bot_names = {guild.name for guild in self.bot.guilds}
        async with aiosqlite.connect(db_path) as connection:
            connection.row_factory = aiosqlite.Row
            async with connection.execute('SELECT name FROM guilds') as cursor:
                rows = await cursor.fetchall()

            db_names = {row['name'] for row in rows}

        missing_names = bot_names - db_names
        extra_names = db_names - bot_names

        if missing_names or extra_names:
            print('Reconciling guild name discrepancies:')
        for name in missing_names:
            print(f'  Adding missing guild row: {name}')
            guild = next((guild for guild in self.bot.guilds if guild.name == name), None)
            if guild is not None:
                await self.add_guild_to_table(guild)

        for name in extra_names:
            print(f'  Removing extra guild row: {name}')
            await self.remove_guild_from_table(name)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        print(f"Bot joined guild: {guild.name} ({guild.id})")
        await self.add_guild_to_table(guild)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        print(f"Bot removed from guild: {guild.name} ({guild.id})")
        await self.remove_guild_from_table(guild.name)

async def setup(bot):
    await bot.add_cog(GuildEvents(bot))
