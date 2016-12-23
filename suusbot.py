# -*- coding: utf-8 -*-
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
	NOTIFY_START_QUESTION = 1

db = firebase.FirebaseApplication(FIREBASE_DB, None)

def message_reveiver(msg):
	user = get_user(msg['from'])
	if user is False:
		user = save_user(msg['from'])

	conversation = get_conversation(msg['chat']['id'])
	if conversation is False:
		conversation = save_conversation(msg['chat']['id'], msg)

	insert = db.post('conversations/' + str(conversation['chat_id']) + '/messages', msg)

	# get connected company
	company = company_by_user(msg['from'])
	if company is False:
		start_conversation('NO_COMPANY', msg, user, conversation)
		return

	if user['state'] == STATES.TUTORIAL:
		start_conversation('TUTORIAL', msg, user, conversation)
		return

	ai_handler(user, company, msg, conversation)

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
	userDb = db.put('users', str(user['id']), user)

	return userDb
def get_company_by_code(code):
	companies = db.get('companies', None)

	for companyName in companies:
		if companies[companyName]['code'].lower() == code.lower():
			return companies[companyName]

	return False
def get_reservations():
	reservations = {}
	companies = db.get('companies', None)

	for companyId in companies:
		company = companies[companyId]

		if 'reservations' in company:
			for reservationId in company['reservations']:
				reservations[reservationId] = {'reservation': company['reservations'][reservationId], 'company': company}

	return reservations
def save_conversation(chat_id, msg):
	conversation = {'chat_id': chat_id}
	conversation['chat'] = msg['chat']
	conversation['state'] = STATES.DEFAULT

	conversationDb = db.put('conversations', str(chat_id), conversation)
	return conversationDb
def get_conversation(chat_id, include_messages = False):
	conversationDb = db.get('conversations', str(chat_id))

	if conversationDb is None:
		return False

	if include_messages is False:
		conversationDb['messages'] = []

	return conversationDb

def start_conversation(type, msg, user, conversation):

	if type == 'NO_COMPANY':
		if conversation['state'] == STATES.NEW_USER:
			#send the welcome message and ask for the SUUS-ID
			bot.sendMessage(msg['chat']['id'], "Hallo " + msg['from']['first_name'] + ", mijn naam is Suus!")
			time.sleep(1)
			bot.sendMessage(msg['chat']['id'], "Ik help je met het reserveren van vergaderruimtes.")
			time.sleep(1)
			bot.sendMessage(msg['chat']['id'], "Om te beginnen heb ik je SUUS-ID nodig. Deze krijg je van je leidinggevende.")

			#set user state to know we already sent the welcome message
			db.put('conversations/' + str(conversation['chat_id']), 'state', STATES.NEW_USER_WELCOME_MESSAGE)
			conversation['state'] = STATES.NEW_USER_WELCOME_MESSAGE

		if conversation['state'] == STATES.NEW_USER_WELCOME_MESSAGE:
			company = get_company_by_code(msg['text'])

			if company is not False:
				#add user to company
				db.put('companies/' + company['id'] + '/users', str(user['id']), user['id'])

				#set company state
				db.put('conversations/' + str(conversation['chat_id']), 'state', STATES.DEFAULT)
				conversation['state'] = STATES.DEFAULT

				#inform user
				bot.sendMessage(msg['chat']['id'], "Welkom bij " + company['name'] + "!")

				#start tutorial
				start_conversation('TUTORIAL', msg, user, conversation)
			else:
				print("COMPANY NOT FOUND!!")
	if type is 'TUTORIAL':

		if conversation['state'] == STATES.DEFAULT:
			db.put('conversations/' + str(conversation['chat_id']), 'state', STATES.TUTORIAL)
			conversation['state'] = STATES.TUTORIAL

			bot.sendMessage(msg['chat']['id'], "We kunnen aan de slag! We beginnen met een korte introductie om je te leren hoe het werkt.")
			time.sleep(2)
			bot.sendMessage(msg['chat']['id'], "We gaan een vergaderruimte reserveren. Om dit te doen type je: \n\n Ik wil graag een vergaderruimte reserveren \n- of - \n Ik wil graag een vergaderruimte voor morgen", parse_mode="HTML")

		if conversation['state'] == STATES.TUTORIAL:
			print("TUTORIAL FASE 2")
			#todo: get msg[text]
			#todo: send to AI
			#todo: check if action is 'reserveren'
			#todo: If so, put state to default or if you want to have more tutorial steps you have to create different states (STATES.TUTORIAL_1, STATES.TUTORIAL_2, etc...)

