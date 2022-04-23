# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/fluency/50/000000/crowdfunding.png
# meta developer: @hikariatama
# scope: inline
# scope: hikka_only
# requires: websockets requests

from .. import loader, utils
from telethon.tl.types import Message
import logging
import websockets
import asyncio
import requests
import time
import json
from urllib.parse import quote_plus
import datetime
from aiogram.utils.exceptions import MessageNotModified
from ..inline.types import InlineCall

logger = logging.getLogger(__name__)


@loader.tds
class RealTimeValutesMod(loader.Module):
    """Track valutes in real time. Updates more than once a second"""

    strings = {
        "name": "RealTimeValutes",
        "loading": "😌 <b>Loading the most actual info from Forex...</b>",
        "wss_error": "🚫 <b>Socket connection error</b>",
        "exchanges": "😌 <b>Exchange rates by Forex</b>\n\n<b>💵 1 USD = {:.2f} RUB\n💶 1 EUR = {:.2f} RUB</b>\n\n<i>This info is relevant to <u>{:%m/%d/%Y %H:%M:%S}</u></i>",
    }

    async def _connect(self):
        r = await utils.run_sync(
            requests.get,
            f"https://rates-live.efxnow.com/signalr/negotiate?clientProtocol=2.1&connectionData=%5B%7B%22name%22%3A%22ratesstreamer%22%7D%5D&_={time.time() * 1000:.0f}",
        )

        token = quote_plus(r.json()["ConnectionToken"])
        base = f"wss://rates-live.efxnow.com/signalr/connect?transport=webSockets&clientProtocol=2.1&connectionToken={token}&connectionData=%5B%7B%22name%22%3A%22ratesstreamer%22%7D%5D&tid=8"

        async with websockets.connect(base) as wss:
            await wss.send(
                '{"H":"ratesstreamer","M":"SubscribeToPricesUpdates","A":[["401203106","401203109"]],"I":8}'
            )  # USD/RUB | EUR/RUB

            self._restart_at = time.time() + 5 * 60

            while time.time() < self._restart_at:
                rates = json.loads(await wss.recv())
                if "M" not in rates or not rates["M"]:
                    continue

                for row in rates["M"]:
                    if "A" not in row:
                        continue

                    rate = row["A"]
                    valute = rate[0].split("|")[1].split("/")[0]
                    rate = float(rate[0].split("|")[3])

                    self._rates[valute] = rate
                    self._upd_time = time.time()

            return await self._connect()

    async def client_ready(self, client, db):
        self._rates = {}
        self._upd_time = 0

        self._ratelimit = 0

        self._reload_markup = self.inline._generate_markup(
            {"text": "🔄 Update", "data": "update_exchanges"}
        )

        self._task = asyncio.ensure_future(self._connect())

    async def valcmd(self, message: Message):
        """Show exchange rates"""
        try:
            m = self.strings("exchanges").format(
                self._rates["USD"],
                self._rates["EUR"],
                getattr(datetime, "datetime", datetime).fromtimestamp(self._upd_time),
            )
        except (KeyError, IndexError):
            await utils.answer(message, self.strings("wss_error"))
            return

        try:
            await self.inline.form(
                m,
                message=message,
                reply_markup={"text": "🔄 Update", "data": "update_exchanges"},
                disable_security=True,
                silent=True,
            )
        except Exception:
            await utils.answer(message, m)

    @loader.inline_everyone
    async def reload_callback_handler(self, call: InlineCall):
        """Processes 'reload' button clicks"""
        if call.data != "update_exchanges":
            return

        if self._ratelimit and time.time() < self._ratelimit:
            await call.answer("Do not spam this button")
            return

        self._ratelimit = time.time() + 1

        try:
            await self.inline.bot.edit_message_text(
                inline_message_id=call.inline_message_id,
                text=self.strings("exchanges").format(
                    self._rates["USD"],
                    self._rates["EUR"],
                    getattr(datetime, "datetime", datetime).fromtimestamp(
                        self._upd_time
                    ),
                ),
                reply_markup=self._reload_markup,
                parse_mode="HTML",
            )

            await call.answer("😌 Exchange rates update complete!", show_alert=True)
        except (IndexError, KeyError):
            await call.answer("Socket connection error", show_alert=True)
            return
        except MessageNotModified:
            await call.answer(
                "Exchange rates have not changes since last update", show_alert=True
            )
            return

    async def on_unload(self):
        self._task.cancel()
