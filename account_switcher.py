# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/fluency/48/000000/change-user-male.png
# meta developer: @hikariatama
# scope: hikka_only

from .. import loader, utils
import re

from telethon.tl.functions.users import GetFullUserRequest
from telethon.tl.functions.account import UpdateUsernameRequest, UpdateProfileRequest
from telethon.tl.functions.photos import UploadProfilePhotoRequest

from telethon.tl.types import Message


@loader.tds
class AccountSwitcherMod(loader.Module):
    """Allows you to easily switch between different profiles"""

    strings = {
        "name": "AccountSwitcher",
        "reply_required": "🦊 <b>Reply to service message in db chat named <u>acc-switcher-db</u></b>",
        "account_saved": "🦊 <b>Account saved!</b>",
    }

    async def client_ready(self, client, db) -> None:
        self._db = db
        self._client = client
        self._accounts = db.get("AccountSwitcher", "accounts", {})

    async def _save_acc(self, photo, fn, ln, bio, un):
        accs_db, _ = await utils.asset_channel(
            self._client,
            "acc-switcher-db",
            "This chat will handle your saved profiles via AccountSwitcher Module",
        )

        info = f'<b>First name</b>: "{fn}"\n<b>Last name</b>: "{ln}"\n<b>Bio</b>: "{bio}"\n<b>Username</b>: "{un}"'
        if photo is not None:
            await self._client.send_file(accs_db, photo, caption=info)
        else:
            await self._client.send_message(accs_db, info)

    async def accsavecmd(self, message: Message) -> None:
        """[-n] - Save account for future restoring. -n - To save username, and change it while restoring"""
        args = utils.get_args_raw(message)
        full = await self._client(GetFullUserRequest("me"))
        photo, fn, ln, bio, un = None, None, None, None, None
        acc = await message.client.get_entity("me")
        if full.full_user.profile_photo:
            photo = await message.client.download_profile_photo(acc, bytes)
        fn = getattr(acc, "first_name", None)
        ln = getattr(acc, "last_name", None)
        un = getattr(acc, "username", None) if "-n" in args else "not_saved_username"
        bio = (
            full.full_user.about
            if getattr(full.full_user, "about", None) is not None
            else ""
        )
        await self._save_acc(photo, fn, ln, bio, un)
        await utils.answer(message, self.strings("account_saved"))

    async def accrestcmd(self, message: Message) -> None:
        """<reply to message in db> - Restore account from backup. Your username could be stolen!"""
        reply = await message.get_reply_message()
        if not reply:
            return await utils.answer(message, self.strings("reply_required"))

        # chat = await reply.get_chat()
        # if chat.title != "acc-switcher-db":
        #     return await utils.answer(message, self.strings('reply_required'))

        log = ""

        data = re.sub(r"<.*?>", "", reply.message)
        fn = re.search(r'First name: "([^"]+)"', data).group(1)
        ln = re.search(r'Last name: "([^"]+)"', data).group(1)
        bio = re.search(r'Bio: "([^"]+)"', data).group(1)
        un = re.search(r'Username: "([^"]+)"', data).group(1)

        fn = fn if fn != "None" else None
        ln = ln if ln != "None" else None
        bio = bio if bio != "None" else None
        un = un if un != "None" else None

        if un != "not_saved_username":
            try:
                await self._client(UpdateUsernameRequest(un))
            except Exception:
                log += "👉🏻 Error while restoring username\n"
        else:
            log += "👉🏻 Username not restored\n"

        try:
            await self._client(UpdateProfileRequest(fn, ln, bio))
            log += (
                "👉🏻 First name restored\n"
                if fn is not None
                else "👉🏻 First name not restored\n"
            )
            log += (
                "👉🏻 Last name restored\n"
                if ln is not None
                else "👉🏻 Last name not restored\n"
            )
            log += "👉🏻 Bio restored\n" if bio is not None else "👉🏻 Bio not restored\n"
        except Exception:
            log += "👉🏻 First name not restored\n👉🏻 Last name not restored\n👉🏻 Bio not restored"

        try:
            if reply.media:
                upload = await self._client.upload_file(
                    await self._client.download_media(reply.media)
                )
                await self._client(UploadProfilePhotoRequest(upload))
                log += "👉🏻 Profile photo restored"
            else:
                log += "👉🏻 Profile photo not restored"
        except Exception:
            log += "👉🏻 Profile photo not restored"

        log = re.sub(r"\n{2,}", r"\n", log)

        await utils.answer(message, log)
