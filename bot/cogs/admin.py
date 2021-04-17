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

def setup(bot):
    bot.add_cog(Admin(bot))