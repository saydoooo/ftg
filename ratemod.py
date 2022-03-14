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

# meta pic: https://img.icons8.com/fluency/48/000000/heart-with-pulse.png
# meta developer: @hikariatama

from .. import loader, utils
import requests
import re
import hashlib
from telethon.tl.types import Message

URL_REGEX = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"


@loader.tds
class RateModuleMod(loader.Module):
    """Rates module and suggests fixes"""

    strings = {
        "name": "RateMod",
        "template": "👮‍♂️ <b>Mode rating </b><code>{}</code><b>:</b>\n{} {} <b>[{}]</b>\n\n{}",
        "no_file": "<b>What should I check?... 🗿</b>",
        "cannot_check_file": "<b>Check error</b>",
    }

    async def client_ready(self, client, db):
        self.client = client
        self.db = db

    @loader.unrestricted
    async def ratemodcmd(self, message: Message) -> None:
        """<reply_to_file|file|link> - Rate code"""
        args = utils.get_args_raw(message)
        reply = await message.get_reply_message()
        if (
            not reply
            and not getattr(reply, "media", None)
            and not getattr(message, "media", None)
            and not args
            and not re.match(URL_REGEX, args)
        ):
            return await utils.answer(message, self.strings("no_file"))

        checking = (
            getattr(reply, "media", None)
            if getattr(reply, "media", None) is not None
            else (
                getattr(message, "media", None)
                if getattr(message, "media", None) is not None
                else (args if args and re.match(URL_REGEX, args) else 0)
            )
        )
        if type(checking) is int:
            return await utils.answer(message, self.strings("no_file"))

        if type(checking) is not str:
            try:
                file = await self.client.download_file(
                    getattr(reply, "media", None)
                    if getattr(reply, "media", None) is not None
                    else getattr(message, "media", None)
                )
            except:
                return await utils.answer(
                    message, self.strings("cannot_check_file", message)
                )

            try:
                code = file.decode("utf-8").replace("\r\n", "\n")
            except:
                return await utils.answer(
                    message, self.strings("cannot_check_file", message)
                )

        else:
            try:
                code = (await utils.run_sync(requests.get, args)).text
            except:
                return await utils.answer(
                    message, self.strings("cannot_check_file", message)
                )

        try:
            mod_name = re.search(
                r"""strings[ ]*=[ ]*{.*?name['"]:[ ]*['"](.*?)['"]""", code, flags=re.S
            ).group(1)
        except:
            mod_name = "Unknown"

        import_regex = [
            r"^[^#]rom ([^\n\r]*) import [^\n\r]*$",
            r"^[^#]mport ([^\n\r]*)[^\n\r]*$",
            r"""__import__[(]['"]([^'"]*)['"][)]""",
        ]
        imports = [
            re.findall(import_re, code, flags=re.M | re.DOTALL)
            for import_re in import_regex
        ]

        if ".." in imports:
            del imports[imports.index("..")]

        splitted = [
            _
            for _ in list(
                zip(
                    list(
                        map(
                            lambda x: len(re.findall(r"[ \t]+(if|elif|else).+:", x)),
                            re.split(r"[ \t]*async def .*?cmd\(", code),
                        )
                    ),
                    [""] + re.findall(r"[ \t]*async def (.*?)cmd\(", code),
                )
            )
            if _[0] > 10
        ]

        comments = ""

        score = 4.6
        if len(imports) > 10:
            comments += f"🔻 <code>{{-0.1}}</code> <b>A lot of imports ({len(imports)}) </b><i>[memory]</i>\n"
            score -= 0.1
        if "requests" in imports and "utils.run_sync" not in code:
            comments += (
                "🔻 <code>{-0.5}</code> <b>Sync requests</b> <i>[blocks runtime]</i>\n"
            )
            score -= 0.5
        if "while True" in code or "while 1" in code:
            comments += (
                "🔻 <code>{-0.1}</code> <b>While true</b> <i>[block runtime*]</i>\n"
            )
            score -= 0.1
        if ".edit(" in code:
            comments += "🔻 <code>{-0.3}</code> <b>Classic message.edit</b> <i>[no twink support]</i>\n"
            score -= 0.3
        if re.search(r"@.*?[bB][oO][tT]", code) is not None:
            bots = " | ".join(re.findall(r"@.*?[bB][oO][tT]", code))
            comments += f"🔻 <code>{{-0.2}}</code> <b>Bot-abuse (</b><code>{bots}</code><b>)</b> <i>[module will die some day]</i>\n"
            score -= 0.2
        if re.search(r'[ \t]+async def .*?cmd.*\n[ \t]+[^\'" \t]', code) is not None:
            undoc = " | ".join(
                list(re.findall(r'[ \t]+async def (.*?)cmd.*\n[ \t]+[^" \t]', code))
            )

            comments += f"🔻 <code>{{-0.4}}</code> <b>No docs (</b><code>{undoc}</code><b>)</b> <i>[all commands must be documented]</i>\n"
            score -= 0.4
        if "time.sleep" in code or "from time import sleep" in code:
            comments += "🔻 <code>{-2.0}</code> <b>Sync sleep (</b><code>time.sleep</code><b>) replace with (</b><code>await asyncio.sleep</code><b>)</b> <i>[blocks runtime]</i>\n"
            score -= 2
        if [_ for _ in code.split("\n") if len(_) > 300]:
            ll = max(len(_) for _ in code.split("\n") if len(_) > 300)
            comments += f"🔻 <code>{{-0.1}}</code> <b>Long lines ({ll})</b> <i>[PEP violation]</i>\n"
            score -= 0.1
        if re.search(r'[\'"] ?\+ ?.*? ?\+ ?[\'"]', code) is not None:
            comments += "🔻 <code>{-0.1}</code> <b>Avoiding f-строк</b> <i>[causes problems]</i>\n"
            score -= 0.1
        if splitted:
            comments += f"🔻 <code>{{-0.2}}</code> <b>Big 'if' trees (</b><code>{' | '.join([f'{chain} в {fun}' for chain, fun in splitted])}</code><b>)</b> <i>[readability]</i>\n"
            score -= 0.2
        if "== None" in code or "==None" in code:
            comments += "🔻 <code>{-0.3}</code> <b>Type comparsation via ==</b> <i>[google it]</i>\n"

            score -= 0.3
        if "is not None else" in code:
            comments += "🔻 <code>{-0.1}</code> <b>Unneccessary ternary operator usage (</b><code>if some_var is not None else another</code> <b>-></b> <code>some_var or another</code><b>)</b> <i>[readability]</i>\n"

            score -= 0.1
        if "utils.answer" in code and ".edit(" not in code:
            comments += (
                "🔸 <code>{+0.3}</code> <b>utils.answer</b> <i>[twinks support]</i>\n"
            )
            score += 0.3
        if re.search(r'[ \t]+async def .*?cmd.*\n[ \t]+[^\'" \t]', code) is None:
            comments += "🔸 <code>{+0.3}</code> <b>Docs</b> <i>[all commands are documented]</i>\n"
            score += 0.3
        if "requests" in imports and "utils.run_sync" in code or "aiohttp" in imports:
            comments += "🔸 <code>{+0.3}</code> <b>Async requests</b> <i>[do not stop runtime]</i>\n"
            score += 0.3

        api_endpoint = "https://mods.hikariatama.ru/check?hash="
        sha1 = hashlib.sha1()
        sha1.update(code.encode("utf-8"))
        try:
            check_res = (
                await utils.run_sync(requests.get, api_endpoint + str(sha1.hexdigest()))
            ).text
        except:
            check_res = ""

        if check_res in {"yes", "db"}:
            comments += (
                "🔸 <code>{+1.0}</code> <b>Module is verified</b> <i>[no scam]</i>\n"
            )
            score += 1.0

        score = round(score, 1)

        score = min(score, 5.0)
        await utils.answer(
            message,
            self.strings("template").format(
                mod_name,
                "⭐️" * round(score),
                score,
                ["Shit", "Bad", "Poor", "Normal", "Ok", "Good"][round(score)],
                comments,
            ),
        )
