import irclib, re
from datetime import datetime, timedelta

message_buffer = []
MAX_MESSAGES = 15
last_message = datetime.now()

def handle_pubmsg(connection, event):
  global message_buffer, MAX_MESSAGES, last_message
  nick = event.source().partition("!")[0]
  msg = event.arguments()[0]
  
  if msg.startswith('s/'):
    # handle regex
    parts = msg.split('/')
    
    # now flood protect!
    now = datetime.now()
    delta = now - last_message
    last_message = now
    
    if delta < timedelta(seconds=5):
      # 5 seconds between requests
      # any more are ignored
      print "Flood protection hit, %s of %s seconds were waited" % (delta.seconds, timedelta(seconds=5).seconds)
      connection.kick(event.target(), nick, 'Flood protection activated')
      
      return 
    
    if len(message_buffer) == 0:
      connection.privmsg(event.target(), '%s: message buffer is empty' % nick)
      return
    
    if len(parts) == 3:
      connection.privmsg(event.target(), '%s: invalid regular expression, you forgot the trailing slash, dummy' % nick)
      return
    
    if len(parts) != 4:
      # not a valid regex
      connection.privmsg(event.target(), '%s: invalid regular expression, not the right amount of slashes' % nick)
      return
    
    # find messages matching the string
    if len(parts[1]) == 0:
      connection.privmsg(event.target(), '%s: original string is empty' % nick)
      return
      
    ignore_case = 'i' in parts[3]
    
    e = None
    try:
      if ignore_case:
        e = re.compile(parts[1], re.I)
      else:
        e = re.compile(parts[1], re.I)
    except Exception, ex:
      connection.privmsg(event.target(), '%s: failure compiling regular expression: %s' % (nick, ex))
      return
    
    # now we have a valid regular expression matcher!
    
    for x in range(len(message_buffer)-1, -1, -1):
      if e.search(message_buffer[x][1]) != None:
        # match found!
        
        new_message = []
        # replace the message in the buffer
        try:
          new_message = [message_buffer[x][0],  e.sub(parts[2], message_buffer[x][1]).replace('\n','').replace('\r','')[:200]]
          del message_buffer[x]
          message_buffer.append(new_message)
        except Exception, ex:
          connection.privmsg(event.target(), '%s: failure replacing: %s' % (nick, ex))
          return
        
        # now print the new text
        print new_message
        connection.privmsg(event.target(), ('<%s> %s' % (new_message[0], new_message[1]))[:200])
        return
    
    # no match found
    connection.privmsg(event.target(), '%s: no match found' % nick)    
  else:
    # add to buffer
    message_buffer.append([nick, msg[:200]])
    
  # trim the buffer
  message_buffer = message_buffer[-MAX_MESSAGES:]

irc = irclib.IRC()
irc.add_global_handler('pubmsg', handle_pubmsg)
server = irc.server()
server.connect("irc.micolous.id.au", 6667, "regexbot")
server.join("#streetgeek")
irc.process_forever()
