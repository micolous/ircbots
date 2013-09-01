#!/usr/bin/python
"""

ircAsync -- An asynchronous IRC client interface.

This is intended as a component in a semantic web agent
with several interfaces, one of them being IRC.
It's implemented on top of asyncore so that the same
agent can export an HTTP interface in asynchronous,
non-blocking style.

see Log at end for recent changes/status info.

Share and Enjoy. Open Source license:
Copyright (c) 2001 W3C (MIT, INRIA, Keio)
http://www.w3.org/Consortium/Legal/copyright-software-19980720

$Id: ircAsync.py,v 1.9 2003/10/15 01:54:10 timbl Exp $

Contains various improvements by Michael Farrell <http://micolous.id.au> (2010)
to make it a lot nicer to work with, and updated to take advantage of new
features in recent versions of Python.

The improvements are a work in progress.  It is hoped from this will be a good,
general-purpose IRC library for Python.


"""

# asyncore -- Asynchronous socket handler 
# http://www.python.org/doc/current/lib/module-asyncore.html

import re, socket, asyncore, asynchat
from datetime import datetime

#RFC 2811: Internet Relay Chat: Client Protocol
#2.3 Messages
# http://www.valinor.sorcery.net/docs/rfc2812/2.3-messages.html
SPC="\x20"
CR="\x0d"
LF="\x0a"
CRLF=CR+LF
DEFAULT_PORT = 6667

# commands...
PRIVMSG = 'PRIVMSG'
NOTICE = 'NOTICE'
PING='PING'
PONG='PONG'
USER='USER'
NICK='NICK'
JOIN='JOIN'
PART='PART'
INVITE='INVITE'
QUIT='QUIT'
MODE='MODE'
CHANSERV='CHANSERV'
NICKSERV='NICKSERV'
TOPIC='TOPIC'
ISON='ISON'
# UnrealIRCd-specific commands
AB='AB;'
HELPOP='HELPOP'

# pseudo-message types we use internally
CTCP_REQUEST='CTCP_REQUEST'
CTCP_RESPONSE='CTCP_RESPONSE'

# reply codes...
RPL_WELCOME='001'

class IRCEvent:
	"""Represents an event on IRC.
	
	The event_type is an IRC command / event that is sent from the server.  Some
	extra useful bits:
	
	 - nick: The nickname of the user who sent the message, if available.
	 - user: The username of the user who sent the message, if available.
	 - host: The hostname of the user who sent the message, if available.
	
	channel will be set to the name of the channel where the message came from, or
	the name of the user (if it was a private message). 
	"""
	 
	def __init__(self, connection, event_type, args, text, origin=None):
		self.connection = connection
		self.when = datetime.now()
		self.event_type = event_type
		self.args = args
		self.text = text
		
		# now setup nice things
		self.origin = origin
		if origin != None:
			self.nick, self.user, self.host = self.__split_origin(origin)
		else:
			self.nick = self.user = self.host = None
			
		if event_type in (NOTICE, PRIVMSG, CTCP_REQUEST, CTCP_RESPONSE, PART):
			if args[0] == self.connection.nick:
				self.channel = self.nick				
			else:
				self.channel = args[0]
			
			# shift arguments across
			if len(args) > 1:
				self.args = args[1:]
			else:
				self.args = []
		elif event_type in (JOIN,):
			self.channel = text
		else:
			self.channel = None
	
	def reply(self, msg):
		"""Replies to a message.  Only works for PRIVMSG, NOTICE, and CTCP_REQUEST."""
		if self.event_type == PRIVMSG:
			self.connection.tell(self.channel, msg)
		elif self.event_type == NOTICE:
			self.connection.notice(self.channel, msg)
		elif self.event_type == CTCP_REQUEST:
			# ctcp response should be sent with the same command type
			# directly to the requesting user (and not the channel)
			self.connection.ctcp_response(self.nick, self.args[0], msg)
		else:
			raise Exception, "cannot reply to a %s" % self.event_type
		
	def __split_origin(self, origin):
		if origin and '!' in origin:
			nick, userHost = origin.split('!', 1)
			if '@' in userHost:
				user, host = userHost.split('@', 1)
			else:
				user, host = userHost, None
		else:
			nick = origin
			user, host = None, None
		return nick, user, host

