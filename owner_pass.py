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

# meta title: β OwnerPass
# meta pic: https://img.icons8.com/fluency/48/000000/show-password.png
# meta desc: Get userbot owner by password [No support]

from .. import loader, utils
import time
import telethon
from telethon.tl.types import Message


@loader.tds
class OwnerPassMod(loader.Module):
    """Gives access to userbot through password
    GeekTG Only"""

    strings = {
        "name": "OwnerPass",
        "weak_pass": "<b>🚫 This password is very weak. You need to use at least 8 symbols and at least 1 letter</b>",
        "password_set": "<b>✅ Password set successfully</b>",
        "incorrect_pass": "⛎ <b>Incorrect password. Try again in 5 minutes</b>",
        "owner": "⛎ <b>You're owner now.</b>",
        "not_owner": "⛎ <b>Owner removed.</b>",
        "no_owner": "⛎ <b>This user is not owner.</b>",
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db
        self._ratelimit = db.get(__name__, "ratelimit", {})

    @loader.owner
    async def setownerpasscmd(self, message: Message) -> None:
        """<pass> - Set up password for root access. Can be executed only from userbot account and cannot be executed in chats"""
        if not message.out or isinstance(
            message.peer_id, telethon.tl.types.PeerChannel
        ):
            return

        args = utils.get_args_raw(message)
        if (
            not args
            or len(args) < 8
            or not any(_ for _ in args if _.lower() in "abcdefghigklmnopqrstuvwxyz")
        ):
            return await utils.answer(message, self.strings("weak_pass"))

        self.db.set(__name__, "password", hash(args))
        await utils.answer(message, self.strings("password_set"))

    @loader.unrestricted
    async def getownercmd(self, message: Message) -> None:
        """<pass> - Get owner of userbot using password"""
        if (
            not message.out
            and message.sender_id in self._ratelimit
            and self._ratelimit[message.sender_id] > time.time()
        ):
            return

        args = utils.get_args_raw(message)
        if not args or hash(args) != self.db.get(__name__, "password"):
            await utils.answer(message, self.strings("incorrect_pass"))
            if not message.out:
                self._ratelimit[message.sender_id] = round(time.time()) + 5 * 60
                self.db.set(__name__, "ratelimit", self._ratelimit)

            return

        self.db.set(
            "friendly-telegram.security",
            "owner",
            list(
                set(
                    self.db.get("friendly-telegram.security", "owner", [])
                    + [message.sender_id]
                )
            ),
        )
        await utils.answer(message, self.strings("owner"))
        if not message.out:
            await message.delete()
        try:
            await self.client.dispatcher.security.update_owners()
        except Exception:
            await self.allmodules.commands["restart"](
                await message.respond("restarting")
            )

    @loader.owner
    async def takeownercmd(self, message: Message) -> None:
        """Take owner from user"""
        if not message.out:
            return
        try:
            u = message.peer_id.user_id
        except Exception:
            return

        if u not in self.db.get("friendly-telegram.security", "owner", []):
            return await utils.answer(message, self.strings("no_owner"))
        self.db.set(
            "friendly-telegram.security",
            "owner",
            list(
                set(self.db.get("friendly-telegram.security", "owner", [])) - set([u])
            ),
        )
        return await utils.answer(message, self.strings("not_owner"))
