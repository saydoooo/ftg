# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/fluency/48/000000/dota.png
# meta developer: @hikariatama
# scope: inline
# scope: hikka_only
# scope: hikka_min 1.0.25

from .. import loader
from telethon.tl.types import Message
from aiogram.types import CallbackQuery
import logging
import asyncio

logger = logging.getLogger(__name__)


@loader.tds
class InlineGhoulMod(loader.Module):
    """Non-spammy ghoul module"""

    strings = {
        "name": "InlineGhoul",
        "iamghoul": "🧐 <b>Who am I?</b>",
        "tired": "😾 <b>I'm tired to count!</b>",
    }

    async def inline_close(self, call: CallbackQuery) -> None:
        await call.close()

    async def inline__handler(self, call: CallbackQuery, correct: bool) -> None:
        if not correct:
            await call.answer("NO!")
            return

        x = 1000
        while x > 900:
            await call.edit(f"👊 <b>{x} - 7 = {x - 7}</b>")
            x -= 7
            await asyncio.sleep(1)

        await call.edit(self.strings("tired"))
        await asyncio.sleep(10)
        await call.edit(
            self.strings("tired"),
            reply_markup={"text": "💔 Хочу также!", "url": "https://t.me/chat_ftg"},
        )
        await call.unload()

    async def ghoulcmd(self, message: Message) -> None:
        """Sends ghoul message"""
        await self.inline.form(
            self.strings("iamghoul"),
            message=message,
            reply_markup=[
                {
                    "text": "🧠 Ghoul",
                    "callback": self.inline__handler,
                    "args": (True,),
                },
                {
                    "text": "💃 Ballerina",
                    "callback": self.inline__handler,
                    "args": (False,),
                },
            ],
            disable_security=True,
        )
