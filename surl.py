# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/external-icongeek26-linear-colour-icongeek26/64/000000/external-short-clothes-icongeek26-linear-colour-icongeek26.png
# meta developer: @hikariatama

from .. import loader, utils, main
from telethon.tl.types import Message, MessageEntityUrl
import logging
import requests

logger = logging.getLogger(__name__)


@loader.tds
class AutoShortenerMod(loader.Module):
    """Automatically shortens urls in your messages, which are larger than specified threshold"""

    strings = {
        "name": "AutoShortener",
        "state": "🔗 <b>Auotmatic url shortener is now {}</b>",
        "no_args": "🔗 <b>No link to shorten</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "threshold",
            80,
            lambda: "Urls larger than this value will be automatically shortened",
            "auto_engine",
            "owo",
            lambda: "Engine to auto-shorten urls with",
        )

    async def client_ready(self, client, db):
        self._db = db
        self.prefix = utils.escape_html(
            (db.get(main.__name__, "command_prefix", False) or ".")[0]
        )

    async def autosurlcmd(self, message: Message):
        """Toggle automatic url shortener"""
        state = not self.get("state", False)
        self.set("state", state)
        await utils.answer(
            message, self.strings("state").format("on" if state else "off")
        )

    async def surlcmd(self, message: Message):
        """[url] [engine]- Shorten url"""
        if (
            not getattr(message, "raw_text", False)
            or not getattr(message, "entities", False)
            or not message.entities
            or not any(
                isinstance(entity, MessageEntityUrl) for entity in message.entities
            )
        ):
            reply = await message.get_reply_message()
            if (
                not reply
                or not getattr(reply, "raw_text", False)
                or not getattr(reply, "entities", False)
                or not reply.entities
                or not any(
                    isinstance(entity, MessageEntityUrl) for entity in reply.entities
                )
            ):
                await utils.answer(message, self.strings("no_args"))
                return

            txt = reply.raw_text
            text = reply.text
            entities = reply.entities
            just_url = False
        else:
            txt = message.raw_text
            text = message.text
            entities = message.entities
            just_url = True

        urls = [
            txt[entity.offset : entity.offset + entity.length] for entity in entities
        ]

        if just_url:
            text = ""

        for url in urls:
            surl = await self.shorten(
                url, txt.split()[-1] if len(txt.split()) > 1 else None
            )
            if not just_url:
                text = text.replace(url, surl)
            else:
                text += f"{surl} | "

        await utils.answer(message, text.strip(" | "))

    @staticmethod
    async def shorten(url, engine=None) -> str:
        if not engine or engine == "gg":
            r = await utils.run_sync(
                requests.post,
                "http://gg.gg/create",
                data={
                    "custom_path": None,
                    "use_norefs": 0,
                    "long_url": url,
                    "app": "site",
                    "version": "0.1",
                },
            )

            return r.text
        elif engine in ["owo", "gay"]:
            r = await utils.run_sync(
                requests.post,
                "https://owo.vc/generate",
                json={
                    "link": url,
                    "generator": engine,
                    "preventScrape": True,
                    "owoify": True,
                },
                headers={"User-Agent": "https://mods.hikariatama.ru/view/surl.py"},
            )

            logger.debug(r.json())

            return "https://" + r.json()["result"]

    async def watcher(self, message: Message):
        if (
            not getattr(message, "text", False)
            or not getattr(message, "out", False)
            or not getattr(message, "entities", False)
            or not message.entities
            or not any(
                isinstance(entity, MessageEntityUrl) for entity in message.entities
            )
            or not self.get("state", False)
            or message.raw_text.lower().startswith(self.prefix)
        ):
            return

        entities = message.entities
        urls = list(
            filter(
                lambda x: len(x) > int(self.config["threshold"]),
                [
                    message.raw_text[entity.offset : entity.offset + entity.length]
                    for entity in entities
                ],
            )
        )

        if not urls:
            return

        text = message.text

        for url in urls:
            text = text.replace(
                url, await self.shorten(url, self.config["auto_engine"])
            )

        await message.edit(text)
