"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    © Copyright 2022 t.me/hikariatama
    Licensed under CC BY-NC-ND 4.0

    🌐 https://creativecommons.org/licenses/by-nc-nd/4.0
"""

# meta pic: https://img.icons8.com/external-vitaliy-gorbachev-flat-vitaly-gorbachev/58/000000/external-poll-infographic-elements-vitaliy-gorbachev-flat-vitaly-gorbachev.png
# meta developer: @hikariatama
# requires: matplotlib

from .. import loader, utils
from telethon.tl.types import Message
import logging
import matplotlib.pyplot as plt
import io


logger = logging.getLogger(__name__)


@loader.tds
class PollPlotMod(loader.Module):
    """Visualises polls as plots"""

    strings = {
        "name": "PollPlot",
        "no_reply": "🚫 <b>Reply to a poll is required!</b>",
        "no_answers": "😔 <b>This poll has not answers yet.</b>",
    }

    def get(self, *args) -> dict:
        return self._db.get(self.strings["name"], *args)

    def set(self, *args) -> None:
        return self._db.set(self.strings["name"], *args)

    async def client_ready(self, client, db) -> None:
        self._db = db
        self._client = client

    async def plotcmd(self, message: Message) -> None:
        """<reply> - Create plot from poll"""
        reply = await message.get_reply_message()
        if not reply or not getattr(reply, "poll", False):
            await utils.answer(message, self.strings("no_reply"))
            return

        sizes = [i.voters for i in reply.poll.results.results]

        if not sum(sizes):
            await utils.answer(message, self.strings("no_answers"))
            return

        labels = [
            f"{a.text} [{sizes[i]}] ({round(sizes[i] / sum(sizes) * 100, 1)}%)"
            for i, a in enumerate(reply.poll.poll.answers)
        ]

        explode = [0.05] * len(sizes)
        fig1, ax1 = plt.subplots()
        ax1.pie(
            sizes,
            explode=explode,
            labels=labels,
            textprops={"color": "white", "size": "large"},
        )
        buf = io.BytesIO()
        fig1.patch.set_facecolor("#303841")
        fig1.savefig(buf)
        buf.seek(0)

        await self._client.send_file(message.peer_id, buf.getvalue(), reply_to=reply)

        if message.out:
            await message.delete()
