# micolous/ircbots #

IRC bots created for the #blackhats IRC network.  The bots all follow a pretty similar structure.  Not all the bots are in use, but they're kept in this repository for historical purposes.

This includes a Python IRC library, `ircasync.py`.  The library was originally written by W3C, but I've made some additions and changes to make it more Pythonic.  The library still needs some work though.

There's also an IRC server (carirc) that I wrote as a competition with @aktowns while in a car coming home from Sydney.  More details of the competition parameters and implementation details are in it's source file, `ircserver.py`.  It only implements a subset of the IRC protocol (enough to make clients happy) and does some things strangely.

## feedbot ##

Requires feedparser.

## twitterbot ##

Requirements: pip install python-twitter oauth2


