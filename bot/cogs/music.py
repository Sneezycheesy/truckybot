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
        self.playing = ""


########################################################################################################################
    # Helper Functions #
########################################################################################################################
    async def send_embedded_message_song(self, ctx, title, song, artist, thumbnail, footer, url = None):
        embedded_message = discord.Embed(
            title=title,
            color=0x700A1B,
        )

        if url is not None:
            embedded_message.url = url
        else:
            embedded_message.url = "https://spotify.com"
        
        embedded_message.set_thumbnail(
            url=thumbnail
        )
        embedded_message.add_field(
            name=song,
            value=artist,
            inline=False,
        )
        embedded_message.set_footer(
            text= footer,
            icon_url=self.bot.get_user(self.bot.client_id).avatar_url,
        )
        await ctx.send(embed=embedded_message)
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
                        self.player.stop()
                        await i.disconnect()
                        self.playing = False
                        await self.bot.change_presence(activity=discord.Game(".help"))

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
        help="Connect to specified radio stream [neo, tfm, truckersfm] and channel",
        parameters="neo, tfm, truckersfm"
    )
    async def connect_to_voice(self, ctx, source: t.Optional[str], channel: t.Optional[discord.VoiceChannel]):
        if (channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel

        if channel is not None:
            voice_client = ctx.voice_client
            if voice_client is not None:
                await self.disconnect_from_voice(ctx)
            self.player = voice = await channel.connect()

            if source in [None, "neo", "Neo Radio"]:
                new_source = FFmpegPCMAudio("http://curiosity.shoutca.st:6383/;stream.nsv")
                source = "Neo Radio"
            elif source in ["tfm", "truckersfm", "TruckersFM"]:
                new_source = FFmpegPCMAudio("http://live.truckers.fm")
                source = "TruckersFM"
            else:
                new_source = FFmpegPCMAudio(source)

            voice.play(new_source)
            await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=source))
            self.playing = source

        else:
            await ctx.send("Can´t connect to that...")
    
    @commands.command(name="tfm", aliases=["truckersfm"], pass_context=True, help="Play truckersFM on your joined channel or specified channel")
    async def connect_tfm_command(self, ctx, channel: t.Optional[discord.VoiceChannel]):
        source = "TruckersFM"
        if channel is None:
            await self.connect_to_voice(ctx, source, ctx.voice_client)
        else:
            await self.connect_to_voice(ctx, source, channel)

    @commands.command(name="neo", aliases=["neofm"], pass_context=True, help="Play neo on your joined channel or specified channel")
    async def connect_neo_command(self, ctx, channel: t.Optional[discord.VoiceChannel]):
        source = "Neo Radio"
        if channel is None:
            await self.connect_to_voice(ctx, source, ctx.voice_client)
        else:
            await self.connect_to_voice(ctx, source, channel)

    # Command to disconnect from voice channel
    @commands.command(name="disconnect", aliases=["leave"], pass_context=True, help="Disconnect from active voice channel")
    async def disconnect_from_voice(self, ctx):
        if ctx.voice_client is not None:
            self.player.stop()
            await ctx.guild.voice_client.disconnect()
            self.playing = False
            await self.bot.change_presence(activity=discord.Game(".help"))
        else:
            raise NotConnectedError

################################
# START Currently Playing Song #
################################
    @commands.command(name="currentsong", aliases=["song"], pass_content=True, help="Show song currently playing on current stream or specified stream")
    async def current_song_command(self, ctx, source: t.Optional[str]):
        if source is None:
            await self.show_currently_playing_command(ctx)
        elif source.lower() in ["neo", "neo radio"]:
            await self.show_currently_playing_song_neo(ctx)
        elif source.lower() in ["tfm", "truckersfm"]:
            await self.show_currently_playing_song_tfm(ctx)

    @commands.command(name="current", pass_context=True, help="Show song currently playing on the active voice client")
    async def show_currently_playing_command(self, ctx):
        if self.playing == "TruckersFM":
            await self.show_currently_playing_song_tfm(ctx)
        elif self.playing == "Neo Radio":
            await self.show_currently_playing_song_neo(ctx)
        else:
            await ctx.send("Not playing anything right now...", delete_after=5.0)

    # Handle displaying the current song in chat, this is different for both streams...
    async def show_currently_playing_song_tfm(self, ctx):
        current_song_json = json.loads(
            requests.get("https://api.truckyapp.com/v2/truckersfm/lastPlayed").content
        )
        title = "Now Playing On TruckersFM"
        song = current_song_json["response"]["title"]
        artist = current_song_json["response"]["artist"]
        thumbnail = current_song_json['response']['album_art']
        footer = f"This track has been played {current_song_json['response']['playcount']} times."
        url = current_song_json["response"]["link"]

        await self.send_embedded_message_song(ctx, title, song, artist, thumbnail, footer, url)

    async def show_currently_playing_song_neo(self, ctx):
        current_song_json = json.loads(
            requests.get("https://scraper2.onlineradiobox.com/nz.neo").content
        )
        artist_title = current_song_json["title"].split(" - ")
        title = "Now Playing On Neo Radio"
        song = artist_title[1]
        artist = artist_title[0]
        thumbnail = "https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Fmytuner.global.ssl.fastly.net%2Fmedia%2Ftvos_radios%2Frgbdygbrjzms.png&f=1&nofb=1"
        footer="Enjoy Neo Radio."

        await self.send_embedded_message_song(ctx, title, song, artist, thumbnail, footer)
                                                                                                                    ##############################
                                                                                                                    # END Currently Playing Song #
                                                                                                                    ##############################
######################
# Error handling     #
######################
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
