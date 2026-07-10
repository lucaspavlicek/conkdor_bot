from calendar import weekday
import io
import datetime
import traceback
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

    def create_date_timestamp(self, d: datetime.date, h: int = 0):
        t = datetime.time(h, 0, 0)
        dt = datetime.datetime.combine(d, t, tzinfo=ZoneInfo('America/New_York'))
        return f'<t:{int(dt.timestamp())}:d>'
    
    def count_weekdays(self, start_date: datetime.date, end_date: datetime.date, weekday: int):
        return max(1, sum(1 for i in range((end_date - start_date).days) if (start_date + datetime.timedelta(days=i)).weekday() == weekday))

    @app_commands.command(name="gathers_stats", description="View gather stats for this channel.")
    @app_commands.describe(
        emoji="Emoji to show reaction stats for.",
        start_date="Start date (YYYY-MM-DD) to get data for. Gets all data by default.",
        end_date="End date (YYYY-MM-DD) to get data for. Gets all data by default."
    )
    async def gathers_stats(self, interaction: discord.Interaction, emoji: str, start_date: str | None = None, end_date: str | None = None):
        
        await interaction.response.defer(ephemeral=False)

        channel_id = getattr(interaction.channel, 'id', interaction.channel_id)

        async with aiosqlite.connect(db_path) as connection:
            async with connection.execute(
                "SELECT user_id, timestamp FROM data WHERE channel_id = ? AND emoji = ?",
                (channel_id, emoji)
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await interaction.followup.send("No data found for this channel and emoji.")
            return
        
        async with aiosqlite.connect(db_path) as connection:
            async with connection.execute(
                "SELECT start_time, end_time FROM gather_channels WHERE id = ?",
                (channel_id, )
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            await interaction.followup.send("No gather settings found for this channel. You can set them up using `/setup_gathers`.")
            return

        start_time = int(row[0])
        end_time = int(row[1])

        if start_date:
            start_date = datetime.datetime.fromisoformat(start_date).date()
        else:
            start_date = datetime.datetime.fromtimestamp(rows[0][1], tz=ZoneInfo("America/New_York")).date()
        

        if end_date:
            end_date = datetime.datetime.fromisoformat(end_date).date()
        else:
            end_date = datetime.datetime.fromtimestamp(rows[-1][1], tz=ZoneInfo("America/New_York")).date()

        days = (end_date - start_date).days + 1

        # hourly counts
        hours = list(range(24))
        hourly_counts = [0] * 24

        for row in rows:
            dt = datetime.datetime.fromtimestamp(row[1], tz=ZoneInfo("America/New_York"))
            if dt.date() >= start_date and dt.date() <= end_date:
                hourly_counts[dt.hour] += 1

        averages = [count / days for count in hourly_counts]

        if end_time > start_time:
            plot_hours = hours[start_time:end_time + 1]
            plot_averages = averages[start_time:end_time + 1]
        else:
            plot_hours = hours[start_time:24] + hours[0:end_time + 1]
            plot_averages = averages[start_time:24] + averages[0:end_time + 1]

        # weekly counts
        reaction_counts = []
        counter = 0
        last_dt = datetime.datetime.fromtimestamp(rows[0][1], tz=ZoneInfo("America/New_York"))
        for row in rows:
            dt = datetime.datetime.fromtimestamp(row[1], tz=ZoneInfo("America/New_York"))
            if dt.date() >= start_date and dt.date() <= end_date:
                if dt == last_dt:
                    counter += 1
                else:
                    reaction_counts.append((last_dt.weekday(), counter))
                    counter = 1
                
                last_dt = dt

        x = list(range(7))

        weekly_counts4 = [0] * 7
        weekly_counts5 = [0] * 7
        weekly_counts6 = [0] * 7
        for weekday, count in reaction_counts:
            if count > 3:
                weekly_counts4[weekday] += 1
            
            if count > 4:
                weekly_counts5[weekday] += 1
                
            if count > 5:
                weekly_counts6[weekday] += 1

        weekly_av4 = [weekly_counts4[i] / self.count_weekdays(start_date, end_date, i) for i in range(7)]
        weekly_av5 = [weekly_counts5[i] / self.count_weekdays(start_date, end_date, i) for i in range(7)]
        weekly_av6 = [weekly_counts6[i] / self.count_weekdays(start_date, end_date, i) for i in range(7)]

        plt.rcParams.update({
            'text.color': 'white',
            'axes.labelcolor': 'white',
            'axes.edgecolor': 'white',
            'xtick.color': 'white',
            'ytick.color': 'white',
            'figure.facecolor': plot_color_palette['background_color'],
            'axes.facecolor': plot_color_palette['axis_color'],
        })

        fig, axs = plt.subplots(nrows=2, ncols=1, figsize=(7, 6))

        # hourly plot
        axs[0].bar(range(len(plot_hours)), plot_averages, color=plot_color_palette['object_colors'][0])
        axs[0].set_title(f'Average Count per day')
        axs[0].set_xlabel('Hour [Eastern Time]')
        axs[0].set_ylabel('Average Reaction Count')
        axs[0].set_xticks(range(len(plot_hours)))
        axs[0].set_xticklabels([f'{str(h)}:00' for h in plot_hours], rotation=60)

        # weekday plot
        axs[1].bar([i-0.2 for i in x], weekly_av4, width=0.2, label='>= 4 reactions', color=plot_color_palette['object_colors'][0])
        axs[1].bar(x, weekly_av5, width=0.2, label='>= 5 reactions', color=plot_color_palette['object_colors'][1])
        axs[1].bar([i+0.2 for i in x], weekly_av6, width=0.2, label='>= 6 reactions', color=plot_color_palette['object_colors'][2])
        axs[1].set_xticks(x)
        axs[1].set_xticklabels(['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], rotation=60)
        axs[1].set_ylim(0, max(weekly_av4) * 1.25)
        axs[1].set_ylabel("Average number of gathers")
        axs[1].legend(loc='upper left', ncols=3, fontsize="small")
        axs[1].set_title(f'Average number of gathers per weekday')

        fig.tight_layout()

        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)

        embed=Embed(title=f'Reactions data for {emoji} in <#{channel_id}>', color=Color.pink())
        embed.set_image(url="attachment://hour_plot.png")

        embed.add_field(name='First Day of Data:', value=self.create_date_timestamp(start_date, 0), inline=True)
        embed.add_field(name='Last Day of Data:', value=self.create_date_timestamp(end_date, 23), inline=True)
        embed.add_field(name='Days of data:', value=str(days), inline=True)

        embed.add_field(name='Reactions Counted:', value=str(sum(hourly_counts)), inline=True)
        embed.add_field(name='Most Common Hour:', value=f'{create_timestamp(hourly_counts.index(max(hourly_counts)))}', inline=True)
        embed.add_field(name='Most Common Day:', value=f'{["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][weekly_av4.index(max(weekly_av4))]}', inline=True)

        embed.set_footer(text=f"A 'gather' is counted when at least 4/5/6 reactions are made on a single hour. The second plot shows the average number of gathers per day at the 4/5/6 thresholds.")

        discord_file = discord.File(fp=buffer, filename="hour_plot.png")

        await interaction.followup.send(
            embed=embed,
            file=discord_file
        )

        return

async def setup(bot: commands.Bot):
    await bot.add_cog(DataCommands(bot))