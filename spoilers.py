__version__ = (1, 0, 2)
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
# scope: hikka_min 1.1.6

from .. import loader, utils
import logging
from ..inline.types import InlineQuery, InlineCall
from telethon.utils import get_display_name

logger = logging.getLogger(__name__)


@loader.tds
class SpoilersMod(loader.Module):
    """Create spoilers, that can be accessed only by certain users"""

    strings = {"name": "Spoilers"}

    async def client_ready(self, client, db) -> None:
        self._db = db
        self._client = client
        self._me = (await client.get_me()).id

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

        return {
            "title": for_user,
            "description": "ℹ Only (s)he will be able to open it",
            "message": (
                f'🙈 <b>Hidden message for <a href="tg://user?id={for_user_id}">{utils.escape_html(get_display_name(user))}</a></b>\n<i>You can open this message only once!</i>'
                if user
                else "🚫 <b>User not specified</b>"
            ),
            "thumb": "https://img.icons8.com/color/48/000000/anonymous-mask.png",
            "reply_markup": {
                "text": "👀 Open",
                "callback": self._handler,
                "args": (" ".join(text.split(" ")[:-1]), for_user_id),
                "always_allow": [for_user_id],
            }
            if for_user_id
            else {},
        }

    async def _handler(self, call: InlineCall, text: str, for_user: int) -> None:
        """Process button presses"""
        if call.from_user.id not in {
            for_user,
            self._me,
        }:
            await call.answer("This button is not for you")
            return

        await call.answer(text, show_alert=True)
        await call.edit("🕔 <b>Seen</b>")
