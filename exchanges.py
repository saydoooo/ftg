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

# meta title: Exchanges
# meta pic: https://img.icons8.com/stickers/100/000000/candle-sticks.png
# meta desc: Forex scraper integrations to get current exchanges


from .. import loader, utils  # noqa
from telethon.tl.types import Message
import logging
from forex_python.converter import CurrencyRates  # noqa
import time
import datetime

# requires: forex-python

c = CurrencyRates()

logger = logging.getLogger(__name__)


@loader.tds
class ExchangesMod(loader.Module):
    """Forex scraper integrations to get current exchanges"""

    strings = {
        "name": "Exchanges",
        "loading": "😌 <b>Loading the most actual info from Forex...</b>",
        "exchanges": "😌 <b>Current exchange rates by Forex</b>\n\n<b>💵 1 USD = {:.2f} RUB\n💶 1 EUR = {:.2f} RUB\n💷 1 GBP = {:.2f} RUB</b>\n\n<i>Update: {:%m/%d/%Y %H:%M:%S}</i>",  # noqa
    }

    def get(self, *args) -> dict:
        return self.db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self.db.set(self.strings["name"], *args)

    async def client_ready(self, client, db) -> None:
        self.db = db
        self.client = client
        self._is_inline = hasattr(self, "inline") and self.inline.init_complete
        self._ratelimit = 0
        if self._is_inline:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton  # noqa

            self._reload_markup = InlineKeyboardMarkup()  # noqa
            self._reload_markup.add(
                InlineKeyboardButton(  # noqa
                    "🔄 Reload exchanges", callback_data="reload_exchanges"
                )
            )

    async def exchcmd(self, message: Message) -> None:
        """Load exchanges"""
        message = await utils.answer(message, self.strings("loading"))

        if isinstance(message, (tuple, list, set)):
            message = message[0]

        exch = c.get_rates("RUB")

        usd = 1 / exch["USD"]
        eur = 1 / exch["EUR"]
        gbp = 1 / exch["GBP"]

        m = self.strings("exchanges").format(
            usd, eur, gbp, getattr(datetime, "datetime", datetime).now()
        )

        if not self._is_inline:
            await utils.answer(message, m)
            return

        await self.inline.form(
            m,
            message=message,
            reply_markup=[[{"text": "🔄 Reload exchanges", "data": "reload_exchanges"}]],
        )

    async def reload_callback_handler(
        self, call: "aiogram.types.CallbackQuery"  # noqa: F821
    ):
        """
        Processes 'reload' button clicks
        @allow: all
        """
        if call.data != "reload_exchanges":
            return

        if self._ratelimit and time.time() < self._ratelimit:
            await call.answer("Do not spam this button")
            return

        self._ratelimit = time.time() + 10

        await call.answer("😌 Reloading exchanges, please, wait.")

        exch = c.get_rates("RUB")

        usd = 1 / exch["USD"]
        eur = 1 / exch["EUR"]
        gbp = 1 / exch["GBP"]

        await self.inline._bot.edit_message_text(
            inline_message_id=call.inline_message_id,
            text=self.strings("exchanges").format(
                usd, eur, gbp, getattr(datetime, "datetime", datetime).now()
            ),
            reply_markup=self._reload_markup,
            parse_mode="HTML",
        )
