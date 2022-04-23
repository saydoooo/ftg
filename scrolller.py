# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://scrolller.com/assets/favicon-16x16.png
# meta developer: @hikariatama
# scope: hikka_only
# scope: hikka_min 1.0.11
# requires: requests

from .. import loader, utils
import requests
import logging
from telethon.tl.types import Message
from typing import List, Union
import functools
from telethon.utils import get_display_name
from ..inline.types import InlineQuery
import random

logger = logging.getLogger(__name__)


async def photos(subreddit: str, quantity: int) -> List[str]:
    """Loads `quantity` photos from `subreddit` on scrolller.com"""
    ans = (
        await utils.run_sync(
            requests.get,
            "https://api.scrolller.com/api/v2/graphql",
            json={
                "query": f" query SubredditQuery( $url: String! $filter: SubredditPostFilter $iterator: String ) {{ getSubreddit(url: $url) {{ children( limit: {quantity}"
                " iterator: $iterator filter: $filter disabledHosts: null ) { iterator items {url subredditTitle isNsfw mediaSources { url } } } } } ",
                "variables": {"url": subreddit, "filter": None, "hostsDown": None},
                "authorization": None,
            },
        )
    ).json()

    posts = ans["data"]["getSubreddit"]["children"]["items"]
    return [post["mediaSources"][0]["url"] for post in posts]


def caption(subreddit: dict) -> str:
    return f"{'🔞' if subreddit['isNsfw'] else '👨‍👩‍👧'} <b>{utils.escape_html(subreddit['secondaryTitle'])} ({utils.escape_html(subreddit['url'])})</b>\n\n<i>{utils.escape_html(subreddit['description'])}</i>\n\n<i>Enjoy! {utils.escape_html(utils.ascii_face())}</i>"


async def search_subreddit(query: str) -> List[dict]:
    """Searches for subreddits using `query`"""
    ans = (
        await utils.run_sync(
            requests.get,
            "https://api.scrolller.com/api/v2/graphql",
            json={
                "query": " query SearchQuery($query: String!, $isNsfw: Boolean) { searchSubreddits( query: $query isNsfw: $isNsfw limit: 500 ) { __typename url title secondaryTitle description createdAt isNsfw subscribers isComplete itemCount videoCount pictureCount albumCount isFollowing } } ",
                "variables": {"query": query, "isNsfw": None},
                "authorization": None,
            },
        )
    ).json()
    res = ans["data"]["searchSubreddits"]
    random.shuffle(res)
    return res[:30]


async def fetch_multiple_subreddits(subreddits: List[str]) -> Union[List[str], bool]:
    """Fetches preview from multiple `subreddits`"""
    args = [f"$url_{i}: String!" for i in range(len(subreddits))]
    vals = {f"url_{i}": subreddit for i, subreddit in enumerate(subreddits)}
    funcs = [
        subreddit.split("/")[-1]
        + """: getSubreddit(url: $url_"""
        + str(i)
        + """) {children(limit: 1 iterator: $iterator filter: $filter disabledHosts: null ) {iterator items {url subredditTitle isNsfw mediaSources { url } } } }"""
        for i, subreddit in enumerate(subreddits)
    ]

    r = (
        await utils.run_sync(
            requests.get,
            "https://api.scrolller.com/api/v2/graphql",
            json={
                "query": """query SubredditQuery ("""
                + "\n".join(args)
                + """$filter: SubredditPostFilter $iterator: String ) {"""
                + "\n".join(funcs)
                + """} """,
                "variables": {**vals, "filter": None, "hostsDown": None},
                "authorization": None,
            },
        )
    ).json()

    try:
        return [
            i["children"]["items"][0]["mediaSources"][0]["url"] for i in r["data"].values()
        ]
    except KeyError:
        return False


@loader.tds
class ScrolllerMod(loader.Module):
    """Sends pictures from scrolller.com via inline gallery"""

    strings = {
        "name": "Scrolller",
        "sreddit404": "🚫 <b>Subreddit not found</b>",
        "default_subreddit": "🙂 <b>Set new default subreddit: </b><code>{}</code>",
    }

    async def gallerycmd(self, message: Message):
        """<subreddit | default> - Send inline gallery with photos from subreddit"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()

        if reply:
            for_ = f"<b>❤️ Special for {utils.escape_html(get_display_name(reply.sender))}</b>"
        else:
            for_ = ""

        if not args:
            args = self.get("default_subreddit", "cat")

        subreddit = f"/r/{args}"

        ans = await utils.run_sync(
            requests.get, f"https://api.scrolller.com{subreddit}"
        )
        if ans.status_code != 200:
            await utils.answer(message, self.strings("sreddit404", message))
            return

        await self.inline.gallery(
            message=message,
            next_handler=functools.partial(photos, subreddit=subreddit, quantity=15),
            caption=lambda: f"<i>Enjoy this {subreddit} photos &lt;3\n{utils.escape_html(utils.ascii_face())}</i>\n\n{for_}",
            always_allow=[reply.sender_id] if reply else [],
        )

    async def gallerycatcmd(self, message: Message):
        """<subreddit> - Set new default subreddit"""
        args = utils.get_args_raw(message)
        if not args:
            args = "cat"

        ans = await utils.run_sync(requests.get, f"https://api.scrolller.com/r/{args}")
        if ans.status_code != 200:
            await utils.answer(message, self.strings("sreddit404", message))
            return

        self.set("default_subreddit", args)
        await utils.answer(
            message, self.strings("default_subreddit", message).format(args)
        )

    async def gallery_inline_handler(self, query: InlineQuery):
        """
        Search for Scrolller subreddits
        """
        if not query.args:
            query.args = self.get("default_subreddit", "cat")

        subreddits = await search_subreddit(query.args)
        thumbs = await fetch_multiple_subreddits([i["url"] for i in subreddits])

        if not thumbs or not subreddits:
            await query.e404()
            return

        await self.inline.query_gallery(
            query,
            [
                {
                    "title": f"{'🔞' if subreddit['isNsfw'] else '👨‍👩‍👧'} {subreddit['secondaryTitle']} ({subreddit['url']})",
                    "description": subreddit["description"],
                    "next_handler": functools.partial(
                        photos,
                        subreddit=subreddit["url"],
                        quantity=15,
                    ),
                    "thumb_handler": [thumbs[i]],
                    "caption": functools.partial(
                        caption,
                        subreddit=subreddit,
                    )
                }
                for i, subreddit in enumerate(subreddits)
            ],
        )
