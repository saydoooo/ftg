# █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
# █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█
#
#              © Copyright 2022
#
#          https://t.me/hikariatama
#
# 🔒 Licensed under the GNU GPLv3
# 🌐 https://www.gnu.org/licenses/agpl-3.0.html

# meta pic: https://img.icons8.com/fluency/48/000000/time.png
# meta developer: @hikariatama

from .. import loader, utils
import asyncio
import json
import re
import datetime
import time
import telethon
from telethon.tl.types import Message


@loader.tds
class TempChatMod(loader.Module):
    """Creates temprorary chats to avoid trashcans in TG."""

    strings = {
        "name": "TempChat",
        "chat_is_being_removed": "<b>🚫 This chat is being removed...</b>",
        "args": "<b>PZD with args: </b><code>.help TempChat</code>",
        "chat_not_found": "<b>Chat not found</b>",
        "tmp_cancelled": "<b>Chat </b><code>{}</code><b> will now live forever!</b>",
        "delete_error": "<b>An error occured while deleting this temp chat. Remove it manually.</b>",
        "temp_chat_header": "<b>⚠️ This chat</b> (<code>{}</code>)<b> is temporary and will be removed {}.</b>",
        "chat_created": "<b>Chat have been created</b>",
        "delete_error_me": "<b>Error occured while deleting chat {}</b>",
    }

    @staticmethod
    def s2time(temp_time):
        seconds, minutes, hours, days, weeks, months = 0, 0, 0, 0, 0, 0

        try:
            seconds = int(str(re.search("([0-9]+)s", temp_time).group(1)))
        except Exception:
            pass

        try:
            minutes = int(str(re.search("([0-9]+)min", temp_time).group(1))) * 60
        except Exception:
            pass

        try:
            hours = int(str(re.search("([0-9]+)h", temp_time).group(1))) * 60 * 60
        except Exception:
            pass

        try:
            days = int(str(re.search("([0-9]+)d", temp_time).group(1))) * 60 * 60 * 24
        except Exception:
            pass

        try:
            weeks = (
                int(str(re.search("([0-9]+)w", temp_time).group(1))) * 60 * 60 * 24 * 7
            )
        except Exception:
            pass

        try:
            months = (
                int(str(re.search("([0-9]+)m[^i]", temp_time).group(1)))
                * 60
                * 60
                * 24
                * 31
            )
        except Exception:
            pass

        return round(time.time() + seconds + minutes + hours + days + weeks + months)

    async def chats_handler_async(self):
        while self._db.get("TempChat", "loop", False):
            # await self._client.send_message('me', 'testing')
            for chat, info in self.chats.items():
                if int(info[0]) <= time.time():
                    try:
                        await self._client.send_message(
                            int(chat), self.strings("chat_is_being_removed")
                        )
                        async for user in self._client.iter_participants(
                            int(chat), limit=50
                        ):
                            await self._client.kick_participant(int(chat), user.id)
                        await self._client.delete_dialog(int(chat))
                    except Exception:
                        try:
                            await self._client.send_message(
                                int(chat), self.strings("delete_error")
                            )
                        except Exception:
                            await self._client.send_message(
                                "me", self.strings("delete_error_me").format(info[1])
                            )

                    del self.chats[chat]
                    self._db.set("TempChat", "chats", self.chats)
                    break
            await asyncio.sleep(0.5)

    async def client_ready(self, client, db):
        self._db = db
        self.chats = self._db.get("TempChat", "chats", {})
        self._client = client
        self._db.set("TempChat", "loop", False)
        await asyncio.sleep(1)
        self._db.set("TempChat", "loop", True)
        asyncio.ensure_future(self.chats_handler_async())

    async def tmpchatcmd(self, message: Message):
        """<time> <title> - Create new temp chat
        Time format: 30s, 30min, 1h, 1d, 1w, 1m"""
        args = utils.get_args_raw(message)
        if args == "":
            await utils.answer(message, self.strings("args", message))
            await asyncio.sleep(3)
            await message.delete()
            return

        if len(args.split()) < 2:
            await utils.answer(message, self.strings("args", message))
            await asyncio.sleep(3)
            await message.delete()
            return

        temp_time = args.split()[0]
        tit = args.split(" ", 1)[1].strip()

        until = self.s2time(temp_time)
        if until == round(time.time()):
            await utils.answer(message, self.strings("args", message))
            await asyncio.sleep(3)
            await message.delete()
            return

        res = await self._client(
            telethon.functions.messages.CreateChatRequest(
                users=["kanekiguard_tests_bot"], title=tit
            )
        )
        await utils.answer(message, self.strings("chat_created", message))
        cid = res.chats[0].id

        await self._client.send_message(
            cid,
            self.strings("temp_chat_header", message).format(
                cid,
                datetime.datetime.utcfromtimestamp(until + 10800).strftime(
                    "%d.%m.%Y %H:%M:%S"
                ),
            ),
        )
        self.chats[str(cid)] = [until, tit]
        self._db.set("TempChat", "chats", self.chats)

    async def tmpcurrentcmd(self, message: Message):
        """<time> - Create current chat temporary
        Time format: 30s, 30min, 1h, 1d, 1w, 1m"""
        args = utils.get_args_raw(message)
        if not args:
            await utils.answer(message, self.strings("args", message))
            await asyncio.sleep(3)
            await message.delete()
            return

        until = self.s2time(args)
        if until == round(time.time()):
            await utils.answer(message, self.strings("args", message))
            await asyncio.sleep(3)
            await message.delete()
            return

        cid = utils.get_chat_id(message)

        await utils.answer(
            message,
            self.strings("temp_chat_header", message).format(
                cid,
                datetime.datetime.utcfromtimestamp(until + 10800).strftime(
                    "%d.%m.%Y %H:%M:%S"
                ),
            ),
        )
        self.chats[str(cid)] = [until, (await self._client.get_entity(cid)).title]
        self._db.set("TempChat", "chats", self.chats)

    async def tmpchatscmd(self, message: Message):
        """List temp chats"""
        res = "<b>= Temporary Chats =</b>\n<s>==================</s>\n"
        for chat, info in self.chats.items():
            res += f'<b>{info[1]}</b> (<code>{chat}</code>)<b>: {datetime.datetime.utcfromtimestamp(info[0] + 10800).strftime("%d.%m.%Y %H:%M:%S")}.</b>\n'
        res += "<s>==================</s>"

        await utils.answer(message, res)

    async def tmpcancelcmd(self, message: Message):
        """[chat-id] - Disable deleting chat by id, or current chat if unspecified."""
        args = utils.get_args_raw(message)
        if args not in self.chats:
            args = str(utils.get_chat_id(message))

        if args not in self.chats:
            await utils.answer(message, self.strings("chat_not_found", message))
            await asyncio.sleep(3)
            await message.delete()
            return

        await utils.answer(
            message, self.strings("tmp_cancelled", message).format(self.chats[args][1])
        )
        del self.chats[args]
        self._db.set("TempChat", "chats", json.dumps(self.chats))

    async def tmpctimecmd(self, message: Message):
        """<chat_id> <new_time> - Change chat deletion time"""
        args = utils.get_args_raw(message)
        if args == "":
            await utils.answer(message, self.strings("args", message))
            await asyncio.sleep(3)
            await message.delete()
            return

        args = args.split()
        if len(args) == 0:
            await utils.answer(message, self.strings("args", message))
            await asyncio.sleep(3)
            await message.delete()
            return

        if len(args) >= 2:
            chat = args[0]
            new_time = self.s2time(args[1])
        else:
            chat = str(utils.get_chat_id(message))
            new_time = self.s2time(args[0])

        if chat not in list(self.chats.keys()):
            await utils.answer(message, self.strings("chat_not_found", message))
            await asyncio.sleep(3)
            await message.delete()
            return

        self.chats[chat][0] = new_time
        self._db.set("TempChat", "chats", self.chats)