class IRC(asynchat.async_chat):
	def __init__(self, nick='ircAsync', user=None, full_name=None, start_channels=['#test'], builtin_ctcp=True, version='ircAsync Sample 2010'):
		"""Initialises a new IRC client.
		
		builtin_ctcp - Provide hanlders for CTCP VERSION and CTCP TIME.  You can
		overwrite the sent version string in the 'version' attribute.  This will
		make these two events NOT flow through to dispatchers.  By default this is
		turned on.
		"""
		asynchat.async_chat.__init__(self)
		self.bufIn = ''
		self.set_terminator(CRLF)

		# public attributes
		# no blanks in nick.
		# openprojects.net says:
		# Connect with your real username, in lowercase.
		# If your mail address were foo@bar.com, your username would be foo.
		# other limitations? @@see IRC RFC?"""

		self.nick = nick
		if user == None:	
			user = nick
		self.user = user
		if full_name == None:
			full_name = nick
		self.full_name = full_name
		self.version = version
		self.builtin_ctcp = builtin_ctcp
		self._startChannels = start_channels
		self._dispatch = []
		self._doc = []
		
	def make_conn(self, host, port=DEFAULT_PORT, ipv6=False):
		if ipv6:
			self.create_socket(socket.AF_INET6, socket.SOCK_STREAM)
		else:
			self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		debug("connecting to...", host, port)
		self.connect((host, port))

		self.bufIn = ''

	def todo(self, args, *text):
		command = ' '.join(args)
		if text: command = command + ' :' + ' '.join(text)
		
		
		# remove newline characters because they can cause problems and command
		# injection
		if '\r' in command or '\n' in command:
			debug("WARNING! you sent some newline characters in that message.  they have been removed.")
		command = command.replace('\r','').replace('\n','')
		comm  = command.decode('utf-8', 'replace')
		command = comm.encode('utf-8')
		self.push(command + CRLF)
		debug("sent/pushed command:", command)

	# asyncore methods
	def handle_connect(self):
		debug("connected")

		#@@ hmm... RFC says mode is a bitfield, but
		# irc.py by @@whathisname says +iw string.
		self.todo([NICK, self.nick])
		self.todo([USER, self.user, "+iw", self.nick], self.full_name)


	# asynchat methods
	def collect_incoming_data(self, bytes):
		self.bufIn = self.bufIn + bytes

	def found_terminator(self):
		#debug("found terminator", self.bufIn)
		line = self.bufIn
		self.bufIn = ''

		if line[0] == ':':
			origin, line = line[1:].split(' ', 1)
		else:
			origin = None

		try:
			args, text = line.split(' :', 1)
		except ValueError:
			args = line
			text = ''
		args = args.split()
		
		if text.startswith('\x01') and text.endswith('\x01'):
			# change to being a CTCP
			if args[0] == PRIVMSG:
				args[0] = CTCP_REQUEST
			elif args[0] == NOTICE:
				args[0] = CTCP_RESPONSE
			text = text[1:-1]
			ctcp_parts = text.split(' ', 1)
			
			args.append(ctcp_parts[0])
			if len(ctcp_parts) == 2:
				text = ctcp_parts[1]
			else:
				text = ""

		debug("from::", origin, "|message::", args, "|text::", text)

		self.rx_msg(args, text, origin)

	def bind(self, thunk, command, textPat=None, doc=None):
		"""
		thunk is the routine to bind; it's called ala
		  thunk(connection, matchObj or None, origin, args, text)
		
		command is one of the commands above, e.g. PRIVMSG
		textpat is None or a regex object or string to compile to one
		
		doc should be a list of strings; each will go on its own line"""

		if type(textPat) is type(""): textPat = re.compile(textPat)

		self._dispatch.append((command, textPat, thunk))

		if doc: self._doc = self._doc + doc

	def rx_msg(self, args, text, origin):
		event = IRCEvent(self, args[0], args[1:], text, origin)
		
		# do autojoin
		if event.event_type == RPL_WELCOME:
			self._welcome_join(event, None)
			
		# respond to ping
		if event.event_type == PING:
			self.todo([PONG, text])
			
		# handle server-enforced nick changes
		if event.event_type == NICK and event.nick == self.nick:
			self.nick = args[1]
			
		# handle CTCP internally?
		if self.builtin_ctcp and event.event_type == CTCP_REQUEST:
			if event.args[0] == "VERSION":
				event.reply(self.version)
				return
			elif event.args[0] == "TIME":
				event.reply(event.when.isoformat(' '))
				return
				
		for cmd, pat, thunk in self._dispatch:
			if args[0] == cmd:
				if pat:
					#debug('dispatching on...', pat)
					m = pat.search(text)
					if m:
						thunk(event, m)
				else:
					thunk(event, None)

	def start_channels(self, chans):
		self._startChannels = chans
		#self.bind(self._welcome_join, RPL_WELCOME)
				  
	def _welcome_join(self, event, m):
		for chan in self._startChannels:
			self.todo([JOIN, chan])

	def tell(self, dest, text):
		"""send a PRIVMSG to dest, a channel or user"""
		self.todo([PRIVMSG, dest], text)

	def tell_lines(self, dest, text):
		lines = text.split("\n")
		for line in lines:
			self.tell(dest, line)
		
	def notice(self, dest, text):
		"""send a NOTICE to dest, a channel or user"""
		self.todo([NOTICE, dest], text)
	
	def usermode(self, mode):
		"""Sets your usermodes"""
		self.todo([MODE, self.nick, mode])
		
	def ctcp_request(self, dest, command, args=""):
		"""Sends a CTCP Request to a client or channel"""
		self.tell(dest, '\x01%s %s\x01' % (command, args))
	
	def ctcp_response(self, dest, command, args=""):
		"""Sends a CTCP Response to a client or channel"""
		self.notice(dest, '\x01%s %s\x01' % (command, args))
		
	def action(self, dest, msg=""):
		"""Sends a CTCP ACTION to a client or channel."""
		self.ctcp_request(dest, 'ACTION', msg)
	
	def topic(self, channel, text=""):
		"Sets the topic in a channel"
		self.todo([TOPIC, channel], text)
	
	def chanserv_topic(self, channel, text=""):
		"Sets the topic in a channel via chanserv"
		self.todo([CHANSERV, TOPIC, channel, text])
	
	def ab(self, command):
		"Sends UnrealIRCd AB command ;-)"
		self.todo([AB, command])

