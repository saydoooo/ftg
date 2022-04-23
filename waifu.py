# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://cdn-icons-png.flaticon.com/512/2405/2405001.png
# scope: inline
# scope: hikka_only
# meta developer: @hikariatama

from .. import loader, utils
from telethon.tl.types import Message
import logging
import requests
import functools

logger = logging.getLogger(__name__)

categories = ["waifu", "neko", "shinobu", "megumin", "cuddle", "cry", "hug", "awoo", "kiss", "lick", "pat", "smug", "bonk", "yeet", "blush", "smile", "wave", "highfive", "handhold", "nom", "bite", "glomp", "slap"]  # fmt: skip
nsfw_categories = ["waifu", "neko", "trap", "blowjob"]  # fmt: skip


async def photo(type_: str, category: str) -> list:
    if category in nsfw_categories and category not in categories:
        type_ = "nsfw"

    ans = (
        await utils.run_sync(
            requests.post,
            f"https://api.waifu.pics/many/{type_}/{category}",
            json={"exclude": []},
        )
    ).json()

    if "files" not in ans:
        logger.error(ans)
        return []

    return ans["files"]


@loader.tds
class WaifuMod(loader.Module):
    """Unleash best waifus of all time"""
    strings = {"name": "Waifu"}

    async def waifucmd(self, message: Message):
        """[nsfw] [category] - Send waifu"""
        category = (
            [
                category
                for category in categories + nsfw_categories
                if category in utils.get_args_raw(message)
            ]
            or [
                categories[0]
                if "nsfw" not in utils.get_args_raw(message)
                else nsfw_categories[0]
            ]
        )[0]

        await self.inline.gallery(
            message=message,
            next_handler=functools.partial(
                photo,
                type_=("nsfw" if "nsfw" in utils.get_args_raw(message) else "sfw"),
                category=category,
            ),
            caption=f"<b>{('🔞 NSFW' if 'nsfw' in utils.get_args_raw(message) else '👨‍👩‍👧 SFW')}</b>: <i>{category}</i>",
            preload=10,
        )

    async def waifuscmd(self, message: Message):
        """Show available categories"""
        await utils.answer(
            message,
            "\n".join(
                [
                    " | ".join(i)
                    for i in utils.chunks([f"<code>{i}</code>" for i in categories], 5)
                ]
            )
            + "\n<b>NSFW:</b>\n"
            + "\n".join(
                [
                    " | ".join(i)
                    for i in utils.chunks(
                        [f"<code>{i}</code>" for i in nsfw_categories], 5
                    )
                ]
            ),
        )
