import telepot
import time
from dateutil.parser import parse
import requests

APITOKEN = "262947791:AAFApOcx33pmIFnho6JbpQnuFZicQgWDhQs"
user_states = {}
reservering = {}
ruimtes = ['Vergaderzaal 1','Vergaderzaal 2','Vergaderzaal 3']

def is_time(string):
    try:
        parse(string)
        return True
    except ValueError:
        return False

def state_switcher(msg):
    try:

        chat_id = msg['chat']['id']
        if 'suus' in msg['text'].lower():
                bot.sendMessage(msg['chat']['id'], "Hoi "+msg['from']['first_name']+ " wat kan ik voor je doen?")

                if chat_id not in user_states or user_states[chat_id] == 0:
                    user_states[chat_id] = 0
                    reservering[chat_id] = {}
                    state = 1
                    print(msg['text'])
                    user_states[chat_id] = state

        elif 'wanneer' in msg['text'].lower():
            begintijd = reservering[chat_id]['begintijd']
            eindtijd = reservering[chat_id]['eindtijd']
            ruimte = reservering[chat_id]['ruimte']
            bot.sendMessage(chat_id, "Je hebt "+ruimte+" van "+begintijd.strftime('%d-%m-%y %H:%M')+" tot "+eindtijd.strftime('%H:%M')+" gereserveerd.")

        elif '/ruimtes' in msg['text']:
            state = 0
            #command = msg['text'].split(" ")
            #ruimtes = command[1].split(",")
            bot.sendMessage(chat_id, "Ruimtes zijn geset")

        else:
            state = user_states[chat_id]

            if state == 1:
                if 'opnieuw' in msg['text'].lower() or 'overnieuw' in msg['text'].lower():
                    state = 0

                elif 'reserveren' in msg['text'].lower():
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
                state = 0
                reservering[chat_id]['eindtijd'] = parse(msg['text'])
                begintijd = reservering[chat_id]['begintijd']
                eindtijd = reservering[chat_id]['eindtijd']
                ruimte = reservering[chat_id]['ruimte']
                if eindtijd < begintijd:
                    bot.sendMessage(chat_id, "Leer rekenen idioot. Je kan niet eerder eindigen dan wanneer je begint!")
                else:
                    requests.post("http://api.akoo.nl/agenda/post?key=cbcs", data={"_method": "post","data[title]": "Reservering door "+msg["from"]["first_name"], "data[starttime]": begintijd.strftime('%H:%M'), "data[endtime]": eindtijd.strftime('%H:%M'), "data[location]": ruimte})
                    keyboard = {'hide_keyboard': True}
                    bot.sendMessage(chat_id, "Van "+begintijd.strftime('%H:%M')+" tot "+eindtijd.strftime('%H:%M')+" in "+ruimte+". Staat genoteerd!", reply_markup=keyboard)
            else:
                pass

        user_states[chat_id] = state

    except:
        print("I dont give a fuck about errors")


def on_chat_message(msg):
    state_switcher(msg)

bot = telepot.Bot(APITOKEN)
bot.message_loop({'chat':on_chat_message})

while 1:
    time.sleep(10)