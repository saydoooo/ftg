# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/stickers/100/000000/python.png
# meta developer: @hikariatama
# requires: black

from .. import loader, utils
from telethon.tl.types import Message
import logging
import requests
import re
import io
from random import choice

logging.getLogger("blib2to3.pgen2.driver").setLevel(logging.ERROR)

import black  # noqa: E402

logger = logging.getLogger(__name__)

URL = r"(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-&?=%.]+"

captions = [
    "Here is your new fresh linted code! Enjoy",
    "This was such a hard work to clean this code... Uff..",
    "Here we go!",
    "Glad to be your virtual code-cleaning-maid!",
    "Take this, master!",
]

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


@loader.tds
class PyLinterMod(loader.Module):
    """`Black` plugin wrapper for telegram"""

    strings = {"name": "PyLinter", "no_code": "🚫 <b>Please, specify code to lint</b>"}

    async def client_ready(self, client, db):
        self._db = db
        self._client = client

    async def lintcmd(self, message: Message):
        """[code|reply] - Perform automatic lint to python code"""
        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        media = message.media or (reply.media if reply else False)

        if media:
            try:
                args = (await self._client.download_file(media)).decode("utf-8")
            except TypeError:
                pass

        if not args:
            if not reply:
                await utils.answer(message, self.strings("no_code"))
                return

            args = reply.raw_text

        if re.match(URL, args):
            args = (await utils.run_sync(requests.get, args)).text

        lint_result = black.format_str(args, mode=black.Mode())

        if len(lint_result) < 2048:
            await utils.answer(
                message,
                f"<code>{utils.escape_html(lint_result)}</code>",
            )
            return

        file = io.BytesIO(args.encode("utf-8"))
        file.name = "lint_result.py"
        await self._client.send_file(
            message.peer_id,
            file,
            caption=f"<i>{choice(captions)}</i> <b>{choice(faces)}</b>",
        )
        if message.out:
            await message.delete()
