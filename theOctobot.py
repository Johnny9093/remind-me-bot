# coding=utf-8
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Job, CallbackQueryHandler
import logging, re

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Hi!')


def help(bot, update):
    bot.sendMessage(update.message.chat_id,
                    text='/help - Show this message.\n'
                         '/set - Set a timer for your wanted number of seconds.\n'
                         '/unset - Cancel last timer.\n'
                         '\n'
                         'You can also use me for echo! Just type a message and i\'ll reply.')


def echo(bot, update):

    msgtxt = unicode(update.message.text).lower()

    # remove the 'remind me' part and get the reminder text.
    text = re.sub(ur"^remind me to\s|^remindme\s|^הזכר לי\s|^תזכיר לי\s", '', msgtxt)

    text = 'You said: ' + text
    bot.sendMessage(update.message.chat_id, text=text)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))

def alarm(bot, job):
    """Function to send the alarm message"""
    bot.sendMessage(job.context, text='Beep!')


def set(bot, update, args, job_queue):
    """Adds a job to the queue"""
    chat_id = update.message.chat_id

    try:
        # args[0] should contain the time for the timer in seconds
        due = int(args[0])
        if due < 0:
            bot.sendMessage(chat_id, text='Sorry we can not go back to future!')
            return

        # Add job to queue
        job = Job(alarm, due, repeat=False, context=chat_id)
        timers[chat_id] = job
        job_queue.put(job)

        bot.sendMessage(chat_id, text='Timer successfully set!')

    except (IndexError, ValueError):
        bot.sendMessage(chat_id, text='Usage: /set <seconds>')

def unset(bot, update, job_queue):
    """Removes the job if the user changed their mind"""
    chat_id = update.message.chat_id

    if chat_id not in timers:
        bot.sendMessage(chat_id, text='You have no active timer')
        return

    job = timers[chat_id]
    job.schedule_removal()
    del timers[chat_id]

    bot.sendMessage(chat_id, text='Timer successfully unset!')

def keyboard_test(bot, update):
    keyboard = [[InlineKeyboardButton("Option 1", callback_data='1'),
                 InlineKeyboardButton("Option 2", callback_data='2')],
                [InlineKeyboardButton("Option 3", callback_data='3')]]

    reply_markup = InlineKeyboardMarkup(keyboard)

    bot.sendMessage(update.message.chat_id, text="Please choose:", reply_markup=reply_markup)

def button(bot, update):
    query = update.callback_query

    bot.editMessageText(text="Selected option: %s" % query.data,
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id)

def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater(BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("set", set, pass_args=True, pass_job_queue=True))
    dp.add_handler(CommandHandler("unset", unset, pass_job_queue=True))
    dp.add_handler(CommandHandler("k", keyboard_test))
    dp.add_handler(CallbackQueryHandler(button))

    # on noncommand i.e message - echo the message on Telegram
    dp.add_handler(MessageHandler([Filters.text], echo))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

timers = dict()
remind_me_keys = [u'הזכר לי', u'תזכיר לי', u'remind me']

if __name__ == '__main__':
    main()
