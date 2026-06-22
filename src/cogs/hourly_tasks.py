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

async def setup(bot):
    await bot.add_cog(HourlyTasks(bot))
