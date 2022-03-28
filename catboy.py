"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    © Copyright 2022 t.me/hikariatama
    Licensed under CC BY-NC-ND 4.0

    🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
"""

# meta pic: https://img.icons8.com/color/48/000000/neko-boy.png
# meta developer: @hikariatama
# requires: requests
# scope: hikka_only
# scope: hikka_min 1.0.7

from .. import loader, utils
from telethon.tl.types import Message
import requests


async def photo() -> str:
    return [
        (
            await utils.run_sync(
                requests.get,
                "https://api.catboys.com/img"
            )
        ).json()["url"]
    ]


@loader.tds
class CatboyMod(loader.Module):
    """Sends cute anime boy pictures"""

    strings = {"name": "Catboy"}

    async def client_ready(self, client, db) -> None:
        self._client = client

    async def catboycmd(self, message: Message) -> None:
        """Send catboy picture"""
        await self.inline.gallery(
            caption=lambda: f"<i>{utils.escape_html(utils.ascii_face())}</i>",
            message=message,
            next_handler=photo,
            preload=5,
        )
