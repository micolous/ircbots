#!/usr/bin/env python
"""
Car IRC 0.1
Copyright 2010 Michael Farrell <http://micolous.id.au/>, licensed under the AGPL3.

Preface:

This is an IRC server that I wrote on the way home (Adelaide) from Sydney in the car.  It was written with only pydoc, unit tests being available for example code, RFC 1459 (the old IRC specification from 1993), a short packet capture of another IRC session, no internet access, and no working IRC server implementation to compare it to (only copies of irssi and Colloquy to test with).

You shouldn't ever use this software in a production environment, it's probably horribly broken in so many ways, and I don't plan on "finishing" the software unless I'm in a similar situation again.

I wrote this in about 7 hours, and it was extremely difficult to do given the circumstances.  It was a really great challenge to have and thanks to William <http://firstyear.id.au> for coming up with it.
"""
# the car irc server of awesome.
# based on asyncore
import asynchat, socket, threading, time

CRLF = '\x0d\x0a'

RPL_WELCOME = '001'
RPL_MOTDSTART = '375'
RPL_MOTD = '372'
RPL_ENDOFMOTD = '376'
RPL_PONG = 'PONG'
RPL_NAMREPLY = '353'
RPL_ENDOFNAMES = '366'
RPL_CHANNELCREATED = '329'
RPL_WHOREPLY = '352'
RPL_ENDOFWHO = '315'
RPL_CHANNELMODEIS = '324'
RPL_TOPIC = '332'
RPL_ENDOFBANLIST = '368'
RPL_ISON = '303'

RPL_WHOISUSER = '311'
RPL_WHOISSERVER = '312'
RPL_WHOISCHANNELS = '319'
RPL_ENDOFWHOIS = '318'

ERR_NOSUCHNICK = '401'
ERR_NOSUCHCHANNEL = '403'
ERR_NICKNAMEINUSE = '433'
ERR_NOTREGISTERED = '451'
ERR_ALREADYREGISTRED = '462'
ERR_UNKNOWNCOMMAND = '421'
ERR_NEEDMOREPARAMS = '461'

CMD_USER = 'USER'
CMD_NICK = 'NICK'
CMD_QUIT = 'QUIT'
CMD_JOIN = 'JOIN'
CMD_PART = 'PART'
CMD_PING = 'PING'
CMD_WHO = 'WHO'
CMD_MODE = 'MODE'
CMD_WHOIS = 'WHOIS'
CMD_PRIVMSG = 'PRIVMSG'
CMD_TOPIC = 'TOPIC'
CMD_OPER = 'OPER'
CMD_ISON = 'ISON'

MOTD_DATA = """carirc v0.1
An IRC server that was written in a car on a trip from Sydney to Adelaide, without internet connectivity.


"""

class ClientDestroyedException(Exception):
	pass

class Channel(object):
	def __init__(self, name):
		self.name = name
		self.created = long(time.time())
		self.members = []
		self.modes = 'n'
		self.topic = 'This is a placeholder topic by CAR IRC'
	
	def join(self, client):
		self.members.append(client)
		# now send headers to them
		self.send_names(client)
		self.send_topic(client)
		client.send(RPL_CHANNELCREATED, '%s %s' % (self.name, self.created))
		# broadcast join to everyone
		for user in self.members:
			user.send(CMD_JOIN, ':' + self.name, src=client.get_hostmask())
	
	def send_names(self, client):
		nicks = ''
		for user in self.members:
			nicks += user.nickname + ' '
		client.send(RPL_NAMREPLY, '= %s :%s' % (self.name, nicks))
		client.send(RPL_ENDOFNAMES, self.name + ' :End of /NAMES list')
		
	def send_who(self, client):
		for user in self.members:
			client.send(RPL_WHOREPLY, '%s %s %s localhost %s H :0 %s' % (self.name, user.nickname, user.hostname, user.username, user.gecos))
		client.send(RPL_ENDOFWHO, self.name + ' :End of /WHO list')
	
	def send_modes(self, client):
		client.send(RPL_CHANNELMODEIS, self.name + ' +' + self.modes)
	
	def send_topic(self, client):
		client.send(RPL_TOPIC, self.name + ' :' + self.topic)
	
	def broadcast_topic(self):
		for member in self.members:
			self.send_topic(member)
	
	def send_message(self, src, msg):
		# distribute the message to all except the source
		for user in self.members:
			if user != src:
				user.send(CMD_PRIVMSG, self.name + ' :' + msg, src=src.get_hostmask())
	
	def user_part(self, src):
		# distribute the part to all members
		for user in self.members:
			user.send(CMD_PART, self.name + ' :', src=src.get_hostmask())
		self.members.remove(user)
	
	def send_banlist(self, client):
		client.send(RPL_ENDOFBANLIST, self.name + ' :End of channel ban list')
	
	
