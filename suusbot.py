import telepot
import time
from firebase import firebase

APITOKEN = "262947791:AAFApOcx33pmIFnho6JbpQnuFZicQgWDhQs"
FIREBASE_DB = "https://suus-bot.firebaseio.com/"

class STATES:
	NEW_USER = -1
	NEW_USER_WELCOME_MESSAGE = -2

db = firebase.FirebaseApplication(FIREBASE_DB, None)

def message_reveiver(msg):
	user = get_user(msg['from'])
	if user is False:
		user = save_user(msg['from'])

	insert = db.post('messages/received/' + str(msg['chat']['id']), msg)

	if 'name' in insert:
		insertID = insert['name']
	else:
		insertID = None

	# get connected company
	company = company_by_user(msg['from'])
	if company is False:
		start_conversation('NO_COMPANY', msg, user)
		return

	#TODO: Send message to AI



def company_by_user(user):
	companies = db.get('companies', None)

	for companyName in companies:
		if 'users' in companies[companyName]:
			if user['id'] in companies[companyName]['users']:
				return companies[companyName]

	return False
def get_user(user):
	user = db.get('users', user['id'])

	if user is None:
		return False

	return user
def save_user(user):
	user['state'] = STATES.NEW_USER
	userDb = db.put('users', str(user['id']), user)

	return userDb
def get_company_by_code(code):
	companies = db.get('companies', None)

	for companyName in companies:
		if companies[companyName]['code'].lower() == code.lower():
			return companies[companyName]

	return False

def start_conversation(type, msg, user):

	if type is 'NO_COMPANY':
		if user['state'] is STATES.NEW_USER:
			#send the welcome message and ask for the SUUS-ID
			bot.sendMessage(msg['chat']['id'], "Hallo " + msg['from']['first_name'] + ", mijn naam is Suus!")
			time.sleep(1)
			bot.sendMessage(msg['chat']['id'], "Ik help je met het reserveren van vergaderruimtes.")
			time.sleep(1)
			bot.sendMessage(msg['chat']['id'], "Om te beginnen heb ik je SUUS-ID nodig. Deze krijg je van je leidinggevende.")

			#set user state to know we already sent the welcome message
			db.put('users/' + str(user['id']), 'state', STATES.NEW_USER_WELCOME_MESSAGE)
			user['state'] = STATES.NEW_USER_WELCOME_MESSAGE

		if user['state'] is STATES.NEW_USER_WELCOME_MESSAGE:
			company = get_company_by_code(msg['text'])

			if company is not False:
				bot.sendMessage(msg['chat']['id'], "Welkom bij " + company['name'] + "!")
			else:
				print("COMPANY NOT FOUND!!")




bot = telepot.Bot(APITOKEN)
bot.message_loop(message_reveiver)

while 1:
	time.sleep(10)