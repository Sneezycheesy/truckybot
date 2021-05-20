from pathlib import Path
import discord
from discord.ext import commands


class TruckyBot(commands.Bot):
    def __init__(self):
        self._cogs = [p.stem for p in Path(".").glob("./bot/cogs/*.py")]
        super().__init__(
            command_prefix=self.prefix,
            case_insensitive=True,
            intents=discord.Intents.all(),
        )

    def setup(self):
        print("Running setup...")
        print("Setup complete.")

    def run(self):
        self.setup()

        with open("./data/token.0", "r", encoding="utf-8") as f:
            TOKEN = f.read()

        print("Running bot...")
        super().run(TOKEN, reconnect=True)

    async def shutdown(self):
        print("Closing connection to Discord...")
        await super().close()

    async def close(self):
        print("Closing on keyboard interrupt...")
        await self.shutdown()

    async def on_connect(self):
        print(f"Connected to Discord (latency: {self.latency * 1000:,.0f}ms).")

    async def on_resume(self):
        print("Bot resumed.")

    async def on_disconnect(self):
        print("Bot disconnected.")

    # async def on_error(self, err, *args, **kwargs):
    #     raise err
    #
    # async def on_command_error(self, ctx, exc):
    #     raise getattr(exc, "original", exc)

    async def on_ready(self):
        self.client_id = (await self.application_info()).id
        await self.change_presence(activity=discord.Game(".help"))
        for cog in self._cogs:
            self.load_extension(f"bot.cogs.{cog}")
            print(f"Loaded {cog} cog.")

        print("Bot ready.")

    # Start the steam_news_command in channels named appropriately
    async def run_steam_news_in_specific_channels(self):
        await self.cogs["Steam"].steam_news_ets(self.get_channel(831785058528264235))
        pass

    async def prefix(self, bot, msg):
        return commands.when_mentioned_or(".")(bot, msg)

    async def process_commands(self, msg):
        ctx = await self.get_context(msg, cls=commands.Context)
        if ctx.command is not None:
            await ctx.message.delete()
            await self.invoke(ctx)

    async def on_message(self, msg):
        if not msg.author.bot:
            await self.process_commands(msg)