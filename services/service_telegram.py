import asyncio
import os

import telegram
from telegram.helpers import escape_markdown as em


class TelegramService:
    CHAT_ID = os.environ.get("TELEGRAM_BOT_DMS")
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    PARSE_MODE = "markdown"
    MESSAGE_MARKDOWN = (
        "{name}\n"
        "\n"
        "([OPEN]({href})) - ([EDIT](http://192.168.0.155:30011/feeds/{feed_id}/edit))"
    )

    @classmethod
    async def send_message(cls, msg):
        await telegram.Bot(cls.TOKEN).sendMessage(
            parse_mode=cls.PARSE_MODE,
            chat_id=cls.CHAT_ID,
            text=msg,
        )

    @classmethod
    def send_update_bulk(cls, updates, feed):
        if not updates:
            raise ValueError(f"Bulk cannot be empty {updates=}")

        tags = [f"#{x}" for x in feed.json.get("tags", [])]
        tags = "[" + ", ".join(tags) + "]"

        # plaintext section
        message = em(feed.title) + "\n"
        message += f"➤ {em(tags)}\n"
        message += "➤ " + em(feed.json.get("region", "region unknown")) + "\n"
        for each in updates:
            message += (
                f"\n➤ [(OPEN)]({each.href}) {em(each.name.replace('@', '[at]'))}\n"
            )
            # cutting big messages and avoiding footer being sent alone
            if len(message) > 2000 and each != updates[-1]:
                asyncio.run(
                    cls.send_message(
                        message,
                    )
                )
                message = ""

        message += f"\n([EDIT](http://192.168.0.155:30011/feeds/{feed._id}/edit))"

        asyncio.run(
            cls.send_message(
                message,
            )
        )

    @classmethod
    def send_update(cls, update):
        message = cls.MESSAGE_MARKDOWN.format(
            name=telegram.helpers.escape_markdown(update.name),
            href=telegram.helpers.escape_markdown(update.href),
            feed_id=str(int(update.feed_id)),
        )

        asyncio.run(
            cls.send_message(
                message,
            )
        )
