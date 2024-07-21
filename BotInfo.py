""" General """

TOKEN = "TOKEN"

DEV_ID = 484188368838852648

BOT_VERSION = "3.7"

BOT_VERSION_DESCRIPTION = "3.0: Slash commands."

EMBED_COLOR = 0xbd1609

IMAGES_PATH = "./media/images"

GAME = "with mint jelly."

INITIAL_EXTENSIONS = ["cogs.UtilityCog", "cogs.RaspberryCog", "cogs.FunnyCog", "cogs.MusicCog"]

""" Raspberry Cog """

THROTTLING_MESSAGES = {
    0: "Under-voltage!",
    1: "ARM frequency capped!",
    2: "Currently throttled!",
    3: "Soft temperature limit active!",
    16: "Under-voltage has occurred since last reboot.",
    17: "Throttling has occurred since last reboot.",
    18: "ARM frequency capped has occurred since last reboot.",
    19: "Soft temperature limit has occurred."
}

""" Funny Cog """

NUM_IMAGES = 755

""" Music Cog """

PLAYER_START_DELAY = 5

FFMPEG_OPTIONS = {"before_options": "-loglevel quiet -reconnect 1 -reconnect_streamed 1 -reconnect_on_http_error 4xx -reconnect_delay_max 5", "options": "-vn"}

EMOJI_PLAYER_BUTTONS = ["🔁", "⏸️", "⏹️", "⏭️"]
EMOJI_QUEUE_BUTTONS = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "⬅️", "➡️"]

""" Utility Cog """

DELETE_ALLOWED_LIST = [
    484188368838852648,
    288726415719923712,
    444982515690766347
]

