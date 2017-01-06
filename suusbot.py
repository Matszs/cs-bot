# -*- coding: utf-8 -*-
import telepot
import time
from firebase import firebase
import threading
import apiai
import json
import datetime
import random

APITOKEN = "262947791:AAFApOcx33pmIFnho6JbpQnuFZicQgWDhQs" # Telegram token
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
	user = get_user(msg['from']) # get user from db
	if user is False:
		user = save_user(msg['from']) # if it is a new user we create a profile

	conversation = get_conversation(msg['chat']['id']) # get conversation from db
	if conversation is False:
		conversation = save_conversation(msg['chat']['id'], msg) # if it is a new conversation we create a profile

	insert = db.post('conversations/' + str(conversation['chat_id']) + '/messages', msg) # save all the messages

	# get connected company
	company = company_by_user(msg['from']) # get the company which the user is connected to
	if company is False:
		start_conversation('NO_COMPANY', msg, user, conversation) # if the user isn't connected to a company we arrange that first.
		return

	if conversation['state'] == STATES.TUTORIAL:
		start_conversation('TUTORIAL', msg, user, conversation) # the user first has to follow the tutorial before he can start using the bot
		return

	ai_handler(user, company, msg, conversation) # all other situations are handled by the AI.

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
	reservationsAll = {}
	companies = db.get('companies', None)

	for companyId in companies:
		company = companies[companyId]

		if 'rooms' in company:
			for roomId in company['rooms']:
				room = company['rooms'][roomId]
				reservations = {}

				if 'reservations' in room:
					reservations = room['reservations']

					del room['reservations']

					for reservationId in reservations:
						reservationsAll[reservationId] = {'reservation': reservations[reservationId], 'company': company, 'room': room}

	return reservationsAll
def save_conversation(chat_id, msg):
	conversation = {'chat_id': chat_id}
	conversation['chat'] = msg['chat']
	conversation['state'] = STATES.NEW_USER # default value when adding new conversation to the db

	conversationDb = db.put('conversations', str(chat_id), conversation)
	return conversationDb
def get_conversation(chat_id, include_messages = False):
	conversationDb = db.get('conversations', str(chat_id))

	if conversationDb is None:
		return False

	if include_messages is False:
		conversationDb['messages'] = []

	return conversationDb

# this method handles a few 'basic' situations, like when the user isn't connected to company or has to follow the tutorial
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


			request = ai_request(conversation, msg['text'])
			formatted = ai_request_handler(request)

			if formatted['action'] == "Reserveren":
				bot.sendMessage(msg['chat']['id'], "Ja goed gedaan! Het is je nu gelukt om een reservering te maken. Je bent klaar met de tutorial.")
				time.sleep(1)
				bot.sendMessage(msg['chat']['id'], "Je kunt nu aan de slag.")

				db.put('conversations/' + str(conversation['chat_id']), 'state', STATES.DEFAULT)
				conversation['state'] = STATES.DEFAULT


			print("TUTORIAL FASE 2")
			#todo: get msg[text]
			#todo: send to AI
			#todo: check if action is 'reserveren'
			#todo: If so, put state to default or if you want to have more tutorial steps you have to create different states (STATES.TUTORIAL_1, STATES.TUTORIAL_2, etc...)

def ai_request(conversation, text):
	request = ai.text_request()
	request.lang = 'nl'
	request.session_id = conversation['chat_id'] # conversation id instead of user id so everybody in the conversation can answer questions.
	request.query = text
	return json.loads(request.getresponse().read().decode('utf_8'))
def ai_request_handler(request):
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
	db.post('companies/' + conversation['last_data']['company']['id'] + '/rooms/' + conversation['last_data']['room']['id'] + '/reservations/' + str(conversation['last_data']['reservation_id']) + '/feedback', msg)

