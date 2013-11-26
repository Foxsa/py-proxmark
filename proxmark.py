#! /usr/bin/env python
# Copyright 2009, Rysc Corp.

import struct
import usb

class ProxError(Exception):
	def __init__(self, msg):
		self.msg = msg

	def __str__(self):
		return self.msg

class USBCommand:
	cmd = 0
	ext1 = 0
	ext2 = 0
	ext3 = 0
	buf = "\x00"*48

	def __init__(self, blob=None, cmd=None):
		if blob: 
			self.cmd, self.ext1, self.ext2, self.ext3 = struct.unpack("IIII", blob[:16])
			self.buf = blob[16:]
		elif cmd:
			self.cmd = cmd

	def __str__(self):
		s = struct.pack("IIII", self.cmd, self.ext1, self.ext2, self.ext3)
		s += self.buf
		return s

class Antenna:
	name = ""
	voltage = 0.0
	impedance = 0.0

	def __init__(self, name=""):
		if name:
			self.name = name

	def __str__(self):
		return "%s v=%dmV z=%d ohms" %(self.name, self.voltage, self.impedance)

class Proxmark:
	productID = 0x4b8f
	vendorID = 0x9ac4
	dev = None

	def __init__(self):
		dev = self._find()
		if not dev:
			raise ProxError("Cannot find Proxmark")
		self.dev = dev.open()
		conf = dev.configurations[0]
		intf = conf.interfaces[0]
		try:
			self.dev.detachKernelDriver(intf[0])
		except:
			pass
		self.dev.setConfiguration(conf)
		self.dev.claimInterface(intf[0])

	def _find(self):
		for bus in usb.busses():
			for dev in bus.devices:
				if dev.idVendor == self.vendorID and dev.idProduct == self.productID:
					return dev

	def __del__(self):
		if not self.dev: return
		self.dev.releaseInterface()

	def _send(self, cmd):
		c = USBCommand(cmd=cmd)
		self._sendcmd(c)

	def _sendcmd(self, cmd):
		cmdstr = str(cmd)
		self.dev.bulkWrite(0x01, cmdstr, 1000)

	def _recvcmd(self):
		cmd_t = self.dev.bulkRead(0x82, 64, 1000)
		cmdstr = "".join([chr(c) for c in cmd_t])
		cmd = USBCommand(cmdstr)
		return cmd

	# COMMANDS

	def tune(self):
		"""
		Measure voltage and impedance in each antenna.
		Returns a tuple of 3 Antenna objects.
		"""
		self._send(0x400)
		resp = self._recvcmd()
		if resp.cmd != 0x401:
			raise ProxError("Unexpected response %x" %resp.cmd)

		# decode tuning information
		lf125 = Antenna(name="125kHz")
		lf134 = Antenna(name="134kHz")
		hf = Antenna(name="13.56MHz")
		
		lf125.voltage = resp.ext1 & 0xffff
		lf134.voltage = resp.ext1 >> 16
		lf125.impedance = lf134.impedance = resp.ext3 & 0xffff
		hf.voltage = resp.ext2
		hf.impedance = resp.ext3 >> 16

		return (lf125, lf134, hf)

	def samples(self, n=128):
		"""
		Download samples from Proxmark.
		n is the number of samples to retrieve divided by 4.
		"""
		samples = []
		c = USBCommand(cmd=0x0204)

		if n > 16000: n = 16000

		for i in xrange(0, n, 12):
			c.ext1 = i
			self._sendcmd(c)
			r = self._recvcmd()
			if r.cmd != 0x205:
				raise ProxError("Unexpected response %d" %r.cmd)
			for sample in r.buf:
				samples.append(ord(sample) - 128)
		return samples

	def read_msgs(self):
		"""
		Read messages from the Proxmark until none remain... more or less.
		"""
		msgs = []
		while 1:
			try:
				c = self._recvcmd()
				msgs.append(c)
			except:
				break
		return msgs

	# LOW FREQUENCY OPS

	def lf_read_125khz(self):
		"""Energize a 125kHz tag, acquire samples and download samples to host."""
		self.lf_read()
		return self.samples()

	def lf_read_134khz(self):
		"""Energize a 134kHz tag, acquire samples and download samples to host."""
		self.lf_read(highMode=True)
		return self.samples()

	def lf_read(self, highMode=False):
		c = USBCommand(cmd=0x203)
		if highMode:
			c.ext1 = 1
		self._sendcmd(c)
		dbg = self._recvcmd()
		return dbg

	def lf_xmit(self, data):
		"""Transmit current contents of samples buffer."""
		self._send(0x207)

	# HID
	def lf_hid_fsk_demod(self):
		"""Turn Proxmark into a HID tag reader. Press button on Proxmark to stop."""
		c = USBCommand(cmd=0x208)
		self._sendcmd(c)

	# HIGH FREQUENCY OPS

	# ISO 14443A
	def hf_read_iso14443a(self, x=None):
		"""Read ISO14443A tag. x is an integer, need to investigate significance in firmware."""
		c = USBCommand(cmd=0x301)
		if x: c.ext1 = x
		self._sendcmd(c)
		dbg = self._recvcmd()
		return self.samples(1000)

	def hf_snoop_iso14443a(self):
		"""Snoop ISO14443A traffic. Push Proxmark button to stop."""
		self._send(0x0383)

	def hf_iso14443a_reader(self, x=None):
		"""Act as ISO14443A reader. x parameter is not used by firmware."""
		c = USBCommand(cmd=0x385)
		if x: c.ext1 = x
		self._sendcmd(c)

	# ISO 15693
	def hf_read_iso15693(self):
		self._send(0x300)

	def hf_iso15693_reader(self):
		self._send(0x0310)

	def hf_sim_iso15693(self, x=None):
		"""Simulate an ISO 15693 tag."""
		c = USBCommand(cmd=0x0311)
		if x: c.ext1 = x
		self._sendcmd(c)
