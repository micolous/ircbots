#!/usr/bin/env python
import asyncore, random, re, twitter, urllib2
from ConfigParser import ConfigParser
from datetime import datetime, timedelta
from sys import argv, exit
from ircasync import *
from subprocess import Popen, PIPE

config = ConfigParser()
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
try: PORT = config.getint('twitterbot', 'port')
except: PORT = DEFAULT_PORT
NICK = config.get('twitterbot', 'nick')
CHANNEL = config.get('twitterbot', 'channel')
VERSION = 'twitterbot hg:%s; http://hg.micolous.id.au/ircbots/'
try: VERSION = VERSION % Popen(["hg","id"], stdout=PIPE).communicate()[0].strip()
except: VERSION = VERSION % 'unknown'
del Popen, PIPE

try: FLOOD_COOLDOWN = timedelta(seconds=config.getint('twitterbot', 'flood_cooldown'))
except: FLOOD_COOLDOWN = timedelta(seconds=5)
try: NICKSERV_PASS = config.get('twitterbot', 'nickserv_pass')
except: NICKSERV_PASS = None

tweetURLRegex = re.compile(r"(http(s?):\/\/twitter.com\/.*\/status\/([0-9]{0,20}))")
message_buffer = []
last_message = datetime.now()
flooders = []

def handle_msg(event, match):
    global message_buffer, MAX_MESSAGES, last_message, flooders, CHANNEL
    msg = event.text
    
    if event.channel.lower() != CHANNEL.lower():
        # ignore messages not from our channel
        return
    
    if tweetURLRegex.search(msg):
        tweetIDRegex = re.compile(r".*/status\/([0-9]{0,20})") 
        twitterApi = twitter.Api()
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
            line = "{0} => {1}".format(tweet.user.screen_name, tweet.text)
        except twitter.TwitterError, e:
                if e.message == "No status found with that ID.":
                   error = "Tweet not found"
                if e.message == "Sorry, you are not authorized to see this status.":
                    error = "Tweet is private"
        if error:
            irc.action(CHANNEL,"Oshi, error!: %s" % error)
        if line:
            irc.action(CHANNEL, line)

def handle_welcome(event, match):
    global NICKSERV_PASS
    # Compliance with most network's rules to set this mode on connect.
    event.connection.usermode("+B")
    if NICKSERV_PASS != None:
        event.connection.todo(['NickServ', 'identify', NICKSERV_PASS])

irc = IRC(nick=NICK, start_channels=[CHANNEL], version=VERSION)
irc.bind(handle_msg, PRIVMSG)
irc.bind(handle_welcome, RPL_WELCOME)

irc.make_conn(SERVER, PORT)
asyncore.loop()

