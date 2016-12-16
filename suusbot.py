import telepot
import time
from firebase import firebase

APITOKEN = "262947791:AAFApOcx33pmIFnho6JbpQnuFZicQgWDhQs"
FIREBASE_DB = "https://suus-bot.firebaseio.com/"

db = firebase.FirebaseApplication(FIREBASE_DB, None)

def message_reveiver(msg):
	insert = db.post('messages/received/' + str(msg['chat']['id']), msg)

	if 'name' in insert:
		insertID = insert['name']
	else:
		insertID = None

	#TODO: Send message to AI


bot = telepot.Bot(APITOKEN)
bot.message_loop(message_reveiver)

while 1:
	time.sleep(10)