import discord
import os
import datetime
import wmi


from discord.ext import commands
from googletrans import Translator
from models import Spotify
from google.antigravity import Agent, LocalAgentConfig, types


class General(commands.Cog):
    """This is a cog with general commands:
    - Ping
    - Check Temperature
    - translate

    """

    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()
        self.w = wmi.WMI(namespace=r"root\OpenHardwareMonitor")
        self.agent = None
        self.agent_context = None

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"Pong! ```{self.bot.latency *  1000:.2f}ms```")

    @commands.command(aliases=["temp"])
    async def temperature(self, ctx: commands.Context):
        sensors = self.w.Sensor()
        sensors = sorted([sensor for sensor in sensors if sensor.SensorType in ["Temperature", "Fan"]], key=lambda sensor: sensor.name)

        final = []
        seen = set()
        txt = ""
        for sensor in sensors:
            key = sensor.name
            if key not in seen:
                seen.add(key)
                final.append(sensor)

        
        for sensor in final:
            txt += f"**{sensor.name}:**\n"
            txt += f"-# {sensor.SensorType}: **{sensor.Value}**{"c°" if sensor.SensorType == "Temperature" else " RPM"}\n\n"
                
        await ctx.send(txt)
        await ctx.send("""CPU Core	Internal CPU diode	CPU (not Nuvoton)
    Temperature #1	Motherboard (chipset area)	Nuvoton NCT6776F
    Temperature #2	VRM (power delivery)	Nuvoton NCT6776F
    Temperature #3	GPU/PCIe/ambient area	Nuvoton NCT6776F\n\nCPU Core 1	Temperature sensor inside core #1	Individual sensor for that core
    CPU Core 2	Temperature sensor inside core #2	i3-3220 is dual-core
    CPU Core	May be an average or a copy of Core 1 (tool-dependent)	Sometimes redundant
    CPU Package	Temperature of the entire CPU die (package)	Most accurate for CPU health/throttle""")

    @commands.command(aliases=["trans", "tl"])
    async def translate(self, ctx: commands.Context, *, text=None):
        text = (
            text or (
                (await ctx.channel.fetch_message(ctx.message.reference.message_id)).content
            )
        )
        source = "en" if self.translator.detect(text).lang == "en" else "id"
        translated_to = "en" if source == "id" else "id"
        translated_text = self.translator.translate(text, src=source, dest=translated_to).text
        embed = discord.Embed(
            title=f"{source} -> {translated_to}",
            description=translated_text,
            colour=discord.Color.blurple(),
            timestamp=datetime.datetime.now(),
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["sp"])
    async def spotify(self, ctx: commands.Context, member: discord.Member = None):
        """
        Shows the spotify status of a member.

        Usage:
        ------
        `{prefix}spotify`: *will show your spotify status*
        `{prefix}spotify [member]`: *will show the spotify status of [member]*
        """
        member = ctx.guild.get_member((member or ctx.author).id)

        spotify = Spotify(bot=self.bot, member=member)
        result = await spotify.get_embed()
        
        if not result:
            if member == ctx.author:
                return await ctx.reply(
                    "You are currently not listening to spotify!", mention_author=False
                )
            return await self.bot.reply(
                ctx,
                f"{member.mention} is not listening to Spotify",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions(users=False),
            )
        file, view = result
        await ctx.send(file=file, view=view)

    @commands.command()
    @commands.is_owner()
    async def test(self, ctx, channel_id, *, txt = ""):
        await ctx.message.delete()
        try:
            int(channel_id)
        except ValueError:
            return await ctx.channel.send(channel_id + " " + txt)
        await (self.bot.get_channel(int(channel_id))).send(txt)

    async def cog_load(self):
        # Spawns a persistent agent when the cog is loaded to eliminate startup latency on command calls
        # Force the agent context to lock into your ecebot folder right at startup
        project_path = r"C:\Users\User\Documents\project\ecebot"
        os.chdir(project_path)
        config = LocalAgentConfig(
            system_instructions="You are ecebot, a helpful discord bot for the Tecnical One English Club discord server. Your job is to answer general questions about any topic. You will use your skills accordingly and your action is limited to only reply the user with correct answer without harming the user verbally or physically. If you need to use tools to execute a command, view, or write something into the current working directory, make sure to check if the executed User's discord ID is 685082846993317953, if not, reply with the text: 'You do not have permission to do this.'. You will also answer the user with discord formatted text as your response will be sent to a discord TextChannel. Your response must be below 2000 characters.",
            api_key=os.environ.get("GEMINI_API_KEY"),
            model="gemini-3.1-flash-lite",
            workspace=project_path
        )
        self.agent_context = Agent(config)
        self.agent = await self.agent_context.__aenter__()

    async def cog_unload(self):
        # Cleans up the persistent agent when the cog is unloaded
        if self.agent_context:
            await self.agent_context.__aexit__(None, None, None)

    @commands.command()
    async def chat(self, ctx, *, q):
        if not self.agent:
            await ctx.send("The chatbot agent is not initialized yet or failed to start.")
            return
        
        # We can send an immediate notification to let the user know we're processing
        async with ctx.typing():
            try:
                response = await self.agent.chat(f"{ctx.author.id} asked:" + q)
                full_message = ""
                async for chunk in response:
                    if isinstance(chunk, str):
                        print(chunk)
                        print("====================================================================================")
                        full_message += chunk
                
                if full_message:
                    # Discord limits messages to 2000 characters
                    if len(full_message) > 2000:
                        full_message = full_message[:1996] + "..."
                    await ctx.reply(full_message)
                else:
                    await ctx.reply("The agent did not return a response.")
            except Exception as e:
                await ctx.send(f"An error occurred while communicating with Antigravity: {e}")

async def setup(bot):
    await bot.add_cog(General(bot))
