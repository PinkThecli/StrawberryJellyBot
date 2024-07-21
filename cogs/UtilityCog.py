import discord
from discord.ext import commands
from discord import app_commands

import requests
import datetime
from pathlib import Path
import os
import asyncio

import Logger
import BotInfo as info

logger = Logger.getLogger(__name__)


class UtilityCog(commands.Cog, name="Utility"):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Shows help message.")
    @app_commands.guild_only()
    async def help(self, interaction: discord.Interaction):
        app_cmds = await self.bot.tree.fetch_commands()
        cmds_dict = {}
        for cmd in app_cmds:
            cmds_dict[cmd.name] = cmd.id

        mesg = ""
        for name, cog in self.bot.cogs.items():
            mesg += "**" + name + ":**\n"

            for cmd in cog.get_app_commands():
                if not isinstance(cmd, discord.app_commands.Group):
                    mesg += f"* </{cmd.name}:{cmds_dict[cmd.name]}> - " + cmd.description + "\n"
                else:
                    mesg += f"* `/{cmd.name}` - " + cmd.description + "\n"
                    for subcmd in cmd.commands:
                        mesg += f" * </{cmd.name} {subcmd.name}:{cmds_dict[cmd.name]}> - " + subcmd.description + "\n"

        embed = discord.Embed(color=info.EMBED_COLOR, title="Commands list:", description=mesg)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(description="Echoes your message to this channel.")
    @app_commands.guild_only()
    @app_commands.describe(
        message="Message to echo."
    )
    async def echo(self, interaction: discord.Interaction, message: str):
        await interaction.response.send_message(
            f"You said: {message}\n"
        )

    @app_commands.command(description="Sends the member's avatar.")
    @app_commands.guild_only()
    @app_commands.describe(
        member="Member of this server. If no member is specified this command sends your avatar."
    )
    async def avatar(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        embed = discord.Embed(color=info.EMBED_COLOR, title="", description=f"Member: {member.mention}")
        embed.set_image(url=member.avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(description="Shows the current bot version.")
    @app_commands.guild_only()
    async def version(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"Bot version: {info.BOT_VERSION}    discord.py version: {discord.__version__}\n" +
            f"Description: \"{info.BOT_VERSION_DESCRIPTION}\""
        )

    @app_commands.command(description="Deletes several last messages in channel.")
    @app_commands.guild_only()
    @app_commands.describe(
        count="Amount of last messages to delete."
    )
    async def delmsg(self, interaction: discord.Interaction, count: int):
        if not interaction.user.id in info.DELETE_ALLOWED_LIST:
            await interaction.response.send_message(f"Sorry, you are not allowed to do this!", ephemeral=True)
        if count <= 0:
            await interaction.response.send_message(f"Sorry, incorrect messages amount: {count}!", ephemeral=True)
            return
        await interaction.response.send_message(f"Deleting {count} last messages...")
        original_response = await interaction.original_response()

        channel = interaction.channel

        async for message in channel.history(limit=count+1):
            await asyncio.sleep(0.5)
            if message.id == original_response.id:
                continue
            try:
                await message.delete()
            except discord.errors.NotFound:
                count -= 1
                continue

        await original_response.edit(content=f"{count} last messages were successfully deleted!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild and message.author.id != self.bot.user.id:

            if len(message.attachments) == 0:
                await message.reply("Please, send me png or jpg images.")
                return

            id = len([entry for entry in os.listdir("./media/images/contributions")]) + info.NUM_IMAGES

            count = 0
            for attachment in message.attachments:
                if not Path(attachment.filename).suffix.lower() in [".png", ".jpg", ".jpeg"]:
                    continue

                r = requests.get(attachment.url)
                with open(f"./media/images/contributions/{id}.png", "wb") as image:
                    image.write(r.content)

                with open(f"./media/images/contributions/data.txt", "a") as data:
                    data.write(f"{id}.png,{attachment.filename},{message.author},{datetime.datetime.now()}\n")

                count += 1
                id += 1

            if count == 0:
                await message.reply("Please, send me png or jpg images.")
                return

            await message.reply("Thanks for your contribution!")

    @app_commands.command(description="Sends message to my creator.")
    @app_commands.guild_only()
    @app_commands.describe(
        message="Text message to be sent.",
        attachment="Image/Video/Music file attached with message."
    )
    async def sm(self, interaction: discord.Interaction, message: str, attachment: discord.Attachment = None):
        if interaction.user.id in self.bot.blacklist:
            await interaction.response.send_message(f"Sorry! You are in blacklist.", ephemeral=True)
            return

        if attachment:
            file = await attachment.to_file()
        else:
            file = None
        user = self.bot.get_user(self.bot.owner_id)
        await user.send(f"{interaction.user} ({interaction.user.id}) from {interaction.guild} ({interaction.guild_id}):\n\""+message+"\"", file=file)
        await interaction.response.send_message(f"Message was sent to my creator.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(UtilityCog(bot))
    logger.info(f"Loaded cog Utility.")
