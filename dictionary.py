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
# scope: hikka_min 1.0.21

from .. import loader, utils
from telethon.tl.types import Message
import logging
from urllib.parse import quote_plus
import aiohttp
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)
logging.getLogger("charset_normalizer").setLevel(logging.ERROR)

headers = {
    "accept": "text/html",
    "user-agent": "Hikka userbot",
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

        return [
            definition.get_text().replace("♠️", "\n")
            for definition in soup.find_all("div", class_="meaning")
        ]

    async def meancmd(self, message: Message):
        """<term> - Find definition of the word in urban dictionary"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("no_args"))
            return

        means = await self.scrape(args)

        if not means:
            await utils.answer(message, self.strings("err").format(args))
            return

        await self.inline.list(
            message=message,
            strings=[self.strings("meaning").format(args, mean) for mean in means],
        )
