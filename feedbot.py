import re, asyncore, feedparser
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
		config.readfp(open('feedbot.ini'))
	except:
		print "Syntax:"
		print "  %s [config]" % argv[0]
		print ""
		print "If no configuration file is specified or there was an error, it will default to `feedbot.ini'."
		print "If there was a failure reading the configuration, it will display this message."
		exit(1)

# read config
SERVER = config.get('feedbot', 'server')
try: PORT = config.getint('feedbot', 'port')
except: PORT = DEFAULT_PORT
NICK = config.get('feedbot', 'nick')
CHANNEL = config.get('feedbot', 'channel')
VERSION = 'feedbot hg:%s; http://hg.micolous.id.au/ircbots/'
try: VERSION = VERSION % Popen(["hg","id"], stdout=PIPE).communicate()[0].strip()
except: VERSION = VERSION % 'unknown'
del Popen, PIPE

try: NICKSERV_PASS = config.get('feedbot', 'nickserv_pass')
except: NICKSERV_PASS = None
try: UPDATE_FREQUENCY = config.getint('feedbot', 'update_frequency')
except: UPDATE_FREQUENCY = 300

feed_urls = {}
if config.has_section('feeds'):
	for k,v in config.items('feeds'):
		feed_urls[k] = v

feeds = {}
last_feeds = {}


def announce_post(irc, feed, entry):
	global CHANNEL
	link = entry.link
	# debug
	print 'NEW POST: %s: %s (%s)' % (entry.title, link, feed)
	irc.action(CHANNEL, 'found a new post on %s: %s: %s' % (str(feed), str(entry.title), link))

def update(irc):
	global feed_urls, feeds, last_feeds
	
	last_feeds = feeds
	feeds = {}
	
	# work though the urls
	for k in feed_urls:
		try:
			# download the new feed
			if last_feeds.has_key(k) and hasattr(last_feeds[k], 'modified'):
				feeds[k] = feedparser.parse(feed_urls[k], modified=last_feeds[k].modified)
			else:
				feeds[k] = feedparser.parse(feed_urls[k])
			
			# there is data to process
			if len(feeds[k].entries) > 0:
				# see what the old feed had
				if last_feeds.has_key(k):
					# there was old feed data
					# we should see what entries are new, and stop when we encounter the last oldest one.
					# assume that the old feed has the newest entry at the time at the top
					x = 0
					for entry in feeds[k].entries:
						oldlink = False
						# see if link has been published yet
						for oldentry in last_feeds[k].entries:
							if entry.link == oldentry.link:
								oldlink = True
								break
								
						if oldlink or x > 4:
							# link has been published, or 4 links have been pushed
							print "not publishing anymore links"
							break
						
						# all good to announce
						announce_post(irc, k, entry)
						x += 1
						
				else:
					# don't publish anything, this is an initial run
					print "Not publishing all data from new feed `%s'." % k
			else:
				# there's no new data, restore the old data back in here for now.
				if last_feeds.has_key(k):
					feeds[k] = last_feeds[k]
				
			
		except:
			print "Failure updating feed `%s'." % k
			
			# revert to last version
			if last_feeds.has_key(k):
				feeds[k] = last_feeds[k]

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

