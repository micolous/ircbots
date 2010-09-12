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
NICK = config.get('gamebot', 'nick')
CHANNEL = config.get('gamebot', 'channel')
VERSION = 'gamebot hg:%s; http://hg.micolous.id.au/ircbots/'
try: VERSION = VERSION % Popen(["hg","id"], stdout=PIPE).communicate()[0].strip()
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
irc.make_conn(SERVER, PORT)
start_new_thread(game_updater, (irc,))
asyncore.loop()

