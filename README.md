# micolous/ircbots #

IRC bots created for the #blackhats IRC network.  The bots all follow a pretty similar structure.  Not all the bots are in use, but they're kept in this repository for historical purposes.

This includes a Python IRC library, `ircasync.py`.  The library was originally written by W3C, but I've made some additions and changes to make it more Pythonic.  The library still needs some work though.

There's also an IRC server (carirc) that I wrote as a competition with @aktowns while in a car coming home from Sydney.  More details of the competition parameters and implementation details are in it's source file, `ircserver.py`.  It only implements a subset of the IRC protocol (enough to make clients happy) and does some things strangely.

## Implementation of the Global Cooldown Timer / WHY IS REGEXBOT IGNORING ME ITS BROKEN YOU SUCK ##

Most of the command-oriented bots implement a Global Cooldown Timer.

What happens is every time the bot is issued a command. the time is recorded.  If the time since the last command is less than the cooldown duration (default 5 seconds) it'll ignore the command and reset the cooldown timer.

Once the cooldown timer is up, it'll accept commands again.  Magic.

The reason for this is because then you can't flood regexbot with commands and have it be flooded out of the server.

In `regexbot`, this cooldown timer will be set regardless of any errors (missing slashes, invalid seperators, regex errors, substitution errors.  So wait a few seconds before sending a corrected command, and re-read your regex so it's right.

# bots #

## feedbot ##

Requires feedparser.

## linkbot ##

IRC bot that links two different IRC channels (presumably on different networks) together.  Poor man's way to link together two IRC servers.

Note that joins, parts, quits, bans, kicks etc. are not propegated by this bot, and it is not possible to administer one channel from the other side.

If you want more complete functionality, you should set up proper IRC links.  This bot is designed for where that is not possible to do.

## regexbot ##

Requires python 2.6+ and regex libraries http://pypi.python.org/pypi/regex

A simple IRC bot that keeps a rotating list of messages to perform regular expressions on.  By default it keeps 25 messages in it's buffer, but this can be changed with a configuration change.

It records all messages it sees, except regular expressions.  You perform a substitution like this:

    s/original/replacement/
  
It only supports the `i` (case insensitive) option, and is always greedy (`g`-option).  It has Perl-compatible regular expressions.

Escaping forward slashes is not supported, instead represent a forward slash with the octal escape sequence `\057`.  Or you can use one of the alternative syntaxes, `s@`, `s#`, `s%`, `s:` or `s;`.

The bot features an ignore-list and "global cooldown timer", so it will ignore people with a hostmask you specify (as a regular expression, of course), and also ignore those when too many commands are sent.

## twitterbot ##

Requirements: `pip install python-twitter oauth2`

(Note: this requires `python-twitter`, not `twitter`.  The other library is incompatible.  You will need to delete it in order to use this.)

This also has some geocoder support, you'll need an experimental branch of geopy.  Details here: http://code.google.com/p/geopy/wiki/ReverseGeocoding  You don't need to have this installed, you just won't get geocoder support without it.  If you have an old version of python-twitter, such as the one in Debian 6, then you shouldn't install this.  Because that version of the library doesn't support geo extensions in Twitter.

Upon posting a URL of a tweet, twitterbot will display the tweet.

# merging with me in a non-exclusive union of source trees #

Please send me pull requests on github: https://github.com/micolous/ircbots

Either that or if there are too many MacBook-touting hipsters on github for your liking, you can email me a patch file.  There's a link on my website, http://micolous.id.au/

I'm only going to merge bots that are general enough in purpose.  For example:

 * Bot that randomly kicks @peerau out of the channel between every 6 and 49 minutes -- **rejected**
 * Bot that randomly kicks anyone out of the channel based on user-definable rules -- **accepted**

I'll keep an eye on the forks too, if there's something general enough or improvements to the library that'll get pulled in.


