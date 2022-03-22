"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    © Copyright 2022 t.me/hikariatama
    Licensed under CC BY-NC-ND 4.0

    🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
"""

# meta pic: https://img.icons8.com/fluency/48/000000/logbook.png
# meta developer: @hikariatama
# scope: hikka_only

from .. import loader, utils, main
import logging
from telethon.utils import get_display_name
from telethon.tl.types import Message

logger = logging.getLogger(__name__)


@loader.tds
class CommandsLoggerMod(loader.Module):
    """Log any evaluated commands"""

    strings = {"name": "CommandsLogger"}

    async def client_ready(self, client, db):
        self._client = client
        self._db = db

        self.log_channel = await utils.asset_channel(
            client,
            "hikka-log",
            "Executed commands will appear there"
        )
        self.prefix = utils.escape_html(
            (self._db.get(main.__name__, "command_prefix", False) or ".")[0]
        )
        loader.mods = self.allmodules.modules

        logger.warning("CommandsLogger installed")

    async def process_log(self, message: Message) -> None:
        try:
            by = (
                f'\n<b>By: <a href="tg://user?id={message.sender.id}">{get_display_name(message.sender)}</a></b>'
                if not message.out
                else ""
            )
        except AttributeError:
            by = (
                f'\n<b>By: <a href="tg://user?id={message.chat_id}">{get_display_name(await self._client.get_entity(message.chat_id))}</a> in pm</b>'
                if not message.out
                else ""
            )

        await self._client.send_message(
            self.log_channel, f"<code>{self.prefix}{message.raw_text}</code>{by}"
        )
