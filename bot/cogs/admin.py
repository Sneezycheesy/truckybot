import typing as t
import discord
from discord import voice_client
from discord.ext import commands
import re
import requests
import json
import asyncio
import time

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Test command, remove before production
    @commands.command(name="test", help="Function to test new functionalities and should only be used in development")
    async def test_command(self, ctx):
        print(ctx.voice_client.channel)

    # Command to clean chat by <amount> (default=50) of messages
    @commands.command(name="purge", aliases=["clean"], help="Purge (or clean) x amount of messages from chat "
                                                            "(x is 50 by default)")
    async def clean_chat(
            self, ctx, amount: t.Optional[int], user: t.Optional[discord.User]
    ):
        if amount is None:
            amount = 50

        history = ctx.history(limit=amount)
        async for message in history:
            if user is not None:
                if message.author.id == user.id:
                    await message.delete()
            else:
                await message.delete()

def setup(bot):
    bot.add_cog(Admin(bot))