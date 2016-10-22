from datetime import datetime, timedelta
import uuid

class Reminder:

    def __init__(self):
        self.use_date = True # False = use timer
        self.reminder_date = None
        self.reminder_timer = None
        self.reminder_text = ''
        self.email_reminder = False
        self.email_address = ''
        self.created = datetime.now()
        self.id = uuid.uuid1()

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

    def to_string_active(self):

        display = 'Reminder: ' + self.reminder_text + '\n'

        if self.use_date:
            due = int((self.reminder_date - datetime.today()).total_seconds())
        else:
            due_date = self.created + self.reminder_timer
            due = int((due_date - datetime.today()).total_seconds())

        display += 'In ' + \
                   str(int(due / 3600)) + ' hours, ' + \
                   str(int((due % 3600) / 60)) + ' minutes and ' + \
                   str(int((due % 3600) % 60)) + ' seconds\n'

        if self.email_reminder:
            display += 'Email reminder: Yes\nEmail address: ' + self.email_address
        else:
            display += 'Email reminder: No'

        return display

    def is_empty(self):
        return (self.use_date == True and
                self.reminder_date == None and
                self.reminder_timer == None and
                self.reminder_text == '' and
                self.email_reminder == False and
                self.email_address == '')