class ClientHandler(threading.Thread):
	def __init__(self, server, conn, client):
		threading.Thread.__init__(self)
		self.server = server
		self.conn = conn
		self.client = client
		self.buffer = ''
		self.got_user = False
		self.got_nick = False
		self.sent_welcome = False
		self.channels = []
		
		self.nickname = ''
		self.username = ''
		self.gecos = ''
		self.hostname = self.client[0]
	
	def run(self):
		while True:
			try:
				data = self.conn.recv(1)
			except socket.error:
				# disconnect this client from the server
				self.server.client_destroy(self)
			if not data:
				break
			self.buffer = self.buffer + data
			
			# check for a terminator
			if CRLF in self.buffer:
				# there's a terminator in the buffer, we need to split things
				
				# find the commands that are complete
				lastCrlfPos = self.buffer.rfind(CRLF)
				
				buffer_to_process = self.buffer[:lastCrlfPos]
				self.buffer = self.buffer[lastCrlfPos+len(CRLF):]
				
				commands = buffer_to_process.split(CRLF)
				
				for command in commands:
					print "got a command: %s" % command
					# now split up the command
					text = None
					if ':' in command:
						command, text = command.split(':', 1)
						command = command[:-1]
					
					args = command.split(' ')
					self.command_handler(args, text)
			
			# now continue
	def disconnect(self):
		self.conn.close()
		self.server.client_destroy(self)
		raise ClientDestroyedException()
	
	def command_handler(self, args, text):
		print "command_handler(%s, %s)" % (args, text)
		
		# do a cleanup
		self.server.cleanup()
		
		if args[0] == CMD_USER and not self.got_user:
			# record the client userinfo
			if len(args) != 4:
				# it's invalid.
				print "invalid %s command recieved" % CMD_USER
				self.disconnect()
				
			self.username = args[1]
			self.gecos = text
			self.got_user = True
		elif args[0] == CMD_NICK and not self.got_nick:
			# check for nick availability
			nick = args[1].lower()
			if self.server.nicks.has_key(nick):
				# nick clash, fail
				self.send(ERR_NICKNAMEINUSE, args[1] + ' :That nickname is already in use.')
			else:
				self.nickname = args[1]
				self.server.nicks[nick] = self
				self.got_nick = True
		
		elif self.got_nick and self.got_user: # commands that are in the normal context
			if args[0] == CMD_USER:
				self.send(ERR_ALREADYREGISTRED, ':You may not re-register')
			elif args[0] == CMD_NICK:
				# check to see if the nick is taken
				nick = args[1].lower()
				if self.server.nicks.has_key(nick):
					# nick is in use
					self.send(ERR_NICKNAMEINUSE, args[1] + ' :That nickname is already in use.')
				else:
					# nick available
					# do the switch
					del self.server.nicks[self.nickname]
					self.nickname = args[1]
					self.server.nicks[nick] = self
			elif args[0] == CMD_QUIT:
				self.send(CMD_QUIT, ':Goodbye')
				self.disconnect()
			elif args[0] == CMD_PING:
				self.send(RPL_PONG, ' '.join(args[1:]))
			elif args[0] == CMD_JOIN:
				# lets see if we can join the channel
				if args[1][0] == '#':
					# valid channel
					channel = self.server.get_channel(args[1])
					
					# add them in
					channel.join(self)
					self.channels.append(channel)
				else:
					# invalid channel
					self.send(ERR_NOSUCHCHANNEL, args[1] + ' :No such channel')
			elif args[0] == CMD_PART:
				# part the channel
				channel = self.server.get_channel(args[1])
				# make sure they're a member
				if self in channel.members:
					channel.user_part(self)
				self.channels.remove(channel)
			elif args[0] == CMD_WHO:
				# find out who is in the channel
				channel = self.server.get_channel(args[1])
				channel.send_who(self)
			elif args[0] == CMD_MODE:
				channel = self.server.get_channel(args[1])
				# if +b is sent, send a banlist
				if len(args) > 2 and args[2] == 'b':
					channel.send_banlist(self)
				else:
					channel.send_modes(self)
			elif args[0] == CMD_WHOIS:
				self.whois(args[1])
			elif args[0] == CMD_PRIVMSG:
				if text == None:
					# check to see if there's a message to send
					self.send(ERR_NEEDMOREPARAMS, args[0] + ' :You need to say something, stupid')
				else:
					# see if it's a public or private message
					if args[1][0] == '#':
						# channel message
						channel = self.server.get_channel(args[1])
						channel.send_message(self, text)
					else:
						# TODO private message
						# send it to the other user
						target = args[1].lower()
						if self.server.nicks.has_key(target):
							self.server.nicks[target].send(CMD_PRIVMSG, ':' + text, src=self.get_hostmask())
						else:
							self.send(ERR_NOSUCHNICK, args[1] + ' :No such person exists')
			elif args[0] == CMD_TOPIC:
				channel = self.server.get_channel(args[1])
				if text == None:
					# topic request
					channel.send_topic(self)
				else:
					# topic set
					channel.topic = text
					channel.broadcast_topic()
			elif args[0] == CMD_ISON:
				# check to see which of the people are online
				print 'server.nicks = %s' % self.server.nicks
				online_users = []
				for query in args[1:]:
					if self.server.nicks.has_key(query.lower()):
						online_users.append(query)
				
				# send reply
				self.send(RPL_ISON, ':' + (' '.join(online_users)))
			else:
				# unknown command
				self.send(ERR_UNKNOWNCOMMAND, args[0] + ' :wtf ru doin?!')
		else:
			# tried to send commands when not registered
			self.send(ERR_NOTREGISTERED, ':You have not registered')
			
		if self.got_nick and self.got_user and not self.sent_welcome:
			# we've got all the messages we need to log in
			# so lets start processing stuff
			self.sent_welcome = True
			self.send(RPL_WELCOME, 'Welcome to a CAR IRC Network')
			
			# print out motd
			self.send(RPL_MOTDSTART, 'Message of the day:')
			for line in MOTD_DATA.split('\n'):
				self.send(RPL_MOTD, '- ' + line)
			self.send(RPL_ENDOFMOTD, 'End of MOTD')
	
	def send(self, code, msg, src=None):
		if src == None:
			output = ':localhost %s %s %s%s' % (code, self.nickname, msg, CRLF)
		else:
			output = ':%s %s %s%s' % (src, code, msg, CRLF)
		print 'sending %s' % output
		self.conn.send(output)
	
	def whois(self, who):
		# lookup the user
		who = who.lower()
		if self.server.nicks.has_key(who):
			# the user exists
			who = self.server.nicks[who]
			channellist = ''
			for channel in who.channels:
				channellist += channel.name + ' '
			self.send(RPL_WHOISUSER, '%s %s %s * :%s' % (who.nickname, who.username, who.hostname, who.gecos))
			self.send(RPL_WHOISSERVER, '%s localhost :CAR IRC LOL' % who.nickname)
			self.send(RPL_WHOISCHANNELS, '%s :%s' % (who.nickname, channellist))
			self.send(RPL_ENDOFWHOIS, '%s :End of /WHOIS' % who.nickname)
			
		else:
			# the user doesn't exist
			self.send(ERR_NOSUCHNICK, who + ' :No such person exists')
			
	def send_quit(self, hostmask, msg):
		self.send(CMD_QUIT, ':' + msg, src=hostmask)
		
	def get_hostmask(self):
		return '%s!%s@%s' % (self.nickname, self.username, self.hostname)

