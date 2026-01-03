import discord
import tmdbsimple as tmdb

from discord.ext import commands

class Movie(commands.Cog):
    """This is a cog with Movies and TV Shows commands:
    - Search (Movies, TV Shows)

    """
    def __init__(self, bot):
        self.bot = bot
        self.search = tmdb.Search()

    @commands.command()
    async def search(self, ctx, *, query):
        self.search.movie(query=query)
        try:
            result = self.search.results[0]
        except IndexError:
            return await ctx.send("Can't find the movie :/\nMaybe wrong spelling? <:hmm:1452180929203146837>")
        url=f"https://www.themoviedb.org/movie/{result["id"]}-{result["title"]}".lower().replace(" ", "-")
        print(url)
        em = discord.Embed(
            title=result["title"],
            description=(
            result["overview"][:297] + f"[...]({url})") if len(result["overview"]) >= 300 else result["overview"],
            url=url,
            color=discord.Color.random()
        )

        em.set_image(url=f"https://image.tmdb.org/t/p/w500{result["backdrop_path"]}")
        em.set_thumbnail(url=f"https://image.tmdb.org/t/p/w500{result["poster_path"]}")
        
        await ctx.send(embed=em)


async def setup(bot):
    await bot.add_cog(Movie(bot))