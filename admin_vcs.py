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

# meta title: HikariVCS [admin]
# meta pic: https://via.placeholder.com/64
# meta desc: [ADMIN ONLY] Hikari Version Control System

# scope: inline_control


from .. import loader, utils
from telethon.tl.types import Message
import logging
import asyncio
import os
import difflib
from telethon import events
import functools

logger = logging.getLogger(__name__)

PATH = "/home/ftg"

MODS = os.path.join(PATH, "mods")
VCS = os.path.join(PATH, "vcs")
FTG = os.path.join(PATH, "ftg")

mods = []


def pull_mods():
    global mods
    mods = [
        _.path.split("/")[-1].split(".")[0]
        for _ in os.scandir(MODS)
        if _.path.endswith(".py")
    ]


def get_current_version(mod):
    vers = [
        tuple(list(map(int, module.path.split("-")[1].split(".")[0].split("_"))))
        for module in os.scandir(VCS)
        if module.path.split("/")[-1].split("-")[0] == mod
    ]

    if not vers:
        return 0, 0, 0

    return max(vers)


def get_version(mod):
    current = get_current_version(mod)
    if current == (0, 0, 0):
        return (1, 0, 0)

    current = list(current)

    current[-1] += 1

    if current[-1] == 9:
        current[-1] = 0
        current[-2] += 1

    if current[-2] == 9:
        current[-2] = 0
        current[-3] += 1

    return tuple(current)


def get_last_version(mod):
    c = "_".join(list(map(str, list(get_current_version(mod)))))
    try:
        return open(os.path.join(VCS, f"{mod}-{c}.py"), "r").read()
    except FileNotFoundError:
        return ""


def get_code(mod):
    return open(os.path.join(MODS, f"{mod}.py"), "r").read()


def push(mod, confirm=True, new_version=True):
    d = get_diff(mod)
    if not d:
        return "Nothing to commit"

    m = ""

    version = get_version(mod) if new_version else get_current_version(mod)
    build = "_".join(list(map(str, version)))
    ver = ".".join(list(map(str, list(version))))

    vcs = os.path.join(VCS, f"{mod}-{build}.py")
    ftg = os.path.join(FTG, f"{mod}.py")

    code = get_code(mod)
    adds = len([_ for _ in d.splitlines() if _.startswith("+")])
    removes = len([_ for _ in d.splitlines() if _.startswith("-")])

    m += f"💾 <b>{mod} {ver}</b>: {adds} adds | {removes} removes"

    if confirm:
        return m

    open(vcs, "w").write(code)
    open(ftg, "w").write(code)

    return ver
    # commited += [f"Update <a href=\"https://mods.hikariatama.ru/view/{mod}.py\">{mod}.py</a> to version {ver}"]


def get_diff(mod):
    try:
        old = get_last_version(mod).strip().splitlines()
        new = open(os.path.join(MODS, f"{mod}.py"), "r").read().strip().splitlines()
        return "\n".join(
            list(
                difflib.unified_diff(
                    old,
                    new,
                    fromfile=mod
                    + "-"
                    + ".".join(list(map(str, list(get_current_version(mod))))),
                    tofile=f"{mod}-" + ".".join(list(map(str, list(get_version(mod))))),
                    lineterm="",
                )
            )
        )

    except FileNotFoundError:
        return False


