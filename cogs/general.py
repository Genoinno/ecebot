import discord
import datetime
import wmi

from discord.ext import commands
from googletrans import Translator


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

    @commands.command()
    async def ping(self, ctx: commands.Context):
        await ctx.send(f"Pong! ```{self.bot.latency *  1000:.2f}ms```")

    @commands.command(aliases=["temp"])
    async def temperature(self, ctx):
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

async def setup(bot):
    await bot.add_cog(General(bot))