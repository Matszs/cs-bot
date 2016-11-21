import telepot
import time
from dateutil.parser import parse

APITOKEN = "262947791:AAFApOcx33pmIFnho6JbpQnuFZicQgWDhQs"
user_states = {}
reservering = {}
ruimtes = ['TTH04A13','TTH04A14','TTH04A15']

def is_time(string):
    try:
        parse(string)
        return True
    except ValueError:
        return False

def state_switcher(msg):
    chat_id = msg['chat']['id']
    state = 0

    if 'Suus'.lower() or 'Hoer'.lower() in msg['text'].lower():
            bot.sendMessage(msg['chat']['id'], "Hoi "+msg['from']['first_name']+ " wat kan ik voor je doen?")
            state = 1
            if chat_id not in user_states or user_states[chat_id] == 0:
                user_states[chat_id] = 0
                state = user_states[chat_id]
                reservering[chat_id] = {}
                print(msg['text'])

    else:
        state = user_states[chat_id]

        if state == 1:
            if 'opnieuw' or 'overnieuw' in msg['text'].lower():
                state = 0

            if 'reserveren' in msg['text'].lower():
                state = 2

                keyboard = {'keyboard': [ruimtes], 'resize_keyboard': True, 'one_time_keyboard': True }
                bot.sendMessage(chat_id, "Welke ruimte wil je reserveren?", reply_markup=keyboard)
        elif state == 2 and any(msg['text'] in s for s in ruimtes):
            reservering[chat_id]['ruimte'] = msg['text']

            keyboard = {'keyboard': [['8:00','9:00','10:00'],['11:00','12:00', '13:00'],['14:00','15:00','16:00']], 'resize_keyboard': True }
            bot.sendMessage(chat_id, "En hoe laat moet dit beginnen?", reply_markup=keyboard)
            state = 3

        elif state == 3 and is_time(msg['text']):
            reservering[chat_id]['begintijd'] = parse(msg['text'])
            keyboard = {'keyboard': [['8:00','9:00','10:00'],['11:00','12:00', '13:00'],['14:00','15:00','16:00']], 'resize_keyboard': True, 'one_time_keyboard': True }
            bot.sendMessage(chat_id, "En hoe tot hoelaat wil je hem?", reply_markup=keyboard)
            state = 4

        elif state == 4 and is_time(msg['text']):
            state = 5
            reservering[chat_id]['eindtijd'] = parse(msg['text'])
            begintijd = reservering[chat_id]['begintijd']
            eindtijd = reservering[chat_id]['eindtijd']
            ruimte = reservering[chat_id]['ruimte']
            bot.sendMessage(chat_id, "Van "+begintijd.strftime('%H:%M')+" tot "+eindtijd.strftime('%H:%M')+" in "+ruimte+". Staat genoteerd!")
            print(begintijd, eindtijd, ruimte)
        else:
            pass
    user_states[chat_id] = state


def on_chat_message(msg):
    state_switcher(msg)


bot = telepot.Bot(APITOKEN)
bot.message_loop({'chat':on_chat_message})



while 1:
    time.sleep(10)