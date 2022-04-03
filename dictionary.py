# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/external-flat-satawat-anukul/64/000000/external-dictionary-education-flat-flat-satawat-anukul-2.png
# meta developer: @hikariatama
# requires: aiohttp urllib bs4
# scope: inline
# scope: hikka_only

from .. import loader, utils  # noqa
from telethon.tl.types import Message  # noqa
import logging
from urllib.parse import quote_plus
import aiohttp
from bs4 import BeautifulSoup
from aiogram.types import CallbackQuery
import re

logger = logging.getLogger(__name__)
logging.getLogger("charset_normalizer").setLevel(logging.ERROR)

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-encoding": "gzip, deflate, br",
    "accept-language": "en-US,en;q=0.9,ru;q=0.8",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "referer": "https://www.urbandictionary.com/",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "sec-gpc": "1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
}


@loader.tds
class UrbanDictionaryMod(loader.Module):
    """Search for words meaning in urban dictionary"""

    strings = {
        "name": "UrbanDictionary",
        "no_args": "🚫 <b>Specify term to find the definition for</b>",
        "err": "🧞‍♂️ <b>I don't know about term </b><code>{}</code>",
        "no_page": "🚫 Can't switch to that page",
        "meaning": "🧞‍♂️ <b><u>{}</u></b>:\n\n<i>{}</i>",
    }

    async def client_ready(self, client, db) -> None:
        self._memory = {}

    async def scrape(self, term: str) -> str:
        term = "".join(
            [
                i.lower()
                for i in term
                if i.lower()
                in "абвгдежзийклмнопрстуфхцчшщъыьэюяabcdefghijklmnopqrstuvwxyz "
            ]
        )
        endpoint = "https://www.urbandictionary.com/define.php?term={}"
        url = endpoint.format(quote_plus(term.lower()))
        async with aiohttp.ClientSession() as session:
            async with session.request("GET", url, headers=headers) as resp:
                html = await resp.text()

        soup = BeautifulSoup(re.sub(r"<br.*?>", "♠️", html), "html.parser")

        self._memory[term] = [
            definition.get_text().replace("♠️", "\n")
            for definition in soup.find_all("div", class_="meaning")
        ]

        if not self._memory[term]:
            del self._memory[term]
            return False

        return term

    async def inline__close(self, call: CallbackQuery, mean: str) -> None:
        await call.delete()
        del self._memory[mean]

    async def inline__page(self, call: CallbackQuery, mean: str, page: int) -> None:
        if page < 0 or page >= len(self._memory[mean]):
            await call.answer(self.strings("no_page"), show_alert=True)
            return

        next_ = min(page + 1, len(self._memory[mean]))

        await call.edit(
            self.strings("meaning").format(
                mean, utils.escape_html(self._memory[mean][page])
            ),
            reply_markup=[
                [
                    *(
                        [
                            {
                                "text": f"👈 Previous [{page - 1}]",
                                "callback": self.inline__page,
                                "args": (
                                    mean,
                                    page - 1,
                                ),
                            }
                        ]
                        if page >= 1
                        else []
                    ),
                    *(
                        [
                            {
                                "text": f"[{next_}] Next 👉",
                                "callback": self.inline__page,
                                "args": (
                                    mean,
                                    page + 1,
                                ),
                            }
                        ]
                        if page + 1 < len(self._memory[mean])
                        else []
                    ),
                ],
                [
                    {
                        "text": "😌 Close",
                        "callback": self.inline__close,
                        "args": (mean,),
                    }
                ],
            ],
        )

    async def meancmd(self, message: Message) -> None:
        """<term> - Find definition of the word in urban dictionary"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_args"))
            return

        mean = await self.scrape(args)

        if not mean:
            await utils.answer(message, self.strings("err").format(args))
            return

        await self.inline.form(
            self.strings("meaning").format(
                mean, utils.escape_html(self._memory[mean][0])
            ),
            message=message,
            reply_markup=[
                [
                    *(
                        [
                            {
                                "text": "[1] Next 👉",
                                "callback": self.inline__page,
                                "args": (
                                    mean,
                                    1,
                                ),
                            }
                        ]
                        if len(self._memory[mean]) > 1
                        else []
                    )
                ],
                [
                    {
                        "text": "😌 Close",
                        "callback": self.inline__close,
                        "args": (mean,),
                    }
                ],
            ],
            ttl=15 * 60,
        )
