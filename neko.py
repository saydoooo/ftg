# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/fluency/48/000000/anime.png
# scope: hikka_only
# meta developer: @hikariatama
# requires: urllib requests

from .. import loader, utils
import requests
import json
from urllib.parse import quote_plus
import asyncio
import random
from telethon.tl.types import Message
import functools

phrases = ["Uwu", "Senpai", "Uff", "Meow", "Bonk", "Ara-ara", "Hewwo", "You're cute!"]

faces = [
    "ʕ•ᴥ•ʔ",
    "(ᵔᴥᵔ)",
    "(◕‿◕✿)",
    "(づ￣ ³￣)づ",
    "♥‿♥",
    "~(˘▾˘~)",
    "(｡◕‿◕｡)",
    "｡◕‿◕｡",
    "ಠ‿↼",
]


async def photo(self, args: str) -> str:
    return (await utils.run_sync(requests.get, f"{self.endpoints['img']}{args}")).json()["url"]


@loader.tds
class NekosLifeMod(loader.Module):
    """NekosLife API Wrapper"""

    strings = {"name": "NekosLife"}

    async def client_ready(self, client, db):
        self._client = client
        ans = (
            await utils.run_sync(requests.get, "https://nekos.life/api/v2/endpoints")
        ).json()
        self.categories = json.loads(
            "["
            + [_ for _ in ans if "/api" in _ and "/img/" in _][0]
            .split("<")[1]
            .split(">")[0]
            .replace("'", '"')
            + "]"
        )
        self.endpoints = {
            "img": "https://nekos.life/api/v2/img/",
            "owoify": "https://nekos.life/api/v2/owoify?text=",
            "why": "https://nekos.life/api/v2/why",
            "cat": "https://nekos.life/api/v2/cat",
            "fact": "https://nekos.life/api/v2/fact",
        }

    @loader.pm
    async def nkcmd(self, message: Message):
        """Send anime pic"""
        args = utils.get_args_raw(message)
        args = "neko" if args not in self.categories else args
        pic = functools.partial(photo, self=self, args=args)
        await self.inline.gallery(
            message=message,
            next_handler=pic,
            caption=lambda: f"<i>{random.choice(phrases)}</i> {random.choice(faces)}",
        )

    @loader.pm
    async def nkctcmd(self, message: Message):
        """Show available categories"""
        cats = "\n".join(
            [" | </code><code>".join(_) for _ in utils.chunks(self.categories, 5)]
        )
        await utils.answer(
            message,
            f"<b>Available categories:</b>\n<code>{cats}</code>",
        )

    @loader.unrestricted
    async def owoifycmd(self, message: Message):
        """OwOify text"""
        args = utils.get_args_raw(message)
        if not args:
            args = await message.get_reply_message()
            if not args:
                await message.delete()
                return

            args = args.text

        if len(args) > 180:
            message = await utils.answer(message, "<b>OwOifying...</b>")
            try:
                message = message[0]
            except Exception:
                pass

        args = quote_plus(args)
        owo = ""
        for chunk in utils.chunks(args, 180):
            owo += (
                await utils.run_sync(requests.get, f"{self.endpoints['owoify']}{chunk}")
            ).json()["owo"]
            await asyncio.sleep(0.1)
        await utils.answer(message, owo)

    @loader.unrestricted
    async def whycmd(self, message: Message):
        """Why?"""
        await utils.answer(
            message,
            f"<code>👾 {(await utils.run_sync(requests.get, self.endpoints['why'])).json()['why']}</code>",
        )

    @loader.unrestricted
    async def factcmd(self, message: Message):
        """Did you know?"""
        await utils.answer(
            message,
            f"<b>🧐 Did you know, that </b><code>{(await utils.run_sync(requests.get, self.endpoints['fact'])).json()['fact']}</code>",
        )

    @loader.unrestricted
    async def meowcmd(self, message: Message):
        """Sends cat ascii art"""
        await utils.answer(
            message,
            f"<b>{(await utils.run_sync(requests.get, self.endpoints['cat'])).json()['cat']}</b>",
        )
