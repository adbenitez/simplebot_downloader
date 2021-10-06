"""Utilities."""

import functools
import mimetypes
import os
import re
from tempfile import TemporaryDirectory
from typing import Callable, Generator

import multivolumefile
import py7zr
import requests
from simplebot.bot import DeltaBot

session = requests.Session()
session.headers.update(
    {
        "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
    }
)
session.request = functools.partial(session.request, timeout=15)  # noqa


class FileTooBig(ValueError):
    """File is too big."""


def get_setting(bot: DeltaBot, key: str, value=None) -> str:
    """Get setting value, if value is given and the setting is not set, the setting will be set to the given value."""
    scope = __name__.split(".", maxsplit=1)[0]
    val = bot.get(key, scope=scope)
    if val is None and value is not None:
        bot.set(key, value, scope=scope)
        val = value
    return val


def download_file(url: str, folder: str, max_size: int) -> str:
    """Download URL and save the file in the give folder.

    If the file is bigger than max_size a FileTooBig exception is raised.
    Returns the path of the downloaded file.
    """
    if not url.startswith("http"):
        url = "http://" + url
    with session.get(url, stream=True) as resp:
        resp.raise_for_status()
        filepath = os.path.join(folder, get_filename(resp)[-20:].lstrip("."))
        with open(filepath, "wb") as file:
            size = 0
            for chunk in resp.iter_content(chunk_size=1024 * 500):
                size += len(chunk)
                if size > max_size:
                    raise FileTooBig(
                        f"Only files smaller than {sizeof_fmt(max_size)} are allowed"
                    )
                file.write(chunk)

    return filepath


def split_download(
    url: str, part_size: int, max_size: int, downloader: Callable = download_file
) -> Generator:
    with TemporaryDirectory() as tempdir:
        path = downloader(url, tempdir, max_size)
        if os.stat(path).st_size > part_size:
            with multivolumefile.open(path + ".7z", "wb", volume=part_size) as vol:
                with py7zr.SevenZipFile(
                    vol, "w", filters=[{"id": py7zr.FILTER_COPY}]
                ) as archive:
                    archive.write(path, os.path.basename(path))

            os.remove(path)
            parts = sorted(os.listdir(tempdir))
            parts_count = len(parts)
            for num, filename in enumerate(parts, 1):
                path = os.path.join(tempdir, filename)
                yield path, num, parts_count
                os.remove(path)
        else:
            yield path, 1, 1


def get_filename(resp: requests.Response) -> str:
    disp = resp.headers.get("content-disposition")
    if disp is not None and re.findall("filename=(.+)", disp):
        fname = re.findall("filename=(.+)", disp)[0].strip('"')
    else:
        fname = resp.url.split("/")[-1].split("?")[0].split("#")[0]

    if "." in fname:
        return fname

    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if ctype == "text/plain":
        ext = ".txt"
    elif ctype == "image/jpeg":
        ext = ".jpg"
    else:
        ext = mimetypes.guess_extension(ctype) or ""
    return (fname or "file") + ext


def sizeof_fmt(num: float) -> str:
    """Format size in human redable form."""
    suffix = "B"
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)  # noqa
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)  # noqa
