import requests
from bs4 import BeautifulSoup, NavigableString
import datetime
import re
import os
import time
from schedule import Scheduler
import pickle
import threading


class Lunchy(object):
    '''
    A docstring documenting this bot.
    '''
    JOBSFILE = 'jobs.p'

    def initialize(self, bot_handler):
        self.load_jobs(bot_handler)

    def __init__(self):
        self.schedule = Scheduler()
        self.cease_continuous_run = self.run_continously()

    def load_jobs(self, bot_handler):
        if os.path.isfile(self.JOBSFILE):
            with open('jobs.p', 'rb') as f:
                jobs = pickle.load(f)
                # jobs = bot_handler.storage.get('jobs')

                for (t, id) in jobs:
                    self.schedule.every().day.at(t).do(
                        lambda: bot_handler.send_message(dict(
                            type=id[0],  # can be 'stream' or 'private'
                            to=id[1],  # either the stream name or user's email
                            subject=id[2],  # message subject
                            content=self.menu(),  # content of the sent message
                        ))).tag(id)
                    print("Job file loaded!")

    def save_jobs(self, bot_handler):
        l = [(j.at_time.strftime('%H:%M'), list(j.tags)[0]) for j in self.schedule.jobs]
        # bot_handler.storage.put('jobs', l)
        pickle.dump(l, open(self.JOBSFILE, "wb"))

    def run_continously(self, interval=1):
        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease_continuous_run.is_set():
                    self.schedule.run_pending()
                    time.sleep(interval)

        continuous_thread = ScheduleThread()
        continuous_thread.start()
        return cease_continuous_run

    def tag(self):
        lst = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
        return lst[datetime.datetime.today().weekday()]

    def salonwichtig(self):
        print('Parsing facebook.com/salonwichtig')
        page = requests.get('https://www.facebook.com/salonwichtig')

        soup = BeautifulSoup(page.text, 'html.parser')
        timestamp = soup.find_all("span", attrs={"class": "timestampContent"})

        last = [t for t in timestamp if re.match('\d+ Std', t.text)]

        if last:
            p = last[0].find_parent("div", attrs={"class": None}).find_parent("div", attrs={"class": None})
            pars = p.find_all('p')

            all = ''
            for p in pars:
                all += p.text

            lines = all.split('#')

            if len(lines) >= 2:
                return lines[2:-1]
            else:
                return lines

        else:
            return []

    def teigware(self):
        print('Parsing teigware.at')

        page = requests.get('http://www.teigware.at/')

        soup = BeautifulSoup(page.text, 'html.parser')
        elem = soup.find("table", attrs={"cellpadding": "8"})
        text = []

        def clean(s):
            return ' '.join(s.split())

        for r in elem.find_all('tr'):
            row = [c.text.strip() for c in r.find_all('td') if c.text.strip()]

            if re.search(self.tag(), row[0], flags=re.IGNORECASE):

                if row[1].isupper():
                    text = ['Geschlossen']
                    break

                text.append('{} - *{}*'.format(clean(row[1]), '€5,80'))
                text.append('{} - *{}*'.format(clean(row[2]), '€6,80'))

        return text

    def feinessen(self):
        print('Parsing feinessen.at')

        page = requests.get('http://www.feinessen.at/')

        soup = BeautifulSoup(page.text, 'html.parser')
        elem = soup.find("div", attrs={"id": "vbid-424badbc-rraljy31"})

        text = []

        # create separated list of items on page
        def br_list(node):
            list = []
            current = ''

            for c in node.find_all():

                if c.name == 'br':
                    list.append(current)
                    current = ''

                elif type(c.next) == NavigableString:
                    
                    if c.string and c.string.startswith('__'):
                        list.append(current)
                        current = ''
                    else:
                        current += str(c.string)

                        if c.find_parent(name='h3'):
                            list.append(current)
                            current = ''

            list.append(current)
            return list

        list = br_list(elem)

        for i, e in enumerate(list):
            if re.search(self.tag(), e, flags=re.IGNORECASE) or re.search('WOCHENGERICHTE', e):
                text.append('{} - *{}*'.format(list[i + 1], list[i + 3].replace(' ', '')))

        return text

    def set_reminder(self, message, bot_handler):
        global reminder
        t = re.match('set reminder (.*)', message['content']).group(1)

        if message['type'] == 'private':
            id = (message['type'], message['sender_email'], message['subject'])
        else:
            id = (message['type'], message['display_recipient'], message['subject'])

        if t == 'off':
            self.schedule.clear(id)
            msg = 'Reminder cleared'
            self.save_jobs(bot_handler)

        elif t and time.strptime(t, '%H:%M'):
            self.schedule.clear(id)
            self.schedule.every().day.at(t).do(
                lambda: bot_handler.send_message(dict(
                    type=id[0],  # can be 'stream' or 'private'
                    to=id[1],  # either the stream name or user's email
                    subject=id[2],  # message subject
                    content=self.menu(),  # content of the sent message
                ))).tag(id)
            msg = 'Reminder set to {}'.format(t)
            self.save_jobs(bot_handler)

        else:
            msg = 'Wrong format. Example "set reminder 11:50'

        bot_handler.send_reply(
            message,
            msg,
        )

    def list_reminder(self, message, bot_handler):
        msg = 'No reminder set'

        if message['type'] == 'private':
            id = (message['type'], message['sender_email'], message['subject'])
        else:
            id = (message['type'], message['display_recipient'], message['subject'])

        if message['content'].endswith('all'):
            reminder = ['{} for streams {}'.format(j.at_time.strftime('%H:%M'), list(j.tags)[0])
                        for j in self.schedule.jobs]

            if reminder:
                msg = '\n'.join(reminder)

        else:
            reminder = ['{}'.format(j.at_time.strftime('%H:%M'))
                        for j in self.schedule.jobs if id in j.tags]

            if reminder:
                msg = 'Reminder set to {}'.format(
                    '\n'.join(reminder))

        bot_handler.send_reply(
            message,
            msg,
        )

    def menu(self):
        msg = "**{}'s lunch menu**\n\n".format(self.tag())
        msg += "**Teigware:**\n" + "\n".join(self.teigware()) + '\n\n'
        msg += "**Feinessen:**\n" + "\n".join(self.feinessen()) + '\n\n'
        msg += "**Salon Wichtig:**\n" + "\n".join(self.salonwichtig()) + '\n'

        print(msg)
        return msg

    def usage(self):
        return '''
        Hi, I'm lunchy. How can I help you?
        
        `menu` gives you today's lunch menu right away
        `set reminder <hours>:<min>` sets a daily reminder for the current stream
        `list reminder` lists reminders for the current stream
        `list reminder all` lists reminders in all streams
        '''

    def handle_message(self, message, bot_handler):
        if message['content'].startswith('menu'):
            bot_handler.send_reply(
                message,
                self.menu(),
            )
        elif message['content'].startswith('reminder'):
            self.schedule.every(5).seconds.do(
                lambda: bot_handler.send_reply(
                    message,
                    self.menu(),
                ))
        elif message['content'].startswith('set reminder'):
            self.set_reminder(message, bot_handler)
        elif message['content'].startswith('load jobs'):
            self.load_jobs(bot_handler)
        elif message['content'].startswith('list reminder'):
            self.list_reminder(message, bot_handler)
        else:
            bot_handler.send_reply(
                message,
                self.usage(),
            )

        print('message recieved')


handler_class = Lunchy