def checkRoomAvailability(room, start_time, end_time):

	if 'reservations' not in room:  # if there are no reservations, the room is always available
		return True

	date = datetime.datetime.now().strftime("%Y-%m-%d")

	start_time_date_time = datetime.datetime.strptime(date + " " + start_time, '%Y-%m-%d %H:%M:%S').timestamp()
	end_time_date_time = datetime.datetime.strptime(date + " " + end_time, '%Y-%m-%d %H:%M:%S').timestamp()

	for reservationId in room['reservations']:
		reservation = room['reservations'][reservationId]

		reservation_start_time_date_time = datetime.datetime.strptime(date + " " + reservation['start_time'], '%Y-%m-%d %H:%M:%S').timestamp()
		reservation_end_time_date_time = datetime.datetime.strptime(date + " " + reservation['end_time'], '%Y-%m-%d %H:%M:%S').timestamp()

		if reservation_start_time_date_time > start_time_date_time and reservation_end_time_date_time < start_time_date_time:
			return False
		if reservation_start_time_date_time < end_time_date_time and reservation_end_time_date_time > end_time_date_time:
			return False

	return True
def getAvailableRoom(conversation, user, company, start_time, end_time):

	available_rooms = {}
	default_room_id = None

	if 'rooms' in company:
		for roomId in company['rooms']:
			room = company['rooms'][roomId]

			if checkRoomAvailability(room, start_time, end_time):
				available_rooms[roomId] = room
				if room['default'] == '1':
					default_room_id = roomId
				print("BESCHIKBAAR " + room['name'])
			else:
				print("NIET BESCHIKBAAR " + room['name'])

	if default_room_id is not None:
		return available_rooms[default_room_id]

	if len(available_rooms) > 0:
		keys = list(available_rooms.keys())
		random.shuffle(keys)

		return available_rooms[keys[0]]

	return None

def cancel_reservation(conversation, date, time):

	reservations = get_reservations()

	for reservationId in reservations:
		reservation = reservations[reservationId]

		if reservation['reservation']['canceled']:
			print("[DEBUG][" + reservationId + "] Cancel -> 6")
			continue # reservation is already canceled.

		if reservation['reservation']['chat_id'] != conversation['chat_id']:
			print("[DEBUG][" + reservationId + "] Cancel -> 5")
			continue # reservation not created by this conversation

		startTime = datetime.datetime.strptime(reservation['reservation']['date'] + " " + reservation['reservation']['start_time'], '%Y-%m-%d %H:%M:%S')
		endTime = datetime.datetime.strptime(reservation['reservation']['date'] + " " + reservation['reservation']['end_time'], '%Y-%m-%d %H:%M:%S')


		if reservation['reservation']['date'] != date:
			print("[DEBUG][" + reservationId + "] Cancel -> 1")
			continue # not the reservation from params

		if startTime.timestamp() < datetime.datetime.now().timestamp():
			print("[DEBUG][" + reservationId + "] Cancel -> 2")
			continue # reservation already started

		reservationDeleteTime = datetime.datetime.strptime(reservation['reservation']['date'] + " " + time, '%Y-%m-%d %H:%M:%S')

		if startTime.timestamp() > reservationDeleteTime.timestamp():
			print("[DEBUG][" + reservationId + "] Cancel -> 3")
			continue # reservation is before given time

		print(endTime)
		print(reservationDeleteTime)

		print("------------")
		print(endTime.timestamp())
		print(reservationDeleteTime.timestamp())
		print("------------")
		print("------------")
		print("------------")

		if endTime.timestamp() < reservationDeleteTime.timestamp():
			print("[DEBUG][" + reservationId + "] Cancel -> 4")
			continue # reservation is after given time

		# put canceled on 1
		db.put('companies/' + reservation['company']['id'] + '/rooms/' + reservation['room']['id'] + '/reservations/' + reservationId, 'canceled', 1)

		return True
	return False

