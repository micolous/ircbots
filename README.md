# micolous/ircbots #

IRC bots created for the #blackhats IRC network.  The bots all follow a pretty similar structure.  Not all the bots are in use, but they're kept in this repository for historical purposes.

This includes a Python IRC library, `ircasync.py`.  The library was originally written by W3C, but I've made some additions and changes to make it more Pythonic.  The library still needs some work though.

There's also an IRC server (carirc) that I wrote as a competition with @aktowns while in a car coming home from Sydney.  More details of the competition parameters and implementation details are in it's source file, `ircserver.py`.  It only implements a subset of the IRC protocol (enough to make clients happy) and does some things strangely.

## feedbot ##

Requires feedparser.

## regexbot ##

A simple IRC bot that keeps a rotating list of messages to perform regular expressions on.  By default it keeps 25 messages in it's buffer, but this can be changed with a configuration change.

It records all messages it sees, except regular expressions.  You perform a substitution like this:

    s/original/replacement/
  
It only supports the `i` (case insensitive) option, and is always greedy (`g`-option).  It has Perl-compatible regular expressions.

Escaping forward slashes is not supported, instead represent a forward slash with the octal escape sequence `\057`.  Or you can use one of the alternative syntaxes, `s@`, `s#`, `s%`, `s:` or `s;`.

The bot features an ignore-list and "global cooldown timer", so it will ignore people with a hostmask you specify (as a regular expression, of course), and also ignore those when too many commands are sent.

## twitterbot ##

Requirements: pip install python-twitter oauth2


