import os

from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler


async def bot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm swamp-courier bot.")

def bot_builder():
    app = Application.builder().token(os.environ.get('TELEGRAM_BOT_TOKEN')).read_timeout(30).write_timeout(30).build()

    app.add_handler(CommandHandler('start', bot_start))

    app.run_polling()
    app.idle()

# not imported as there is no need in it for now
bot_builder()
