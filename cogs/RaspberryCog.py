import discord
from discord.ext import commands
from discord import app_commands

import subprocess

import BotInfo as info
import Logger

logger = Logger.getLogger(__name__)


class RaspberryCog(commands.Cog, name="Raspberry"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Shows current temperature of Raspberry Pi CPU.")
    @app_commands.guild_only()
    async def temp(self, interaction: discord.Interaction):
        temp = self._temp()
        await interaction.response.send_message(f"My CPU's current temperature: {temp:.01f}°C")

    @app_commands.command(description="Shows current throttling status of Raspberry Pi CPU.")
    @app_commands.guild_only()
    async def throt(self, interaction: discord.Interaction):
        throt_status = self._throt()
        message = "Current throttling status:\n"
        for mes in throt_status:
            message = message + mes + "\n"
        message = message[:-1]
        await interaction.response.send_message(message)

    def _temp(self):
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as file:
            res = file.readlines()[0]

        res = int(res)/1000

        return res

    def _throt(self):
        throttled_output = subprocess.check_output("vcgencmd get_throttled", shell=True)
        throttled_binary = bin(int(throttled_output.split(b"=")[1], 0))

        res = []
        for position, message in info.THROTTLING_MESSAGES.items():
            if len(throttled_binary) > position and throttled_binary[0 - position - 1] == "1":
                res.append(f"Flag {position}: {message}")

        if len(res) == 0:
            res.append("All good!")

        return res


async def setup(bot):
    await bot.add_cog(RaspberryCog(bot))
    logger.info("Loaded cog Raspberry.")
