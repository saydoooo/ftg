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

# meta pic: https://img.icons8.com/fluency/48/000000/kermit-the-frog.png

# scope: inline
# scope: geektg_only

from .. import loader
from telethon.tl.types import Message
from aiogram.types import CallbackQuery
import logging

logger = logging.getLogger(__name__)


@loader.tds
class InlineTestMod(loader.Module):
    """Test module for inline buttons"""

    strings = {
        "name": "InlineTest",
        "poll": "📊 Poll <b>GeekTG vs. FTG</b>\n\n<b>🕶 GeekTG</b>: {}\n<b>😔 FTG</b>: {}",
    }

    def get(self, *args) -> dict:
        return self.db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self.db.set(self.strings["name"], *args)

    async def client_ready(self, client, db) -> None:
        self.db = db
        self.client = client
        self._geek = 0
        self._ftg = 0
        self._voted = []
        self._kb = [
            [{"text": "GeekTG", "callback": self.vote, "args": [False]}],
            [{"text": "FTG", "callback": self.vote, "args": [True]}],
        ]

    async def vote(self, call: CallbackQuery, option: str) -> None:
        if call.from_user.id in self._voted:
            await call.answer("You already participated in this poll!")
            return

        self._voted += [call.from_user.id]

        self._ftg += 1 if option else 0
        self._geek += 1 if not option else 0

        geek_prcnt = self._geek / (self._ftg + self._geek)
        ftg_prcnt = self._ftg / (self._ftg + self._geek)

        await call.edit(
            self.strings("poll").format(
                "#" * round(geek_prcnt * 10)
                + " "
                + str(round(geek_prcnt * 100))
                + f"% ({self._geek} vote(-s))",
                "#" * round(ftg_prcnt * 10)
                + " "
                + str(round(ftg_prcnt * 100))
                + f"% ({self._ftg} vote(-s))",
            ),
            reply_markup=self._kb,
            force_me=False,
        )

    async def inlinecmd(self, message: Message) -> None:
        await self.inline.form(
            self.strings("poll").format("No votes", "No votes"),
            message,
            self._kb,
        )
