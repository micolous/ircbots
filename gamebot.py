#!/usr/bin/env python
"""
gamebot: Ensures loss of the game.
Copyright 2010 Michael Farrell <http://micolous.id.au>

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
from time import sleep
from ConfigParser import ConfigParser
from sys import argv, exit
from ircasync import *
from subprocess import Popen, PIPE
from thread import start_new_thread

config = ConfigParser()
try:
	config.readfp(open(argv[1]))
except:
	try:
		config.readfp(open('gamebot.ini'))
	except:
		print "Syntax:"
		print "  %s [config]" % argv[0]
		print ""
		print "If no configuration file is specified or there was an error, it will default to `gamebot.ini'."
		print "If there was a failure reading the configuration, it will display this message."
		exit(1)

# read config
SERVER = config.get('gamebot', 'server')
try: PORT = config.getint('gamebot', 'port')
except: PORT = DEFAULT_PORT
try: IPV6 = ( config.getint('gamebot', 'ipv6_support') == "yes" )
except: IPV6 = False
NICK = config.get('gamebot', 'nick')
CHANNEL = config.get('gamebot', 'channel')
VERSION = 'gamebot; https://github.com/micolous/ircbots/; %s'
try: VERSION = VERSION % Popen(["git","branch","-v","--contains"], stdout=PIPE).communicate()[0].strip()
except: VERSION = VERSION % 'unknown'
del Popen, PIPE

try: NICKSERV_PASS = config.get('gamebot', 'nickserv_pass')
except: NICKSERV_PASS = None

def update(irc):
	irc.action(CHANNEL, 'would like to inform you that you all just lost the game.')

def game_updater(irc):
	while True:
		sleep(30*60)
		update(irc)

# main code
def handle_welcome(event, match):
	global NICKSERV_PASS
	# Compliance with most network's rules to set this mode on connect.
	event.connection.usermode("+B")
	if NICKSERV_PASS != None:
		event.connection.todo(['NickServ', 'identify', NICKSERV_PASS])
	update(event.connection)

irc = IRC(nick=NICK, start_channels=[CHANNEL], version=VERSION)
irc.bind(handle_welcome, RPL_WELCOME)
irc.make_conn(SERVER, PORT, ipv6=IPV6)
start_new_thread(game_updater, (irc,))
asyncore.loop()

