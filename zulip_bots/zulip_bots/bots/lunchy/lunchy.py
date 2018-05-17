class Lunchy(object):
    '''
    A docstring documenting this bot.
    '''

    def usage(self):
        return '''Testbot'''

    def handle_message(self, message, bot_handler):
        print('message recieved')


handler_class = Lunchy
