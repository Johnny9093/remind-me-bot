#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from reminder import Reminder
from telegram import (ReplyKeyboardMarkup, ReplyKeyboardHide)
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
                          ConversationHandler, Job, JobQueue)
import logging, re, os

# Enable logging
logging.basicConfig(filename='log.txt',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

EDIT, REDIRECT_REMINDER, REDIRECT_SETTING, SET_TIMER, CHOOSE_DAY, CHOOSE_TIME, ACTIVATE_TIMER = range(7)

current_reminder = Reminder()
active_reminders = []


def error(bot, update, error):
    logger.error('Update "%s" caused error "%s"' % (update, error))

    bot.sendMessage(update.message.chat_id,
                    text='An error has occurred. Please retry.',
                    reply_markup=ReplyKeyboardHide())

    return -1 # end conversation


def set_reminder(bot, update):

    global current_reminder
    current_reminder = Reminder()

    msgtxt = unicode(update.message.text).lower()

    # remove the 'remind me' part and get the reminder text.
    text = re.sub(ur"^remind me to\s|^remindme\s|^הזכר לי\s|^תזכיר לי\s", '', msgtxt)

    # user asked for a reminder
    bot.sendMessage(update.message.chat_id,
                    text='Confirm reminder message:\n' + text,
                    reply_markup=ReplyKeyboardMarkup([['Ok', 'Edit']],
                                                     one_time_keyboard=True))

    current_reminder.reminder_text = text

    return REDIRECT_REMINDER


def redirect_reminder(bot, update):

    if update.message.text == 'Ok':

        bot.sendMessage(update.message.chat_id, text='Great!', reply_markup=ReplyKeyboardHide())
        return choose_time_setting(bot, update)

    elif update.message.text == 'Edit':

        bot.sendMessage(update.message.chat_id, text='No problem!\nJust enter a new message.',
                        reply_markup=ReplyKeyboardHide())
        return EDIT

    else:

        bot.sendMessage(update.message.chat_id,
                        text='Please enter one of these values:\n\nOk\nEdit',
                        reply_markup=ReplyKeyboardHide())
        return set_reminder(bot, update)


def choose_time_setting(bot, update):
    reply_keyboard = [['Specific time', 'Timer']]

    bot.sendMessage(update.message.chat_id,
                    text='Please choose a time setting.',
                    reply_markup=ReplyKeyboardMarkup(reply_keyboard,
                                                     one_time_keyboard=True))

    return REDIRECT_SETTING


def redirect_setting(bot, update):

    if update.message.text == 'Specific time':

        bot.sendMessage(update.message.chat_id, text='When do you wish to be reminded?',
                        reply_markup=ReplyKeyboardHide())
        return set_specific(bot, update)

    elif update.message.text == 'Timer':

        bot.sendMessage(update.message.chat_id, text='How long should I wait?\n'
                                                     'Please enter an amount in the following format:\n<number><s|m|h> (i.e. 30s)',
                        reply_markup=ReplyKeyboardHide())
        return SET_TIMER

    else:
        bot.sendMessage(update.message.chat_id,
                        text='Please enter one of these values:\n\nSpecific time\nTimer',
                        reply_markup=ReplyKeyboardHide())
        return choose_time_setting(bot, update)


def set_specific(bot, update):

    current_reminder.use_date = True

    bot.sendMessage(update.message.chat_id,
                    text='Choose a day from the menu, or enter a date in a DD/MM[/YY] format.',
                    reply_markup=ReplyKeyboardMarkup([['Today', 'Tomorrow']],
                                                     one_time_keyboard=True))

    return CHOOSE_DAY


def choose_day(bot, update):

    global current_reminder

    full_date_re = re.compile('^(\d{2}\/\d{2}\/\d{2})$')
    partial_date_re = re.compile('^(\d{2}\/\d{2})$')

    if update.message.text == 'Today':
        date = datetime.today()

    elif update.message.text == 'Tomorrow':
        date = datetime.today() + timedelta(days=1)

    elif full_date_re.match(update.message.text):
        date = datetime.strptime(update.message.text, '%d/%m/%y')

    elif partial_date_re.match(update.message.text):
        date = datetime.strptime(update.message.text, '%d/%m')
        date.replace(year=datetime.today().year)

    current_reminder.reminder_date = date

    bot.sendMessage(update.message.chat_id,
                    text='Next, please enter a time in the following format: HH:MM.',
                    reply_markup=ReplyKeyboardHide())
    return CHOOSE_TIME


def choose_time(bot, update):

    global current_reminder

    time = datetime.strptime(update.message.text, '%H:%M')
    current_reminder.reminder_date = current_reminder.reminder_date.replace(hour=time.hour,
                                                                            minute=time.minute,
                                                                            second=0,
                                                                            microsecond=0)

    # register reminder and set timer
    bot.sendMessage(update.message.chat_id,
                    'Details:\n' + current_reminder.to_string(),
                    reply_markup=ReplyKeyboardMarkup([['Set it up!']],
                                                     one_time_keyboard=True))

    return ACTIVATE_TIMER


def set_timer(bot, update):

    global current_reminder

    current_reminder.use_date = False

    timer_type = update.message.text[-1]
    amount = int(update.message.text[:-1])

    if timer_type == 's':
        timer = timedelta(seconds=amount)
    elif timer_type == 'm':
        timer = timedelta(minutes=amount)
    elif timer_type == 'h':
        timer = timedelta(hours=amount)

    current_reminder.reminder_timer = timer

    # register reminder and set timer
    bot.sendMessage(update.message.chat_id,
                    'Details:\n' + current_reminder.to_string(),
                    reply_markup=ReplyKeyboardMarkup([['Set it up!']],
                                                     one_time_keyboard=True))

    return ACTIVATE_TIMER


def activate_timer(bot, update, job_queue):

    global active_reminders

    if current_reminder.use_date:
        due = int((current_reminder.reminder_date - datetime.today()).total_seconds())
    else:
        due = current_reminder.reminder_timer.total_seconds()

    if due < 0:
        bot.sendMessage(update.message.chat_id,
                        text='This reminder was set in the past; Please enter a valid value next time.',
                        reply_markup=ReplyKeyboardHide())
        return -1 # end conversation
        #  or just return SET_TIMER again? but i would need to remember the decision for which time setting to use

    # Add job to queue
    job = create_job(current_reminder, update, due)
    job_queue.put(job)

    active_reminders.append(current_reminder)

    logger.info('Added new reminer:\n%s' % current_reminder.to_string())

    bot.sendMessage(update.message.chat_id,
                    text='Reminder successfully set!',
                    reply_markup=ReplyKeyboardHide())

    return -1 # end conversation


def reminder_alarm(bot, job):

    global active_reminders

    bot.sendMessage(job.context['chat_id'],
                    text='Reminding you to ' + job.context['message'],
                    reply_markup=ReplyKeyboardHide())

    active_reminders = [reminder for reminder in active_reminders if reminder.id != job.context['reminder_id']]


def cancel(bot, update):
    global current_reminder
    if not current_reminder.is_empty():
        bot.sendMessage(update.message.chat_id, text='Reminder cancelled.',
                        reply_markup=ReplyKeyboardHide())
        current_reminder = Reminder()
    else:
        bot.sendMessage(update.message.chat_id, text='There is no active reminder.',
                        reply_markup = ReplyKeyboardHide())

    return -1 # end conversation


def show_actives(bot, update):
    global active_reminders

    if len(active_reminders) == 0:
        bot.sendMessage(update.message.chat_id, text='There are no active reminders.')
        return

    all = str(len(active_reminders)) + ' reminders:\n'

    for i in range(len(active_reminders)):
        all += str(i+1) + ') ' + active_reminders[i].to_string_active() + '\n'

    bot.sendMessage(update.message.chat_id, text=all)


def bot_help(bot, update):
    bot.sendMessage(update.message.chat_id,
                    text='Hello!\nI am Remind Me Bot. Use me to set up reminders!\n\n'
                         'To set up a new reminder, simply ask me to remind you!\n'
                         'i.e Remind me to take out the trash\n\n'
                         'Commands:\n'
                         '/help - show help message\n'
                         '/cancel - cancels current reminder\n'
                         '/active - show all active reminders\n'
                         '/stop - stop specific reminder (i.e. /stop 2 stops reminder number 2)')


def create_job(reminder, update, due):
    return Job(reminder_alarm, due, repeat=False, context=dict(chat_id=update.message.chat_id,
                                                               message=reminder.reminder_text,
                                                               reminder_id=reminder.id))


def stop_reminder(bot, update, args, job_queue):

    global active_reminders

    try:
        request = int(args[0])

    except ValueError:
        bot.sendMessage(update.message.chat_id,
                        text='Please enter a valid reminder number.',
                        reply_markup=ReplyKeyboardHide())
        return -1

    if request < 0 or request > len(active_reminders):
        bot.sendMessage(update.message.chat_id,
                        text='Please enter a valid reminder number.',
                        reply_markup=ReplyKeyboardHide())
        return -1

    id = active_reminders[request - 1].id
    [job for job in list(job_queue.jobs()) if job.context['reminder_id'] == id][0].schedule_removal()
    active_reminders = [reminder for reminder in active_reminders if reminder.id != id]

    bot.sendMessage(update.message.chat_id,
                    text='Reminder %d stopped.' % request,
                    reply_markup=ReplyKeyboardHide())


def main():
    # creating main event handler
    updater = Updater("291734070:AAG0u_LMBw9UdKmaAX1LqtDcLDTuWbUjCq4")

    # getting dispatcher to register handlers
    dp = updater.dispatcher

    # command handlers
    help = CommandHandler('help', bot_help)
    show = CommandHandler('active', show_actives)
    stop = CommandHandler('stop', stop_reminder, pass_args=True, pass_job_queue=True)

    # main conversation handler
    conv_handler = ConversationHandler(
        entry_points=[RegexHandler(u'^remind me to\s|^remindme\s|^הזכר לי\s|^תזכיר לי\s', set_reminder)],

        states={
            EDIT: [MessageHandler([Filters.text], set_reminder)],

            REDIRECT_REMINDER: [RegexHandler('^(Edit|Ok)$', redirect_reminder)],

            REDIRECT_SETTING: [RegexHandler('^(Specific time|Timer)$', redirect_setting)],

            SET_TIMER: [RegexHandler('^(\d+s|\d+m|\d+h)$', set_timer)],

            CHOOSE_DAY: [MessageHandler([Filters.text], choose_day)],

            CHOOSE_TIME: [RegexHandler('(\d{2}:\d{2})', choose_time)],

            ACTIVATE_TIMER: [RegexHandler('^(Set it up!)$', activate_timer, pass_job_queue=True)]
        },

        fallbacks=[CommandHandler('cancel', cancel)]
    )

    conv_handler.allow_reentry = True

    # registering handlers
    dp.add_handler(conv_handler)
    dp.add_handler(help)
    dp.add_handler(show)
    dp.add_handler(stop)

    # log all errors
    dp.add_error_handler(error)

    # starting bot
    updater.start_polling()

    # running bot
    updater.idle()

if __name__ == '__main__':
    main()