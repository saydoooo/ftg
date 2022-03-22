"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    © Copyright 2022 t.me/hikariatama
    Licensed under CC BY-NC-ND 4.0

    🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
"""

# meta pic: https://img.icons8.com/fluency/48/000000/spotify.png
# meta developer: @hikariatama

from .. import loader, utils
from telethon.tl.types import Message


@loader.tds
class SpotifyDownloaderMod(loader.Module):
    """Download music from Spotify"""

    strings = {"name": "SpotifyDownloader"}

    async def client_ready(self, client, db):
        self._db = db
        self._client = client

    @loader.unrestricted
    async def sdcmd(self, message: Message) -> None:
        """<track> - search and download from Spotify"""
        args = utils.get_args_raw(message)
        if not args:
            return await utils.answer(message, "<b>No args.</b>")

        message = await utils.answer(message, "<b>Loading...</b>")
        try:
            message = message[0]
        except Exception:
            pass
        music = await self._client.inline_query("spotifysavebot", args)
        for mus in music:
            if mus.result.type == "audio":
                await self._client.send_file(
                    message.peer_id,
                    mus.result.document,
                    reply_to=message.reply_to_msg_id,
                )
                return await message.delete()

        return await utils.answer(
            message, f"<b> Music named <code> {args} </code> not found. </b>"
        )
