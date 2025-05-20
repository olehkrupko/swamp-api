import telegram
from telegram.helpers import escape_markdown as em

from config.settings import settings


class TelegramService:
    PARSE_MODE = "markdown"
    MESSAGE_MARKDOWN = (
        "{name}\n"
        "\n"
        "([OPEN]({href})) - ([EDIT](http://192.168.0.155:30011/feeds/{feed_id}/edit))"
    )

    @classmethod
    async def send_message(cls, msg):
        await telegram.Bot(settings.TELEGRAM_BOTTOKEN).sendMessage(
            parse_mode=cls.PARSE_MODE,
            chat_id=settings.TELEGRAM_CHATID,
            text=msg,
        )

    @classmethod
    async def send_feed_updates(cls, feed, updates):
        if settings.TELEGRAM_BROADCAST != "enabled":
            return
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
                await cls.send_message(
                    message,
                )
                message = ""

        message += f"\n([EDIT](http://192.168.0.155:30011/feeds/{feed._id}/edit))"

        await cls.send_message(
            message,
        )

    @classmethod
    async def send_update(cls, update):
        message = cls.MESSAGE_MARKDOWN.format(
            name=telegram.helpers.escape_markdown(update.name),
            href=telegram.helpers.escape_markdown(update.href),
            feed_id=str(int(update.feed_id)),
        )

        await cls.send_message(
            message,
        )
