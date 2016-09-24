from time import strftime


class Reminder:

    def __init__(self):
        self.use_date = True # False = use timer
        self.reminder_date = None
        self.reminder_timer = None
        self.reminder_text = ''
        self.email_reminder = False
        self.email_address = ''

    def to_string(self):

        display = 'Reminder: ' + self.reminder_text + '\n'

        if self.use_date:
            display += \
                'At ' + self.reminder_date.strftime('%a, %d %b %Y %H:%M:%S') + '\n'
        else:
            display += 'In ' + \
                str(self.reminder_timer.seconds / 3600) + ' hours, ' +\
                str((self.reminder_timer.seconds % 3600) / 60) + ' minutes and ' +\
                str((self.reminder_timer.seconds % 3600) % 60) + ' seconds\n'

        if self.email_reminder:
            display += 'Email reminder: Yes\nEmail address: ' + self.email_address
        else:
            display += 'Email reminder: No'

        return display
