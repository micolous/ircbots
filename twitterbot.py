#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
twitterbot: Shows tweets for Twitter URLs posted on IRC.
Copyright 2011 Rob McFadzean
Copyright 2011 - 2012 Michael Farrell

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

import asyncore, random, re, twitter, urllib2, exceptions
from configparser_plus import ConfigParserPlus
from datetime import datetime, timedelta
from sys import argv, exit
from ircasync import *
from subprocess import Popen, PIPE
try:
	from geopy import geocoders
	geocoder = geocoders.Google()
except ImportError:
	print "geopy isn't installed, geocoder support disabled."
	geocoder = None


DEFAULT_CONFIG = {
	'twitterbot': {
		'server': 'localhost',
		'port': DEFAULT_PORT,
		'ipv6': 'no',
		'nick': 'twitterbot',
		'channel': '#test',
		'flood_cooldown': 5,
		'version': 'twitterbot; https://github.com/micolous/ircbots/',
	}
}

config = ConfigParserPlus(DEFAULT_CONFIG)
try:
	config.readfp(open(argv[1]))
except:
	try:
		config.readfp(open('twitterbot.ini'))
	except:
		print "Syntax:"
		print "  %s [config]" % argv[0]
		print ""
		print "If no configuration file is specified or there was an error, it will default to `twitterbot.ini'."
		print "If there was a failure reading the configuration, it will display this message."
		exit(1)

SERVER = config.get('twitterbot', 'server')
PORT = config.getint('twitterbot', 'port')
IPV6 = config.getboolean('twitterbot', 'ipv6')
NICK = config.get('twitterbot', 'nick')
CHANNEL = config.get('twitterbot', 'channel')
VERSION = config.get('regexbot', 'version') + '; %s'
try: VERSION = VERSION % Popen(["git","branch","-v","--contains"], stdout=PIPE).communicate()[0].strip()
except: VERSION = VERSION % 'unknown'
del Popen, PIPE

FLOOD_COOLDOWN = timedelta(seconds=config.getint('twitterbot', 'flood_cooldown'))
try: NICKSERV_PASS = config.get('twitterbot', 'nickserv_pass')
except: NICKSERV_PASS = None

tweetURLRegex = re.compile(r"(http(s?):\/\/twitter.com\/.*\/statuse?s?\/([0-9]{0,20}))")
message_buffer = []
last_message = datetime.now()
flooders = []
try:
	# old versions of python-twitter use this.
	twitterApi = twitter.Api()
except AttributeError:
	# 'twitter' in pip is an incompatible library.
	print "You've installed the library called `twitter` from pip, rather than `python-twitter`.  Go fix that."
	print "You'll need to completely remove the other library, try deleting /usr/local/lib/pythonX.X/dist-packages/twitter/"
	exit(1)
        
def handle_msg(event, match):
	global message_buffer, MAX_MESSAGES, last_message, flooders, CHANNEL, twitter_api
	msg = event.text
	
	if event.channel.lower() != CHANNEL.lower():
		# ignore messages not from our channel
		return
	
	if tweetURLRegex.search(msg):
		tweetIDRegex = re.compile(r".*/statuse?s?\/([0-9]{0,20})") 
		
		delta = event.when - last_message
		last_message = event.when
		error = ""
		line = ""
		
		if delta < FLOOD_COOLDOWN:
			print "Flood protection hit, %s of %s seconds were waited" % (delta.seconds, FLOOD_COOLDOWN.seconds)
			return
		
		tweetID = tweetIDRegex.search(msg).groups()[0]
		try:
			tweet = twitterApi.GetStatus(tweetID)
			
			line = u"%s => %s" % (tweet.user.screen_name, tweet.text.replace('\n', ' ').replace('\r',''))
			
			if geocoder != None and tweet.geo != None and tweet.geo['type'] == 'Point':
				try:
					address, point = geocoder.reverse(tweet.geo['coordinates'])
					line += u" (from %s)" % address
				except NotImplementedError:
					print "Warning: Your version of geopy lacks reverse geocoder support.  Not doing anything with the geographic data."
				
		except twitter.TwitterError, e:
			if e.message == "No status found with that ID.":
			   error = "Tweet not found"
			if e.message == "Sorry, you are not authorized to see this status.":
				error = "Tweet is private"
		except urllib2.HTTPError, e:
			error = "Twitter API failure - try again later."
		except Exception, e:
			error = "Something really bad happened, something about a %s?" % e
			
		if error:
			irc.action(CHANNEL,"Error => %s" % error)
		if line:
			irc.action(CHANNEL, line.encode('utf-8'))

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

