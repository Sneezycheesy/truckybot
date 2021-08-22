import asyncio
import typing
import typing as t
import discord
import discord.opus
from discord.ext import commands
import requests
import json
import youtube_dl
import os
from discord import FFmpegPCMAudio


class AlreadyConnectedToChannel(commands.CommandError):
    pass


class NoVoiceChannel(commands.CommandError):
    pass


class NotConnectedError(commands.CommandError):
    pass


class NoSourceError(commands.CommandError):
    pass


class InvalidSourceError(commands.CommandError):
    pass


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player = None
        self.radio = None
        self.current_song = None
        self.playing = False
        self.queue = {}
        self.voice_clients = {}

        self.ytl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': '%(title)s.%(ext)s',
        }

        self.sources = {
            "neo": "http://curiosity.shoutca.st:6383/;stream.nsv",
            "tfm": "http://live.truckers.fm",
            "truckersfm": "http://live.truckers.fm",
            "tsfm": "http://live.trucksim.fm"
        }


########################################################################################################################
    # Helper Functions #
########################################################################################################################
    async def send_embedded_message_song(self, ctx, title, song, artist, thumbnail, footer, url = None):
        embedded_message = discord.Embed(
            title=title,
            color=0x700A1B,
        )

        if url is not None and url != "":
            embedded_message.url = url
        else:
            embedded_message.url = f"https://open.spotify.com/search/{artist} {song}".replace(' ', '%20')
        
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

    # Used as switch statement
    # Using .join neo would work, because it is a known source
    def get_predetermined_source(self, source):
        return self.sources.get(source, None)


    # Functions
    async def fix_audio_stream_error(self, ctx):
        if ctx.voice_client is not None:
            self.player.stop()
            await ctx.guild.voice_client.disconnect()
            await self.bot.change_presence(activity=discord.Game(".help"))
        else:
            raise NotConnectedError

    async def play_next_song(self, ctx):
        guild_id = ctx.message.guild.id
        if self.current_song is not None:
            for file in os.listdir("./"):
                if file == f"{self.current_song}.mp3":
                    os.remove(file)
            self.queue[guild_id].pop(self.current_song)
        if len(self.queue[guild_id]) < 1:
            if self.radio is not None:
                await self.connect_to_voice(ctx, self.radio)
            else:
                await self.disconnect_from_voice(ctx)
        pass
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
                        self.playing = False
                        await self.bot.change_presence(activity=discord.Game(".help"))

    async def cog_check(self, ctx):
        if isinstance(ctx.channel, discord.DMChannel):
            await ctx.send("Music commands are not available in DMs.")
            return False
        return True

########################################################################################################################
    # Commands #
########################################################################################################################
    @commands.command(
        name="sources",
        aliases=[],
        help="Show a message listing the predetermined sources.",
        description="Show a message listing the predetermined sources, so you don't have to type their whole links."
    )
    async def sources_command(self, ctx):
        message = "Current predetermined sources are:\n"
        for source in self.sources:
            message += f"\t{source}\n"
        await ctx.send(message)

    @commands.command(
        name="join",
        aliases=["connect", "voice"],
        help="Play a specified radio stream link in your current voice channel, "
             "or supply the required voice channel name in quotes."
             "The template for this: .join [source] [channel], type '.sources' to view predetermined sources",
        description="Play a specified radio stream link in your current voice channel"

    )
    async def join_command(self, ctx, source: t.Optional[str], channel: t.Optional[discord.VoiceChannel]):
        guild_id = ctx.message.guild.id
        await self.setup_voice_connection(ctx, channel, guild_id)
        self.play_audio_in_voice(source, guild_id)

    # START setup_voice_connection FUNCTION
    async def setup_voice_connection(self, ctx, channel, guild_id):
        if (new_channel := getattr(ctx.author.voice, "channel", channel)) is None:
            raise NoVoiceChannel
        # Disconnect if we're changing to another channel (for example "General" => "Test"
        if guild_id in self.voice_clients and self.voice_clients[guild_id].channel != new_channel:
            await ctx.guild.voice_client.disconnect()
            self.voice_clients[guild_id] = await new_channel.connect()
        # Connect to the channel if it's not yet connected to anything (So no disconnect is needed)
        elif guild_id not in self.voice_clients:
            self.voice_clients[guild_id] = await new_channel.connect()
    # END setup_voice_connection FUNCTION

    # START play_audio_in_voice FUNCTION
    def play_audio_in_voice(self, source, guild_id):
        if source is None:
            raise NoSourceError

        if (new_source := self.get_predetermined_source(source)) is not None:
            source = new_source
        source = FFmpegPCMAudio(source)

        if source.read():
            if self.voice_clients[guild_id].is_playing():
                self.voice_clients[guild_id].source = source
            else:
                self.voice_clients[guild_id].play(source)
        else:
            raise InvalidSourceError
    # END play_audio_in_voice FUNCTION

    @commands.command(name="play", aliases=[], help="Play audio (from youtube) by supplying the requested link.")
    async def queue_song(self, ctx, source: str, channel: t.Optional[discord.VoiceChannel]):
        if source is None:
            raise NoVoiceChannel

        guild_id = ctx.message.guild.id

        with youtube_dl.YoutubeDL(self.ytl_opts) as ydl:
            result = ydl.extract_info(source, download=False)
        # Add each video to queue when it is a playlist
        if 'entries' in result:
            for entry in result['entries']:
                if ctx.message.guild.id in self.queue:
                    self.queue[guild_id].append(entry['url'])
                else:
                    self.queue[guild_id] = [entry['url']]
        # Add to queue when it's not a playlist
        else:
            if guild_id in self.queue:
                self.queue[guild_id].append(result['url'])
            else:
                self.queue[guild_id] = [result['url']]

    # Command to disconnect from voice channel
    @commands.command(name="disconnect", aliases=["leave"], pass_context=True,
                      help="Disconnect from active voice channel")
    async def disconnect_from_voice(self, ctx):
        guild_id = ctx.message.guild.id
        if guild_id in self.voice_clients:
            await ctx.guild.voice_client.disconnect()
            self.voice_clients.pop(guild_id)
            self.playing = False
            self.radio = None
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
    @disconnect_from_voice.error
    async def disconnect_error(self, ctx, exc):
        await ctx.send("Cannot disconnect... Help")

    @join_command.error
    async def no_source_error(self, ctx, exc):
        if isinstance(exc, InvalidSourceError):
            await ctx.send("Invalid source, disconnecting..", delete_after=5.0)
            await ctx.guild.voice_client.disconnect()
            self.voice_clients.pop(ctx.message.guild.id)
        if isinstance(exc, NoVoiceChannel):
            await ctx.send("No Voice Channel Selected... Try again.", delete_after=8.5)


def setup(bot):
    bot.add_cog(Music(bot))
