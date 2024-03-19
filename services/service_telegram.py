import asyncio
import os

import telegram

# from telegram import Update
# from telegram.ext import Application, ContextTypes, CommandHandler


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


# async def bot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await context.bot.send_message(
#         chat_id=update.effective_chat.id,
#         text="I'm swamp-courier bot.",
#     )


# def bot_builder():
#     app = (
#         Application.builder()
#         .token(os.environ.get("TELEGRAM_BOT_TOKEN"))
#         .read_timeout(30)
#         .write_timeout(30)
#         .build()
#     )

#     app.add_handler(CommandHandler("start", bot_start))

#     app.run_polling()
#     app.idle()


# # not imported as there is no need in it for now
# bot_builder()
