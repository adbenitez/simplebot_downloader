import functools
import io
import mimetypes
import os
import re
import shutil
import zipfile
import zlib
from tempfile import NamedTemporaryFile
from urllib.parse import quote, quote_plus, unquote_plus

import bs4
import requests
import simplebot
from deltachat import Message
from html2text import html2text
from readability import Document
from simplebot.bot import DeltaBot, Replies

__version__ = "1.0.0"
zlib.Z_DEFAULT_COMPRESSION = 9
session = requests.Session()
session.headers.update(
    {
        "user-agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0"
    }
)
session.request = functools.partial(session.request, timeout=60)
img_providers: list


class FileTooBig(ValueError):
    pass


@simplebot.hookimpl
def deltabot_init(bot: DeltaBot) -> None:
    global img_providers
    img_providers = [_dogpile_imgs, _startpage_imgs, _google_imgs]

    _getdefault(bot, "max_size", 1024 * 1024 * 5)


@simplebot.filter(name=__name__)
def filter_messages(bot: DeltaBot, message: Message, replies: Replies) -> None:
    """Process messages containing URLs."""
    match = re.search(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|"
        r"(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        message.text,
    )
    if not match:
        return
    kwargs = dict(quote=message)
    url = match.group()
    nitter = _getdefault(bot, "nitter_instance", "https://nitter.cc")
    if url.startswith("https://twitter.com/"):
        url = url.replace("https://twitter.com", nitter, count=1)
    elif url.startswith("https://mobile.twitter.com/"):
        url = url.replace("https://mobile.twitter.com/", nitter, count=1)
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        content_type = r.headers.get("content-type", "").lower()
        if "text/html" in content_type:
            soup = bs4.BeautifulSoup(r.text, "html5lib")
            for t in soup("script"):
                t.extract()
            if soup.title:
                kwargs["text"] = soup.title.get_text().strip()
            else:
                kwargs["text"] = "Page without title"
            url = r.url
            index = url.find("/", 8)
            if index == -1:
                root = url
            else:
                root = url[:index]
                url = url.rsplit("/", 1)[0]
            tags = (
                ("a", "href", "mailto:"),
                ("img", "src", "data:"),
                ("source", "src", "data:"),
                ("link", "href", None),
            )
            for tag, attr, iprefix in tags:
                for e in soup(tag, attrs={attr: True}):
                    if iprefix and e[attr].startswith(iprefix):
                        continue
                    e[attr] = re.sub(
                        r"^(//.*)", r"{}:\1".format(root.split(":", 1)[0]), e[attr]
                    )
                    e[attr] = re.sub(r"^(/.*)", r"{}\1".format(root), e[attr])
                    if not re.match(r"^https?://", e[attr]):
                        e[attr] = "{}/{}".format(url, e[attr])
            kwargs["html"] = str(soup)
        elif "image/" in content_type:
            kwargs["filename"] = "image." + re.search(
                r"image/(\w+)", content_type
            ).group(1)
            kwargs["bytefile"] = io.BytesIO(r.content)
        else:
            size = r.headers.get("content-size")
            if not size:
                _size = 0
                max_size = 1024 * 1024 * 5
                for chunk in r.iter_content(chunk_size=102400):
                    _size += len(chunk)
                    if _size > max_size:
                        size = ">5MB"
                        break
                else:
                    size = "{:,}".format(_size)
            ctype = r.headers.get("content-type", "").split(";")[0] or "-"
            kwargs["text"] = "Content Type: {}\nContent Size: {}".format(ctype, size)

    replies.add(**kwargs)


