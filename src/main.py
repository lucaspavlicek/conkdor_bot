import asyncio
import discord
from discord.ext import commands
import logging
from dotenv import load_dotenv
import os
from pathlib import Path
import sqlite3
import aiosqlite

from cogs.utils import *


class ConkdorBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db: aiosqlite.Connection | None = None 
        self._synced: bool = False

    async def close(self):
        if self.db:
            await self.db.close()
        await super().close()

    async def on_ready(self):
        if not getattr(self, "_synced", False):
            try:
                await self.tree.sync()
                print("Synced global app commands")
                
            except Exception as e:
                print('Error syncing command tree:', e)
            self._synced = True
        print(f'Bot ready. Logged in as {self.user} (ID: {self.user.id})')
        print("Registered commands in local memory:", [cmd.name for cmd in self.tree.walk_commands()], '\n')

bot = ConkdorBot(command_prefix="!", intents=discord.Intents.all())

async def setup(bot: ConkdorBot):

    bot.db = await aiosqlite.connect(db_path)
    
    await bot.db.execute("PRAGMA foreign_keys = ON")
    async with bot.db.cursor() as cursor:
        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS guilds (
            id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL
        )
        """)

        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS gather_channels (
            id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL,
            guild_id INTEGER NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            message TEXT,
            reminder_time INTEGER,
            reminder_message TEXT,
            FOREIGN KEY(guild_id) REFERENCES guilds(id) ON DELETE CASCADE
        )
        """)

        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            timestamp TIME NOT NULL,
            date TEXT NOT NULL,
            username TEXT NOT NULL,
            user_id INT NOT NULL,
            message_id INT NOT NULL,
            FOREIGN KEY(channel_id) REFERENCES gather_channels(id) ON DELETE CASCADE
        )
        """)

        async with bot.db.execute("PRAGMA table_info(data)") as pragma_cursor:
            data_columns = [row[1] for row in await pragma_cursor.fetchall()]

        if 'date' not in data_columns:
            await bot.db.execute("ALTER TABLE data ADD COLUMN date TEXT")

    await bot.db.commit()
    print("Database connected and tables verified.")

    await bot.load_extension("cogs.misc_commands")
    await bot.load_extension("cogs.data_commands")
    await bot.load_extension("cogs.gathers_commands")
    await bot.load_extension("cogs.hourly_tasks")
    await bot.load_extension("cogs.guild_events")

def load_env():
    load_dotenv()
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        raise RuntimeError('DISCORD_TOKEN not set in environment')
    return token

async def main():
    async with bot:
        await setup(bot)
        await bot.start(load_env())

if __name__ == "__main__":
    asyncio.run(main())