class irc_server(threading.Thread):
	# parameter to determine the number of bytes passed back to the
	# client each send
	chunk_size = 512
	
	def __init__(self, event, host = '0.0.0.0', port = 6667):
		threading.Thread.__init__(self)
		self.event = event
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.bind((host, port))
		self.clients = []
		self.channels = {}
		self.nicks = {}
		
	def run(self):
		self.sock.listen(1)
		self.event.set()
		while True:
			conn, client = self.sock.accept()
			print "got client connection from %s" % (client, )
			# dispatch a thread to handle the client
			client_handler = ClientHandler(self, conn, client)
			client_handler.start()
			
			self.clients.append(client_handler)
			
		#conn.close()
		self.sock.close()
	
	def client_destroy(self, client):
		print "client disconnected on %s" % (client.client,)
		self.clients.remove(client)
		quit_message_recipients = []
		for channel in client.channels:
			channel.members.remove(client)
			# copy list of users to here
			for member in channel.members:
				if member not in quit_message_recipients:
					quit_message_recipients.append(member)
		
		# delete from the nicklist
		del self.nicks[client.nickname.lower()]
		# delete client
		del client
		
		# now we have a list of people to send quit messages
		# we should tell them all that Bexi likes arms.
		for member in quit_message_recipients:
			member.send_quit(client, 'Bexi enjoys arms and v-line buses.')
		
	
	def get_channel(self, channel_name):
		# see if the channel exists
		if not self.channels.has_key(channel_name):
			self.channels[channel_name] = Channel(channel_name)
		return self.channels[channel_name]
		
	def cleanup(self):
		# do some cleanup tasks to free some memory
		# hopefully python's resource counter will properly detect the object as something
		# that can be disposed of
		to_delete = []
		for channel in self.channels.values():
			if len(channel.members) == 0:
				to_delete.append(channel)
		
		for channel in to_delete:
			del self.channels[channel.name]
		del to_delete
		

def start_irc_server():
    event = threading.Event()
    s = irc_server(event)
    s.start()
    event.wait()
    event.clear()
    time.sleep(0.01) # Give server time to start accepting.
    return s, event

if __name__ == "__main__":
	start_irc_server()