@loader.tds
class HikariVCSMod(loader.Module):
    """[ADMIN ONLY] Hikari Version Control System"""

    strings = {"name": "HikariVCS"}

    def get(self, *args) -> dict:
        return self.db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self.db.set(self.strings["name"], *args)

    async def _pull_mods(self) -> None:
        global mods
        while True:
            pull_mods()
            await asyncio.sleep(10)

    def check_working_tree(self, bulk=False):
        m = ""
        kb = [
            [{"text": "🔄 Check again", "callback": self.inline__get_working_tree}],
            [],
        ]
        c = 0
        for mod in mods:
            diff = get_diff(mod)
            if not diff:
                continue

            version = get_version(mod)
            build = "_".join(list(map(str, version)))
            ver = ".".join(list(map(str, list(version))))
            ver = ".".join(list(map(str, list(version))))
            adds = len([_ for _ in diff.splitlines() if _.startswith("+")])
            removes = len([_ for _ in diff.splitlines() if _.startswith("-")])

            m += f"🆕 <b>{mod} {ver}</b>: {adds} adds | {removes} removes\n"

            if c and c % 2 == 0:
                kb += [[]]

            c += 1

            kb[-1] += [
                {
                    "text": f"{mod} {ver}",
                    "callback": self.inline__start_push
                    if not bulk
                    else self.inline__start_bulk_push,
                    "args": (mod,) if not bulk else [],
                }
            ]

        if not m:
            m = "🎈 <b>Nothing to commit, working tree is clean as a diamond!</b>"
            kb = [
                [
                    {
                        "text": "🔄 Check again",
                        "callback": self.inline__get_working_tree,
                    },
                    {"text": "💢 Close", "callback": self.inline__close},
                ]
            ]

        return {
            "text": "🧑🏼‍⚖️ <i>Push, or not to push...</i>\n\n" + m,
            "reply_markup": kb,
        }

    def stop(self) -> None:
        if not hasattr(self, "_task") or not self._task:
            return

        self._task.cancel()

    async def client_ready(self, client, db) -> None:
        self.db = db
        self.client = client
        self._task = asyncio.ensure_future(self._pull_mods())
        self._handler = None

    async def on_unload(self) -> None:
        self.stop()

    async def process_commit_message(
        self, message: Message, call=None, mod=None
    ) -> None:
        commit = message.raw_text

        silent = False
        if "-s" in commit:
            commit = commit.replace(" -s", "")
            silent = True

        new_version = True
        if "-o" in commit:
            commit = commit.replace(" -o", "")
            new_version = False

        await message.delete()
        self.client.remove_event_handler(self._handler)

        ver = push(mod, confirm=False, new_version=new_version)
        await call.edit(
            f"🥳 <b>Pushed {mod} with version {ver}</b>",
            reply_markup=[
                [
                    {
                        "text": "🌳 Back to working tree",
                        "callback": self.inline__get_working_tree,
                    },
                    {"text": "💢 Close", "callback": self.inline__close},
                ]
            ],
        )

        if not silent:
            msg = (
                f"🆕 #new_mod: <b>{mod} {ver}</b>:\n{commit}"
                if ver == "1.0.0"
                else f"🆕 #mod_update: <b>{mod} {ver}</b>:\n{commit}"
            )

            await self.client.send_message("@hikari_log", msg)
            await self.client.send_message("@hikari_chat", msg)

    async def inline__get_push_message(self, call, mod):
        await call.answer(f"Enter commit message for {mod} in current chat")
        self._handler = functools.partial(
            self.process_commit_message, call=call, mod=mod
        )
        self.client.add_event_handler(
            self._handler,
            events.NewMessage(chats=[call.form["chat"]], outgoing=True, forwards=False),
        )

    async def inline__start_push(self, call, mod: str) -> None:
        await call.edit(
            text=push(mod),
            reply_markup=[
                [
                    {
                        "text": "📤 Push",
                        "callback": self.inline__get_push_message,
                        "args": (mod,),
                    },
                    {"text": "💢 Cancel", "callback": self.inline__get_working_tree},
                ]
            ],
        )

    async def process_bulk_commit_message(self, message: Message, call=None) -> None:
        commit = message.raw_text

        silent = False
        if "-s" in commit:
            commit = commit.replace(" -s", "")
            silent = True

        new_version = False
        if "-o" in commit:
            commit = commit.replace(" -o", "")
            new_version = True

        await message.delete()
        self.client.remove_event_handler(self._handler)

        m = "🥳 <b>Pushed mods</b>"
        s = "\n".join(
            [
                f"🆕 <b>{mod} {push(mod, confirm=False, new_version=new_version)}</b>"
                for mod in mods
                if get_diff(mod)
            ]
        )

        await call.edit(
            m + "\n" + s,
            reply_markup=[
                [
                    {
                        "text": "🌳 Back to working tree",
                        "callback": self.inline__get_working_tree,
                    },
                    {"text": "💢 Close", "callback": self.inline__close},
                ]
            ],
        )

        msg = f"🆕 #bulk_update: {commit}\n{s}"
        if not silent:
            await self.client.send_message("@hikari_log", msg)
            await self.client.send_message("@hikari_chat", msg)

    async def inline__get_bulk_push_message(self, call):
        await call.answer("Enter commit message for bulk push in current chat")
        self._handler = functools.partial(self.process_bulk_commit_message, call=call)
        self.client.add_event_handler(
            self._handler,
            events.NewMessage(chats=[call.form["chat"]], outgoing=True, forwards=False),
        )

    async def inline__start_bulk_push(self, call) -> None:
        await call.edit(
            text="\n".join(
                [push(mod, new_version=True) for mod in mods if get_diff(mod)]
            ),
            reply_markup=[
                [
                    {"text": "📤 Push", "callback": self.inline__get_bulk_push_message},
                    {"text": "💢 Cancel", "callback": self.inline__get_working_tree},
                ]
            ],
        )

    async def inline__close(self, call) -> None:
        await call.delete()

    async def inline__get_working_tree(self, call) -> None:
        await call.edit(**self.check_working_tree())

    async def pushcmd(self, message: Message) -> None:
        """Push with confirmation"""
        await self.inline.form(
            **self.check_working_tree(),
            message=message,
        )

    async def bulkpushcmd(self, message: Message) -> None:
        """Bulk push with confirmation"""
        await self.inline.form(
            **self.check_working_tree(bulk=True),
            message=message,
        )

    async def diffcmd(self, message: Message) -> None:
        """<mod> - Get mod code diff"""
        await utils.answer(
            message,
            "<code>"
            + utils.escape_html(get_diff(utils.get_args_raw(message)))
            + "</code>",
        )
