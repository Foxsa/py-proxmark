#! /usr/bin/env python
# Copyright 2009, Rysc Corp.

from proxmark import *

pm3 = Proxmark()
samples = pm3.hf_read_iso14443a()
print samples
