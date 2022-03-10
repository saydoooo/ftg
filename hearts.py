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

# meta title: Hearts
# meta pic: https://img.icons8.com/fluency/48/000000/filled-like.png
# meta desc: Big animated hearts


from .. import loader, utils
from asyncio import sleep

from telethon.tl.types import Message


@loader.tds
class HeartsMod(loader.Module):
    """Big animated hearts"""

    strings = {"name": "Hearts"}

    async def heartscmd(self, message: Message) -> None:
        message = await utils.answer(message, "<b>ily &lt;3</b>")
        for _ in range(10):
            for heart in ["🤎", "❤", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍"]:
                await utils.answer(message, heart)
                await sleep(0.4)
