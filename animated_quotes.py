"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    © Copyright 2022 t.me/hikariatama
    Licensed under CC BY-NC-ND 4.0

    🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
"""

# meta pic: https://img.icons8.com/external-flaticons-lineal-color-flat-icons/344/external-anime-addiction-flaticons-lineal-color-flat-icons.png
# meta developer: @hikariatama

from .. import loader, utils
from telethon.tl.types import Message
from random import choice


@loader.tds
class AnimatedQuotesMod(loader.Module):
    """Simple module to create animated stickers via bot"""

    strings = {
        "name": "AnimatedQuotes",
        "no_text": "🚫 <b>Provide a text to create sticker with</b>",
        "processing": "⏱ <b>Processing...</b>",
    }

    async def client_ready(self, client, db) -> None:
        self._client = client

    async def aniqcmd(self, message: Message) -> None:
        """<text> - Create animated quote"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_text"))
            return

        message = await utils.answer(message, self.strings("processing"))
        if isinstance(message, (list, set, tuple)):
            message = message[0]

        try:
            query = await self._client.inline_query("@QuotAfBot", args)
            await message.respond(file=choice(query[1:3]).document)
        except Exception as e:
            await utils.answer(message, str(e))
            return

        await message.delete()
