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

    def __init__(self):
        self.schedule = Scheduler()
        self.cease_continuous_run = self.run_continously()

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

                    if c.string.startswith('__'):
                        list.append(current)
                        current = ''
                    else:
                        current += c.string

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

    def menu(self):
        msg = "**{}'s lunch menu**\n\n".format(self.tag())
        msg += "**Teigware:**\n" + "\n".join(self.teigware()) + '\n\n'
        msg += "**Feinessen:**\n" + "\n".join(self.feinessen()) + '\n'

        print(msg)
        return msg

    def usage(self):
        return '''Testbot'''

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

        else:
            bot_handler.send_reply(
                message,
                self.usage(),
            )

        print('message recieved')


handler_class = Lunchy