def ai_handler(user, company, msg, conversation):
	if 'last_data' in conversation:
		if 'type' in conversation['last_data']:
			if conversation['last_data']['type'] == 'feedback':

				if 'first_message_time' in conversation['last_data']:
					message_time = datetime.datetime.strptime(conversation['last_data']['first_message_time'], '%Y-%m-%d %H:%M:%S')

					if datetime.datetime.now().timestamp() > (message_time + datetime.timedelta(seconds=30)).timestamp():
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
		room = None
		date = datetime.datetime.now().strftime('%Y-%m-%d')

		if 'begin_tijd' in formatted['params'] and formatted['params']['begin_tijd'] is not '' and formatted['params']['begin_tijd']:
			start_time = formatted['params']['begin_tijd']
		if 'eind_tijd' in formatted['params'] and formatted['params']['eind_tijd'] is not '' and formatted['params']['eind_tijd']:
			end_time = formatted['params']['eind_tijd']

		if start_time is not None and end_time is not None:
			if 'Kamer' not in formatted['params'] or ('Kamer' in formatted['params'] and formatted['params']['Kamer'] == ''):
				room = getAvailableRoom(conversation, user, company, start_time, end_time)

			if 'date' in formatted['params'] and formatted['params']['date'] is not '' and formatted['params']['date']:
				date = formatted['params']['date']

			if room is None:
				bot.sendMessage(msg['chat']['id'], "Geen ruimte beschikbaar.")
			else:
				db.put('/conversations/' + str(conversation['chat_id']), 'last_data', {'type': 'reservation', 'start_time': start_time, 'end_time': end_time, 'room': room, 'date': date})
				bot.sendMessage(msg['chat']['id'], "Weet u zeker dat u een kamer wilt reserveren voor het volgende: \n\n Starttijd:  " + start_time + " \n Eindtijd:  " + end_time + " \n Kamer:  " + room['name'])

			postMessage = False # don't post the AI message, we only want to send the confirmation

	if formatted['action'] == "Verwijderen":

		date = None
		time = None

		if 'datum' in formatted['params'] and formatted['params']['datum'] is not '' and formatted['params']['datum']:
			date = formatted['params']['datum']
		if 'tijd' in formatted['params'] and formatted['params']['tijd'] is not '' and formatted['params']['tijd']:
			time = formatted['params']['tijd']


		if date is not None and time is not None:
			if cancel_reservation(conversation, date, time):
				bot.sendMessage(msg['chat']['id'], "De reservering is succesvol geannuleerd.")
			else:
				bot.sendMessage(msg['chat']['id'], "Er is geen reservering gevonden voor deze tijd")

			postMessage = False  # don't post the AI message, we only want to send the confirmation

	elif formatted['action'] == "JaNeeVraag":

		lastData = db.get('/conversations/' + str(conversation['chat_id']), 'last_data')

		if lastData is not None:
			if 'type' in lastData:

				if lastData['type'] == 'reservation':

					if formatted['params']['JaOfNee'] == 'Ja':
						date = datetime.datetime.now()
						start_time = lastData['start_time']
						end_time = lastData['end_time']

						room_availability = checkRoomAvailability(lastData['room'], start_time, end_time)
						if room_availability is False:
							bot.sendMessage(msg['chat']['id'], "Helaas is deze ruimte niet meer beschikbaar om deze tijd.")
						else:
							db.post('companies/' + company['id'] + '/rooms/' + lastData['room']['id'] + '/reservations', {'start_time': start_time, 'end_time': end_time, 'user': user['id'], 'date': lastData['date'], 'created': str(date), 'chat_id': msg['chat']['id'], 'room_id': lastData['room']['id'], 'reminder_sent': 0, 'feedback_sent': 0, 'canceled': 0})
							bot.sendMessage(msg['chat']['id'], "De reservering staat genoteerd.")
					else:
						bot.sendMessage(msg['chat']['id'], "De reservering is geannuleerd.")

				elif lastData['type'] == 'confirm_reservation':
					if formatted['params']['JaOfNee'] == 'Ja':
						bot.sendMessage(msg['chat']['id'], "👍🏻")
					else:
						db.put('companies/' + lastData['company']['id'] + '/rooms/' + lastData['room']['id'] + '/reservations/' + lastData['reservation_id'], 'canceled', 1)
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
		if reservation['reservation']['canceled']:
			continue

		dateFormatted = datetime.datetime.strptime(reservation['reservation']['date'], "%Y-%m-%d")

		if dateFormatted.date() == datetime.date.today(): # check if reservations is for today

			startTimeMargeStart = datetime.datetime.strptime(reservation['reservation']['date'] + " " + reservation['reservation']['start_time'], '%Y-%m-%d %H:%M:%S') - datetime.timedelta(minutes=30)
			startTimeMargeEnd = datetime.datetime.strptime(reservation['reservation']['date'] + " " + reservation['reservation']['start_time'], '%Y-%m-%d %H:%M:%S')

			startTime = datetime.datetime.strptime(reservation['reservation']['start_time'], '%H:%M:%S')

			if datetime.datetime.now().timestamp() >= startTimeMargeStart.timestamp() and datetime.datetime.now().timestamp() < startTimeMargeEnd.timestamp():

				startHours = startTime.hour
				startMinutes = startTime.minute

				if startHours < 10:
					startHours = '0' + str(startHours)

				if startMinutes < 10:
					startMinutes = '0' + str(startMinutes)

				bot.sendMessage(reservation['reservation']['chat_id'], "Uw afspraak begint zometeen om " + str(startHours) + ":" + str(startMinutes) + ", gaat deze afspraak nog door?")
				db.put('companies/' + reservation['company']['id'] + '/rooms/' + reservation['room']['id'] + '/reservations/' + reservationId, 'reminder_sent', 1)

				conversation = get_conversation(reservation['reservation']['chat_id'])
				db.put('/conversations/' + str(conversation['chat_id']), 'last_data', {'type': 'confirm_reservation', 'reservation_id': reservationId, 'company': reservation['company'], 'room': reservation['room']})

				print("reminder sent")
