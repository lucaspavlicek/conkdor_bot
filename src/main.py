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
        # Placeholder attribute to access the DB later
        self.db: aiosqlite.Connection | None = None 
        # Ensure we only sync the command tree once
        self._synced: bool = False

    async def close(self):
        # Clean up and close the database safely when the bot stops
        if self.db:
            await self.db.close()
        await super().close()

    async def on_ready(self):
        # Run a one-time sync of the application command tree after login
        if not getattr(self, "_synced", False):
            try:
                dev_guild = os.getenv('DEV_GUILD_ID')
                if dev_guild:

                    guild_object = discord.Object(id=int(dev_guild))
                    
                    self.tree.copy_global_to(guild=guild_object)
                    await self.tree.sync(guild=guild_object)
                    print(f"Synced app commands to dev guild {dev_guild}")
                else:
                    await self.tree.sync()
                    print("Synced global app commands")
            except Exception as e:
                print('Error syncing command tree:', e)
            self._synced = True
        print(f'Bot ready. Logged in as {self.user} (ID: {self.user.id})')
        print("Registered commands in local memory:", [cmd.name for cmd in self.tree.walk_commands()], '\n')

bot = ConkdorBot(command_prefix="!", intents=discord.Intents.all())

# The async setup function where the DB connection lives
async def setup(bot: ConkdorBot):
    # 1. Connect to the SQLite file asynchronously
    bot.db = await aiosqlite.connect(db_path)
    
    # 2. Setup your database tables if they do not exist yet
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
            FOREIGN KEY(guild_id) REFERENCES guilds(id) ON DELETE CASCADE
        )
        """)

        await cursor.execute("""
        CREATE TABLE IF NOT EXISTS data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            timestamp TIME NOT NULL,
            username TEXT NOT NULL,
            user_id INT NOT NULL,
            message_id INT NOT NULL,
            FOREIGN KEY(channel_id) REFERENCES gather_channels(id) ON DELETE CASCADE
        )
        """)
    await bot.db.commit()
    print("Database connected and tables verified.")

    # 3. Load your extensions/cogs here
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