def ai_request(conversation, text):
	request = ai.text_request()
	request.lang = 'nl'
	request.session_id = conversation['chat_id']
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

def save_feedback_message(user, company, msg, conversation):
	db.post('companies/' + conversation['last_data']['company']['id'] + '/reservations/' + str(conversation['last_data']['reservation_id']) + '/feedback', msg)

def ai_handler(user, company, msg, conversation):
	if 'last_data' in conversation:
		if 'type' in conversation['last_data']:
			if conversation['last_data']['type'] == 'feedback':

				if 'first_message_time' in conversation['last_data']:
					message_time = datetime.datetime.strptime(conversation['last_data']['first_message_time'], '%Y-%m-%d %H:%M:%S')

					if datetime.datetime.now().time() > (message_time + datetime.timedelta(seconds=30)).time():
						db.delete('/conversations/' + str(conversation['chat_id']), 'last_data')  # delete last_data after processing
						save_feedback_message(user, company, msg, conversation)
						bot.sendMessage(msg['chat']['id'], "Bedankt voor uw feedback.")
						print("STOP FEEDBACK")
						return
					else:
						db.put('/conversations/' + str(conversation['chat_id']) + '/last_data', 'first_message_time', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
						save_feedback_message(user, company, msg, conversation)
						return
				else:
					db.put('/conversations/' + str(conversation['chat_id']) + '/last_data', 'first_message_time', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
					save_feedback_message(user, company, msg, conversation)
					return


	request = ai_request(conversation, msg['text'])
	formatted = ai_request_handler(request)
	print(formatted)
	postMessage = True


	if formatted['action'] == "Reserveren":
		start_time = None
		end_time = None

		if 'begin_tijd' in formatted['params'] and formatted['params']['begin_tijd'] is not '' and formatted['params']['begin_tijd']:
			start_time = formatted['params']['begin_tijd']
		if 'eind_tijd' in formatted['params'] and formatted['params']['eind_tijd'] is not '' and formatted['params']['eind_tijd']:
			end_time = formatted['params']['eind_tijd']

		if start_time is not None and end_time is not None:
			db.put('/conversations/' + str(conversation['chat_id']), 'last_data', {'type': 'reservation', 'start_time': start_time, 'end_time': end_time})
			bot.sendMessage(msg['chat']['id'], "Weet u zeker dat u een kamer wilt reserveren voor het volgende: \n\n Starttijd:  " + start_time + " \n Eindtijd:  " + end_time + " \n Kamer:  -")
			postMessage = False # don't post the AI message, we only want to send the confirmation

	elif formatted['action'] == "JaNeeVraag":

		lastData = db.get('/conversations/' + str(conversation['chat_id']), 'last_data')

		if lastData is not None:
			if 'type' in lastData:

				if lastData['type'] == 'reservation':

					if formatted['params']['JaOfNee'] == 'Ja':
						date = datetime.datetime.now()
						start_time = lastData['start_time']
						end_time = lastData['end_time']

						db.post('companies/' + company['id'] + '/reservations', {'start_time': start_time, 'end_time': end_time, 'user': user['id'], 'date': time.strftime('%Y-%m-%d'), 'created': str(date), 'chat_id': msg['chat']['id'], 'reminder_sent': 0, 'feedback_sent': 0, 'canceled': 0})
						bot.sendMessage(msg['chat']['id'], "De reservering staat genoteerd.")
					else:
						bot.sendMessage(msg['chat']['id'], "De reservering is geannuleerd.")

				elif lastData['type'] == 'confirm_reservation':
					if formatted['params']['JaOfNee'] == 'Ja':
						bot.sendMessage(msg['chat']['id'], "👍🏻")
					else:
						db.put('companies/' + lastData['company']['id'] + '/reservations/' + lastData['reservation_id'], 'canceled', 1)
						bot.sendMessage(msg['chat']['id'], "De reservering is geannuleerd.")

				db.delete('/conversations/' + str(conversation['chat_id']), 'last_data') # delete last_data after processing

			else:
				print("ERROR: Data format corrupt")

	if formatted['message'] != "" and postMessage:
		bot.sendMessage(msg['chat']['id'], formatted['message'])

def notify_starting_reservations():
	reservations = get_reservations()

	for reservationId in reservations:
		reservation = reservations[reservationId]

		if reservation['reservation']['reminder_sent']:
			continue

		dateFormatted = datetime.datetime.strptime(reservation['reservation']['date'], "%Y-%m-%d")

		if dateFormatted.date() == datetime.date.today(): # check if reservations is for today

			startTimeMargeStart = datetime.datetime.strptime(reservation['reservation']['start_time'], '%H:%M:%S') - datetime.timedelta(minutes=30)
			startTimeMargeEnd = datetime.datetime.strptime(reservation['reservation']['start_time'], '%H:%M:%S')

			startTime = datetime.datetime.strptime(reservation['reservation']['start_time'], '%H:%M:%S')


			if (datetime.datetime.now().hour == startTimeMargeStart.hour and datetime.datetime.now().minute >= startTimeMargeStart.minute) or (datetime.datetime.now().hour == startTimeMargeEnd.hour and datetime.datetime.now().minute <= startTimeMargeEnd.minute):

				startHours = startTime.hour
				startMinutes = startTime.minute

				if startHours < 10:
					startHours = '0' + str(startHours)

				if startMinutes < 10:
					startMinutes = '0' + str(startMinutes)

				bot.sendMessage(reservation['reservation']['chat_id'], "Uw afspraak begint zometeen om " + str(startHours) + ":" + str(startMinutes) + ", gaat deze afspraak nog door?")
				db.put('companies/' + reservation['company']['id'] + '/reservations/' + reservationId, 'reminder_sent', 1)

				conversation = get_conversation(reservation['reservation']['chat_id'])
				db.put('/conversations/' + str(conversation['chat_id']), 'last_data', {'type': 'confirm_reservation', 'reservation_id': reservationId, 'company': reservation['company']})

				print("reminder sent")
def notify_feedback_reservations():
	reservations = get_reservations()

	for reservationId in reservations:
		reservation = reservations[reservationId]

		if 'feedback_sent' in reservation['reservation']:
			if reservation['reservation']['feedback_sent']:
				continue

			date_formatted = datetime.datetime.strptime(reservation['reservation']['date'], "%Y-%m-%d")

			if date_formatted.date() == datetime.date.today(): # yes if the reservations ends 00:00 it won't work

				end_time_offset = datetime.datetime.strptime(reservation['reservation']['end_time'], '%H:%M:%S') + datetime.timedelta(minutes=30)

				nowTime = datetime.datetime.now().hour * 60 + datetime.datetime.now().minute
				reservationTime = end_time_offset.hour * 60 + end_time_offset.minute

				if nowTime >= reservationTime:
					bot.sendMessage(reservation['reservation']['chat_id'], "U heeft zojuist gebruik gemaakt van een ruimte, hoe is deze u bevallen?")
					db.put('companies/' + reservation['company']['id'] + '/reservations/' + reservationId, 'feedback_sent', 1)

					conversation = get_conversation(reservation['reservation']['chat_id'])
					db.put('/conversations/' + str(conversation['chat_id']), 'last_data', {'type': 'feedback', 'reservation_id': reservationId, 'company': reservation['company']})

def get_conversations():
	return db.get('conversations', None)

def notify_feedback_ended():
	conversations = get_conversations()

	for conversation_id in conversations:
		conversation = conversations[conversation_id]
		if 'last_data' in conversation:
			if 'type' in conversation['last_data']:
				if conversation['last_data']['type'] == 'feedback':
					if 'first_message_time' in conversation['last_data']:
						message_time = datetime.datetime.strptime(conversation['last_data']['first_message_time'], '%Y-%m-%d %H:%M:%S')

						if datetime.datetime.now().time() > (message_time + datetime.timedelta(seconds=30)).time():
							db.delete('/conversations/' + str(conversation['chat_id']), 'last_data')  # delete last_data after processing
							bot.sendMessage(conversation['chat_id'], "Bedankt voor uw feedback.")
							print("STOP FEEDBACK")

def timely_events():

	while True:

		#todo: if reservation is canceled, stop asking for feedback

		print("> TimeEvents Trigger")
		notify_starting_reservations()
		notify_feedback_reservations()
		notify_feedback_ended()

		time.sleep(60)

def main():
	# start timely-events
	t = threading.Thread(target=timely_events)
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