#!/usr/bin/env python

from distutils.core import setup

setup(
	name="ircbots",
	version="1.0",
	description="ircasync library and some IRC bots",
	author="Michael Farrell",
	author_email="micolous@gmail.com",
	url="http://github.com/micolous/ircbots",
	
	py_modules=['ircasync'],
	scripts=['%s.py' % x for x in ['ethicsbot', 'feedbot', 'gamebot', 'ircserver', 'linkbot', 'pagerbot', 'regexbot', 'twitterbot']]
)

