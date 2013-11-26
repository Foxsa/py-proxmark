#! /usr/bin/env python
# Copyright 2009, Rysc Corp.

from proxmark import *

pm3 = Proxmark()
samples = pm3.lf_read_125khz()
for i in xrange(0, len(samples)):
	print i, samples[i]
