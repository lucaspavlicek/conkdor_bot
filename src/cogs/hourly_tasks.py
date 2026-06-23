import asyncio
import datetime
import aiosqlite
from zoneinfo import ZoneInfo

from discord.ext import commands, tasks

from .utils import db_path, reset_gathers, record_reactions

hours = [
    datetime.time(hour=i, minute=0, second=0, tzinfo=ZoneInfo('America/New_York'))
    for i in range(24)
]

class HourlyTasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.hourly_loop.start()

    def cog_unload(self):
        self.hourly_loop.cancel()

    @tasks.loop(time=hours)
    async def hourly_loop(self):
        hour = datetime.datetime.now(tz=ZoneInfo('America/New_York')).hour
        print(f'Running hourly check for {hour}:00 Eastern time.')
        
        await self.process_resets(hour)
        await self.send_reminders(hour)

    async def process_resets(self, hour):
        async with aiosqlite.connect(db_path) as connection:
            async with connection.execute(
                '''
                SELECT id FROM gather_channels WHERE end_time = ?;
                ''',
                (hour-1,),
            ) as cursor:
                ids = await cursor.fetchall()

        print(f'Found {len(ids)} channels to reset for this hour.')

        for channel_id in ids:
            await record_reactions(self.bot, channel_id[0])
            await reset_gathers(self.bot, channel_id[0])

    async def send_reminders(self, hour):
        async with aiosqlite.connect(db_path) as connection:
            async with connection.execute(
                '''
                SELECT id, reminder_message FROM gather_channels WHERE reminder_time = ?;
                ''',
                (hour,),
            ) as cursor:
                channels = await cursor.fetchall()

        print(f'Found {len(channels)} channels to send reminders for this hour.')

        for channel_id, reminder_message in channels:
            channel = self.bot.get_channel(channel_id)
            if channel is not None and reminder_message:
                try:
                    await channel.send(reminder_message)
                except Exception as e:
                    print(f"Error sending reminder to channel {channel_id}: {e}")

async def setup(bot):
    await bot.add_cog(HourlyTasks(bot))
