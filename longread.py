# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/external-wanicon-flat-wanicon/64/000000/external-read-free-time-wanicon-flat-wanicon.png
# meta developer: @hikariatama
# scope: inline
# scope: hikka_only
# scope: hikka_min 1.0.20

from .. import loader, utils
from aiogram.types import CallbackQuery
import logging
from ..inline.types import InlineQuery
from telethon.tl.types import Message
import time

logger = logging.getLogger(__name__)


@loader.tds
class LongReadMod(loader.Module):
    """Pack longreads under button spoilers"""

    strings = {
        "name": "LongRead",
        "no_text": "🚫 <b>Please, specify text to hide</b>",
        "longread": "🗄 <b>This is long read</b>\n<i>Click button to show text!\nThis button is active withing 6 hours</i>",
    }

    async def client_ready(self, client, db) -> None:
        self._db = db
        self._longreads = {
            id_: obj
            for id_, obj in self.get("longreads", {}).items()
            if obj["ttl"] > time.time()
        }

    async def inline__close(self, call: CallbackQuery) -> None:
        await call.delete()

    def _create_longread(self, text: str) -> str:
        message_id = utils.rand(16)

        self._longreads[message_id] = {
            "text": text,
            "ttl": round(time.time() + 6 * 60 * 60),
        }

        self.set("longreads", self._longreads)

        return message_id

    async def lr_inline_handler(self, query: InlineQuery) -> None:
        """Create new hidden message"""
        text = query.args

        if not text:
            return

        return {
            "title": "Create new longread",
            "description": "ℹ This will create button-spoiler",
            "message": self.strings("longread"),
            "reply_markup": {
                "text": "📖 Open spoiler",
                "data": self._create_longread(text),
            },
            "thumb": "https://img.icons8.com/external-wanicon-flat-wanicon/64/000000/external-read-free-time-wanicon-flat-wanicon.png",
        }

    async def lrcmd(self, message: Message) -> None:
        """<text> - Create new longread"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_text"))
            return

        await self.inline.form(
            self.strings("longread"),
            message=message,
            reply_markup=[
                [{"text": "📖 Open spoiler", "data": self._create_longread(args)}]
            ],
        )

    async def button_callback_handler(self, call: CallbackQuery) -> None:
        """Process button presses
        @allow: all
        """
        if call.data not in self._longreads:
            return

        await self.inline.bot.edit_message_text(
            inline_message_id=call.inline_message_id,
            text=self._longreads[call.data]["text"],
            disable_web_page_preview=True,
        )

        await call.answer()

        del self._longreads[call.data]
