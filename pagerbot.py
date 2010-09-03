import re, asyncore
from time import sleep, time
from ConfigParser import ConfigParser
from sys import argv, exit
from ircasync import *
from subprocess import Popen, PIPE
from thread import start_new_thread
from datetime import datetime
import simplejson as json
from urllib2 import urlopen

config = ConfigParser()
try:
	config.readfp(open(argv[1]))
except:
	try:
		config.readfp(open('pagerbot.ini'))
	except:
		print "Syntax:"
		print "  %s [config]" % argv[0]
		print ""
		print "If no configuration file is specified or there was an error, it will default to `pagerbot.ini'."
		print "If there was a failure reading the configuration, it will display this message."
		exit(1)

# read config
SERVER = config.get('pagerbot', 'server')
try: PORT = config.getint('pagerbot', 'port')
except: PORT = DEFAULT_PORT
NICK = config.get('pagerbot', 'nick')
CHANNEL = config.get('pagerbot', 'channel')
VERSION = 'pagerbot hg:%s; http://hg.micolous.id.au/ircbots/'
try: VERSION = VERSION % Popen(["hg","id"], stdout=PIPE).communicate()[0].strip()
except: VERSION = VERSION % 'unknown'
del Popen, PIPE

try: NICKSERV_PASS = config.get('pagerbot', 'nickserv_pass')
except: NICKSERV_PASS = None
try: UPDATE_FREQUENCY = config.getint('pagerbot', 'update_frequency')
except: UPDATE_FREQUENCY = 10

FEED = 'http://paging.sacfs.org/feed1/live/ajax/update.php?f='
LAST_UPDATE = int(time())


def strip_tags(value):
	"Return the given HTML with all tags stripped."
	return re.sub(r'<[^>]*?>', '', value)

def update(irc):
	global LAST_UPDATE, CHANNEL
	#	try:
	if 1:
		# download the new feed
		fp = urlopen(FEED + str(LAST_UPDATE))
		data = json.load(fp)
		LAST_UPDATE = data['timestamp']
		
		messages_sent = 0
		if data['updated']:
		
			# feed was updated, start posting.
			messages = data['data'].split('<tr class="page">')
			for message in messages[1:]:
				# parse this out...
				msg_text = strip_tags(message)
				irc.action(CHANNEL, msg_text)
				
				messages_sent += 1
				if messages_sent > 4:
					print "message limit reached"
					break
#	except:
#		print "Failure updating feed."
def feed_updater(irc):
	global UPDATE_FREQUENCY
	
	while True:
		sleep(UPDATE_FREQUENCY)
		print "Naptime over, updating..."
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
start_new_thread(feed_updater, (irc,))
asyncore.loop()

