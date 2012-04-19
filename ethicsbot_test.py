#!/usr/bin/env python
"""
ethicsbot_test.py: Tests the ethicalness of the ethicsbot algorithm.
Copyright 2010 - 2012 Michael Farrell <http://micolous.id.au>

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

from hashlib import sha512
from random import randint
from optparse import OptionParser
try:
	import progressbar
	PBAR_WIDGET_STYLE = [progressbar.Percentage(), progressbar.Bar(), progressbar.ETA()]
except ImportError:
	progressbar = None

class Object(object): pass
	
def ethical_state(input, states=3):
	h = sha512(input)
	ethical = 0
	for c in h.digest():
		oc = ord(c)
		
		# find number of high bits
		for x in xrange(0, 8):
			if oc & (2**x) > 0:
				ethical += 1
				
		# do this here
		ethical %= states
	
	return ethical

def test_ethics(states=3, iterations=1000, use_pbar=True):
	stats = [0] * states
	
	if use_pbar:
		progress = progressbar.ProgressBar(widgets=PBAR_WIDGET_STYLE, maxval=iterations).start()
	else:
		progress = Object()
		progress.update = lambda x: None
		progress.finish = lambda: None
	
	for x in xrange(iterations):
		# generate some garbage ascii input
		l = randint(0, 300)
		o = ''
		for y in range(l):
			o += chr(randint(0, 128))
		
		stats[ethical_state(o, states)] += 1
		progress.update(x)
		
	
	progress.finish()
	print "Results:"
	for i, s in enumerate(stats):
		print " %i: %.2f%%" % (i, float(s)/iterations*100.)
	
if __name__ == '__main__':
	parser = OptionParser()
	parser.add_option('-s', '--states', type='int', default=3, dest='states',  help='Number of ethical states there can be [default: %default]')
	parser.add_option('-i', '--iterations', type='int', default=1000, dest='iterations',  help='Number of iterations to perform [default: %default]')
	parser.add_option('-N', '--no-progress-bar', action='store_true', default=(not progressbar), dest='no_pbar', help='Disable use of progressbar if it is available [default: %default]')
	options, args = parser.parse_args()
	
	test_ethics(options.states, options.iterations, not options.no_pbar)
