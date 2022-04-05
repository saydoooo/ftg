# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/color/48/000000/anonymous-mask.png
# meta developer: @hikariatama
# scope: inline
# scope: hikka_only
# scope: hikka_min 1.0.20

from .. import loader, utils
from aiogram.types import CallbackQuery
import logging
from ..inline.types import InlineQuery
from telethon.utils import get_display_name
import time

logger = logging.getLogger(__name__)


@loader.tds
class SpoilersMod(loader.Module):
    """Create spoilers, that can be accessed only by certain users"""

    strings = {"name": "Spoilers"}

    async def client_ready(self, client, db) -> None:
        self._db = db
        self._client = client
        self._me = (await client.get_me()).id
        self._messages = {
            message_id: message
            for message_id, message in self.get("messages", {}).items()
            if message["ttl"] > time.time()
        }

    async def hide_inline_handler(self, query: InlineQuery) -> None:
        """Create new hidden message"""
        text = query.args
        for_user = "Specify username in the end"
        for_user_id = None
        user = None
        if len(text.split()) > 1 and text.split()[-1].startswith("@"):
            try:
                user = await self._client.get_entity(text.split()[-1])
            except Exception:
                pass
            else:
                for_user = "Hidden message for " + get_display_name(user)
                for_user_id = user.id

        message_id = None

        if for_user_id:
            message_id = utils.rand(16)

            self._messages[message_id] = {
                "text": " ".join(text.split(" ")[:-1]),
                "ttl": round(time.time() + 12 * 60 * 60),
                "for": for_user_id,
            }

            self.set("messages", self._messages)

        return {
            "title": for_user,
            "description": "ℹ Only (s)he will be able to open it",
            "message": (
                f'🙈 <b>Hidden message for <a href="tg://user?id={for_user_id}">{utils.escape_html(get_display_name(user))}</a></b>\n<i>You can open this message only once!</i>'
                if user
                else "🚫 <b>User not specified</b>"
            ),
            "thumb": "https://img.icons8.com/color/48/000000/anonymous-mask.png",
            "reply_markup": {"text": "👀 Open", "data": message_id}
            if message_id
            else {},
        }

    async def button_callback_handler(self, call: CallbackQuery) -> None:
        """
        Process button presses
        @allow: all
        """
        if (
            call.data not in self._messages
            or call.from_user.id != self._messages[call.data]["for"]
            and call.from_user.id != self._me
        ):
            return

        await call.answer(self._messages[call.data]["text"], show_alert=True)

        if call.from_user.id != self._me:
            del self._messages[call.data]
