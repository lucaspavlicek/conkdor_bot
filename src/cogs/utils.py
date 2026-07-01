import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands
import re

import aiosqlite

db_path = Path(__file__).resolve().parents[2] / 'database.db'

def create_timestamp(t: int):
    now = datetime.datetime.now()
    local_dt = datetime.datetime(
        year=now.year,
        month=now.month,
        day=now.day,
        hour=t,
        minute=0,   
        tzinfo=ZoneInfo('America/New_York')
    )
    
    if local_dt.hour < now.hour:
        local_dt += datetime.timedelta(days=1)

    return f'<t:{int(local_dt.timestamp())}:t>'

time_choices = [
    app_commands.Choice(
        name=f'{hour}:00 Eastern time',
        value=str(hour)
    )
    for hour in range(24)
]

async def record_reactions(bot: discord.Client, channel_id: int, limit: int = 1000):
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden):
            print(f"Could not access or find channel with ID: {channel_id}")
            return []

    if not hasattr(channel, "history"):
        print(f"Channel {channel_id} does not support message history.")
        return []

    est_date = datetime.datetime.now(tz=ZoneInfo('America/New_York')).date().isoformat()
    timestamp_regex = r'<t:(\d+):t>'

    try:

        async for message in channel.history(limit=limit):
            match = re.search(timestamp_regex, message.content)
            if not match:
                continue  # Skip if no matching timestamp pattern found
            
            target_timestamp = match.group(1)

            for reaction in message.reactions:
                emoji_str = str(reaction.emoji)

                async for user in reaction.users():

                    async with aiosqlite.connect(db_path) as connection:
                        await connection.execute(
                            '''
                            INSERT INTO data (channel_id, emoji, timestamp, date, username, user_id, message_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                            ''',
                            (channel_id, emoji_str, target_timestamp, est_date, user.name, user.id, message.id),
                        )
                        await connection.commit()

    except discord.Forbidden:
        print(f"Missing permissions to read history in channel {channel_id}")
    except Exception as e:
        print(f"Error scanning reactions in channel {channel_id}: {e}")

async def reset_gathers(bot, channel_id):
    async with aiosqlite.connect(db_path) as connection:
        async with connection.execute(
            '''
            SELECT * FROM gather_channels WHERE id = ?;
            ''',
            (channel_id,),
        ) as cursor:
            row = await cursor.fetchone()

    if row is None:
        print(f"Channel ID {channel_id} not found in database.")
        return

    channel = bot.get_channel(channel_id)
    if channel is None:
        print(f"Channel ID {channel_id} not found in discord.")
        return
    
    print(f"Resetting channel: {channel_id}")

    try:
        deleted = await channel.purge(limit=None, reason="Daily reset")
        print(f"Deleted {len(deleted)} messages")

        hours = list(range(row[3], row[4]+1)) if row[3] <= row[4] else list(range(row[3], 24)) + list(range(row[4]+1))
        gather_times = [create_timestamp(h) for h in hours]

        for timestamp in gather_times:
            await channel.send(timestamp)

        if row[5] is not None:
            await channel.send(row[5])

    except Exception as exc:
        print(f"Failed to purge or send messages in channel {channel_id}: {exc}")

    print("Gathers reset complete.")

def get_users_by_role(role):

    if isinstance(role, discord.Role):
        return (member for member in role.members)
    elif isinstance(role, discord.User):
        return (role,)
    else:
        return []
    
plot_color_palette = {
    'background_color': "#5F5F5F",
    'axis_color': "#2B2B4B",
    'object_color': "#B082A7",
}