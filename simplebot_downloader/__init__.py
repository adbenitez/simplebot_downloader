"""Hooks and filters."""

import time
from threading import Thread
from typing import Dict, Generator

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
downloads: Dict[str, Generator] = {}


@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    get_setting(bot, "max_size", DEF_MAX_SIZE)
    get_setting(bot, "part_size", DEF_PART_SIZE)


@simplebot.hookimpl
def deltabot_start(bot: DeltaBot) -> None:
    Thread(target=_send_files, args=(bot,)).start()


@simplebot.filter
def download_link(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Send me in private any direct download link and I will send you the file.

    Example:
    https://example.com/path/to/file.zip
    """
    if message.chat.is_group() or not message.text.startswith("http"):
        return
    addr = message.get_sender_contact().addr
    if addr in downloads:
        replies.add(text="❌ You already have a download in queue", quote=message)
    elif len(downloads) >= 50:
        replies.add(
            text="❌ I'm too busy with too many downloads, try again later",
            quote=message,
        )
    else:
        replies.add(text="✔️ Request added to queue", quote=message)
        part_size = int(get_setting(bot, "part_size"))
        max_size = int(get_setting(bot, "max_size"))
        downloads[addr] = split_download(message.text, part_size, max_size)


def _send_files(bot: DeltaBot) -> None:
    replies = Replies(bot, bot.logger)
    while True:
        for addr, parts in list(downloads.items()):
            chat = bot.get_chat(addr)
            try:
                path, num, parts_count = next(parts)
                replies.add(text=f"Part {num}/{parts_count}", filename=path, chat=chat)
                replies.send_reply_messages()
                if num == parts_count:
                    next(parts, None)  # close context
                    downloads.pop(addr, None)
            except FileTooBig as ex:
                downloads.pop(addr, None)
                replies.add(text=f"❌ {ex}", chat=chat)
                replies.send_reply_messages()
            except (StopIteration, Exception) as ex:
                bot.logger.exception(ex)
                downloads.pop(addr, None)
                replies.add(
                    text="❌ Failed to download file, is the link correct?", chat=chat
                )
                replies.send_reply_messages()
        time.sleep(5)
