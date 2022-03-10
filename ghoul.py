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

# meta title: Ghoul
# meta pic: https://img.icons8.com/fluency/48/000000/dota.png
# meta desc: Show other chat members that you are ghoul


from .. import loader
from asyncio import sleep
from math import floor

from telethon.tl.types import Message


@loader.tds
class GULMod(loader.Module):
    """Show other chat members that you are ghoul"""

    strings = {"name": "Ghoul", "iamghoul": "<b>I am ghoul!</b>"}

    async def гульcmd(self, message: Message) -> None:
        """Sends ghoul message"""
        x = 1000
        emojies = ["⚫️", "⚪️", "⬜️"]
        await message.edit(self.strings("iamghoul", message))
        await sleep(2)
        while x > 0:
            await message.edit(
                emojies[floor((1000 - x) / (1000 / len(emojies)))]
                + str(x)
                + " - 7 = "
                + str(x - 7)
            )
            x -= 7
            await sleep(1)