def notify_feedback_reservations():
	reservations = get_reservations()

	for reservationId in reservations:
		reservation = reservations[reservationId]

		if 'feedback_sent' in reservation['reservation']:
			if reservation['reservation']['feedback_sent']:
				continue
			if reservation['reservation']['canceled']:
				continue

			date_formatted = datetime.datetime.strptime(reservation['reservation']['date'], "%Y-%m-%d")

			if date_formatted.date() == datetime.date.today(): # yes if the reservations ends 00:00 it won't work

				end_time_offset = datetime.datetime.strptime(reservation['reservation']['date'] + " " + reservation['reservation']['end_time'], '%Y-%m-%d %H:%M:%S') + datetime.timedelta(minutes=30)

				if datetime.datetime.now().timestamp() >= end_time_offset.timestamp():

					bot.sendMessage(reservation['reservation']['chat_id'], "U heeft zojuist gebruik gemaakt van een ruimte, hoe is deze u bevallen?")
					db.put('companies/' + reservation['company']['id'] + '/rooms/' + reservation['room']['id'] + '/reservations/' + reservationId, 'feedback_sent', 1)

					conversation = get_conversation(reservation['reservation']['chat_id'])
					db.put('/conversations/' + str(conversation['chat_id']), 'last_data', {'type': 'feedback', 'reservation_id': reservationId, 'company': reservation['company'], 'room': reservation['room']})

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

						if datetime.datetime.now().timestamp() > (message_time + datetime.timedelta(seconds=30)).timestamp():
							db.delete('/conversations/' + str(conversation['chat_id']), 'last_data')  # delete last_data after processing
							bot.sendMessage(conversation['chat_id'], "Bedankt voor uw feedback.")
							print("STOP FEEDBACK")

def timely_events():

	while True:

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