import telepot
import time
from firebase import firebase
import threading
import apiai
import json
import datetime

APITOKEN = "262947791:AAFApOcx33pmIFnho6JbpQnuFZicQgWDhQs"
#AI_CLIENT_ACCESS_TOKEN = "900740f8620f4a9897fad1adc5b8c7dc"
AI_CLIENT_ACCESS_TOKEN = "361e9de139384db99766aff1a4687b12"
FIREBASE_DB = "https://suus-bot.firebaseio.com/"

class STATES:
	DEFAULT = 0
	NEW_USER = -1
	NEW_USER_WELCOME_MESSAGE = -2
	TUTORIAL = -3

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

	if user['state'] == STATES.TUTORIAL:
		start_conversation('TUTORIAL', msg, user)
		return

	#TODO: Send message to AI
	ai_handler(user, msg)

def company_by_user(user):
	companies = db.get('companies', None)

	for companyName in companies:
		if 'users' in companies[companyName]:
			if str(user['id']) in companies[companyName]['users']:
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

	if type == 'NO_COMPANY':
		if user['state'] == STATES.NEW_USER:
			#send the welcome message and ask for the SUUS-ID
			bot.sendMessage(msg['chat']['id'], "Hallo " + msg['from']['first_name'] + ", mijn naam is Suus!")
			time.sleep(1)
			bot.sendMessage(msg['chat']['id'], "Ik help je met het reserveren van vergaderruimtes.")
			time.sleep(1)
			bot.sendMessage(msg['chat']['id'], "Om te beginnen heb ik je SUUS-ID nodig. Deze krijg je van je leidinggevende.")

			#set user state to know we already sent the welcome message
			db.put('users/' + str(user['id']), 'state', STATES.NEW_USER_WELCOME_MESSAGE)
			user['state'] = STATES.NEW_USER_WELCOME_MESSAGE

		if user['state'] == STATES.NEW_USER_WELCOME_MESSAGE:
			company = get_company_by_code(msg['text'])

			if company is not False:
				#add user to company
				db.put('companies/' + company['id'] + '/users', str(user['id']), user['id'])

				#set user state
				db.put('users/' + str(user['id']), 'state', STATES.DEFAULT)
				user['state'] = STATES.DEFAULT

				#inform user
				bot.sendMessage(msg['chat']['id'], "Welkom bij " + company['name'] + "!")

				#start tutorial
				start_conversation('TUTORIAL', msg, user)
			else:
				print("COMPANY NOT FOUND!!")
	if type is 'TUTORIAL':

		if user['state'] == STATES.DEFAULT:
			db.put('users/' + str(user['id']), 'state', STATES.TUTORIAL)
			user['state'] = STATES.TUTORIAL

			bot.sendMessage(msg['chat']['id'], "We kunnen aan de slag! We beginnen met een korte introductie om je te leren hoe het werkt.")
			time.sleep(2)
			bot.sendMessage(msg['chat']['id'], "We gaan een vergaderruimte reserveren. Om dit te doen type je: \n\n Ik wil graag een vergaderruimte reserveren \n- of - \n Ik wil graag een vergaderruimte voor morgen", parse_mode="HTML")

		if user['state'] == STATES.TUTORIAL:
			print("TUTORIAL FASE 2")
			#todo: get msg[text]
			#todo: send to AI
			#todo: check if action is 'reserveren'
			#todo: If so, put state to default or if you want to have more tutorial steps you have to create different states (STATES.TUTORIAL_1, STATES.TUTORIAL_2, etc...)

def timelyEvents():

	while True:

		#todo: search if reservation has ended, + 30 minutes, send message and ask for feedback, save feedback to database

		print("> TimeEvents Trigger")

		time.sleep(60)

def ai_request(user, text):
	request = ai.text_request()
	request.lang = 'nl'
	request.session_id = user['id']
	request.query = text
	return json.loads(request.getresponse().read().decode('utf_8'))
def ai_request_handler(request):
	# todo: get action, params and extract everything, making sure json is always the same

	#print(request) # DEBUG

	returnValue = {'action': None, 'message': '', 'params': []}

	if request['status']['code'] == 200:
		returnValue['action'] = request['result']['action']
		if 0 in request['result']['fulfillment']['messages']:
			returnValue['message'] = request['result']['fulfillment']['messages'][0]['speech']
		else:
			returnValue['message'] = request['result']['fulfillment']['speech']
		returnValue['params'] = request['result']['parameters']

	return returnValue
def ai_handler(user, msg):
	request = ai_request(user, msg['text'])
	formatted = ai_request_handler(request)
	# todo: switch/if/.. based on formatted data, check actions and perform actions.
	print(formatted)

	bot.sendMessage(msg['chat']['id'], formatted['message'])
	print(formatted['action'])

	if formatted['action'] == "Reserveren":
		start_time = None
		end_time = None

		if 'begin_tijd' in formatted['params'] and formatted['params']['begin_tijd'] is not '':
			start_time = formatted['params']['begin_tijd']
		if 'eind_tijd' in formatted['params'] and formatted['params']['eind_tijd'] is not '':
			end_time = formatted['params']['eind_tijd']

		if start_time is not None and end_time is not None:
			date = datetime.datetime.now()
			db.post('reserveringen', {'start_time': start_time, 'end_time': end_time, 'user': user['id'], 'date': str(date)})




def main():
	# start timely-events
	t = threading.Thread(target=timelyEvents)
	t.daemon = True
	t.start()

	#init AI
	global ai
	ai = apiai.ApiAI(AI_CLIENT_ACCESS_TOKEN)

	# start listening for data of Telegram
	global bot
	bot = telepot.Bot(APITOKEN)
	bot.message_loop(message_reveiver)

	while 1:
		time.sleep(10)

if __name__ == '__main__':
	main()