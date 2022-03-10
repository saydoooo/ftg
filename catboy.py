"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    Copyright 2022 t.me/hikariatama
    Licensed under the Creative Commons CC BY-NC-ND 4.0

    Full license text can be found at:
    https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode

    Human-friendly one:
    https://creativecommons.org/licenses/by-nc-nd/4.0
"""

# meta title: Catboy
# meta pic: https://img.icons8.com/color/48/000000/neko-boy.png
# meta desc: Sends cute anime boy pictures


from .. import loader, utils
from telethon.tl.types import Message
import logging
import requests
from random import choice
from aiogram.types import CallbackQuery

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

# requires: requests

logger = logging.getLogger(__name__)


@loader.tds
class CatboyMod(loader.Module):
    """Sends cute anime boy pictures"""

    strings = {"name": "Catboy"}

    def get(self, *args) -> dict:
        return self.db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self.db.set(self.strings["name"], *args)

    async def client_ready(self, client, db) -> None:
        self.db = db
        self.client = client

    async def inline__next(self, call: CallbackQuery, chat: int, msg_id: int) -> None:
        url = requests.get("https://api.catboys.com/img").json()["url"]
        caption = f"<i>{choice(phrases)}</i> {choice(faces)}"

        await self.client.edit_message(chat, msg_id, file=url)
        await call.edit(
            caption,
            reply_markup=[
                [
                    {
                        "text": "🎲 Next",
                        "callback": self.inline__next,
                        "args": (chat, msg_id),
                    }
                ]
            ],
        )

    async def catboycmd(self, message: Message) -> None:
        """Send catboy picture"""
        url = requests.get("https://api.catboys.com/img").json()["url"]
        await message.delete()

        caption = f"<i>{choice(phrases)}</i> {choice(faces)}"

        if not hasattr(self, "inline") or not self.inline.init_complete:
            await self.client.send_file(
                message.peer_id, url, caption=caption, reply_to=message.reply_to_msg_id
            )
        else:
            m = await self.client.send_file(
                message.peer_id, url, reply_to=message.reply_to_msg_id
            )
            await self.inline.form(
                caption,
                message=message,
                reply_markup=[
                    [
                        {
                            "text": "🎲 Next",
                            "callback": self.inline__next,
                            "args": (utils.get_chat_id(m), m.id),
                        }
                    ]
                ],
                ttl=15 * 60,
            )
