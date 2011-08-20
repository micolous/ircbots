#!/usr/bin/env python
"""
regexbot: IRC-based regular expression evaluation tool.
Copyright 2010 - 2011 Michael Farrell <http://micolous.id.au>

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


import re, asyncore
from datetime import datetime, timedelta
from ConfigParser import ConfigParser
from sys import argv, exit
from ircasync import *
from subprocess import Popen, PIPE

config = ConfigParser()
try:
	config.readfp(open(argv[1]))
except:
	try:
		config.readfp(open('regexbot.ini'))
	except:
		print "Syntax:"
		print "  %s [config]" % argv[0]
		print ""
		print "If no configuration file is specified or there was an error, it will default to `regexbot.ini'."
		print "If there was a failure reading the configuration, it will display this message."
		exit(1)

# read config
SERVER = config.get('regexbot', 'server')
try: PORT = config.getint('regexbot', 'port')
except: PORT = DEFAULT_PORT
NICK = config.get('regexbot', 'nick')
CHANNEL = config.get('regexbot', 'channel')
try: VERSION = config.get('regexbot', 'version') + '; %s'
except: VERSION = 'regexbot; https://github.com/micolous/ircbots/; %s'
try: VERSION = VERSION % Popen(["git","branch","-v","--contains"], stdout=PIPE).communicate()[0].strip()
except: VERSION = VERSION % 'unknown'
del Popen, PIPE

try: FLOOD_COOLDOWN = timedelta(seconds=config.getint('regexbot', 'flood_cooldown'))
except: FLOOD_COOLDOWN = timedelta(seconds=5)
try: MAX_MESSAGES = config.getint('regexbot', 'max_messages')
except: MAX_MESSAGES = 25
try: NICKSERV_PASS = config.get('regexbot', 'nickserv_pass')
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

def handle_ctcp(event, match):
	global message_buffer, MAX_MESSAGES, CHANNEL
	if event.channel.lower() == CHANNEL.lower():
		if event.args[0] == "ACTION":
			message_buffer.append([event.nick, event.text[:200], True])
			message_buffer = message_buffer[-MAX_MESSAGES:]

			return
def handle_msg(event, match):
	global message_buffer, MAX_MESSAGES, last_message, flooders, CHANNEL
	msg = event.text
	
	if event.channel.lower() != CHANNEL.lower():
		# ignore messages not from our channel
		return
	
	if msg.startswith(NICK):
		lmsg = msg.lower()
		
		if 'help' in lmsg or 'info' in lmsg or '?' in lmsg:
			# now flood protect!
			delta = event.when - last_message
			last_message = event.when
		
			if delta < FLOOD_COOLDOWN:
				# 5 seconds between requests
				# any more are ignored
				print "Flood protection hit, %s of %s seconds were waited" % (delta.seconds, FLOOD_COOLDOWN.seconds)
				return
		
			# give information
			event.reply('%s: I am regexbot, the interactive IRC regular expression tool, originally written by micolous.  Source/docs/version: %s' % (event.nick, VERSION))
			return
			
	
	valid_separaters = ['@','#','%',':',';','/']
	separator = '/'
	if msg.startswith('s') and len(msg) > 1 and msg[1] in valid_separaters:
		separator = msg[1]
		
	if msg.startswith('s' + separator):
		for item in ignore_list:
			if item.search(event.origin) != None:
				# ignore list item hit
				print "Ignoring message from %s because of: %s" % (event.origin, item.pattern)
				return
		
		# handle regex
		parts = msg.split(separator)
		
		# now flood protect!
		delta = event.when - last_message
		last_message = event.when
		
		if delta < FLOOD_COOLDOWN:
			# 5 seconds between requests
			# any more are ignored
			print "Flood protection hit, %s of %s seconds were waited" % (delta.seconds, FLOOD_COOLDOWN.seconds)
			return
		
		if len(message_buffer) == 0:
			event.reply('%s: message buffer is empty' % event.nick)
			return
		
		if len(parts) == 3:
			event.reply('%s: invalid regular expression, you forgot the trailing separator, dummy' % event.nick)
			return
		
		if len(parts) != 4:
			# not a valid regex
			event.reply('%s: invalid regular expression, not the right amount of separators' % event.nick)
			return
		
		# find messages matching the string
		if len(parts[1]) == 0:
			event.reply('%s: original string is empty' % event.nick)
			return
			
		ignore_case = 'i' in parts[3]
		e = None
		try:
			if ignore_case:
				e = re.compile(parts[1], re.I)
			else:
				e = re.compile(parts[1])
		except Exception, ex:
			event.reply('%s: failure compiling regular expression: %s' % (event.nick, ex))
			return
		
		# now we have a valid regular expression matcher!
		for x in range(len(message_buffer)-1, -1, -1):
			if e.search(message_buffer[x][1]) != None:
				# match found!
				
				new_message = []
				# replace the message in the buffer
				try:
					new_message = [message_buffer[x][0],	e.sub(parts[2], message_buffer[x][1]).replace('\n','').replace('\r','')[:200], message_buffer[x][2]]
					del message_buffer[x]
					message_buffer.append(new_message)
				except Exception, ex:
					event.reply('%s: failure replacing: %s' % (event.nick, ex))
					return
				
				# now print the new text
				print new_message
				if new_message[2]:
					# action
					event.reply((' * %s %s' % (new_message[0], new_message[1]))[:200])
				else:
					# normal message
					event.reply(('<%s> %s' % (new_message[0], new_message[1]))[:200])
				return
		
		# no match found
		event.reply('%s: no match found' % event.nick)
	else:
		# add to buffer
		message_buffer.append([event.nick, msg[:200], False])
		
	# trim the buffer
	message_buffer = message_buffer[-MAX_MESSAGES:]

def handle_welcome(event, match):
	global NICKSERV_PASS
	# Compliance with most network's rules to set this mode on connect.
	event.connection.usermode("+B")
	if NICKSERV_PASS != None:
		event.connection.todo(['NickServ', 'identify', NICKSERV_PASS])

irc = IRC(nick=NICK, start_channels=[CHANNEL], version=VERSION)
irc.bind(handle_msg, PRIVMSG)
irc.bind(handle_welcome, RPL_WELCOME)
irc.bind(handle_ctcp, CTCP_REQUEST)

irc.make_conn(SERVER, PORT)
asyncore.loop()

