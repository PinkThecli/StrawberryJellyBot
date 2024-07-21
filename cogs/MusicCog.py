import discord
from discord.ext import commands
from discord import app_commands

import pytube
import datetime
import time
import asyncio
import functools
import re
import json
import random
import traceback

import Logger
import BotInfo as info

logger = Logger.getLogger(__name__)


class MusicCog(commands.Cog, name="Music"):
    def __init__(self, bot):
        self.bot = bot
        self.current = {}
        self.queue = {}
        self.repeat_flags = {}
        self.player = {}
        self.music_channel = {}
        self.abort_flags = {}

    """     Commands     """

    @app_commands.command(description=f"Adds a music track to the playlist and starts the player. There is a {info.PLAYER_START_DELAY} s delay before player start.")
    @app_commands.guild_only()
    @app_commands.describe(
        url="Youtube video or playlist url.",
        shuffle="Flag to shuffle the playlist after loading."
    )
    @app_commands.choices(shuffle=[app_commands.Choice(name="Yes", value=1)])
    async def play(self, interaction: discord.Interaction, url: str, shuffle: int = 0):
        await interaction.response.defer()
        original_response = await interaction.original_response()

        if (interaction.user.voice is None) or (interaction.user.voice.channel is None) or (interaction.guild_id != interaction.user.voice.channel.guild.id):
            try:
                await original_response.edit(content="You are not in a voice channel.", delete_after=5)
            except discord.HTTPException:
                pass
            return

        client = await self.get_client(interaction)

        if (client in self.music_channel) == False:
            self.music_channel[client] = interaction.channel

        tracks = self.get_urls_array(url)

        if (client.is_playing() == False) and (client.is_paused() == False):
            self.bot.loop.call_later(info.PLAYER_START_DELAY, self._play, client)

        await self.add_all(client, tracks, interaction.user, original_response)

        if (shuffle == 1) and self._shuffle(client):
            await interaction.channel.send("The playlist was shuffled.", view=None, delete_after=5)

    @app_commands.command(description="Shows a link to the music player if it exists.")
    @app_commands.guild_only()
    async def player(self, interaction: discord.Interaction):
        client = await self.get_client(interaction, False)

        if (client is None) or not (client in self.player):
            await interaction.response.send_message("Player is inactive now.", ephemeral=True, delete_after=5)
            return

        await interaction.response.send_message(f"The player is currently on {self.player[client][0].channel.mention} channel.\nLink: {self.player[client][0].jump_url}", ephemeral=True, delete_after=5)

    @app_commands.command(description="Shuffles the playlist.")
    @app_commands.guild_only()
    async def shuffle(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        original_response = await interaction.original_response()
        client = await self.get_client(interaction, False)

        res = self._shuffle(client)

        if res == True:
            await original_response.edit(content="The queue is shuffled.", delete_after=5)
        else:
            await original_response.edit(content="The queue is currently empty.", delete_after=5)

    @app_commands.command(description="Erases the playlist without stopping the player.")
    @app_commands.guild_only()
    async def erase(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        original_response = await interaction.original_response()
        if (interaction.user.voice is None) or (interaction.user.voice.channel is None) or (interaction.guild_id != interaction.user.voice.channel.guild.id):
            await original_response.edit(content="You are not in the music player voice channel.", delete_after=5)
            return

        client = await self.get_client(interaction, False)
        if (client is None) or (client in self.queue) == False or (len(self.queue[client]) == 0) or (client in self.player) == False:
            await original_response.edit(content="The queue is currently empty.", delete_after=5)
            return

        self.queue[client] = []
        await self.update_player(client)
        await original_response.edit(content="The queue is empty now.", delete_after=5)

    """     Utility functions     """

    def _play(self, client):
        if (client in self.queue) == False:
            return

        while True:
            if self.repeat_flags.get(client):
                self.fill_data(self.current[client])
                break

            if len(self.queue[client]) > 0:
                self.current[client] = self.queue[client].pop(0)
            else:
                self.current[client] = None

            if self.current[client] is None:
                self.destroy_player(client)
                return

            if (client.is_connected() == False):
                return

            res = self.fill_data(self.current[client])

            if res == 1:
                break

        asyncio.ensure_future(self.update_player(client), loop = self.bot.loop)

        client.play(discord.FFmpegPCMAudio(self.current[client]["info"].get("source"), executable="/usr/local/bin/ffmpeg", **info.FFMPEG_OPTIONS), after=lambda _: self._play(client))

    def _shuffle(self, client):
        if (client is None) or (client in self.queue) == False or (len(self.queue[client]) == 0):
            return False

        random.shuffle(self.queue[client])
        asyncio.ensure_future(self.update_player(client), loop=self.bot.loop)
        return True

    async def get_client(self, interaction, create=True):
        client = interaction.guild.voice_client

        if (client is None) and (create == True):
            client = await interaction.user.voice.channel.connect()

        return client

    async def add_all(self, client, tracks, member, original_response):
        if (client in self.abort_flags) == True:
            self.abort(client)

        view = self.create_add_all_view(client)

        i = -1
        j = 0
        time_start = time.time()
        for i in range(len(tracks)):
            res = await self.add(client, tracks[i], member)
            eta = datetime.timedelta(seconds=round((time.time() - time_start) / (i+1)) * (len(tracks) - (i+1)))

            if res == 0:
                j += 1
                continue
            elif res == -1:
                await original_response.edit(content="Aborted.", view=None, delete_after=5)
                return

            try:
                await original_response.edit(content=f"Added {i+1-j}/{len(tracks)-j} tracks to queue.\nEstimated time: {eta}", view=view)
            except discord.HTTPException:
                await original_response.channel.send("Aborted.", delete_after=5)
                return

            await asyncio.sleep(0, loop=self.bot.loop)

        await original_response.edit(content=f"Added {i+1-j} tracks to queue.", view=None, delete_after=5)

    def create_add_all_view(self, client):
        view = discord.ui.View(timeout=None)

        abort_button = discord.ui.Button(label="Abort")

        async def abort_callback(interaction):
            self.abort(client)

        abort_button.callback = abort_callback

        view.add_item(abort_button)

        return view

    async def add(self, client, url, member):
        if (client in self.queue) == False:
            self.queue[client] = []
            self.current[client] = None

        try:
            func = functools.partial(pytube.YouTube, url)
            yt = await self.bot.loop.run_in_executor(None, func)
        except pytube.exceptions.RegexMatchError:
            return 0

        if self.abort_flags.get(client):
            return -1

        title = yt.title

        if self.abort_flags.get(client):
            return -1

        if not (yt.author in title) and not (" - " in title):
            title = yt.author + " - " + title

        if self.abort_flags.get(client):
            return -1

        data = {
            "yt_instance": yt,
            "member": member,
            "url": url,
            "info": {
                "title": title,
                "duration": None,
                "thumbnail_url": None,
                "source": None,
                "channel": {
                    "name": None,
                    "url": None,
                    "avatar_url": None
                }
            },
            "service": {
                "name": "YouTube",
                "icon_filename": "yticon.png"
            },
            "timestamp": None
        }

        self.queue[client].append(data)

        if (len(self.queue[client]) == 1) and (client in self.player):
            await self.update_player(client)

        return 1

    def fill_data(self, track_data):
        yt = pytube.YouTube(track_data["url"])

        duration = str(datetime.timedelta(seconds=yt.length))
        thumbnail_url = yt.thumbnail_url
        source = self.get_source(yt)
        if source is None:
            return 0
        channel_name, channel_url, channel_avatar_url = self.get_channel_data(yt)

        track_data["info"]["duration"] = duration
        track_data["info"]["thumbnail_url"] = thumbnail_url
        track_data["info"]["source"] = source
        track_data["info"]["channel"]["name"] = channel_name
        track_data["info"]["channel"]["url"] = channel_url
        track_data["info"]["channel"]["avatar_url"] = channel_avatar_url

        return 1

    def abort(self, client):
        if (client in self.abort_flags) == False:
            self.abort_flags[client] = True
        else:
            del self.abort_flags[client]

    def repeat(self, client):
        if (client in self.repeat_flags) == False:
            self.repeat_flags[client] = True
        else:
            del self.repeat_flags[client]

    def get_urls_array(self, url):
        if url is None:
            return []
        elif ("&list=" in url) or ("?list=" in url):
            return pytube.contrib.playlist.Playlist(url)
        else:
            return [url]

    def get_source(self, yt):
        try:
            streams = yt.streams
            audio = streams.get_audio_only()
            source = audio.url
        except pytube.exceptions.LiveStreamError:
            return None
        except pytube.exceptions.AgeRestrictedError:
            try:
                yt.bypass_age_gate()
                source = yt.streams.get_audio_only().url
            except pytube.exceptions.AgeRestrictedError:
                return None
        except pytube.exceptions.RegexMatchError:
            tb = traceback.format_exc()
            logger.error(f"Regex error. YT instance: {yt}. Traceback: {tb}")
            return None
        return source

    def get_channel_data(self, yt):
        initial_data = yt.initial_data

        try:
            channel_url = "https://www.youtube.com/channel/" + initial_data["contents"]["twoColumnWatchNextResults"]["results"]["results"] \
                ["contents"][1]["videoSecondaryInfoRenderer"]["owner"]["videoOwnerRenderer"]["title"]["runs"][0]["navigationEndpoint"]["browseEndpoint"]["browseId"]
        except KeyError:
            channel_url = yt.channel_url

        channel = pytube.contrib.channel.Channel(channel_url)
        try:
            data = json.loads(re.search(r"ytInitialData = (.*);</script>", channel.about_html).group(1))
            channel_avatar_url = data["header"]["c4TabbedHeaderRenderer"]["avatar"]["thumbnails"][-1]["url"]
        except KeyError:
            channel_avatar_url = None
            logger.error("No channel avatar (KeyError). Source: "+yt.watch_url)
        except json.JSONDecodeError:
            channel_avatar_url = None
            logger.error("No channel avatar (JSONDecodeError). Source: "+yt.watch_url)
        except:
            channel_avatar_url = None
            logger.error("No channel avatar (None). Source: "+yt.watch_url)

        channel_name = channel.channel_name

        return channel_name, channel_url, channel_avatar_url

    async def update_player(self, client):
        if not (client in self.current) or (self.current[client] is None):
            return
        if (client in self.player) == False:
            await self.create_player(client)
        else:
            embed, attachments = self.create_player_embed(client)
            self.update_player_view(client)
            await self.player[client][0].edit(embed=embed, attachments=attachments, view=self.player[client][1])

    def create_player_embed(self, client):
        current_track = self.current[client]
        next_track = None
        if self.repeat_flags.get(client):
            next_track = current_track["info"].get("title")
        elif len(self.queue[client]) > 0:
            next_track = self.queue[client][0]["info"].get("title")

        if current_track.get("timestamp") is None:
            current_track["timestamp"] = datetime.datetime.now()

        embed = discord.Embed(color=info.EMBED_COLOR, title=current_track["info"].get("title"), url=current_track.get("url"), timestamp=current_track.get("timestamp"))
        embed.add_field(name="Duration:", value=current_track["info"].get("duration"), inline=True)
        embed.add_field(name="Status:", value=("⏸️ Paused" if client.is_paused() else "▶️ Playing"), inline=True)
        embed.add_field(name="Next:", value=("( 🔁 ) " if self.repeat_flags.get(client) else "") + str(next_track), inline=False)
        embed.add_field(name="Requested by:", value=current_track.get("member").mention, inline=False)
        embed.set_thumbnail(url=current_track["info"].get("thumbnail_url"))
        embed.set_author(name=current_track["info"]["channel"].get("name"), url=current_track["info"]["channel"].get("url"), icon_url=current_track["info"]["channel"].get("avatar_url"))
        embed.set_footer(text=current_track["service"].get("name"), icon_url="attachment://" + current_track["service"].get("icon_filename"))

        attachments = [discord.File(info.IMAGES_PATH + "/" + current_track["service"].get("icon_filename"))]

        return embed, attachments

    async def create_player(self, client):
        embed, attachments = self.create_player_embed(client)

        view = discord.ui.View(timeout=None)

        """ Repeat """
        button_repeat = discord.ui.Button(emoji=info.EMOJI_PLAYER_BUTTONS[0])

        async def repeat_callback(interaction):
            if (interaction.user.voice is None) or (interaction.user.voice.channel is None) or (interaction.guild_id != interaction.user.voice.channel.guild.id):
                await interaction.response.send_message("You are not in the music player voice channel.", ephemeral=True, delete_after=5)
                return
            self.repeat(client)
            await self.update_player(client)
            await interaction.response.send_message("Player repeat is " + ("on" if self.repeat_flags.get(client) else "off") + " now.", ephemeral=True, delete_after=1)
        button_repeat.callback = repeat_callback
        view.add_item(button_repeat)

        """ Pause """
        button_play_pause = discord.ui.Button(emoji=info.EMOJI_PLAYER_BUTTONS[1])

        async def play_pause_callback(interaction):
            if (interaction.user.voice is None) or (interaction.user.voice.channel is None) or (interaction.guild_id != interaction.user.voice.channel.guild.id):
                await interaction.response.send_message("You are not in the music player voice channel.", ephemeral=True, delete_after=5)
                return
            if client.is_playing():
                client.pause()
                await self.update_player(client)
                await interaction.response.send_message("Player paused.", ephemeral=True, delete_after=1)
            elif client.is_paused():
                client.resume()
                await self.update_player(client)
                await interaction.response.send_message("Player resumed.", ephemeral=True, delete_after=1)
        button_play_pause.callback = play_pause_callback
        view.add_item(button_play_pause)

        """ Stop """
        button_stop = discord.ui.Button(emoji=info.EMOJI_PLAYER_BUTTONS[2])

        async def stop_callback(interaction):
            if (interaction.user.voice is None) or (interaction.user.voice.channel is None) or (interaction.guild_id != interaction.user.voice.channel.guild.id):
                await interaction.response.send_message("You are not in the music player voice channel.", ephemeral=True, delete_after=5)
                return
            self.destroy_player(client)
            await interaction.response.send_message("Player stopped.", ephemeral=True, delete_after=1)
        button_stop.callback = stop_callback
        view.add_item(button_stop)

        """ Next """
        button_next = discord.ui.Button(emoji=info.EMOJI_PLAYER_BUTTONS[3])

        async def next_callback(interaction):
            if (interaction.user.voice is None) or (interaction.user.voice.channel is None) or (interaction.guild_id != interaction.user.voice.channel.guild.id):
                await interaction.response.send_message("You are not in the music player voice channel.", ephemeral=True, delete_after=5)
                return
            client.stop()
            await interaction.response.send_message("Track skipped.", ephemeral=True, delete_after=1)
        button_next.callback = next_callback
        view.add_item(button_next)

        """ Queue """
        button_queue = discord.ui.Button(label="Queue")

        async def queue_callback(interaction):
            embed, view = self.create_queue_viewer(client)
            if embed is None:
                await interaction.response.send_message("The queue is currently empty.", ephemeral=True, delete_after=5)
                return
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        button_queue.callback = queue_callback
        view.add_item(button_queue)

        message = await self.music_channel[client].send(embed=embed, view=view, files=attachments)

        self.player[client] = [message, view]

    def update_player_view(self, client):
        view = self.player[client][1]

        view.children[0].style = discord.ButtonStyle.green if self.repeat_flags.get(client) else discord.ButtonStyle.gray
        view.children[1].style = discord.ButtonStyle.green if client.is_paused() else discord.ButtonStyle.gray

    def destroy_player(self, client):
        if self.abort_flags.get(client) is None:
            self.abort(client)

        if self.repeat_flags.get(client):
            self.repeat(client)

        if client in self.queue:
            del self.queue[client]

        if client.is_playing() or client.is_paused():
            client.stop()

        if client in self.current:
            del self.current[client]

        if client in self.music_channel:
            del self.music_channel[client]

        if client in self.player:
            try:
                asyncio.ensure_future(self.player[client][0].delete(), loop=self.bot.loop)
            except (discord.NotFound, discord.HTTPException):
                pass
            del self.player[client]

        asyncio.ensure_future(client.disconnect(force=True), loop=self.bot.loop)

    def create_queue_viewer(self, client):
        tracks_formatted = self.format_queue(client)

        if len(tracks_formatted) == 0:
            return None, None

        current_page = [1]
        max_page = (len(tracks_formatted) - 1) // 10 + 1

        content = self.list_page(tracks_formatted, current_page[0])

        embed = discord.Embed(color=info.EMBED_COLOR, title="Tracks queue:", description=content, timestamp=datetime.datetime.now())
        embed.set_footer(text="Note: to refresh the queue request it again.")

        view = self.create_queue_view(current_page, max_page, tracks_formatted, embed)

        return embed, view

    def create_queue_view(self, current_page, max_page, tracks_formatted, embed):
        view = discord.ui.View(timeout=None)

        """ Left """
        button_left = discord.ui.Button(emoji=info.EMOJI_QUEUE_BUTTONS[10], disabled=True)

        async def left_callback(interaction):
            current_page[0] -= 1
            content = self.list_page(tracks_formatted, current_page[0])
            embed.description = content
            button_page1.emoji = info.EMOJI_QUEUE_BUTTONS[int(f"{current_page[0]:02d}"[0])]
            button_page2.emoji = info.EMOJI_QUEUE_BUTTONS[int(f"{current_page[0]:02d}"[1])]
            if current_page[0] == 1:
                button_left.disabled = True
            else:
                button_left.disabled = False
            if current_page[0] == max_page:
                button_right.disabled = True
            else:
                button_right.disabled = False

            await interaction.response.edit_message(embed=embed, view=view)

        button_left.callback = left_callback

        view.add_item(button_left)

        """ Page number """
        button_page1 = discord.ui.Button(emoji=info.EMOJI_QUEUE_BUTTONS[0], disabled=False)
        button_page2 = discord.ui.Button(emoji=info.EMOJI_QUEUE_BUTTONS[1], disabled=False)

        async def page_callback(interaction):
            await interaction.response.send_message(f"Page {current_page[0]}.", ephemeral=True, delete_after=1)

        button_page1.callback = page_callback
        button_page2.callback = page_callback

        view.add_item(button_page1)
        view.add_item(button_page2)

        """ Right """
        button_right = discord.ui.Button(emoji=info.EMOJI_QUEUE_BUTTONS[11], disabled=(max_page == 1))

        async def right_callback(interaction):
            current_page[0] += 1
            content = self.list_page(tracks_formatted, current_page[0])
            embed.description = content
            button_page1.emoji = info.EMOJI_QUEUE_BUTTONS[int(f"{current_page[0]:02d}"[0])]
            button_page2.emoji = info.EMOJI_QUEUE_BUTTONS[int(f"{current_page[0]:02d}"[1])]
            if current_page[0] == 1:
                button_left.disabled = True
            else:
                button_left.disabled = False
            if current_page[0] == max_page:
                button_right.disabled = True
            else:
                button_right.disabled = False

            await interaction.response.edit_message(embed=embed, view=view)

        button_right.callback = right_callback

        view.add_item(button_right)

        return view

    def list_page(self, strs, page, count=10):
        start_i = (page-1) * count
        end_i = start_i + count - 1

        if end_i >= len(strs):
            end_i = len(strs) - 1

        result = ""
        for i in range(start_i, end_i + 1):
            result += strs[i]
            result += "\n\n" if i < end_i else ""

        return result

    def format_queue(self, client):
        if (client in self.queue) == False:
            return []

        queue = self.queue[client].copy()

        length = len(queue)
        queue_list = []
        for i in range(length):
            title = queue[i]["info"].get("title")
            url = queue[i].get("url")
            member_mention = queue[i].get("member").mention
            queue_list.append(f"**{i+1}.** [{title}]({url})\nRequested by: {member_mention}")

        return queue_list

    """     Listeners     """

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id != self.bot.user.id:
            return

        if not (before.channel is None) and (after.channel is None):
            await asyncio.sleep(3)
            client = None
            for cl in self.player.keys():
                if cl.guild.id == member.guild.id:
                    client = cl
                    break

            if not (client is None) and not client.is_connected():
                self.destroy_player(client)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.id != self.bot.user.id:
            return

        if message.guild is None:
            return

        client = None
        for cl in self.bot.voice_clients:
            if cl.guild.id == message.guild.id:
                client = cl
                break

        if client is None:
            return

        if (client in self.player) == False:
            return

        if (message.id == self.player[client][0].id) and (client.is_playing() or client.is_paused()):
            del self.player[client]
            await self.update_player(client)


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
    logger.info("Loaded cog Music.")