# cf irc:// urls in Mozilla
# http://www.mozilla.org/projects/rt-messaging/chatzilla/irc-urls.html
# Tue, 20 Mar 2001 21:28:14 GMT

def serverAddr(host, port):
	if port == Port: portPart = ''
	else: portPart = ":%s" % port
	return "irc://%s%s/" % (host, portPart)
		
def chanAddr(host, port, chan):
	if port == Port: portPart = ''
	else: portPart = ":%s" % port
	if chan[0] == '&': chanPart = '%26' + chan[1:]
	elif chan[0] == '#': chanPart = chan[1:]
	else: raise ValueError # dunno what to do with this channel name
	return "irc://%s%s/%s" % (host, portPart, chanPart)
		
def debug(*args):
	import sys
	reload(sys)
	sys.setdefaultencoding('utf-8')
	sys.stderr.write("DEBUG: ")
	for a in args:
		sys.stderr.write(str(a))
	sys.stderr.write("\n")


def test(host_name, port, chan):
	c = IRC(start_channels=[chan])

	def spam(event, m):
		event.reply("spam, spam, eggs, and spam!")
	c.bind(spam, PRIVMSG, r"spam\?")

	def bye(event, m):
		event.connection.todo([QUIT], "bye bye!")
	c.bind(bye, PRIVMSG, r"bye bye bot")

	c.make_conn(host_name, port)
	asyncore.loop()
	
	
if __name__=='__main__':
	test('localhost', 6667, '#test')
