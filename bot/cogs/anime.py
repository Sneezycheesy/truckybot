import datetime
import typing as t
import discord
from discord.ext import commands
import requests
import json
import re


class Anime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.query = '''
            query($page:Int
            $perPage:Int
            $id:Int
            $type:MediaType
            $isAdult:Boolean = false
            $search:String
            $format:[MediaFormat]
            $status:MediaStatus
            $countryOfOrigin:CountryCode
            $source:MediaSource
            $season:MediaSeason
            $seasonYear:Int
            $year:String
            $onList:Boolean
            $yearLesser:FuzzyDateInt
            $yearGreater:FuzzyDateInt
            $episodeLesser:Int
            $episodeGreater:Int
            $durationLesser:Int
            $durationGreater:Int
            $chapterLesser:Int
            $chapterGreater:Int
            $volumeLesser:Int
            $volumeGreater:Int
            $licensedBy:[String]
            $genres:[String]
            $excludedGenres:[String]
            $tags:[String]
            $excludedTags:[String]
            $minimumTagRank:Int
            $sort:[MediaSort]=[POPULARITY_DESC,SCORE_DESC]) {
                Page(page:$page
                    ,perPage:$perPage) {
                pageInfo {
                    total
                    perPage
                    currentPage
                    lastPage
                    hasNextPage
                }
                media(id:$id
                        type:$type
                        season:$season
                        format_in:$format
                        status:$status
                        countryOfOrigin:$countryOfOrigin
                        source:$source
                        search:$search
                        onList:$onList
                        seasonYear:$seasonYear
                        startDate_like:$year
                        startDate_lesser:$yearLesser
                        startDate_greater:$yearGreater
                        episodes_lesser:$episodeLesser
                        episodes_greater:$episodeGreater
                        duration_lesser:$durationLesser
                        duration_greater:$durationGreater
                        chapters_lesser:$chapterLesser
                        chapters_greater:$chapterGreater
                        volumes_lesser:$volumeLesser
                        volumes_greater:$volumeGreater
                        licensedBy_in:$licensedBy
                        genre_in:$genres
                        genre_not_in:$excludedGenres
                        tag_in:$tags
                        tag_not_in:$excludedTags
                        minimumTagRank:$minimumTagRank
                        sort:$sort
                        isAdult:$isAdult)
                    {
                    id
                    title {
                        userPreferred
                        romaji
                    }
                    coverImage {
                        extraLarge
                        large
                        color
                    }
                    startDate {
                        year
                        month
                        day
                    }
                    endDate {
                        year
                        month
                        day
                    }
                    siteUrl
                    bannerImage
                    season
                    description
                    type
                    format
                    status(version:2)
                    episodes
                    duration
                    chapters
                    volumes
                    genres
                    isAdult
                    averageScore
                    popularity
                    nextAiringEpisode {
                        airingAt
                        timeUntilAiring
                        episode
                    }
                    mediaListEntry {
                        id
                        status
                    }
                    studios(isMain:true) {
                        edges {
                        isMain
                        node {
                            id
                            name
                        }
                        }
                    }
                    }
                }
        }
        '''
        self.variables = {
        }
        self.url = "https://graphql.anilist.co"

    @commands.command(name="season", aliases=[], help="List anime or manga by season")
    async def season_command(
            self,
            ctx,
            season: t.Optional[str],
            season_year: t.Optional[int],
            per_page: t.Optional[int]
    ):
        self.variables = {
            "season": season.upper(),
            "seasonYear": season_year or datetime.date.today().year,
            "perPage": per_page or 15,
            "page": 1,
        }
        await self.search_function(ctx)
        pass

    @commands.command(name="search", aliases=[], help="List anime or mange based on search term")
    async def search_command(self, ctx, term, per_page: t.Optional[int], media_type: t.Optional[str]):
        if media_type is not None:
            media_type = media_type.upper()
        else:
            media_type = "ANIME"
        self.variables = {
            "search": term,
            "page": 1,
            "perPage": per_page or 15,
            "type": media_type,
        }
        await self.search_function(ctx)
        pass

    async def search_function(self, ctx):
        response = requests.post(self.url, json={"query": self.query, "variables": self.variables})
        data = json.loads(response.content)["data"]["Page"]["media"]
        for i in data:
            embeded_message = discord.Embed(
                title=f'{i["title"]["romaji"]}',
                description=re.sub("<.+?>", "", f'{i["description"]}'),
                url=f'{i["siteUrl"]}',
            )
            embeded_message.set_image(url=f'{i["coverImage"]["large"]}')
            await ctx.send(embed=embeded_message, delete_after=30.0)


def setup(bot):
    bot.add_cog(Anime(bot))
