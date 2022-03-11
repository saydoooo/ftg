__version__ = (8, 0, 8)
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

# meta title: HikariChat
# meta pic: https://emojipedia-us.s3.dualstack.us-west-1.amazonaws.com/thumbs/240/google/313/foggy_1f301.png
# meta desc: Chat administrator toolkit with everything you need and much more

# scope: disable_onload_docs

import re
import io
import abc
import time
import json
import imghdr
import logging
import asyncio
import aiohttp
import telethon
import functools
import traceback
from telethon.tl.types import *
from types import FunctionType
from typing import Union
from .. import loader, utils, main
from telethon.tl.types import User
from telethon.errors import UserAdminInvalidError
from telethon.tl.functions.channels import EditBannedRequest

logger = logging.getLogger(__name__)

version = f"v{__version__[0]}.{__version__[1]}.{__version__[2]}beta"
ver = f"<u>HikariChat {version}</u>"

FLOOD_TIMEOUT = 0.8
FLOOD_TRESHOLD = 3
API_UPDATE_DELAY = 20


def get_link(user: User or Channel) -> str:
    """Get link to object (User or Channel)"""
    return (
        f"tg://user?id={user.id}"
        if isinstance(user, User)
        else (
            f"tg://resolve?domain={user.username}"
            if getattr(user, "username", None)
            else ""
        )
    )


def get_first_name(user: User or Channel) -> str:
    """Returns first name of user or channel title"""
    return user.first_name if isinstance(user, User) else user.title


def get_full_name(user: User or Channel) -> str:
    return (
        user.title
        if isinstance(user, Channel)
        else (
            user.first_name
            + " "
            + (user.last_name if getattr(user, "last_name", False) else "")
        )
    )


async def get_message_link(message: Message, chat: Chat or Channel = None) -> str:
    if not chat:
        chat = await message.get_chat()

    return (
        f"https://t.me/{chat.username}/{message.id}"
        if getattr(chat, "username", False)
        else f"https://t.me/c/{chat.id}/{message.id}"
    )


BANNED_RIGHTS = {
    "view_messages": False,
    "send_messages": False,
    "send_media": False,
    "send_stickers": False,
    "send_gifs": False,
    "send_games": False,
    "send_inline": False,
    "send_polls": False,
    "change_info": False,
    "invite_users": False,
}


class HikariAPI:
    def __init__(self):
        pass

    async def init(
        self,
        client: "telethon.client.telegramclient.TelegramClient",
        db: "friendly-telegram.database.frontend.Database",
        module: "friendly-telegram.modules.python.PythonMod",
    ) -> None:
        """Entry point"""
        self.client = client
        self.db = db
        self.token = db.get("HikariChat", "apitoken", False)
        self.module = module

        await self.assert_token()

        token_valid = await self.validate_token()
        if not token_valid:
            # This message is sent just to let user know, that module will not work either
            # No need to remove this lines, they are not affecting the workflow of module
            await self.client.send_message(
                "@userbot_notifies_bot",
                utils.escape_html(
                    f"<b>You are using an unregistered copy of HikariChat. Please, consider removing it with </b><code>{self.module.prefix}unloadmod HikariChat</code><b>, otherwise you will see flood messages</b>"
                ),
            )
            self.token = False

    async def assert_token(self) -> None:
        if not self.token:
            async with self.client.conversation("@innoapi_auth_" + "bot") as conv:
                m = await conv.send_message("@get+innochat+token")
                res = await conv.get_response()
                await conv.mark_read()
                self.token = res.raw_text
                await m.delete()
                await res.delete()
                self.db.set("HikariChat", "apitoken", self.token)

    async def validate_token(self) -> None:
        if not self.token:
            return False

        answ = await self.get("ping")
        if not answ["success"]:
            return False

        return True

    async def request(self, method, *args, **kwargs) -> dict:
        if not self.token:
            return {"success": False}
        kwargs["headers"] = {
            "Authorization": f"Bearer {self.token}",
        }
        args = (f"https://api.hikariatama.ru/{args[0]}",)

        if "data" in kwargs and "file" not in kwargs["data"]:
            for key, value in kwargs["data"].copy().items():
                kwargs["data"][key] = str(value)

        if "data" in kwargs:
            data = kwargs["data"] if "file" not in kwargs["data"] else "<file>"
        else:
            data = "{}"

        logger.debug(f" >> [HikariApi] [{method}] {args[0]} : {data}")

        async with aiohttp.ClientSession() as session:
            async with session.request(method, *args, **kwargs) as resp:
                r = await resp.text()

                try:
                    r = json.loads(r)
                except Exception:
                    await self.report_error(r)
                    return {"success": False}

                if "error" in r and "Rate limit" in r["error"]:
                    await self.report_error(
                        f"Ratelimit exceeded: [{method}] {args[0]} : {data}"
                    )
                    return {"success": False, "error": r}

                if "success" not in r:
                    await self.report_error(json.dumps(r, indent=4))
                    return {"success": False, "error": r}

                return r

    @asyncio.coroutine
    async def get(self, *args, **kwargs) -> dict:
        return await self.request("GET", *args, **kwargs)

    @asyncio.coroutine
    async def post(self, *args, **kwargs) -> dict:
        return await self.request("POST", *args, **kwargs)

    @asyncio.coroutine
    async def delete(self, *args, **kwargs) -> dict:
        return await self.request("DELETE", *args, **kwargs)

    @asyncio.coroutine
    async def report_error(self, error: str) -> dict:
        error = str(error)
        error = re.sub(r"^.*File .*in wrapped.*$", "", error)
        async with aiohttp.ClientSession() as session:
            async with session.request(
                "POST",
                "https://api.hikariatama.ru/report_error",
                data={"error": error[:2048]},
                headers={"Authorization": f"Bearer {self.token}"},
            ):
                return


api = HikariAPI()


