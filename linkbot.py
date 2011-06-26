#!/usr/bin/env python
"""
linkbot: IRC server linking tool
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
from thread import start_new_thread
from time import sleep
from Queue import Queue, Full

config = ConfigParser()
try:
	config.readfp(open(argv[1]))
except:
	try:
		config.readfp(open('linkbot.ini'))
	except:
		print "Syntax:"
		print "  %s [config]" % argv[0]
		print ""
		print "If no configuration file is specified or there was an error, it will default to `linkbot.ini'."
		print "If there was a failure reading the configuration, it will display this message."
		exit(1)

# get version information from git
try: VERSION = config.get('linkbot', 'version') + '; %s'
except: VERSION = 'linkbot; https://github.com/micolous/ircbots/; %s'
try: VERSION = VERSION % Popen(["git","branch","-v","--contains"], stdout=PIPE).communicate()[0].strip()
except: VERSION = VERSION % 'unknown'
del Popen, PIPE


class Network(object):
	def __init__(self, config, section):
		# setup configuration.
		self.server = config.get(section, 'server')
		try:
			self.port = config.getint(section, 'port')
		except:
			self.port = DEFAULT_PORT
		
		self.nick = config.get(section, 'nick')
		self.channel = config.get(section, 'channel').lower()
		
		try:
			self.nickserv_pass = config.get(section, 'nickserv_pass')
		except:
			self.nickserv_pass = None
			
		try:
			self.max_messages = config.getint(section, 'max_messages')
		except:
			self.max_messages = 25
		
		try:
			self.process_every = config.getint(section, 'process_every')
		except:
			self.process_every = 1
		
		try:
			self.max_msg_length = config.getint(section, 'max_message_length')
		except:
			self.max_msg_length = 512
		
		self.msgbuffer = Queue(self.max_messages)
		
		self.other_network = None
		self.active = False
		
		# setup irc client library.
		self.irc = IRC(nick=self.nick, start_channels=[self.channel], version=VERSION)
		self.irc.bind(self.handle_msg, PRIVMSG)
		self.irc.bind(self.handle_welcome, RPL_WELCOME)
		self.irc.bind(self.handle_ctcp, CTCP_REQUEST)

		
	def add_to_buffer(self, msg):
		if not self.active:
			print "dropping message: connection not active"
			return False
			

		try:
			self.msgbuffer.put(msg[:self.max_msg_length])
		except Full:
			print "queue is full, message dropped."
			return False
		else:
			return True
		
	def handle_ctcp(self, event, match):
		if event.channel.lower() == self.channel and event.args[0] == "ACTION":
			self.other_network.add_to_buffer("* %s %s" % (event.nick, event.text))
		
	def handle_msg(self, event, match):
		if event.channel.lower() != self.channel:
			# ignore messages not from our channel.
			return
		
		# now push it onto the stack.
		self.other_network.add_to_buffer("<%s> %s" % (event.nick, event.text))
	
	def handle_welcome(self, event, match):
		# most networks require this usermode be set on bots.
		event.connection.usermode("+B")
		
		# now handle nickserv.
		if self.nickserv_pass != None:
			event.connection.todo(['NickServ', 'identify', self.nickserv_pass])
		
		# indicates we're now active so processing the event queue is ok.
		self.active = True
		
	def connect(self):
		# spawn event loop
		start_new_thread(self.process_queue_loop, ())
		
		self.irc.make_conn(self.server, self.port)
		
	def process_queue_loop(self):
		while True:
			# process if true
			if self.active:
				# pull a message off the queue, blocking if none is available.
				msg = self.msgbuffer.get(block=True)
				self.irc.tell(self.channel, msg)
		
			# sleep for a moment to avoid flooding the server
			sleep(self.process_every)

# create bots for each side.
lb1 = Network(config, 'linkbot1')
lb2 = Network(config, 'linkbot2')

# join them
lb1.other_network = lb2
lb2.other_network = lb1

# connect them both to the server, and start up their internal loops
lb1.connect()
lb2.connect()

# now tell asyncore to pump
asyncore.loop()

