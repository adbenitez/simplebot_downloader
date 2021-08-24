"""Hooks and filters."""

import os

import simplebot
from deltachat import Message
from pkg_resources import DistributionNotFound, get_distribution
from simplebot.bot import DeltaBot, Replies

from .util import FileTooBig, get_setting, split_download

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    __version__ = "0.0.0.dev0-unknown"
DEF_MAX_SIZE = str(1024 ** 2 * 100)
DEF_PART_SIZE = str(1024 ** 2 * 15)


@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    get_setting(bot, "max_size", DEF_MAX_SIZE)
    get_setting(bot, "part_size", DEF_PART_SIZE)


@simplebot.filter
def download_link(bot: DeltaBot, message: Message) -> None:
    """Send me any direct download link to download file.

    Example:
    https://example.com/path/to/file.zip
    """
    if not message.text.startswith("http"):
        return
    replies = Replies(message, bot.logger)
    chat = bot.get_chat(message.get_sender_contact())
    try:
        part_size = int(get_setting(bot, "part_size"))
        max_size = int(get_setting(bot, "max_size"))
        for path, num, parts_count in split_download(message.text, part_size, max_size):
            replies.add(text=f"Part {num}/{parts_count}", filename=path, chat=chat)
            replies.send_reply_messages()
    except FileTooBig as ex:
        replies.add(text=f"❌ {ex}", quote=message, chat=chat)
    except Exception as ex:
        bot.logger.exception(ex)
        replies.add(
            text="❌ Failed to download file, is the link correct?",
            quote=message,
            chat=chat,
        )