class HikariChatMod(loader.Module):
    """
Advanced chat admin toolkit

Author @hikariatama
"""

    __metaclass__ = abc.ABCMeta

    strings = {
        "name": "HikariChat",
        "args": "🦊 <b>Args are incorrect</b>",
        "no_reason": "Not specified",
        "antitagall_on": "🐵 <b>AntiTagAll is now on in this chat\nAction: {}</b>",
        "antitagall_off": "🐵 <b>AntiTagAll is now off in this chat</b>",
        "antiarab_on": "🐻 <b>AntiArab is now on in this chat\nAction: {}</b>",
        "antiarab_off": "🐻 <b>AntiArab is now off in this chat</b>",
        "antizalgo_on": "🌀 <b>AntiZALGO is now on in this chat\nAction: {}</b>",
        "antizalgo_off": "🌀 <b>AntiZALGO is now off in this chat</b>",
        "antistick_on": "🎨 <b>AntiStick is now on in this chat\nAction: {}</b>",
        "antistick_off": "🎨 <b>AntiStick is now off in this chat</b>",
        "antihelp_on": "🐺 <b>Anti Help On</b>",
        "antihelp_off": "🐺 <b>Anti Help Off</b>",
        "antiraid_on": "🐶 <b>AntiRaid is now on in this chat\nAction: {}</b>",
        "antiraid_off": "🐶 <b>AntiRaid is now off in this chat</b>",
        "antiraid": '🐶 <b>AntiRaid is On. I {} <a href="{}">{}</a> in chat {}</b>',
        "antichannel_on": "📯 <b>AntiChannel is now on in this chat</b>",
        "antichannel_off": "📯 <b>AntiChannel is now off in this chat</b>",
        "report_on": "📣 <b>Report is now on in this chat</b>",
        "report_off": "📣 <b>Report is now off in this chat</b>",
        "antiflood_on": "⏱ <b>AntiFlood is now on in this chat\nAction: {}</b>",
        "antiflood_off": "⏱ <b>AntiFlood is now off in this chat</b>",
        "antispoiler_on": "🪙 <b>AntiSpoiler is now on in this chat</b>",
        "antispoiler_off": "🪙 <b>AntiSpoiler is now off in this chat</b>",
        "antigif_on": "🎑 <b>AntiGIF is now on in this chat</b>",
        "antigif_off": "🎑 <b>AntiGIF is now off in this chat</b>",
        "antiservice_on": "⚙️ <b>AntiService is now on in this chat</b>",
        "antiservice_off": "⚙️ <b>AntiService is now off in this chat</b>",
        "antiexplicit_on": "😒 <b>AntiExplicit is now on in this chat\nAction: {}</b>",
        "antiexplicit_off": "😒 <b>AntiExplicit is now off in this chat</b>",
        "antinsfw_on": "🍓 <b>AntiNSFW is now on in this chat\nAction: {}</b>",
        "antinsfw_off": "🍓 <b>AntiNSFW is now off in this chat</b>",
        "arabic_nickname": '🐻 <b>Seems like <a href="{}">{}</a> is Arab.\n👊 Action: I {}</b>',
        "zalgo": '🌀 <b>Seems like <a href="{}">{}</a> has ZALGO in his nickname.\n👊 Action: I {}</b>',
        "stick": '🎨 <b>Seems like <a href="{}">{}</a> is flooding stickers.\n👊 Action: I {}</b>',
        "explicit": '😒 <b>Seems like <a href="{}">{}</a> sent explicit content.\n👊 Action: I {}</b>',
        "nsfw_content": '🍓 <b>Seems like <a href="{}">{}</a> sent NSFW content.\n👊 Action: I {}</b>',
        "flood": '⏱ <b>Seems like <a href="{}">{}</a> is flooding.\n👊 Action: I {}</b>',
        "tagall": '🐵 <b>Seems like <a href="{}">{}</a> used TagAll.\n👊 Action: I {}</b>',
        "sex_datings": '🔞 <b><a href="{}">{}</a> is suspicious 🧐\n👊 Action: I {}</b>',
        "fwarn": '👮‍♂️💼 <b><a href="{}">{}</a></b> got {}/{} federative warn\nReason: <b>{}</b>',
        "no_fed_warns": "👮‍♂️ <b>This federation has no warns yet</b>",
        "no_warns": '👮‍♂️ <b><a href="{}">{}</a> has no warns yet</b>',
        "warns": '👮‍♂️ <b><a href="{}">{}</a> has {}/{} warns</b>\n<i>{}</i>',
        "warns_adm_fed": "👮‍♂️ <b>Warns in this federation</b>:\n",
        "dwarn_fed": '👮‍♂️ <b>Forgave last federative warn from <a href="tg://user?id={}">{}</a></b>',
        "clrwarns_fed": '👮‍♂️ <b>Forgave all federative warns from <a href="tg://user?id={}">{}</a></b>',
        "warns_limit": '👮‍♂️ <b><a href="{}">{}</a> reached warns limit.\nAction: I {}</b>',
        "welcome": "👋 <b>Now I will greet people in this chat</b>\n{}",
        "unwelcome": "👋 <b>Not I will not greet people in this chat</b>",
        "chat404": "🔓 <b>I am not protecting this chat yet.</b>\n",
        "protections": """<b>🐻 <code>.AntiArab</code> - Bans spammy arabs
<b>🐺 <code>.AntiHelp</code> - Removes frequent userbot commands
<b>🐵 <code>.AntiTagAll</code> - Restricts tagging all members
<b>👋 <code>.Welcome</code> - Greets new members
<b>🐶 <code>.AntiRaid</code> - Bans all new members
<b>📯 <code>.AntiChannel</code> - Restricts writing on behalf of channels
<b>🪙 <code>.AntiSpoiler</code> - Restricts spoilers
<b>🎑 <code>.AntiGIF</code> - Restricts GIFs
<b>🍓 <code>.AntiNSFW</code> - Restricts NSFW photos and stickers
<b>⏱ <code>.AntiFlood</code> - Prevents flooding
<b>😒 <code>.AntiExplicit</code> - Restricts explicit content
<b>⚙️ <code>.AntiService</code> - Removes service messages
<b>👾 Admin: </b><code>.ban</code> <code>.kick</code> <code>.mute</code>
<code>.unban</code> <code>.unmute</code> <b>- Admin tools</b>
<b>👮‍♂️ Warns:</b> <code>.warn</code> <code>.warns</code>
<code>.dwarn</code> <code>.clrwarns</code> <b>- Warning system</b>
<b>💼 Federations:</b> <code>.fadd</code> <code>.frm</code> <code>.newfed</code>
<code>.namefed</code> <code>.fban</code> <code>.rmfed</code> <code>.feds</code>
<code>.fpromote</code> <code>.fdemote</code>
<code>.fdef</code> <code>.fdeflist</code> <b>- Controlling multiple chats</b>
<b>🗒 Notes:</b> <code>.fsave</code> <code>.fstop</code> <code>.fnotes</code> <b>- Federative notes</b>""",
        "not_admin": "🤷‍♂️ <b>I'm not admin here, or don't have enough rights</b>",
        "mute": '🔇 <b><a href="{}">{}</a> muted {}. Reason: {}</b>',
        "ban": '🔒 <b><a href="{}">{}</a> banned {}. Reason: {}</b>',
        "kick": '🚪 <b><a href="{}">{}</a> kicked. Reason: {}</b>',
        "unmuted": '🔊 <b><a href="{}">{}</a> unmuted</b>',
        "unban": '🧙‍♂️ <b><a href="{}">{}</a> unbanned</b>',
        "defense": '🛡 <b>Shield for <a href="{}">{}</a> is now {}</b>',
        "no_defense": "🛡 <b>Federative defense list is empty</b>",
        "defense_list": "🛡 <b>Federative defense list:</b>\n{}",
        "fadded": '💼 <b>Current chat added to federation "{}"</b>',
        "newfed": '💼 <b>Created federation "{}"</b>',
        "rmfed": '💼 <b>Removed federation "{}"</b>',
        "fed404": "💼 <b>Federation not found</b>",
        "frem": '💼 <b>Current chat removed from federation "{}"</b>',
        "f404": '💼 <b>Current chat is not in federation "{}"</b>',
        "fexists": '💼 <b>Current chat is already in federation "{}"</b>',
        "fedexists": "💼 <b>Federation exists</b>",
        "joinfed": "💼 <b>Federation joined</b>",
        "namedfed": "💼 <b>Federation renamed to {}</b>",
        "nofed": "💼 <b>Current chat is not in any federation</b>",
        "fban": '💼 <b><a href="{}">{}</a> banned in federation {}\nReason: {}</b>',
        "fmute": '💼 <b><a href="{}">{}</a> muted in federation {}\nReason: {}</b>',
        "funban": '💼 <b><a href="{}">{}</a> unbanned in federation {}</b>',
        "funmute": '💼 <b><a href="{}">{}</a> unmuted in federation {}</b>',
        "feds_header": "💼 <b>Federations:</b>\n\n",
        "fed": """
💼 <b>Federation "{}" info:</b>
🔰 <b>Chats:</b>
<b>{}</b>
🔰 <b>Admins:</b>
<b>{}</b>
🔰 <b>Warns: {}</b>""",
        "no_fed": "💼 <b>This chat is not in any federation</b>",
        "fpromoted": '💼 <b><a href="{}">{}</a> promoted in federation {}</b>',
        "fdemoted": '💼 <b><a href="{}">{}</a> demoted in federation {}</b>',
        "api_error": "🚫 <b>api.hikariatama.ru Error!</b>\n<code>{}</code>",
        "fsave_args": "💼 <b>Usage: .fsave shortname &lt;reply&gt;</b>",
        "fstop_args": "💼 <b>Usage: .fstop shortname</b>",
        "fsave": "💼 <b>Federative note </b><code>{}</code><b> saved!</b>",
        "fstop": "💼 <b>Federative note </b><code>{}</code><b> removed!</b>",
        "fnotes": "💼 <b>Federative notes:</b>\n{}",
        "usage": "ℹ️ <b>Usage: .{} &lt;on/off&gt;</b>",
        "chat_only": "ℹ️ <b>This command is for chats only</b>",
        "version": """<b>📡 {}</b>

<b>😌 Author: @hikariatama</b>
<b>📥 Downloaded from @hikarimods</b>

<b>Licensed under Apache2.0 license
Distribution without author's personal permission is forbidden
Breaking this license you are getting fban in all GeekNet chats and channels</b>""",
        "error": "⛎ <b>HikariChat Issued error\nIt was reported to @hikariatama</b>",
        "reported": '💼 <b><a href="{}">{}</a> reported this message to admins\nReason: {}</b>',
        "no_federations": "💼 <b>You have no active federations</b>",
        "clrallwarns_fed": "👮‍♂️ <b>Forgave all federative warns from federation</b>",
        "cleaning": "🧹 <b>Looking for Deleted accounts...</b>",
        "deleted": "🧹 <b>Removed {} Deleted accounts</b>",
        "fcleaning": "🧹 <b>Looking for Deleted accounts in federation...</b>",
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            "silent", False, lambda: "Do not notify about protections actions"
        )
        self.__doc__ = f"""
Advanced chat admin toolkit
Author @hikariatama
Version: {version}"""

    async def client_ready(
        self,
        client: "telethon.client.telegramclient.TelegramClient",
        db: "friendly-telegram.database.frontend.Database",
    ) -> None:
        """Entry point"""
        global api

        def get_commands(mod) -> dict:
            return {
                method_name[:-3]: getattr(mod, method_name)
                for method_name in dir(mod)
                if callable(getattr(mod, method_name)) and method_name[-3:] == "cmd"
            }

        self.db = db
        self.client = client

        self.ratelimit = {"notes": {}, "report": {}}
        self._me = (await client.get_me()).id

        self.last_feds_update = 0
        self.last_chats_update = 0
        self.chats_update_delay = API_UPDATE_DELAY
        self.feds_update_delay = API_UPDATE_DELAY

        self.flood_timeout = FLOOD_TIMEOUT
        self.flood_threshold = FLOOD_TRESHOLD

        self.chats = {}
        self.my_protects = {}
        self.federations = {}
        self._sticks_ratelimit = {}
        self._sticks_limit = 7
        self.prefix = utils.escape_html(
            (db.get(main.__name__, "command_prefix", False) or ".")[0]
        )

        self.api = api
        await api.init(client, db, self)

        try:
            self.variables = (await self.api.get("variables"))["variables"]
        except Exception:
            pass

        try:
            self.flood_cache = json.loads(open("flood_cache.json", "r").read())
        except Exception:
            self.flood_cache = {}

        await self.update_feds()

        commands = get_commands(self)
        for protection in self.variables["protections"]:
            commands[protection] = self.protection_template(protection)

        self.commands = commands

    def save_flood_cache(self) -> None:
        open("flood_cache.json", "w").write(json.dumps(self.flood_cache))

    def chat_command(func) -> FunctionType:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            if len(args) < 2 or not isinstance(args[1], Message):
                return await func(*args, **kwargs)

            if args[1].is_private:
                await utils.answer(args[1], args[0].strings("chat_only"))
                return

            return await func(*args, **kwargs)

        wrapped.__doc__ = func.__doc__
        wrapped.__module__ = func.__module__

        return wrapped

    def error_handler(func) -> FunctionType:
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception:
                if func.__name__.startswith("p__"):
                    logger.exception("Exception caught in HikariChat")
                    return

                await api.report_error(traceback.format_exc())
                if func.__name__ == "watcher":
                    return

                try:
                    await utils.answer(args[1], args[0].strings("error"))
                except Exception:
                    pass

        wrapped.__doc__ = func.__doc__
        wrapped.__module__ = func.__module__

        return wrapped

    @error_handler
    async def update_chats(self):
        if time.time() - self.last_chats_update < self.chats_update_delay:
            return

        self.last_chats_update = time.time()

        answ = await self.api.get("chats")

        if not answ["success"]:
            return

        self.chats = answ["chats"]
        self.my_protects = answ["my_protects"]

    @error_handler
    async def update_feds(self):
        if time.time() - self.last_feds_update < self.feds_update_delay:
            return

        self.last_feds_update = time.time()

        answ = await self.api.get("federations")

        if answ["success"]:
            self.federations = answ["feds"]

    @error_handler
    async def protect(self, message: Message, protection: str) -> None:
        args = utils.get_args_raw(message)
        chat = utils.get_chat_id(message)
        if protection in self.variables["argumented_protects"]:
            if args not in self.variables["protect_actions"]:
                args = "off"
                await utils.answer(message, self.strings(f"{protection}_off"))
            else:
                await utils.answer(
                    message, self.strings(f"{protection}_on").format(args)
                )

            answ = await self.api.post(
                f"chats/{chat}/protects/{protection}",
                data={"info": args, "state": "null"},
            )
        else:
            if args == "on":
                await utils.answer(message, self.strings(f"{protection}_on"))
            elif args == "off":
                await utils.answer(
                    message, self.strings(f"{protection}_off").format(args)
                )
            else:
                await utils.answer(message, self.strings("usage").format(protection))
                return

            answ = await self.api.post(
                f"chats/{chat}/protects/{protection}",
                data={"state": args, "info": "null"},
            )

        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

    def protection_template(self, protection: str) -> FunctionType:
        comments = self.variables["named_protects"]
        func_name = f"{protection}cmd"
        func = functools.partial(self.protect, protection=protection)
        func.__module__ = self.__module__
        func.__name__ = func_name
        func.__self__ = self
        func.__doc__ = f"<action> - Toggle {comments[protection]}"
        setattr(func, self.__module__ + "." + func.__name__, loader.support)
        return func

    @staticmethod
    def convert_time(t: str) -> int:
        try:
            if not str(t)[:-1].isdigit():
                return 0

            if "d" in str(t):
                t = int(t[:-1]) * 60 * 60 * 24
            if "h" in str(t):
                t = int(t[:-1]) * 60 * 60
            if "m" in str(t):
                t = int(t[:-1]) * 60
            if "s" in str(t):
                t = int(t[:-1])

            t = int(re.sub(r"[^0-9]", "", str(t)))
        except ValueError:
            return 0

        return t

    async def ban(
        self, chat: Chat or int, user: User or Channel or int, period: int = 0
    ) -> None:
        """Ban user in chat"""
        if str(user).isdigit():
            user = int(user)

        await self.client.edit_permissions(
            chat,
            user,
            until_date=(time.time() + period) if period else 0,
            **BANNED_RIGHTS,
        )

    async def mute(
        self, chat: Chat or int, user: User or Channel or int, period: int = 0
    ) -> None:
        """Mute user in chat"""
        if str(user).isdigit():
            user = int(user)

        await self.client.edit_permissions(
            chat, user, until_date=time.time() + period, send_messages=False
        )

    async def args_parser(self, message: Message) -> tuple:
        """Get args from message"""
        args = utils.get_args_raw(message)
        if "-s" in args:
            args = args.replace("-s", "").replace("  ", " ")
            silent = True
        else:
            silent = False
        reply = await message.get_reply_message()

        try:
            a = args.split()[0]
            if str(a).isdigit():
                a = int(a)
            user = (
                (await self.client.get_entity(reply.sender_id))
                if reply
                else (await self.client.get_entity(a))
            )
        except Exception:
            return False

        t = ([_ for _ in args.split() if self.convert_time(_)] or ["0"])[0]
        args = args.replace(t, "").replace("  ", " ")
        t = self.convert_time(t)

        if not reply:
            try:
                args = " ".join(args.split(" ")[1:])
            except Exception:
                pass

        if time.time() + t >= 2147483647:
            t = 0

        return user, t, (args or self.strings("no_reason")), silent

    def find_fed(self, message: Message) -> None or str:
        """Find if chat belongs to any federation"""
        for federation, info in self.federations.items():
            if str(utils.get_chat_id(message)) in list(map(str, info["chats"])):
                return federation

        return None

    @error_handler
    async def punish(
        self,
        chat_id: int,
        user: int or Channel or User,
        violation: str,
        action: str,
        user_name: str,
    ) -> None:
        if action == "ban":
            comment = "banned him for 1 hour"
            await self.ban(chat_id, user, 60**2)
        elif action == "delmsg":
            return
        elif action == "kick":
            comment = "kicked him"
            await self.client.kick_participant(chat_id, user)
        elif action == "mute":
            comment = "muted him for 1 hour"
            await self.mute(chat_id, user, 60 * 60)
        elif action == "warn":
            comment = "warned him"
            warn_msg = await self.client.send_message(
                chat_id, f".warn {user.id} {violation}"
            )
            await self.allmodules.commands["warn"](warn_msg)
            await warn_msg.delete()
        else:
            comment = "just chill 😶‍🌫️"

        if not self.config["silent"]:
            await self.client.send_message(
                chat_id,
                self.strings(violation).format(get_link(user), user_name, comment),
            )

    @error_handler
    async def versioncmd(self, message: Message) -> None:
        """Get module info"""
        await utils.answer(message, self.strings("version").format(ver))

    @error_handler
    @chat_command
    async def deletedcmd(self, message: Message) -> None:
        """Remove deleted accounts from chat"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        kicked = 0

        message = await utils.answer(message, self.strings("cleaning"))
        if not isinstance(message, Message):
            message = message[0]

        async for user in self.client.iter_participants(chat):
            if user.deleted:
                try:
                    await self.client.kick_participant(chat, user)
                    await self.client.edit_permissions(
                        chat,
                        user,
                        until_date=0,
                        **{right: True for right in BANNED_RIGHTS.keys()},
                    )
                    kicked += 1
                except Exception:
                    pass

        await utils.answer(message, self.strings("deleted").format(kicked))

    @error_handler
    @chat_command
    async def fcleancmd(self, message: Message) -> None:
        """Remove deleted accounts from federation"""
        chat_id = utils.get_chat_id(message)
        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        answ = await self.api.get(f'federations/{self.federations[fed]["uid"]}/chats')

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        chats = answ["chats"]

        cleaned_in = []

        message = await utils.answer(message, self.strings("fcleaning"))
        if not isinstance(message, Message):
            message = message[0]

        overall = 0

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self.client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                kicked = 0
                async for user in self.client.iter_participants(chat):
                    if user.deleted:
                        try:
                            await self.client.kick_participant(chat, user)
                            await self.client.edit_permissions(
                                chat,
                                user,
                                until_date=0,
                                **{right: True for right in BANNED_RIGHTS.keys()},
                            )
                            kicked += 1
                        except Exception:
                            pass

                overall += kicked

                cleaned_in += [str(chat.title) + " - " + str(kicked)]
            except UserAdminInvalidError:
                pass

        await utils.answer(
            message,
            self.strings("deleted").format(overall)
            + "\n\n<b>"
            + "\n".join(cleaned_in)
            + "</b>",
        )

    @error_handler
    @chat_command
    async def newfedcmd(self, message: Message) -> None:
        """<shortname> <name> - Create new federation"""
        args = utils.get_args_raw(message)
        if not args or args.count(" ") == 0:
            await utils.answer(message, self.strings("args"))
            return

        shortname, name = args.split(maxsplit=1)
        if shortname in self.federations:
            await utils.answer(message, self.strings("fedexists"))
            return

        answ = await self.api.post(
            "federations", data={"shortname": shortname, "name": name}
        )

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        await utils.answer(message, self.strings("newfed").format(name))

    @error_handler
    @chat_command
    async def rmfedcmd(self, message: Message) -> None:
        """<shortname> - Remove federation"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("args"))
            return

        if args not in self.federations:
            await utils.answer(message, self.strings("fed404"))
            return

        name = self.federations[args]["name"]

        answ = await self.api.delete(f'federations/{self.federations[args]["uid"]}')

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        await utils.answer(message, self.strings("rmfed").format(name))

    @error_handler
    @chat_command
    async def fpromotecmd(self, message: Message) -> None:
        """<reply|user> - Promote user in federation"""
        chat_id = utils.get_chat_id(message)
        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        if not reply and not args:
            await utils.answer(message, self.strings("args"))
            return

        user = reply.sender_id if reply else args
        try:
            try:
                if str(user).isdigit():
                    user = int(user)
                obj = await self.client.get_entity(user)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

            name = get_full_name(obj)
        except Exception:
            await utils.answer(message, self.strings("args"))
            return

        answ = await self.api.post(
            f'federations/{self.federations[fed]["uid"]}/promote', data={"user": obj.id}
        )

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        await utils.answer(
            message,
            self.strings("fpromoted").format(
                get_link(obj), name, self.federations[fed]["name"]
            ),
        )

    @error_handler
    @chat_command
    async def fdemotecmd(self, message: Message) -> None:
        """<shortname> <reply|user> - Demote user in federation"""
        chat_id = utils.get_chat_id(message)
        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        if not reply and not args:
            await utils.answer(message, self.strings("args"))
            return

        user = reply.sender_id if reply else args
        try:
            try:
                if str(user).isdigit():
                    user = int(user)
                obj = await self.client.get_entity(user)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

            user = obj.id

            name = get_full_name(user)
        except Exception:
            name = "User"

        answ = await self.api.post(
            f'federations/{self.federations[fed]["uid"]}/demote', data={"user": user}
        )

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        await utils.answer(
            message,
            self.strings("fdemoted").format(user, name, self.federations[fed]["name"]),
        )

    @error_handler
    @chat_command
    async def faddcmd(self, message: Message) -> None:
        """<fed name> - Add chat to federation"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("args"))
            return

        if args not in self.federations:
            await utils.answer(message, self.strings("fed404"))
            return

        chat = utils.get_chat_id(message)

        answ = await self.api.post(
            f'federations/{self.federations[args]["uid"]}/chats', data={"cid": chat}
        )

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        await utils.answer(
            message, self.strings("fadded").format(self.federations[args]["name"])
        )

    @error_handler
    @chat_command
    async def frmcmd(self, message: Message) -> None:
        """Remove chat from federation"""
        fed = self.find_fed(message)
        if not fed:
            await utils.answer(message, self.strings("fed404"))
            return

        chat = utils.get_chat_id(message)

        answ = await self.api.delete(
            f'federations/{self.federations[fed]["uid"]}/chats/{chat}'
        )

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        await utils.answer(
            message, self.strings("frem").format(self.federations[fed]["name"])
        )

    @error_handler
    @chat_command
    async def fbancmd(self, message: Message) -> None:
        """<reply | user> [reason] [-s silent] - Ban user in federation"""
        chat_id = utils.get_chat_id(message)
        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        a = await self.args_parser(message)

        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason, silent = a

        answ = await self.api.get(f'federations/{self.federations[fed]["uid"]}/chats')

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        chats = answ["chats"]

        banned_in = []

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self.client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                await self.ban(chat, user, t)
                if chat.id != chat_id and not silent:
                    await self.client.send_message(
                        chat,
                        self.strings("fban").format(
                            get_link(user),
                            get_first_name(user),
                            self.federations[fed]["name"],
                            reason,
                        ),
                    )

                banned_in += [chat.title]
            except Exception:
                raise

        await utils.answer(
            message,
            self.strings("fban").format(
                get_link(user),
                get_first_name(user),
                self.federations[fed]["name"],
                reason,
            )
            + "\n\n<b>"
            + "\n".join(banned_in)
            + "</b>",
        )

        await self.api.delete(
            f'federations/{self.federations[fed]["uid"]}/clrwarns',
            data={"user": str(user.id)},
        )

        reply = await message.get_reply_message()
        if reply:
            await reply.delete()

    @error_handler
    @chat_command
    async def funbancmd(self, message: Message) -> None:
        """<reply | user> [reason] [-s silent] - Unban user in federation"""
        chat_id = utils.get_chat_id(message)
        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        a = await self.args_parser(message)

        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason, silent = a

        answ = await self.api.get(f'federations/{self.federations[fed]["uid"]}/chats')

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        chats = answ["chats"]

        unbanned_in = []

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self.client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                await self.client.edit_permissions(
                    chat,
                    user,
                    until_date=0,
                    **{right: True for right in BANNED_RIGHTS.keys()},
                )
                if chat.id != chat_id and not silent:
                    await self.client.send_message(
                        chat,
                        self.strings("funban").format(
                            get_link(user),
                            get_first_name(user),
                            self.federations[fed]["name"],
                        ),
                    )

                unbanned_in += [chat.title]
            except UserAdminInvalidError:
                pass

        await utils.answer(
            message,
            self.strings("funban").format(
                get_link(user), get_first_name(user), self.federations[fed]["name"]
            )
            + "\n\n<b>"
            + "\n".join(unbanned_in)
            + "</b>",
        )

        reply = await message.get_reply_message()
        if reply:
            await reply.delete()

    @error_handler
    @chat_command
    async def fmutecmd(self, message: Message) -> None:
        """<reply | user> [reason] [-s silent] - Mute user in federation"""
        chat_id = utils.get_chat_id(message)
        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        a = await self.args_parser(message)

        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason, silent = a

        answ = await self.api.get(f'federations/{self.federations[fed]["uid"]}/chats')

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        chats = answ["chats"]

        banned_in = []

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self.client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                await self.mute(chat, user, t)
                if chat.id != chat_id and not silent:
                    await self.client.send_message(
                        chat,
                        self.strings("fmute").format(
                            get_link(user),
                            get_first_name(user),
                            self.federations[fed]["name"],
                            reason,
                        ),
                    )

                banned_in += [chat.title]
            except Exception:
                pass

        await utils.answer(
            message,
            self.strings("fmute").format(
                get_link(user),
                get_first_name(user),
                self.federations[fed]["name"],
                reason,
            )
            + "\n\n<b>"
            + "\n".join(banned_in)
            + "</b>",
        )

        reply = await message.get_reply_message()
        if reply:
            await reply.delete()

    @error_handler
    @chat_command
    async def funmutecmd(self, message: Message) -> None:
        """<reply | user> [reason] [-s silent] - Unban user in federation"""
        chat_id = utils.get_chat_id(message)
        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        a = await self.args_parser(message)

        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason, silent = a

        answ = await self.api.get(f'federations/{self.federations[fed]["uid"]}/chats')

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        chats = answ["chats"]

        unbanned_in = []

        for c in chats:
            try:
                if str(c).isdigit():
                    c = int(c)
                chat = await self.client.get_entity(c)
            except Exception:
                continue

            if not chat.admin_rights and not chat.creator:
                continue

            try:
                await self.client.edit_permissions(
                    chat,
                    user,
                    until_date=0,
                    **{right: True for right in BANNED_RIGHTS.keys()},
                )
                if chat.id != chat_id and not silent:
                    await self.client.send_message(
                        chat,
                        self.strings("funmute").format(
                            get_link(user),
                            get_first_name(user),
                            self.federations[fed]["name"],
                        ),
                    )

                unbanned_in += [chat.title]
            except UserAdminInvalidError:
                pass

        await utils.answer(
            message,
            self.strings("funmute").format(
                get_link(user), get_first_name(user), self.federations[fed]["name"]
            )
            + "\n\n<b>"
            + "\n".join(unbanned_in)
            + "</b>",
        )

        reply = await message.get_reply_message()
        if reply:
            await reply.delete()

    @error_handler
    @chat_command
    async def kickcmd(self, message: Message) -> None:
        """<reply | user> <reason | optional> - Kick user"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        user, reason = None, None

        try:
            if reply:
                user = await self.client.get_entity(reply.sender_id)
                reason = args or self.strings
            else:
                uid = args.split(maxsplit=1)[0]
                if str(uid).isdigit():
                    uid = int(uid)
                user = await self.client.get_entity(uid)
                reason = (
                    args.split(maxsplit=1)[1]
                    if len(args.split(maxsplit=1)) > 1
                    else self.strings("no_reason")
                )
        except Exception:
            await utils.answer(message, self.strings("args"))
            return

        try:
            await self.client.kick_participant(utils.get_chat_id(message), user)
            await utils.answer(
                message,
                self.strings("kick").format(
                    get_link(user), get_first_name(user), reason
                ),
            )
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    @chat_command
    async def bancmd(self, message: Message) -> None:
        """<reply | user> <reason | optional> - Ban user"""
        chat = await message.get_chat()

        a = await self.args_parser(message)
        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason, silent = a

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        try:
            await self.ban(chat, user, t)
            await utils.answer(
                message,
                self.strings("ban").format(
                    get_link(user),
                    get_first_name(user),
                    f"for {t // 60} min(-s)" if t != 0 else "forever",
                    reason,
                ),
            )
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    @chat_command
    async def mutecmd(self, message: Message) -> None:
        """<reply | user> <time | 0 for infinity> <reason | optional> - Mute user"""
        chat = await message.get_chat()

        a = await self.args_parser(message)
        if not a:
            await utils.answer(message, self.strings("args"))
            return

        user, t, reason, _ = a

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        try:
            await self.client.edit_permissions(
                chat, user, until_date=time.time() + t, send_messages=False
            )
            await utils.answer(
                message,
                self.strings("mute").format(
                    get_link(user),
                    get_first_name(user),
                    f"for {t // 60} min(-s)" if t != 0 else "forever",
                    reason,
                ),
            )
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    @chat_command
    async def unmutecmd(self, message: Message) -> None:
        """<reply | user> - Unmute user"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        user = None

        try:
            if args.isdigit():
                args = int(args)
            user = await self.client.get_entity(args)
        except Exception:
            try:
                user = await self.client.get_entity(reply.sender_id)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

        try:
            await self.client.edit_permissions(
                chat, user, until_date=0, send_messages=True
            )
            await utils.answer(
                message,
                self.strings("unmuted").format(get_link(user), get_first_name(user)),
            )
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    @chat_command
    async def unbancmd(self, message: Message) -> None:
        """<reply | user> - Unban user"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        reply = await message.get_reply_message()
        args = utils.get_args_raw(message)
        user = None

        try:
            if args.isdigit():
                args = int(args)
            user = await self.client.get_entity(args)
        except Exception:
            try:
                user = await self.client.get_entity(reply.sender_id)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

        try:
            await self.client.edit_permissions(
                chat,
                user,
                until_date=0,
                **{right: True for right in BANNED_RIGHTS.keys()},
            )
            await utils.answer(
                message,
                self.strings("unban").format(get_link(user), get_first_name(user)),
            )
        except UserAdminInvalidError:
            await utils.answer(message, self.strings("not_admin"))
            return

    @error_handler
    async def protectscmd(self, message: Message) -> None:
        """List available filters"""
        await utils.answer(message, self.strings("protections"))

    @error_handler
    async def fedscmd(self, message: Message) -> None:
        """List federations"""
        res = self.strings("feds_header")
        await self.update_feds()
        if not self.federations:
            await utils.answer(message, self.strings("no_federations"))
            return

        for shortname, config in self.federations.copy().items():
            res += f"    ☮️ <b>{config['name']}</b> (<code>{shortname}</code>)"
            for chat in config["chats"]:
                try:
                    if str(chat).isdigit():
                        chat = int(chat)
                    c = await self.client.get_entity(chat)
                except Exception:
                    continue

                res += f"\n        <b>- <a href=\"tg://resolve?domain={getattr(c, 'username', '')}\">{c.title}</a></b>"

            res += f"\n        <b>👮‍♂️ {len(config.get('warns', []))} warns</b>\n\n"

        await utils.answer(message, res)

    @error_handler
    @chat_command
    async def fedcmd(self, message: Message) -> None:
        """<shortname> - Info about federation"""
        args = utils.get_args_raw(message)
        chat = utils.get_chat_id(message)

        await self.update_feds()

        fed = self.find_fed(message)

        if (not args or args not in self.federations) and not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        if not args or args not in self.federations:
            args = fed

        res = self.strings("fed")

        fed = args

        admins = ""
        for admin in self.federations[fed]["admins"]:
            try:
                if str(admin).isdigit():
                    admin = int(admin)
                user = await self.client.get_entity(admin)
            except Exception:
                continue
            name = get_full_name(user)
            status = (
                "<code> 🧃 online</code>"
                if isinstance(getattr(user, "status", None), UserStatusOnline)
                else ""
            )
            admins += f' <b>👤 <a href="{get_link(user)}">{name}</a></b>{status}\n'

        chats = ""
        for chat in self.federations[fed]["chats"]:
            try:
                if str(chat).isdigit():
                    chat = int(chat)
                c = await self.client.get_entity(chat)
            except Exception:
                continue

            chats += f" <b>🫂 <a href=\"tg://resolve?domain={getattr(c, 'username', '')}\">{c.title}</a></b>\n"

        await utils.answer(
            message,
            res.format(
                self.federations[fed]["name"],
                chats,
                admins,
                len(self.federations[fed].get("warns", [])),
            ),
        )

    # @error_handler
    # @chat_command
    # async def pchatcmd(self, message: Message) -> None:
    #     """List protection for current chat"""

    #     chat_id = str(utils.get_chat_id(message))
    #     await self.update_chats()
    #     if chat_id not in self.chats or not self.chats[chat_id]:
    #         await utils.answer(message, self.strings('chat404'))
    #         return

    #     res = f"📡 <b>{ver}</b>\n"

    #     answ = await self.api.get(f'chats/{chat_id}/protects')

    #     if not answ['success']:
    #         await utils.answer(message, self.strings('api_error').format(answ))
    #         return

    #     obj = answ['protects']

    #     fed = self.find_fed(message)

    #     res += "\n🚪 <b>AntiRaid</b> Action: <b>{} all joined</b>"\
    #         .format(obj['antiraid']) if 'antiraid' in obj else ""
    #     res += "\n🐵 <b>AntiTagAll.</b> Action: <b>{}</b>"\
    #         .format(obj['antitagall']) if 'antitagall' in obj else ""
    #     res += "\n🐻 <b>AntiArab.</b> Action: <b>{}</b>"\
    #         .format(obj['antiarab']) if 'antiarab' in obj else ""
    #     res += "\n⏱ <b>AntiFlood</b> Action: <b>{}</b>"\
    #         .format(obj['antiflood']) if 'antiflood' in obj else ""
    #     res += "\n🍓 <b>AntiNSFW.</b> Action: <b>{}</b>"\
    #         .format(obj['antinsfw']) if 'antinsfw' in obj else ""
    #     res += "\n😒 <b>AntiExplicit.</b> Action: <b>{}</b>"\
    #         .format(obj['antiexplicit']) if 'antiexplicit' in obj else ""
    #     res += "\n🤵 <b>AntiSpam.</b> Action: <b>{}</b>"\
    #         .format(obj['antispam']) if 'antispam' in obj else ""

    #     res += "\n📯 <b>AntiChannel.</b>" if 'antichannel' in obj else ""
    #     res += "\n⚙️ <b>AntiService.</b>" if 'antiservice' in obj else ""
    #     res += "\n🪙 <b>AntiSpoiler.</b>" if 'antispoiler' in obj else ""
    #     res += "\n🎑 <b>AntiGIF.</b>" if 'antigif' in obj else ""
    #     res += "\n🐺 <b>AntiHelp.</b>" if 'antihelp' in obj else ""

    #     res += "\n💼 <b>Federation: </b>" + \
    #            self.federations[fed]['name'] if fed else ""

    #     res += "\n👋 <b>Welcome.</b> \n{}"\
    #         .format(obj['welcome']) if 'welcome' in obj else ""

    #     await utils.answer(message, res)

    @error_handler
    @chat_command
    async def pchatcmd(self, message: Message) -> None:
        """List protection for current chat"""
        chat_id = utils.get_chat_id(message)
        q = await self.client.inline_query("@hikarichat_bot", f"chat_{chat_id}")
        await q[0].click(message.peer_id)
        await message.delete()

    @error_handler
    @chat_command
    async def warncmd(self, message: Message) -> None:
        """<reply | user_id | username> <reason | optional> - Warn user"""
        chat = await message.get_chat()

        if not chat.admin_rights and not chat.creator:
            await utils.answer(message, self.strings("not_admin"))
            return

        chat_id = utils.get_chat_id(message)
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = None
        if reply:
            user = await self.client.get_entity(reply.sender_id)
            reason = args or self.strings("no_reason")
        else:
            try:
                u = args.split(maxsplit=1)[0]
                if u.isdigit():
                    u = int(u)

                user = await self.client.get_entity(u)
            except IndexError:
                await utils.answer(message, self.strings("args"))
                return

            try:
                reason = args.split(maxsplit=1)[1]
            except IndexError:
                reason = self.strings("no_reason")

        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        answ = await self.api.post(
            f'federations/{self.federations[fed]["uid"]}/warn',
            data={"user": str(user.id), "reason": reason},
        )

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        await self.update_feds()

        warns = answ["user_warns"]

        if len(warns) >= 7:
            user_name = get_first_name(user)
            answ = await self.api.get(
                f'federations/{self.federations[fed]["uid"]}/chats'
            )

            if not answ["success"]:
                await utils.answer(
                    message,
                    self.strings("api_error").format(json.dumps(answ, indent=4)),
                )
                return

            chats = answ["chats"]
            for c in chats:
                await self.client(
                    EditBannedRequest(
                        c,
                        user,
                        ChatBannedRights(
                            until_date=time.time() + 60**2 * 24,
                            send_messages=True,
                        ),
                    )
                )

                await self.client.send_message(
                    c,
                    self.strings("warns_limit").format(
                        get_link(user), user_name, "muted him for 24 hours"
                    ),
                )

            await message.delete()

            answ = await self.api.delete(
                f'federations/{self.federations[fed]["uid"]}/clrwarns',
                data={"user": str(user.id)},
            )
        else:
            await utils.answer(
                message,
                self.strings("fwarn", message).format(
                    get_link(user), get_first_name(user), len(warns), 7, reason
                ),
            )

    @error_handler
    @chat_command
    async def warnscmd(self, message: Message) -> None:
        """<reply | user_id | username | optional> - Show warns in chat \\ of user"""
        chat_id = utils.get_chat_id(message)

        fed = self.find_fed(message)

        async def check_admin(user_id):
            try:
                return (await self.client.get_permissions(chat_id, user_id)).is_admin
            except ValueError:
                return (
                    user_id in self.client.dispatcher.security._owner
                    or user_id in self.client.dispatcher.security._sudo
                )

        async def check_member(user_id):
            try:
                await self.client.get_permissions(chat_id, user_id)
                return True
            except Exception:
                return False

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        answ = await self.api.get(f'federations/{self.federations[fed]["uid"]}/warns')

        if not answ["success"]:
            await utils.answer(
                message, self.strings("api_error").format(json.dumps(answ, indent=4))
            )
            return

        await self.update_feds()

        warns = answ["warns"]

        if not warns:
            await utils.answer(message, self.strings("no_fed_warns"))
            return

        async def send_user_warns(usid):
            try:
                if int(usid) < 0:
                    usid = int(str(usid)[4:])
            except Exception:
                pass

            if not warns:
                await utils.answer(message, self.strings("no_fed_warns"))
                return

            if str(usid) not in warns or not warns[str(usid)]:
                user_obj = await self.client.get_entity(usid)
                await utils.answer(
                    message,
                    self.strings("no_warns").format(
                        get_link(user_obj), get_full_name(user_obj)
                    ),
                )
            else:
                user_obj = await self.client.get_entity(usid)
                _warns = ""
                processed = []
                for warn in warns[str(usid)].copy():
                    if warn in processed:
                        continue
                    processed += [warn]
                    _warns += (
                        "<code>   </code>🏴󠁧󠁢󠁥󠁮󠁧󠁿 <i>"
                        + warn
                        + (
                            f" </i><b>[x{warns[str(usid)].count(warn)}]</b><i>"
                            if warns[str(usid)].count(warn) > 1
                            else ""
                        )
                        + "</i>\n"
                    )
                await utils.answer(
                    message,
                    self.strings("warns").format(
                        get_link(user_obj),
                        get_full_name(user_obj),
                        len(warns[str(usid)]),
                        7,
                        _warns,
                    ),
                )

        if not await check_admin(message.sender_id):
            await send_user_warns(message.sender_id)
        else:
            reply = await message.get_reply_message()
            args = utils.get_args_raw(message)
            if not reply and not args:
                res = self.strings("warns_adm_fed")
                for user, _warns in warns.copy().items():
                    try:
                        user_obj = await self.client.get_entity(int(user))
                    except Exception:
                        continue

                    if isinstance(user_obj, User):
                        try:
                            name = get_full_name(user_obj)
                        except TypeError:
                            continue
                    else:
                        name = user_obj.title

                    res += f'🐺 <b><a href="{get_link(user_obj)}">' + name + "</a></b>\n"
                    processed = []
                    for warn in _warns.copy():
                        if warn in processed:
                            continue
                        processed += [warn]
                        res += (
                            "<code>   </code>🏴󠁧󠁢󠁥󠁮󠁧󠁿 <i>"
                            + warn
                            + (
                                f" </i><b>[x{_warns.count(warn)}]</b><i>"
                                if _warns.count(warn) > 1
                                else ""
                            )
                            + "</i>\n"
                        )

                await utils.answer(message, res)
                return
            elif reply:
                await send_user_warns(reply.sender_id)
            elif args:
                await send_user_warns(args)

    @error_handler
    @chat_command
    async def dwarncmd(self, message: Message) -> None:
        """<reply | user_id | username> - Remove last warn"""
        chat_id = str(utils.get_chat_id(message))
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = None

        if reply:
            user = await self.client.get_entity(reply.sender_id)
        else:
            if args.isdigit():
                args = int(args)

            try:
                user = await self.client.get_entity(args)
            except IndexError:
                await utils.answer(message, self.strings("args"))
                return

        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        answ = await self.api.delete(
            f'federations/{self.federations[fed]["uid"]}/warn',
            data={"user": str(user.id)},
        )
        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

        await utils.answer(
            message,
            self.strings("dwarn_fed").format(get_link(user), get_first_name(user)),
        )

    @error_handler
    @chat_command
    async def clrwarnscmd(self, message: Message) -> None:
        """<reply | user_id | username> - Remove all warns from user"""
        chat_id = str(utils.get_chat_id(message))
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = None
        if reply:
            user = await self.client.get_entity(reply.sender_id)
        else:
            if args.isdigit():
                args = int(args)

            try:
                user = await self.client.get_entity(args)
            except IndexError:
                await utils.answer(message, self.strings("args"))
                return

        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        answ = await self.api.delete(
            f'federations/{self.federations[fed]["uid"]}/clrwarns',
            data={"user": str(user.id)},
        )
        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

        await utils.answer(
            message,
            self.strings("clrwarns_fed").format(get_link(user), get_first_name(user)),
        )

    @error_handler
    @chat_command
    async def clrallwarnscmd(self, message: Message) -> None:
        """Remove all warns from current federation"""
        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        answ = await self.api.delete(
            f'federations/{self.federations[fed]["uid"]}/clrallwarns'
        )
        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

        await utils.answer(message, self.strings("clrallwarns_fed"))

    @error_handler
    @chat_command
    async def welcomecmd(self, message: Message) -> None:
        """<text> - Change welcome text"""
        chat_id = utils.get_chat_id(message)
        args = utils.get_args_raw(message) or ""

        answ = await self.api.post(
            f"chats/{chat_id}/welcome", data={"state": args, "info": ""}
        )

        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

        if args:
            await utils.answer(message, self.strings("welcome").format(args))
        else:
            await utils.answer(message, self.strings("unwelcome"))

    @error_handler
    @chat_command
    async def fdefcmd(self, message: Message) -> None:
        """<user | reply> - Toggle global user invulnerability"""
        chat_id = utils.get_chat_id(message)

        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        user = None
        if reply:
            user = await self.client.get_entity(reply.sender_id)
        else:
            if str(args).isdigit():
                args = int(args)

            try:
                user = await self.client.get_entity(args)
            except Exception:
                await utils.answer(message, self.strings("args"))
                return

        answ = await self.api.post(
            f'federations/{self.federations[fed]["uid"]}/fdef/{user.id}'
        )

        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

        await utils.answer(
            message,
            self.strings("defense").format(
                get_link(user), get_first_name(user), "on" if answ["status"] else "off"
            ),
        )

    @error_handler
    @chat_command
    async def fsavecmd(self, message: Message) -> None:
        """<note name> <reply> - Save federative note"""
        chat_id = utils.get_chat_id(message)

        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if not reply or not args or not reply.text:
            await utils.answer(message, self.strings("fsave_args"))
            return

        answ = await self.api.post(
            f'federations/{self.federations[fed]["uid"]}/notes',
            data={"shortname": args, "note": reply.text},
        )

        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

        await utils.answer(message, self.strings("fsave").format(args))

    @error_handler
    @chat_command
    async def fstopcmd(self, message: Message) -> None:
        """<note name> - Remove federative note"""
        chat_id = utils.get_chat_id(message)

        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("fsop_args"))
            return

        answ = await self.api.delete(
            f'federations/{self.federations[fed]["uid"]}/notes',
            data={"shortname": args},
        )

        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

        await utils.answer(message, self.strings("fstop").format(args))

    @error_handler
    @chat_command
    async def fnotescmd(self, message: Message, from_watcher: bool = False) -> None:
        """Show federative notes"""
        chat_id = utils.get_chat_id(message)

        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        answ = await self.api.get(f'federations/{self.federations[fed]["uid"]}/notes')

        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

        res = {}
        for shortname, note in answ["notes"].items():
            if int(note["creator"]) != self._me and from_watcher:
                continue

            try:
                obj = await self.client.get_entity(int(note["creator"]))
                name = obj.first_name or obj.title
                key = f'<a href="{get_link(obj)}">{name}</a>'
                if key not in res:
                    res[key] = ""
                res[key] += f"  <code>{shortname}</code>\n"
            except Exception:
                key = "unknown"
                if key not in res:
                    res[key] = ""
                res[key] += f"  <code>{shortname}</code>\n"

        notes = "".join(f"\nby {owner}:\n{note}" for owner, note in res.items())
        if not notes:
            return

        await utils.answer(message, self.strings("fnotes").format(notes))

    @error_handler
    @chat_command
    async def fdeflistcmd(self, message: Message) -> None:
        """Show global invulnerable users"""
        chat_id = utils.get_chat_id(message)

        fed = self.find_fed(message)

        if not fed:
            await utils.answer(message, self.strings("no_fed"))
            return

        answ = await self.api.get(f'federations/{self.federations[fed]["uid"]}/fdef')

        if not answ["success"]:
            await utils.answer(message, self.strings("api_error").format(answ))
            return

        if not answ["fdef"]:
            await utils.answer(message, self.strings("no_defense"))
            return

        res = ""
        defense = answ["fdef"]
        for user in defense.copy():
            try:
                u = await self.client.get_entity(int(user))
            except Exception:
                await self.api.post(
                    f'federations/{self.federations[fed]["uid"]}/fdef/{user}'
                )
                await asyncio.sleep(0.2)
                continue

            tit = get_full_name(u)

            res += f'  🇻🇦 <a href="{get_link(u)}">{tit}</a>\n'

        await utils.answer(message, self.strings("defense_list").format(res))
        return

    @error_handler
    async def p__antiservice(self, chat_id: Union[str, int], message: Message) -> None:
        if (
            str(chat_id) in self.chats
            and str(chat_id) in self.my_protects
            and "antiservice" in self.chats[str(chat_id)]
            and "antiservice" in self.my_protects[str(chat_id)]
            and getattr(message, "action_message", False)
        ):
            await message.delete()

    @error_handler
    async def p__antiraid(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> bool:
        if (
            "antiraid" in self.chats[str(chat_id)]
            and "antiraid" in self.my_protects[str(chat_id)]
        ):
            if getattr(message, "user_joined", False) or getattr(
                message, "user_added", False
            ):
                action = self.chats[str(chat_id)]["antiraid"]
                if action == "kick":
                    await self.client.send_message(
                        "me",
                        self.strings("antiraid").format(
                            "kicked", user.id, get_full_name(user), chat.title
                        ),
                    )
                    await self.client.kick_participant(chat_id, user)
                elif action == "ban":
                    await self.client.send_message(
                        "me",
                        self.strings("antiraid").format(
                            "banned", user.id, get_full_name(user), chat.title
                        ),
                    )
                    await self.ban(chat, user)
                elif action == "mute":
                    await self.client.send_message(
                        "me",
                        self.strings("antiraid").format(
                            "muted", user.id, get_full_name(user), chat.title
                        ),
                    )
                    await self.mute(chat, user)

                return True

        return False

    @error_handler
    async def p__welcome(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
        chat: Chat,
    ) -> bool:
        if (
            "welcome" in self.chats[str(chat_id)]
            and "welcome" in self.my_protects[str(chat_id)]
        ):
            if getattr(message, "user_joined", False) or getattr(
                message, "user_added", False
            ):
                await self.client.send_message(
                    chat_id,
                    self.chats[str(chat_id)]["welcome"]
                    .replace("{user}", get_full_name(user))
                    .replace("{chat}", chat.title)
                    .replace(
                        "{mention}",
                        f'<a href="{get_link(user)}">{get_full_name(user)}</a>',
                    ),
                    reply_to=message.action_message.id,
                )

                return True

        return False

    @error_handler
    async def p__report(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> None:
        if (
            "report" in self.chats[str(chat_id)]
            and "report" in self.my_protects[str(chat_id)]
            and getattr(message, "get_reply_message", False)
        ):
            reply = await message.get_reply_message()
            if (
                str(user_id) not in self.ratelimit["report"]
                or self.ratelimit["report"][str(user_id)] < time.time()
            ):
                if message.raw_text.startswith("#report") and reply:
                    reason = (
                        message.raw_text.split(maxsplit=1)[1]
                        if message.raw_text.count(" ") >= 1
                        else self.strings("no_reason")
                    )

                    answ = await self.api.post(
                        f"chats/{chat_id}/report",
                        data={
                            "reason": reason,
                            "link": await get_message_link(reply, chat),
                            "user_link": get_link(user),
                            "user_name": get_full_name(user),
                            "text_thumbnail": reply.raw_text[:1024],
                        },
                    )

                    if not answ["success"]:
                        await utils.answer(
                            message, self.strings("api_error").format(answ)
                        )
                        return

                    if not self.config["silent"]:
                        await utils.answer(
                            reply,
                            self.strings("reported").format(
                                get_link(user), get_full_name(user), reason
                            ),
                        )

                    self.ratelimit["report"][str(user_id)] = time.time() + 60

                    await message.delete()

    @error_handler
    async def p__antiflood(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if (
            "antiflood" in self.chats[str(chat_id)]
            and "antiflood" in self.my_protects[str(chat_id)]
        ):
            if str(chat_id) not in self.flood_cache:
                self.flood_cache[str(chat_id)] = {}

            if str(user_id) not in self.flood_cache[str(chat_id)]:
                self.flood_cache[str(chat_id)][str(user_id)] = []

            for item in self.flood_cache[str(chat_id)][str(user_id)].copy():
                if time.time() - item > self.flood_timeout:
                    self.flood_cache[str(chat_id)][str(user_id)].remove(item)

            self.flood_cache[str(chat_id)][str(user_id)].append(round(time.time(), 2))
            self.save_flood_cache()

            if (
                len(self.flood_cache[str(chat_id)][str(user_id)])
                >= self.flood_threshold
            ):
                return self.chats[str(chat_id)]["antiflood"]

        return False

    @error_handler
    async def p__antichannel(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> bool:
        if (
            "antichannel" in self.chats[str(chat_id)]
            and "antichannel" in self.my_protects[str(chat_id)]
        ):
            if getattr(message, "sender_id", 0) < 0:
                await message.delete()
                return True

        return False

    @error_handler
    async def p__antigif(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> bool:
        if (
            "antigif" in self.chats[str(chat_id)]
            and "antigif" in self.my_protects[str(chat_id)]
        ):
            try:
                if (
                    message.media
                    and DocumentAttributeAnimated() in message.media.document.attributes
                ):
                    await message.delete()
                    return True
            except Exception:
                pass

        return False

    @error_handler
    async def p__antispoiler(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> bool:
        if (
            "antispoiler" in self.chats[str(chat_id)]
            and "antispoiler" in self.my_protects[str(chat_id)]
        ):
            try:
                if any([isinstance(_, MessageEntitySpoiler) for _ in message.entities]):
                    await message.delete()
                    return True
            except Exception:
                pass

        return False

    @error_handler
    async def p__antiexplicit(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if (
            "antiexplicit" in self.chats[str(chat_id)]
            and "antiexplicit" in self.my_protects[str(chat_id)]
        ):
            text = getattr(message, "raw_text", "")
            P = "пПnPp"
            I = "иИiI1uІИ́Їіи́ї"
            E = "еЕeEЕ́е́"
            D = "дДdD"
            Z = "зЗ3zZ3"
            M = "мМmM"
            U = "уУyYuUУ́у́"
            O = "оОoO0О́о́"
            L = "лЛlL1"
            A = "аАaAА́а́@"
            N = "нНhH"
            G = "гГgG"
            K = "кКkK"
            R = "рРpPrR"
            H = "хХxXhH"
            YI = "йЙyуУY"
            YA = "яЯЯ́я́"
            YO = "ёЁ"
            YU = "юЮЮ́ю́"
            B = "бБ6bB"
            T = "тТtT1"
            HS = "ъЪ"
            SS = "ьЬ"
            Y = "ыЫ"

            occurrences = re.findall(
                rf"""\b[0-9]*(\w*[{P}][{I}{E}][{Z}][{D}]\w*|(?:[^{I}{U}\s]+|{N}{I})?(?<!стра)[{H}][{U}][{YI}{E}{YA}{YO}{I}{L}{YU}](?!иг)\w*|\w*[{B}][{L}](?:[{YA}]+[{D}{T}]?|[{I}]+[{D}{T}]+|[{I}]+[{A}]+)(?!х)\w*|(?:\w*[{YI}{U}{E}{A}{O}{HS}{SS}{Y}{YA}][{E}{YO}{YA}{I}][{B}{P}](?!ы\b|ол)\w*|[{E}{YO}][{B}]\w*|[{I}][{B}][{A}]\w+|[{YI}][{O}][{B}{P}]\w*)|\w*(?:[{P}][{I}{E}][{D}][{A}{O}{E}]?[{R}](?!о)\w*|[{P}][{E}][{D}][{E}{I}]?[{G}{K}])|\w*[{Z}][{A}{O}][{L}][{U}][{P}]\w*|\w*[{M}][{A}][{N}][{D}][{A}{O}]\w*|\w*[{G}][{O}{A}][{N}][{D}][{O}][{N}]\w*)""",
                text,
            )

            occurrences = [
                word
                for word in occurrences
                if not any(
                    [excl in word for excl in self.variables["censor_exclusions"]]
                )
            ]

            if occurrences:
                return self.chats[str(chat_id)]["antiexplicit"]

        return False

    @error_handler
    async def p__antinsfw(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if (
            "antinsfw" in self.chats[str(chat_id)]
            and "antinsfw" in self.my_protects[str(chat_id)]
        ):
            media = False

            if getattr(message, "sticker", False):
                media = message.sticker
            elif getattr(message, "media", False):
                media = message.media

            if media:
                photo = io.BytesIO()
                await self.client.download_media(message.media, photo)
                photo.seek(0)

                if imghdr.what(photo) in self.variables["image_types"]:
                    response = await self.api.post("check_nsfw", data={"file": photo})
                    if response["verdict"] == "nsfw":
                        todel = []
                        async for _ in self.client.iter_messages(
                            message.peer_id, reverse=True, offset_id=message.id - 1
                        ):
                            todel += [_]
                            if _.sender_id != message.sender_id:
                                break

                        await self.client.delete_messages(
                            message.peer_id, message_ids=todel, revoke=True
                        )
                        return self.chats[str(chat_id)]["antinsfw"]

        return False

    @error_handler
    async def p__antitagall(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if (
            "antitagall" in self.chats[str(chat_id)]
            and "antitagall" in self.my_protects[str(chat_id)]
            and getattr(message, "text", False)
        ):
            if message.text.count("tg://user?id=") >= 5:
                return self.chats[str(chat_id)]["antitagall"]

        return False

    @error_handler
    async def p__antihelp(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> bool:
        if (
            "antihelp" in self.chats[str(chat_id)]
            and "antihelp" in self.my_protects[str(chat_id)]
            and getattr(message, "text", False)
        ):
            search = message.text
            if "@" in search:
                search = search[: search.find("@")]

            if (
                len(search.split()) > 0
                and search.split()[0][1:] in self.variables["blocked_commands"]
            ):
                logger.debug("Deleted message with blocked command")
                await message.delete()
                return True

        return False

    @error_handler
    async def p__antiarab(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if (
            "antiarab" in self.chats[str(chat_id)]
            and "antiarab" in self.my_protects[str(chat_id)]
        ):
            if getattr(message, "user_joined", False) or getattr(
                message, "user_added", False
            ):
                if (
                    len(re.findall("[\u4e00-\u9fff]+", get_full_name(user))) != 0
                    or len(re.findall("[\u0621-\u064A]+", get_full_name(user))) != 0
                ):
                    return self.chats[str(chat_id)]["antiarab"]

        return False

    @error_handler
    async def p__antizalgo(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if (
            "antizalgo" in self.chats[str(chat_id)]
            and "antizalgo" in self.my_protects[str(chat_id)]
        ):
            if getattr(message, "user_joined", False) or getattr(
                message, "user_added", False
            ):
                if len(re.findall("[^\x20-\x7E\x20-\x7E]", get_full_name(user))) > 5:
                    return self.chats[str(chat_id)]["antizalgo"]

        return False

    @error_handler
    async def p__antistick(
        self,
        chat_id: Union[str, int],
        user_id: Union[str, int],
        user: Union[User, Channel],
        message: Message,
    ) -> Union[bool, str]:
        if (
            "antistick" in self.chats[str(chat_id)]
            and "antistick" in self.my_protects[str(chat_id)]
            and (
                getattr(message, "sticker", False)
                or getattr(message, "media", False)
                and isinstance(message.media, MessageMediaUnsupported)
            )
        ):

            sender = user.id
            if sender not in self._sticks_ratelimit:
                self._sticks_ratelimit[sender] = []

            self._sticks_ratelimit[sender] += [round(time.time())]

            for timing in self._sticks_ratelimit[sender].copy():
                if time.time() - timing > 60:
                    self._sticks_ratelimit[sender].remove(timing)

            if len(self._sticks_ratelimit[sender]) > self._sticks_limit:
                return self.chats[str(chat_id)]["antistick"]

        return False

    @error_handler
    async def watcher(self, message: Message) -> None:
        if not (
            isinstance(getattr(message, "chat", 0), Chat)
            or isinstance(getattr(message, "chat", 0), Channel)
            and getattr(message.chat, "megagroup", False)
        ):
            return

        chat_id = utils.get_chat_id(message)

        await self.p__antiservice(chat_id, message)

        try:
            user_id = (
                getattr(message, "sender_id", False)
                or message.action_message.action.users[0]
            )
        except Exception:
            try:
                user_id = message.action_message.action.from_id.user_id
            except Exception:
                try:
                    user_id = message.from_id.user_id
                except Exception:
                    try:
                        user_id = message.action_message.from_id.user_id
                    except Exception:
                        try:
                            user_id = message.action.from_user.id
                        except Exception:
                            # It's not the event we want to see, bc
                            # There is no user. Probably, it was sent by
                            # anonymous admin

                            # await self.api.report_error(str(message))
                            return

        user_id = (
            int(str(user_id)[4:]) if str(user_id).startswith("-100") else int(user_id)
        )

        logger.debug(f"Got event from {user_id}")

        violation = None
        action = None

        fed = self.find_fed(message)

        if fed in self.federations:
            if getattr(message, "raw_text", False):
                if user_id and isinstance(message, Message):
                    if (
                        str(user_id) not in self.ratelimit["notes"]
                        or self.ratelimit["notes"][str(user_id)] < time.time()
                    ):
                        if not (
                            message.raw_text.startswith(self.prefix)
                            and len(message.raw_text) > 1
                            and message.raw_text[1] != self.prefix
                        ):
                            await self.update_feds()
                            if message.raw_text.lower().strip() in [
                                "#заметки",
                                "#notes",
                            ]:
                                self.ratelimit["notes"][str(user_id)] = time.time() + 3
                                if any(
                                    [
                                        str(note["creator"]) == str(self._me)
                                        for _, note in self.federations[fed][
                                            "notes"
                                        ].items()
                                    ]
                                ):
                                    await self.fnotescmd(
                                        await message.reply(
                                            f"<code>{self.prefix}fnotes</code>"
                                        ),
                                        True,
                                    )

                            for note, note_info in self.federations[fed][
                                "notes"
                            ].items():
                                if str(note_info["creator"]) != str(self._me):
                                    continue

                                if note.lower() in message.raw_text.lower():
                                    await utils.answer(message, note_info["text"])
                                    self.ratelimit["notes"][str(user_id)] = (
                                        time.time() + 3
                                    )
                                    break

            if int(user_id) in list(map(int, self.federations[fed]["fdef"])):
                return

        if user_id < 0:
            user_id = int(str(user_id)[4:])

        await self.update_chats()
        if str(chat_id) not in self.chats or not self.chats[str(chat_id)]:
            return

        if str(chat_id) not in self.my_protects:
            return

        try:
            if (await self.client.get_permissions(chat_id, message.sender_id)).is_admin:
                return
        except Exception:
            pass

        user = await self.client.get_entity(user_id)
        chat = await message.get_chat()
        user_name = get_full_name(user)

        args = (chat_id, user_id, user, message)

        if await self.p__antiraid(*args):
            return

        if await self.p__welcome(*args, chat):
            return

        r = await self.p__antiarab(*args)
        if r:
            await self.punish(chat_id, user, "arabic_nickname", r, user_name)
            return

        r = await self.p__antizalgo(*args)
        if r:
            await self.punish(chat_id, user, "zalgo", r, user_name)
            return

        if getattr(message, "action", ""):
            return

        await self.p__report(*args)

        r = await self.p__antiflood(*args)
        if r:
            await self.punish(chat_id, user, "flood", r, user_name)
            await message.delete()
            return

        if await self.p__antichannel(*args):
            return

        if await self.p__antigif(*args):
            return

        r = await self.p__antistick(*args)
        if r:
            await self.punish(chat_id, user, "stick", r, user_name)
            return

        if await self.p__antispoiler(*args):
            return

        r = await self.p__antiexplicit(*args)
        if r:
            await self.punish(chat_id, user, "explicit", r, user_name)
            await message.delete()
            return

        r = await self.p__antinsfw(*args)
        if r:
            await self.punish(chat_id, user, "nsfw_content", r, user_name)
            return

        r = await self.p__antitagall(*args)
        if r:
            await self.punish(chat_id, user, "tagall", r, user_name)
            await message.delete()
            return

        if await self.p__antihelp(*args):
            return
