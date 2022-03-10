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

# meta title: Help
# meta pic: https://img.icons8.com/fluency/48/000000/chatbot.png
# meta desc: Help module, made specifically for GeekTG with <3


import inspect
from .. import loader, utils, main
import logging

from telethon.tl.types import Message

logger = logging.getLogger(__name__)


@loader.tds
class HelpMod(loader.Module):
    """Help module, made specifically for GeekTG with <3"""

    strings = {
        "name": "Help",
        "bad_module": "<b>🚫 <b>Module</b> <code>{}</code> <b>not found</b>",
        "single_mod_header": "📼 <b>{}</b>:",
        "single_cmd": "\n▫️ <code>{}{}</code> 👉🏻 ",
        "undoc_cmd": "🦥 No docs",
        "all_header": "👓 <b>{} mods available, {} hidden:</b>",
        "mod_tmpl": "\n{} <code>{}</code>",
        "first_cmd_tmpl": ": ( {}",
        "cmd_tmpl": " | {}",
        "args": "🚫 <b>Args are incorrect</b>",
        "set_cat": "ℹ️ <b>{} placed in category {}</b>",
        "no_mod": "🚫 <b>Specify module to hide</b>",
        "hidden_shown": "👓 <b>{} modules hidden, {} module shown:</b>\n{}\n{}",
        "ihandler": "\n🎹 <code>{}</code> 👉🏻 ",
        "undoc_ihandler": "🦥 No docs",
    }

    def get(self, *args) -> dict:
        return self.db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self.db.set(self.strings["name"], *args)

    async def helphidecmd(self, message: Message) -> None:
        """<module or modules> - Hide module(-s) from help
        *Split modules by spaces"""
        modules = utils.get_args(message)
        if not modules:
            await utils.answer(message, self.strings("no_mod"))
            return

        mods = [
            i.strings["name"]
            for i in self.allmodules.modules
            if hasattr(i, "strings") and "name" in i.strings
        ]

        modules = list(filter(lambda module: module in mods, modules))
        currently_hidden = self.get("hide", [])
        hidden, shown = [], []
        for module in modules:
            if module in currently_hidden:
                currently_hidden.remove(module)
                shown += [module]
            else:
                currently_hidden += [module]
                hidden += [module]

        self.set("hide", currently_hidden)

        await utils.answer(
            message,
            self.strings("hidden_shown").format(
                len(hidden),
                len(shown),
                "\n".join([f"👁‍🗨 <i>{m}</i>" for m in hidden]),
                "\n".join([f"👁 <i>{m}</i>" for m in shown]),
            ),
        )

    @loader.unrestricted
    async def helpcmd(self, message: Message) -> None:
        """[module] [-f] - Show help"""
        args = utils.get_args_raw(message)
        force = False
        if "-f" in args:
            args = args.replace(" -f", "").replace("-f", "")
            force = True

        prefix = utils.escape_html(
            (self.db.get(main.__name__, "command_prefix", False) or ".")[0]
        )

        if args:
            module = None
            for mod in self.allmodules.modules:
                if mod.strings("name", message).lower() == args.lower():
                    module = mod

            if module is None:
                args = args.lower()
                args = args[1:] if args.startswith(prefix) else args
                if args in self.allmodules.commands:
                    module = self.allmodules.commands[args].__self__
                else:
                    await utils.answer(message, self.strings("bad_module").format(args))
                    return

            try:
                name = module.strings("name")
            except KeyError:
                name = getattr(module, "name", "ERROR")

            reply = self.strings("single_mod_header").format(utils.escape_html(name))
            if module.__doc__:
                reply += (
                    "<i>\nℹ️ " + utils.escape_html(inspect.getdoc(module)) + "\n</i>"
                )

            commands = {
                name: func
                for name, func in module.commands.items()
                if await self.allmodules.check_security(message, func)
            }

            if hasattr(module, "inline_handlers"):
                inline_handlers = {
                    name: func for name, func in module.inline_handlers.items()
                }
                for name, fun in inline_handlers.items():
                    reply += self.strings("ihandler", message).format(
                        f"@{self.inline._bot_username} {name}"
                    )

                    if fun.__doc__:
                        reply += utils.escape_html(
                            "\n".join(
                                [
                                    line.strip()
                                    for line in inspect.getdoc(fun).splitlines()
                                    if not line.strip().startswith("@")
                                ]
                            )
                        )
                    else:
                        reply += self.strings("undoc_ihandler", message)

            for name, fun in commands.items():
                reply += self.strings("single_cmd").format(prefix, name)
                if fun.__doc__:
                    reply += utils.escape_html(inspect.getdoc(fun))
                else:
                    reply += self.strings("undoc_cmd")

            await utils.answer(message, reply)
            return

        count = 0
        for i in self.allmodules.modules:
            try:
                if i.commands or i.inline_handlers:
                    count += 1
            except Exception:
                pass

        mods = [
            i.strings["name"]
            for i in self.allmodules.modules
            if hasattr(i, "strings") and "name" in i.strings
        ]

        hidden = list(filter(lambda module: module in mods, self.get("hide", [])))
        self.set("hide", hidden)

        reply = self.strings("all_header").format(count, len(hidden))
        shown_warn = False
        cats = {}

        for mod_name, cat in self.db.get("Help", "cats", {}).items():
            if cat not in cats:
                cats[cat] = []

            cats[cat].append(mod_name)

        # logger.info(cats)

        help_ = []

        for mod in self.allmodules.modules:
            if not hasattr(mod, "commands"):
                logger.error(f"Module {mod.__class__.__name__} is not inited yet")
                continue

            if mod.strings["name"] in self.get("hide", []):
                continue

            tmp = ""

            try:
                name = mod.strings["name"]
            except KeyError:
                name = getattr(mod, "name", "ERROR")

            inline = (
                hasattr(mod, "callback_handlers")
                and mod.callback_handlers
                or hasattr(mod, "inline_handlers")
                and mod.inline_handlers
            )

            for cmd_ in mod.commands.values():
                try:
                    "self.inline.form(" in inspect.getsource(cmd_.__code__)
                except Exception:
                    pass

            core = mod.__origin__ == "<file>"

            if core:
                emoji = "▪️"
            elif inline:
                emoji = "🕶"
            else:
                emoji = "▫️"

            tmp += self.strings("mod_tmpl").format(emoji, name)

            first = True

            commands = [
                name
                for name, func in mod.commands.items()
                if await self.allmodules.check_security(message, func) or force
            ]

            for cmd in commands:
                if first:
                    tmp += self.strings("first_cmd_tmpl").format(cmd)
                    first = False
                else:
                    tmp += self.strings("cmd_tmpl").format(cmd)

            icommands = [
                name
                for name, func in mod.inline_handlers.items()
                if self.inline._check_inline_security(func, message.sender_id) or force
            ]

            for cmd in icommands:
                if first:
                    tmp += self.strings("first_cmd_tmpl").format(f"🎹 {cmd}")
                    first = False
                else:
                    tmp += self.strings("cmd_tmpl").format(f"🎹 {cmd}")

            if commands or icommands:
                tmp += " )"
                if inline:
                    help_ += [tmp]
                else:
                    help_ = [tmp] + help_
            elif not shown_warn and (mod.commands or mod.inline_handlers):
                reply = (
                    "<i>You have permissions to execute only this commands</i>\n"
                    + reply
                )
                shown_warn = True

        await utils.answer(message, f"{reply}\n{''.join(help_)}")

    async def client_ready(self, client, db) -> None:
        self.client = client
        self.is_bot = await client.is_bot()
        self.db = db
