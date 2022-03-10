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

# meta title: Python
# meta pic: https://img.icons8.com/fluency/48/000000/python.png
# meta desc: Executes python code

import logging
import telethon
from meval import meval
from .. import loader, utils
from traceback import format_exc
import itertools
from types import ModuleType
from telethon.tl.types import Message

logger = logging.getLogger(__name__)


@loader.tds
class PythonMod(loader.Module):
    """Evaluates python code"""

    strings = {
        "name": "Python",
        "eval": "<b>🎬 Code:</b>\n<code>{}</code>\n<b>🪄 Result:</b>\n<code>{}</code>",
        "err": "<b>🎬 Code:</b>\n<code>{}</code>\n\n<b>🚫 Error:</b>\n<code>{}</code>",
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    def lookup(self, modname: str):
        for mod in self.allmodules.modules:
            if mod.name.lower() == modname.lower():
                return mod

    @loader.owner
    async def ecmd(self, message: Message) -> None:
        """MEvaluates python code"""
        phone = message.client.phone
        ret = self.strings("eval", message)
        try:
            it = await meval(
                utils.get_args_raw(message), globals(), **await self.getattrs(message)
            )
        except BaseException:
            exc = format_exc().replace(phone, "📵")
            await utils.answer(
                message,
                self.strings("err", message).format(
                    utils.escape_html(utils.get_args_raw(message)),
                    utils.escape_html(exc),
                ),
            )

            return
        ret = ret.format(
            utils.escape_html(utils.get_args_raw(message)), utils.escape_html(it)
        )
        ret = ret.replace(str(phone), "📵")
        await utils.answer(message, ret)

    async def getattrs(self, message: Message) -> dict:
        return {
            "message": message,
            "client": self.client,
            "self": self,
            "db": self.db,
            "reply": await message.get_reply_message(),
            **self.get_sub(telethon.tl.types),
            **self.get_sub(telethon.tl.functions),
            "event": message,
            "chat": message.to_id,
            "telethon": telethon,
            "utils": utils,
            "f": telethon.tl.functions,
            "c": self.client,
            "m": message,
            "loader": loader,
            "lookup": self.lookup,
        }

    def get_sub(self, it, _depth=1):
        """Get all callable capitalised objects in an object recursively, ignoring _*"""
        # TODO: refactor
        return {
            **dict(
                filter(
                    lambda x: x[0][0] != "_"
                    and x[0][0].upper() == x[0][0]
                    and callable(x[1]),
                    it.__dict__.items(),
                )
            ),
            **dict(
                itertools.chain.from_iterable(
                    [
                        self.get_sub(y[1], _depth + 1).items()
                        for y in filter(
                            lambda x: x[0][0] != "_"
                            and isinstance(x[1], ModuleType)
                            and x[1] != it
                            and x[1].__package__.rsplit(".", _depth)[0]
                            == "telethon.tl",
                            it.__dict__.items(),
                        )
                    ]
                )
            ),
        }
