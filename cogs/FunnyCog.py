import discord
from discord.ext import commands
from discord import app_commands

import cv2 as cv
import numpy as np
import requests as req
from io import BytesIO
import random as r
from datetime import date

import BotInfo as info
import Logger

logger = Logger.getLogger(__name__)


class FunnyCog(commands.Cog, name="Funny"):
    def __init__(self, bot):
        self.bot = bot

    """     Commands     """

    @app_commands.command(description="Sends gachi image with you as top and member as bottom.")
    @app_commands.guild_only()
    @app_commands.describe(
        member="Member of this server to gachi."
    )
    async def gachi(self, interaction: discord.Interaction, member: discord.Member):
        await interaction.response.defer()
        img1 = self.url_to_img(str(interaction.user.avatar.replace(format="png", size=512)))
        img2 = self.url_to_img(str(member.avatar.replace(format="png", size=512)))
        make_collage = self.make_collage1
        message = f"{interaction.user.mention} gachied {member.mention}!"
        if member.id == self.bot.user.id and interaction.user.id != self.bot.owner_id:
            img1, img2 = img2, img1
            message = "Nice try!"
        elif member.id == self.bot.owner_id and interaction.user.id != self.bot.owner_id:
            make_collage = self.make_collage2
            message = "Congratulations! You have found the secret scene! Member DanielTheGreat is under my protection!"
        original_response = await interaction.original_response()
        await original_response.edit(content=message, attachments=[discord.File(BytesIO(make_collage(img1, img2).tobytes()), filename="collage.png")])

    @app_commands.command(description="Shows what you look like today.")
    @app_commands.guild_only()
    async def lava(self, interaction: discord.Interaction):
        await interaction.response.defer()
        d = str(date.today())
        u = str(interaction.user)
        r.seed(d+u, 2)
        res = r.randint(1, info.NUM_IMAGES)
        r.seed()
        original_response = await interaction.original_response()
        await original_response.edit(content=f"Today {interaction.user.mention} looks like this:", attachments=[discord.File(f"media/images/avatars/{res}.png")])

    @app_commands.command(description="Filters input image with selected filter type.")
    @app_commands.guild_only()
    @app_commands.describe(
        input="Input image.",
        filter="Filter type."
    )
    @app_commands.choices(filter=[
        app_commands.Choice(name="Dead", value=0),
        app_commands.Choice(name="Edges", value=1),
        app_commands.Choice(name="Canny Edges", value=2),
        app_commands.Choice(name="Sine Horizontal", value=3),
        app_commands.Choice(name="Sine Vertical", value=4),
        app_commands.Choice(name="Erode", value=5),
        app_commands.Choice(name="Dilate", value=6)
    ])
    async def fim(self, interaction: discord.Interaction, input: discord.Attachment, filter: int):
        await interaction.response.defer()
        original_response = await interaction.original_response()

        if "image" not in input.content_type:
            await original_response.edit(content="Error! Only images are supported.")
            return

        if "gif" in input.content_type:
            await original_response.edit(content="Error! Only images are supported.")
            return

        data = await input.read()
        image = np.frombuffer(data, dtype=np.uint8)
        image = cv.imdecode(image, cv.IMREAD_UNCHANGED)

        if image.shape[0] > 1024:
            k = image.shape[0] / 1024
            image = cv.resize(image, (int(image.shape[1] / k), 1024), interpolation=cv.INTER_AREA)

        if image.shape[1] > 1024:
            k = image.shape[1] / 1024
            image = cv.resize(image, (1024, int(image.shape[0] / k)), interpolation=cv.INTER_AREA)

        if filter == 0:
            res = self.filter_dead(image)
        elif filter == 1:
            res = self.filter_edges(image)
        elif filter == 2:
            res = self.filter_canny_edges(image)
        elif filter == 3:
            res = self.filter_sine_horizontal(image)
        elif filter == 4:
            res = self.filter_sine_vertical(image)
        elif filter == 5:
            res = self.filter_erode(image)
        elif filter == 6:
            res = self.filter_dilate(image)

        await original_response.edit(attachments=[discord.File(BytesIO(res.tobytes()), filename="filtered_image.png")])

    """     Utility functions     """

    def make_collage1(self, img1, img2):
        bg = cv.imread("media/images/image1.png")
        r1 = [290, 382, 42, 134]
        r2 = [480, 610, 470, 600]
        w1 = r1[1]-r1[0]
        w2 = r2[1]-r2[0]
        h1 = r1[3]-r1[2]
        h2 = r2[3]-r2[2]

        mask1 = cv.imread("media/images/image1_mask1.png", cv.IMREAD_GRAYSCALE)
        mask2 = cv.imread("media/images/image1_mask2.png", cv.IMREAD_GRAYSCALE)

        img1 = cv.imdecode(img1, cv.IMREAD_COLOR)
        img2 = cv.imdecode(img2, cv.IMREAD_COLOR)
        img1 = cv.resize(img1, (w1, h1), interpolation=cv.INTER_AREA)
        img2 = cv.resize(img2, (w2, h2), interpolation=cv.INTER_AREA)

        cv.bitwise_and(bg[r1[2]:r1[3], r1[0]:r1[1]], img1, bg[r1[2]:r1[3], r1[0]:r1[1]], mask1)
        cv.bitwise_and(bg[r2[2]:r2[3], r2[0]:r2[1]], img2, bg[r2[2]:r2[3], r2[0]:r2[1]], mask2)

        bg = np.array(cv.imencode(".png", bg)[1], dtype=np.uint8)

        return bg

    def make_collage2(self, img, _):
        bg = cv.imread("media/images/image2.png")
        r = [772, 888, 440, 556]
        w = r[1]-r[0]
        h = r[3]-r[2]

        mask = cv.imread("media/images/image2_mask.png", cv.IMREAD_GRAYSCALE)

        img = cv.imdecode(img, cv.IMREAD_COLOR)
        img = cv.resize(img, (w, h), interpolation=cv.INTER_AREA)

        cv.bitwise_and(bg[r[2]:r[3], r[0]:r[1]], img, bg[r[2]:r[3], r[0]:r[1]], mask)

        bg = np.array(cv.imencode(".png", bg)[1], dtype=np.uint8)

        return bg

    def url_to_img(self, url):
        res = req.get(url)
        arr = np.frombuffer(res.content, dtype=np.uint8)
        return arr
        
    def filter_dead(self, image):
        if image.shape[2] == 4:
            gray = cv.cvtColor(image[:, :, :3], cv.COLOR_RGB2GRAY)
            gray = cv.cvtColor(gray, cv.COLOR_GRAY2RGBA)
            gray[:, :, 3] = image[:, :, 3]
            color = (0, 0, 0, 255)
        elif image.shape[2] == 3:
            gray = cv.cvtColor(image, cv.COLOR_RGB2GRAY)
            gray = cv.cvtColor(gray, cv.COLOR_GRAY2RGB)
            color = (0, 0, 0)
        else:
            gray = image
            color = 0

        pm = 0.7
        offset = 50
        if image.shape[1] >= image.shape[0]:
            thickness = int(image.shape[0] * 0.1)
            point_0 = (image.shape[1] - 1 + offset, int(image.shape[0] * pm) - offset)
            point_1 = (image.shape[1] - int(image.shape[0] * (1 - pm)) - offset, image.shape[0] - 1 + offset)
        else:
            thickness = int(image.shape[1] * 0.1)
            point_0 = (int(image.shape[1] * pm) - offset, image.shape[0] - 1 + offset)
            point_1 = (image.shape[1] - 1 + offset, image.shape[0] - int(image.shape[1] * (1 - pm)) - offset)
        cv.line(gray, point_0, point_1, color, thickness)

        gray = np.array(cv.imencode(".png", gray)[1], dtype=np.uint8)
        return gray

    def filter_edges(self, image):
        if image.shape[2] == 3:
            gray = cv.cvtColor(image, cv.COLOR_RGB2GRAY)
        elif image.shape[2] == 4:
            gray = cv.cvtColor(image, cv.COLOR_RGBA2GRAY)
        else:
            gray = image
        thresh = cv.threshold(gray, 135, 255, cv.THRESH_BINARY)[1]
        kernel = cv.getStructuringElement(cv.MORPH_RECT, (7, 7))
        dilate = cv.morphologyEx(thresh, cv.MORPH_DILATE, kernel)
        diff = cv.absdiff(dilate, thresh)
        edges = 255 - diff

        edges = np.array(cv.imencode(".png", edges)[1], dtype=np.uint8)
        return edges

    def filter_canny_edges(self, image):
        if image.shape[2] == 3:
            gray = cv.cvtColor(image, cv.COLOR_RGB2GRAY)
        elif image.shape[2] == 4:
            gray = cv.cvtColor(image, cv.COLOR_RGBA2GRAY)
        else:
            gray = image
        blur = cv.GaussianBlur(gray, (5, 5), 0.5)
        edges = cv.Canny(blur, 100, 200)
        edges = edges * -1 + 255

        edges = np.array(cv.imencode(".png", edges)[1], dtype=np.uint8)
        return edges

    def filter_sine_horizontal(self, image):
        A = image.shape[0] / 20.0
        w = 4.0 / image.shape[1]
        shift = lambda x: A * np.sin(2.0 * np.pi * x * w)

        for i in range(image.shape[1]):
            image[:, i, 0] = np.roll(image[:, i, 0], int(shift(i)))
        if image.shape[2] > 1:
            for i in range(image.shape[1]):
                image[:, i, 1] = np.roll(image[:, i, 1], int(shift(i)))
                image[:, i, 2] = np.roll(image[:, i, 2], int(shift(i)))
        if image.shape[2] > 3:
            for i in range(image.shape[1]):
                image[:, i, 3] = np.roll(image[:, i, 3], int(shift(i)))

        image = np.array(cv.imencode(".png", image)[1], dtype=np.uint8)
        return image

    def filter_sine_vertical(self, image):
        A = image.shape[0] / 20.0
        w = 4.0 / image.shape[1]
        shift = lambda x: A * np.sin(2.0 * np.pi * x * w)

        for i in range(image.shape[0]):
            image[i, :, 0] = np.roll(image[i, :, 0], int(shift(i)))
        if image.shape[2] > 1:
            for i in range(image.shape[0]):
                image[i, :, 1] = np.roll(image[i, :, 1], int(shift(i)))
                image[i, :, 2] = np.roll(image[i, :, 2], int(shift(i)))
        if image.shape[2] > 3:
            for i in range(image.shape[0]):
                image[i, :, 3] = np.roll(image[i, :, 3], int(shift(i)))

        image = np.array(cv.imencode(".png", image)[1], dtype=np.uint8)
        return image

    def filter_erode(self, image):
        for i in range(20):
            image = cv.erode(image, (9, 9))

        image = np.array(cv.imencode(".png", image)[1], dtype=np.uint8)
        return image

    def filter_dilate(self, image):
        for i in range(20):
            image = cv.dilate(image, (9, 9))

        image = np.array(cv.imencode(".png", image)[1], dtype=np.uint8)
        return image


async def setup(bot):
    await bot.add_cog(FunnyCog(bot))
    logger.info("Loaded cog Funny.")
