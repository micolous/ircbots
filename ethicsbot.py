#!/usr/bin/env python
"""
ethicsbot: Acts as automated ethical consultant on IRC.  Not a lawyer.  Like a magic 8-ball, except always gives the same answer to the same question.
Copyright 2010 - 2012 Michael Farrell <http://micolous.id.au>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import asyncore, random
from hashlib import sha512
from datetime import datetime, timedelta
from ConfigParser import ConfigParser
from sys import argv, exit
from ircasync import *
from subprocess import Popen, PIPE

ETHICAL_MESSAGES = [
	[ # unethical
		'your chairman resigns after the plan is revealed to the public by "60 Minutes".',
		'your company was fined 1.4m$ after a probe into your activities.',
		'your company was fined a record 600m$ by the EU after reports of bribery.',
		'accounting irregularities were exposed by a whistleblower, resulting in a fine for your company.',
		'the prime minister announces new taxes on employees because of a percieved lack of local investment by your company in rural areas.',
	],
	
	[ # ethical
		'a jury found no misconduct by board members.',
		'testimony of key witnesses had to be striken from the record after finding they were all under the influence of drugs.',
		'the prime minister issued a public apology over the government\'s handling of your company\'s case in the media.',
		
	],
	
	[ # unsure
		'a royal commission is establisted into your activities.',
		'the government announces a bailout package for your company.',
		'your company\'s charity activities in the third world were recognised by the judge in giving your company a lenient sentence.',
		'your company owns a 70% share in local newspapers and television stations, meaning this incident is never brought to the public\'s attention.',
	],
]

ETHICAL_STATES = [
	'unethical',
	'ethical',
	'unsure',
]

ETHICAL_STATES_COUNT = len(ETHICAL_STATES)

config = ConfigParser()
try:
	config.readfp(open(argv[1]))
except:
	try:
		config.readfp(open('ethicsbot.ini'))
	except:
		print "Syntax:"
		print "  %s [config]" % argv[0]
		print ""
		print "If no configuration file is specified or there was an error, it will default to `ethicsbot.ini'."
		print "If there was a failure reading the configuration, it will display this message."
		exit(1)

# read config
SERVER = config.get('ethicsbot', 'server')
try: PORT = config.getint('ethicsbot', 'port')
except: PORT = DEFAULT_PORT
try: IPV6 = ( config.getint('ethicsbot', 'ipv6_support') == "yes" )
except: IPV6 = False
NICK = config.get('ethicsbot', 'nick')
CHANNEL = config.get('ethicsbot', 'channel')
VERSION = 'ethicsbot; https://github.com/micolous/ircbots/; %s'
try: VERSION = VERSION % Popen(["git","branch","-v","--contains"], stdout=PIPE).communicate()[0].strip()
except: VERSION = VERSION % 'unknown'
del Popen, PIPE

try: FLOOD_COOLDOWN = timedelta(seconds=config.getint('ethicsbot', 'flood_cooldown'))
except: FLOOD_COOLDOWN = timedelta(seconds=5)
try: NICKSERV_PASS = config.get('ethicsbot', 'nickserv_pass')
except: NICKSERV_PASS = None

message_buffer = []
last_message = datetime.now()
flooders = []
ignore_list = []

if config.has_section('ignore'):
	for k,v in config.items('ignore'):
		try:
			ignore_list.append(re.compile(v, re.I))
		except Exception, ex:
			print "Error compiling regular expression in ignore list (%s):" % k
			print "  %s" % v
			print ex
			exit(1)

# main code


def handle_msg(event, match):
	global message_buffer, MAX_MESSAGES, last_message, flooders, CHANNEL
	msg = event.text
	
	if event.channel.lower() != CHANNEL.lower():
		# ignore messages not from our channel
		return
	
	if msg.startswith('?ethical'):
		for item in ignore_list:
			if item.search(event.origin) != None:
				# ignore list item hit
				print "Ignoring message from %s because of: %s" % (event.origin, item.pattern)
				return
				
		# now flood protect!
		delta = event.when - last_message
		last_message = event.when
		
		if delta < FLOOD_COOLDOWN:
			# 5 seconds between requests
			# any more are ignored
			print "Flood protection hit, %s of %s seconds were waited" % (delta.seconds, FLOOD_COOLDOWN.seconds)
			return

		parts = msg.split(' ')
		query = (''.join(parts[1:])).lower()
		
		if len(query) == 0:
			event.reply("%s: you must give me an ethical conundrum to process!" % event.nick)
			return
		
		# hash the request
		h = sha512()
		h.update(query)
		
		ethical = 0
		for c in h.digest():
			for x in xrange(0,8):
				if ord(c) & (2 ** x) > 0:
					ethical += 1
			ethical %= ETHICAL_STATES_COUNT
		
		event.reply('%s: (%s) %s' % (event.nick, ETHICAL_STATES[ethical], random.choice(ETHICAL_MESSAGES[ethical])))

def handle_welcome(event, match):
	global NICKSERV_PASS
	# Compliance with most network's rules to set this mode on connect.
	event.connection.usermode("+B")
	if NICKSERV_PASS != None:
		event.connection.todo(['NickServ', 'identify', NICKSERV_PASS])

irc = IRC(nick=NICK, start_channels=[CHANNEL], version=VERSION)
irc.bind(handle_msg, PRIVMSG)
irc.bind(handle_welcome, RPL_WELCOME)

irc.make_conn(SERVER, PORT, ipv6=IPV6)
asyncore.loop()

