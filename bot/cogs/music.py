import asyncio
import typing as t
import discord
from discord.ext import commands
import requests
import json

from discord import FFmpegPCMAudio


class AlreadyConnectedToChannel(commands.CommandError):
    pass


class NoVoiceChannel(commands.CommandError):
    pass

class NotConnectedError(commands.CommandError):
    pass


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player = None

########################################################################################################################
    # Listeners #
########################################################################################################################
    # When last user leaves voice, disconnect from channel
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not member.bot and after.channel is None:
            if not [m for m in before.channel.members if not m.bot]:
                for i in self.bot.voice_clients:
                    if i.channel is before.channel:
                        await i.disconnect()

########################################################################################################################
    # Commands #
########################################################################################################################

    # Test command, remove before production
    @commands.command(name="test")
    async def test_command(self, ctx):
        print(ctx.voice_client.channel)

    # Command to clean chat by <amount> (default=50) of messages
    @commands.command(name="purge", aliases=["clean"])
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

    # Command to connect to voice channel <channel>
    @commands.command(
        name="connect",
        aliases=["join"],
        pass_context=True,
        help="Connect to specified voice channel or channel you are currently in",
    )
    async def connect_to_voice(self, ctx, *, channel: t.Optional[discord.VoiceChannel]):
        if (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel

        if channel is not None:
            voice_client = ctx.voice_client
            if voice_client is not None:
                if channel is not ctx.voice_client.channel:
                    await self.disconnect_from_voice(ctx)
                else:
                    raise AlreadyConnectedToChannel
            self.player = voice = await channel.connect()
            source = FFmpegPCMAudio("http://live.truckers.fm")
            voice.play(source)
            song = ""

            while True:
                current_song_json = json.loads(requests
                                               .get("https://api.truckyapp.com/v2/truckersfm/lastPlayed")
                                               .content)["response"]

                if song is not f"{current_song_json['artist']} - {current_song_json['title']}":
                    song = f"{current_song_json['artist']} - {current_song_json['title']}"
                    await self.bot.change_presence(
                        activity=discord.Activity(
                            type=discord.ActivityType.listening, name=song
                        )
                    )
                await asyncio.sleep(5)
        else:
            await ctx.send("Can´t connect to that...")

    # Command to disconnect from voice channel
    @commands.command(name="disconnect", aliases=["leave"], pass_context=True)
    async def disconnect_from_voice(self, ctx):
        if ctx.voice_client is not None:
            await ctx.guild.voice_client.disconnect()
            await self.bot.change_presence(activity=discord.Game(".help"))
        else:
            raise NotConnectedError

    @commands.command(name="currentsong", aliases=["song", "current"], pass_content=True)
    async def current_song_command(self, ctx):
        current_song_json = json.loads(
            requests.get("https://api.truckyapp.com/v2/truckersfm/lastPlayed").content
        )
        url = current_song_json["response"]["link"]
        if url is None:
            url = "http://spotify.com"
        embedded_message = discord.Embed(
            title=f"{current_song_json['response']['title']}",
            # description=f"{current_song_json['response']['artist']}",
            url=f"{url}",
            color=0x700A1B,
        )
        embedded_message.set_thumbnail(
            url=f"{current_song_json['response']['album_art']}"
        )
        embedded_message.add_field(
            name=f"{current_song_json['response']['artist']}",
            value="On TruckersFM",
            inline=False,
        )
        embedded_message.set_footer(
            text=f"This track has been played {current_song_json['response']['playcount']} times.",
            icon_url=self.bot.get_user(self.bot.client_id).avatar_url,
        )
        await ctx.send(embed=embedded_message)

########################################################################################################################
    # Error handling #
########################################################################################################################
    @connect_to_voice.error
    async def connect_command_error(self, ctx, exc):
        if isinstance(exc, AlreadyConnectedToChannel):
            await ctx.send("Already connected...")
        elif isinstance(exc, NoVoiceChannel):
            await ctx.send("No channel to connect to...")

    @disconnect_from_voice.error
    async def disconnect_error(self, ctx, exc):
        await ctx.send("Cannot disconnect... Help")

    # Functions
    async def fix_audio_stream_error(self):
        await self.player.stop()
        await self.player.start("http://live.truckers.fm")

def setup(bot):
    bot.add_cog(Music(bot))
