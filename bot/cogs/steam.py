import discord
from discord.ext import commands
import re
import asyncio
import feedparser
from datetime import datetime


async def create_embedded_message(ctx, news_item):
    news_title = news_item["title"]
    news_link = news_item["link"]
    news_contents = re.sub(r'<.+?>', '', news_item["summary"][:2000])
    news_image = news_item["links"][1]["href"]

    embedded_message = discord.Embed(
        title=news_title,
        description=news_contents,
        url=news_link, )
    embedded_message.set_thumbnail(url=news_image)

    embedded_message.set_footer(
        text=f"Published: {datetime.strftime(news_item.published, '%d %b %Y')}",
        icon_url="https://external-content.duckduckgo.com/iu/"
                 "?u=https%3A%2F%2Fupload.wikimedia.org%2Fwikipedia%2Fcommons%2Fthumb%2F8%2F83%"
                 "2FSteam_icon_logo.svg%2F1200px-Steam_icon_logo.svg.png&f=1&nofb=1",
    )
    await ctx.send(embed=embedded_message)


class Steam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ets2", aliases=["ets"], help="Initialize ETS2 Steam News sync")
    async def steam_news_ets(self, ctx):
        await self.steam_news(self.bot, ctx, "ets")

    @commands.command(name="ats", aliases=["amt"], help="Initialize ATS Steam News sync")
    async def steam_news_ats(self, ctx):
        await self.steam_news(self.bot, ctx, "ats")

    async def steam_news(self, bot, ctx, game):
        game_code = ""
        if game.lower().replace(' ', '') in ["ets"]:
            game_code = "227300"
            print(game_code)
        elif game.lower().replace(' ', '') in ["ats", "americantrucksim", "americantrucksimulator"]:
            game_code = "270880"
            print(game_code)

        news_gid = ""
        steam_news_url = \
            f"https://store.steampowered.com/feeds/news/app/{game_code}/"

        if game_code is not None:
            while True:
                f = feedparser.parse(steam_news_url)
                news_content = f.entries

                previous_news = ctx.history(limit=None)
                news_links = []

                for news_item in news_content:
                    published_date = datetime.strptime(news_item.published, "%a, %d %b %Y %X %z")
                    published_string = datetime.strftime(published_date, "%d %b %Y")
                    published_date = datetime.strptime(published_string, "%d %b %Y")
                    news_item.published = published_date

                news_content.sort(key=lambda x: x.published, reverse=False)
                for news_item in news_content:
                    news_item.published = datetime.strptime(datetime.strftime(news_item.published, "%d %b %Y"), "%d %b %Y")

                if previous_news is None:
                    for news_item in news_content:
                        await create_embedded_message(ctx, news_item)
                else:
                    async for message in previous_news:
                        if len(message.embeds) > 0:
                            message_link = message.embeds[0].url
                            news_links.append(message_link)
                    for news_item in news_content:
                        if news_item["link"] not in news_links:
                            await create_embedded_message(ctx, news_item)

                await asyncio.sleep(3600)


def setup(bot):
    bot.add_cog(Steam(bot))
