import discord
from discord.ext import commands
import re
import asyncio
import feedparser
from datetime import datetime

class System(commands.Cog):
    @commands.command(name="new", aliases=["upcoming", "planned"], help="List upcoming or planned changes to the bot")
    async def show_upcoming_changes_to_the_bot(self, ctx):
        await ctx.send("""The next features to be added are:\n
        - ~~Automatic initialization of steam news~~
        - Supporting custom intervals for steam news (smallest will be 15 min, highest will be 24hours, this only applies to manual initialization)
        - Stopping the Steam news refreshes (both for automatic AND manual initialization, per channel or for entire server)""")

def setup(bot):
    bot.add_cog(System(bot))