@simplebot.command
def ddg(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Search in DuckDuckGo."""
    mode = _get_mode(bot, message.get_sender_contact().addr)
    page = "lite" if mode == "htmlzip" else "html"
    url = "https://duckduckgo.com/{}?q={}".format(page, quote_plus(payload))
    replies.add(**_download_file(bot, url, mode))


@simplebot.command
def wt(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Search in Wiktionary."""
    sender = message.get_sender_contact().addr
    lang = _get_locale(bot, sender)
    url = "https://{}.m.wiktionary.org/wiki/?search={}".format(
        lang, quote_plus(payload)
    )
    replies.add(**_download_file(url, _get_mode(bot, sender)))


@simplebot.command
def w(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Search in Wikipedia."""
    sender = message.get_sender_contact().addr
    lang = _get_locale(bot, sender)
    url = "https://{}.m.wikipedia.org/wiki/?search={}".format(lang, quote_plus(payload))
    replies.add(**_download_file(bot, url, _get_mode(bot, sender)))


@simplebot.command
def wttr(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Search weather info from wttr.in"""
    lang = _get_locale(bot, message.get_sender_contact().addr)
    url = "https://wttr.in/{}_Fnp_lang={}.png".format(quote(payload), lang)
    reply = _download_file(bot, url)
    reply.pop("text")
    replies.add(**reply)


@simplebot.command
def web(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Download a webpage or file."""
    mode = _get_mode(bot, message.get_sender_contact().addr)
    try:
        replies.add(**_download_file(bot, payload, mode))
    except FileTooBig as err:
        replies.add(text=str(err))


@simplebot.command(name="/read")
def cmd_read(bot: DeltaBot, payload: str, message: Message, replies: Replies) -> None:
    """Download a webpage and try to improve its readability."""
    mode = _get_mode(bot, message.get_sender_contact().addr)
    try:
        replies.add(**_download_file(bot, payload, mode, True))
    except FileTooBig as err:
        replies.add(text=str(err))


@simplebot.command
def img(bot: DeltaBot, payload: str, replies: Replies) -> None:
    """Search for images, returns image links."""
    text = "\n\n".join(_get_images(bot, payload))
    if text:
        replies.add(text="{}:\n\n{}".format(payload, text))
    else:
        replies.add(text="No results for: {}".format(payload))


@simplebot.command
def img1(bot: DeltaBot, payload: str, replies: Replies) -> None:
    """Get an image based on the given text."""
    imgs = _download_images(bot, payload, 1)
    if not imgs:
        replies.add(text="No results for: {}".format(payload))
    else:
        for reply in imgs:
            replies.add(**reply)


@simplebot.command
def img5(bot: DeltaBot, payload: str, replies: Replies) -> None:
    """Search for images, returns 5 results."""
    imgs = _download_images(bot, payload, 5)
    if not imgs:
        replies.add(text="No results for: {}".format(payload))
    else:
        for reply in imgs:
            replies.add(**reply)


def _getdefault(bot: DeltaBot, key: str, value=None) -> str:
    val = bot.get(key, scope=__name__)
    if val is None and value is not None:
        bot.set(key, value, scope=__name__)
        val = value
    return val


def _get_locale(bot: DeltaBot, addr: str) -> str:
    return bot.get("locale", scope=addr) or bot.get("locale") or "en"


def _get_mode(bot: DeltaBot, addr: str) -> str:
    return bot.get("mode", scope=addr) or bot.get("mode") or "htmlzip"


def html2read(html) -> str:
    return Document(html).summary()


def _download_images(bot: DeltaBot, query: str, img_count: int) -> list:
    imgs = _get_images(bot, query)
    results = []
    for img_url in imgs[:img_count]:
        with session.get(img_url) as r:
            r.raise_for_status()
            filename = "web" + (get_ext(r) or ".jpg")
            results.append(dict(filename=filename, bytefile=io.BytesIO(r.content)))
    return results


def _get_images(bot: DeltaBot, query: str) -> list:
    for provider in img_providers.copy():
        try:
            bot.logger.debug("Trying %s", provider)
            imgs = provider(query)
            if imgs:
                return imgs
        except Exception as err:
            img_providers.remove(provider)
            img_providers.append(provider)
            bot.logger.exception(err)
    return []


def _google_imgs(query: str) -> list:
    url = "https://www.google.com/search?tbm=isch&sout=1&q={}".format(quote_plus(query))
    with session.get(url) as r:
        r.raise_for_status()
        soup = bs4.BeautifulSoup(r.text, "html.parser")
    imgs = []
    for table in soup("table"):
        for img in table("img"):
            imgs.append(img["src"])
    return imgs


def _startpage_imgs(query: str) -> list:
    url = "https://startpage.com/do/search"
    url += "?cat=pics&cmd=process_search&query=" + quote_plus(query)
    with session.get(url) as r:
        r.raise_for_status()
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        url = r.url
    soup = soup.find("div", class_="mainline-results")
    if not soup:
        return []
    index = url.find("/", 8)
    if index == -1:
        root = url
    else:
        root = url[:index]
        url = url.rsplit("/", 1)[0]
    imgs = []
    for div in soup("div", {"data-md-thumbnail-url": True}):
        img = div["data-md-thumbnail-url"]
        if img.startswith("data:"):
            continue
        img = re.sub(r"^(//.*)", r"{}:\1".format(root.split(":", 1)[0]), img)
        img = re.sub(r"^(/.*)", r"{}\1".format(root), img)
        if not re.match(r"^https?://", img):
            img = "{}/{}".format(url, img)
        imgs.append(img)
    return imgs


def _dogpile_imgs(query: str) -> list:
    url = "https://www.dogpile.com/search/images?q={}".format(quote_plus(query))
    with session.get(url) as r:
        r.raise_for_status()
        soup = bs4.BeautifulSoup(r.text, "html.parser")
    soup = soup.find("div", class_="mainline-results")
    if not soup:
        return []
    return [img["src"] for img in soup("img")]


def _process_html(bot: DeltaBot, r) -> str:
    html, url = r.text, r.url
    soup = bs4.BeautifulSoup(html, "html5lib")
    for t in soup(["script", "iframe", "noscript", "link", "meta"]):
        t.extract()
    soup.head.append(soup.new_tag("meta", charset="utf-8"))
    for comment in soup.find_all(text=lambda text: isinstance(text, bs4.Comment)):
        comment.extract()
    for b in soup(["button", "input"]):
        if b.has_attr("type") and b["type"] == "hidden":
            b.extract()
        b.attrs["disabled"] = None
    for i in soup(["i", "em", "strong"]):
        if not i.get_text().strip():
            i.extract()
    for f in soup("form"):
        del f["action"], f["method"]
    for t in soup(["img"]):
        src = t.get("src")
        if not src:
            t.extract()
        elif not src.startswith("data:"):
            t.name = "a"
            t["href"] = src
            alt = t.get("alt")
            if not alt:
                alt = "IMAGE"
            t.string = "[{}]".format(alt)
            del t["src"], t["alt"]

            parent = t.find_parent("a")
            if parent:
                t.extract()
                parent.insert_before(t)
                contents = [
                    e for e in parent.contents if not isinstance(e, str) or e.strip()
                ]
                if not contents:
                    parent.string = "(LINK)"
    styles = [str(s) for s in soup.find_all("style")]
    for t in soup(lambda t: t.has_attr("class") or t.has_attr("id")):
        classes = []
        for c in t.get("class", []):
            for s in styles:
                if "." + c in s:
                    classes.append(c)
                    break
        del t["class"]
        if classes:
            t["class"] = " ".join(classes)
        if t.get("id") is not None:
            for s in styles:
                if "#" + t["id"] in s:
                    break
            else:
                del t["id"]
    if url.startswith("https://www.startpage.com"):
        for a in soup("a", href=True):
            u = a["href"].split("startpage.com/cgi-bin/serveimage?url=")
            if len(u) == 2:
                a["href"] = unquote_plus(u[1])

    index = url.find("/", 8)
    if index == -1:
        root = url
    else:
        root = url[:index]
        url = url.rsplit("/", 1)[0]
    for a in soup("a", href=True):
        if not a["href"].startswith("mailto:"):
            a["href"] = re.sub(
                r"^(//.*)", r"{}:\1".format(root.split(":", 1)[0]), a["href"]
            )
            a["href"] = re.sub(r"^(/.*)", r"{}\1".format(root), a["href"])
            if not re.match(r"^https?://", a["href"]):
                a["href"] = "{}/{}".format(url, a["href"])
            a["href"] = "mailto:{}?body=/web%20{}".format(
                bot.self_contact.addr, quote_plus(a["href"])
            )
    return str(soup)


def _process_file(bot: DeltaBot, r) -> tuple:
    max_size = int(_getdefault(bot, "max_size"))
    data = b""
    size = 0
    for chunk in r.iter_content(chunk_size=10240):
        data += chunk
        size += len(chunk)
        if size > max_size:
            msg = "Only files smaller than {} Bytes are allowed"
            raise FileTooBig(msg.format(max_size))

    return (data, get_ext(r))


def get_ext(r) -> str:
    d = r.headers.get("content-disposition")
    if d is not None and re.findall("filename=(.+)", d):
        fname = re.findall("filename=(.+)", d)[0].strip('"')
    else:
        fname = r.url.split("/")[-1].split("?")[0].split("#")[0]
    if "." in fname:
        ext = "." + fname.rsplit(".", maxsplit=1)[-1]
    else:
        ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype == "text/plain":
            ext = ".txt"
        elif ctype == "image/jpeg":
            ext = ".jpg"
        else:
            ext = mimetypes.guess_extension(ctype)
    return ext


def save_file(bot, data, ext: str) -> str:
    with NamedTemporaryFile(
        dir=bot.account.get_blobdir(), prefix="web-", suffix=ext, delete=False
    ) as file:
        path = file.name
    if isinstance(data, str):
        mode = "w"
    else:
        mode = "wb"
    with open(path, mode) as file:
        file.write(data)
    return path


def save_htmlzip(bot, html) -> str:
    with NamedTemporaryFile(
        dir=bot.account.get_blobdir(), prefix="web-", suffix=".html.zip", delete=False
    ) as file:
        path = file.name
    with open(path, "wb") as f:
        with zipfile.ZipFile(f, "w", compression=zipfile.ZIP_DEFLATED) as fzip:
            fzip.writestr("index.html", html)
    return path


def _download_file(
    bot: DeltaBot, url: str, mode: str = "htmlzip", readability: bool = False
) -> dict:
    if "://" not in url:
        url = "http://" + url
    with session.get(url, stream=True) as r:
        r.raise_for_status()
        r.encoding = "utf-8"
        bot.logger.debug("Content type: {}".format(r.headers["content-type"]))
        if "text/html" in r.headers["content-type"]:
            if mode == "text":
                html = html2read(r.text) if readability else r.text
                return dict(text=html2text(html))
            html = _process_html(bot, r)
            if readability:
                html = html2read(html)
            if mode == "md":
                return dict(text=r.url, filename=save_file(bot, html2text(html), ".md"))
            if mode == "html":
                return dict(text=r.url, filename=save_file(bot, html, ".html"))
            return dict(text=r.url, filename=save_htmlzip(bot, html))
        data, ext = _process_file(bot, r)
        return dict(text=r.url, filename="web" + (ext or ""), bytefile=io.BytesIO(data))
