"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    © Copyright 2022 t.me/hikariatama
    Licensed under CC BY-NC-ND 4.0

    🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
"""

# meta pic: https://img.icons8.com/fluency/50/000000/event-log.png
# meta developer: @hikariatama
# scope: hikka_only

from .. import loader, utils, main
import logging

logger = logging.getLogger(__name__)


@loader.tds
class OnloadExecutorMod(loader.Module):
    """Executes selected commands after every userbot restart"""

    strings = {"name": "OnloadExecutor"}

    async def client_ready(self, client, db) -> None:
        self._me = (await client.get_me()).id

        self.c, _ = await utils.asset_channel(
            client,
            f"onload-commands-{self._me}",
            "All commands from this chat will be executed once FTG is started, be careful!",
        )

        self.prefix = utils.escape_html(
            (db.get(main.__name__, "command_prefix", False) or ".")[0]
        )

        async for message in client.iter_messages(self.c):
            if (getattr(message, "raw_text", "") or "").startswith(self.prefix):
                try:
                    m = await client.send_message("me", message.raw_text)
                    await self.allmodules.commands[message.raw_text[1:].split()[0]](m)
                    logger.info("Registered onload command")
                    await m.delete()
                except Exception:
                    logger.exception(
                        f"Exception while executing command {message.raw_text[:15]}..."
                    )
