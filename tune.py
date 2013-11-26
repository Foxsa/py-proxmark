#! /usr/bin/env python
# Copyright 2009, Rysc Corp.

from proxmark import *

if __name__ == '__main__':
	pm3 = Proxmark()
	antennas = pm3.tune()
	for ant in antennas:
		print ant
