"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    © Copyright 2022 t.me/hikariatama
    Licensed under CC BY-NC-ND 4.0

    🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
"""

# meta pic: https://img.icons8.com/fluency/48/000000/keep-away-from-children.png
# meta developer: @hikariatama
# scope: hikka_only
# requires: requests

from .. import loader, utils
import requests
import logging
from telethon.tl.types import Message
from typing import List
import functools
from telethon.utils import get_display_name

logger = logging.getLogger(__name__)


async def photos(subreddit: str) -> List[str]:
    ans = (
        await utils.run_sync(
            requests.get,
            "https://api.scrolller.com/api/v2/graphql",
            json={
                "query": " query SubredditQuery( $url: String! $filter: SubredditPostFilter $iterator: String ) { getSubreddit(url: $url) { children( limit: 10"
                " iterator: $iterator filter: $filter disabledHosts: null ) { iterator items { __typename url title subredditTitle subredditUrl redditPath isNsfw albumUrl isFavorite mediaSources { url width height isOptimized } } } } } ",
                "variables": {"url": subreddit, "filter": None, "hostsDown": None},
                "authorization": None,
            },
        )
    ).json()

    posts = ans["data"]["getSubreddit"]["children"]["items"]
    return [
        post["mediaSources"][0]["url"]
        for post in posts
    ]


@loader.tds
class NSFWMod(loader.Module):
    """Sends random NSFW Picture from scrolller.com"""

    strings = {
        "name": "NSFW",
        "sreddit404": "🦊 <b>Subreddit not found</b>",
        "default_subreddit": "🦊 <b>Set new default subreddit: </b><code>{}</code>",
        "loading": "🦊 <b>Loading...</b>",
    }

    async def client_ready(self, client, db):
        self._db = db
        self._client = client

    async def nsfwcmd(self, message: Message) -> None:
        """<subreddit | default> - Send NSFW gallery"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if reply:
            for_ = f"<b>❤️ Special for {utils.escape_html(get_display_name(reply.sender))}</b>"
        else:
            for_ = ""

        if not args:
            args = self._db.get("NSFW", "default_subreddit", "nsfw")

        subreddit = f"/r/{args}"

        ans = await utils.run_sync(requests.get, f"https://api.scrolller.com{subreddit}")
        if ans.status_code != 200:
            await utils.answer(message, self.strings("sreddit404", message))
            return

        await self.inline.gallery(
            message=message,
            next_handler=functools.partial(photos, subreddit=subreddit),
            caption=lambda: f"<i>Enjoy this {subreddit} photos &lt;3\n{utils.escape_html(utils.ascii_face())}</i>\n\n{for_}",
            always_allow=[reply.sender_id] if reply else [],
        )

    async def nsfwcatcmd(self, message: Message) -> None:
        """<subreddit> - Set new default subreddit"""
        args = utils.get_args_raw(message)
        if not args:
            args = "nsfw"

        ans = await utils.run_sync(requests.get, f"https://api.scrolller.com/r/{args}")
        if ans.status_code != 200:
            await utils.answer(message, self.strings("sreddit404", message))
            return

        self._db.set("NSFW", "default_subreddit", args)
        await utils.answer(
            message, self.strings("default_subreddit", message).format(args)
        )
