import asyncio
import os

import telegram


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
    def send_update_bulk(cls, updates):
        if not updates:
            raise ValueError(f"Bulk cannot be empty {updates=}")

        MESSAGE_START = (
            f"{updates[0].feed.title}\n"
            f"{updates[0].feed.json.region} [{updates[0].feed.json.tags}]\n"
            "\n"
        )
        MESSAGE_END = (
            "\n"
            "([EDIT](http://192.168.0.155:30011/feeds/{feed_id}/edit))"
        )

        message = ""
        message += MESSAGE_START
        for each in updates:
            message += f"- {each.title} - ([OPEN]({each.href}))"
        message += MESSAGE_END

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
