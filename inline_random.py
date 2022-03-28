"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    © Copyright 2022 t.me/hikariatama
    Licensed under CC BY-NC-ND 4.0

    🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
"""

# meta pic: https://img.icons8.com/emoji/48/000000/shiffle-tracks-button-emoji.png
# meta developer: @hikariatama
# scope: inline
# scope: hikka_only

from .. import loader, utils
from aiogram.types import CallbackQuery
import logging
from ..inline.types import InlineQuery
from random import randint, choice
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent

logger = logging.getLogger(__name__)


@loader.tds
class InlineRandomMod(loader.Module):
    """Random tools for your userbot"""

    strings = {"name": "InlineRandom"}

    async def inline__close(self, call: CallbackQuery) -> None:
        await call.delete()

    async def coin_inline_handler(self, query: InlineQuery) -> None:
        """
        Heads or tails?
        @allow: all
        """

        r = "🦅 Heads" if randint(0, 1) else "🪙 Tails"
        await query.answer(
            [
                InlineQueryResultArticle(
                    id=utils.rand(20),
                    title="Toss a coin",
                    description="Trust in the God of luck, and he will be by your side!",
                    input_message_content=InputTextMessageContent(
                        f"<i>The God of luck tells us...</i> <b>{r}</b>",
                        "HTML",
                        disable_web_page_preview=True,
                    ),
                    thumb_url="https://img.icons8.com/external-justicon-flat-justicon/64/000000/external-coin-pirates-justicon-flat-justicon-1.png",
                    thumb_width=128,
                    thumb_height=128,
                )
            ],
            cache_time=0,
        )

    async def random_inline_handler(self, query: InlineQuery) -> None:
        """
        [number] - Send random number less than specified
        @allow: all
        """

        if not query.args:
            return

        a = query.args

        if not str(a).isdigit():
            return

        await query.answer(
            [
                InlineQueryResultArticle(
                    id=utils.rand(20),
                    title=f"Toss random number less or equal to {a}",
                    description="Trust in the God of luck, and he will be by your side!",
                    input_message_content=InputTextMessageContent(
                        f"<i>The God of luck screams...</i> <b>{randint(1, int(a))}</b>",
                        "HTML",
                        disable_web_page_preview=True,
                    ),
                    thumb_url="https://img.icons8.com/external-flaticons-flat-flat-icons/64/000000/external-numbers-auction-house-flaticons-flat-flat-icons.png",
                    thumb_width=128,
                    thumb_height=128,
                )
            ],
            cache_time=0,
        )

    async def choice_inline_handler(self, query: InlineQuery) -> None:
        """
        [args, separated by comma] - Make a choice
        @allow: all
        """

        if not query.args or not query.args.count(","):
            return

        a = query.args

        await query.answer(
            [
                InlineQueryResultArticle(
                    id=utils.rand(20),
                    title="Choose one item from list",
                    description="Trust in the God of luck, and he will be by your side!",
                    input_message_content=InputTextMessageContent(
                        f"<i>The God of luck whispers...</i> <b>{choice(a.split(',')).strip()}</b>",
                        "HTML",
                        disable_web_page_preview=True,
                    ),
                    thumb_url="https://img.icons8.com/external-filled-outline-geotatah/64/000000/external-choice-customer-satisfaction-filled-outline-filled-outline-geotatah.png",
                    thumb_width=128,
                    thumb_height=128,
                )
            ],
            cache_time=0,
        )
