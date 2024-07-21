import discord
from discord.ext import commands

import BotInfo as info
import Logger

logger = Logger.getLogger(__name__)


class StrawberryJellyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            owner_id=info.DEV_ID,
            command_prefix=commands.when_mentioned,
            help_command=commands.DefaultHelpCommand(),
            intents=discord.Intents.all(),
            activity=discord.Game(info.GAME)
        )
        self.synced = False

    """    Events    """

    async def on_ready(self):
        logger.info(f"Logged in as:    name = {self.user}    id = {self.user.id}")
        logger.info(f"Bot info:    version = {info.BOT_VERSION}    discord.py version = {discord.__version__}")

        if len(self.cogs) == 0:
            logger.info("Loading cogs...")
            for extension in info.INITIAL_EXTENSIONS:
                await self.load_extension(extension)
            self.help_command.cog = self.cogs["Utility"]

        if self.synced == False:
            logger.info("Synchronizing commands...")
            app_coms = await self.tree.sync()
            self.synced = True
            logger.info(f"{len(app_coms)} commands synchronized.")
            
        with open("blacklist.txt", "r") as file:
            self.blacklist = file.readlines()
        for i in range(len(self.blacklist)):
            self.blacklist[i] = int(self.blacklist[i])
        logger.info(f"Blacklist initialized with {len(self.blacklist)} entries.")

        logger.info("Bot ready.")

    async def on_connect(self):
        logger.info("Connected to Discord servers.")

    async def on_resumed(self):
        logger.info("Reconnected to Discord servers.")

    async def on_disconnect(self):
        logger.info("Disconnected from Discord servers.")

    async def on_command_error(self, ctx, error):
        logger.error(f"Command error: {error}.")

#    async def on_error(event, *args, **kwargs):
#        logger.error(f"{event}. Agrs: {args}. Kwargs: {kwargs}.")

    async def on_message(self, message):
        pass


if __name__ == "__main__":
    bot = StrawberryJellyBot()
    bot.run(info.TOKEN)
