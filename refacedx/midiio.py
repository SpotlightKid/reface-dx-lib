#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# refacedx/midiio.py

from os.path import join
from queue import Empty, Queue

from rtmidi.midiconstants import PROGRAM_CHANGE, SYSTEM_EXCLUSIVE
from rtmidi.midiutil import open_midiinput, open_midioutput

from .constants import *
from .util import split_sysex


class TimeoutError(Exception):
    """Raised when timeout occurs waiting for reception of a MIDI message."""
    pass


class RefaceDX:

    def __init__(self, inport=None, outport=None, device=0, channel=0, timeout=5.0, debug=False):
        self.midiin, self.midiin_name = open_midiinput(inport)
        self.midiout, self.midiout_name = open_midioutput(inport if outport is None else outport)
        self.device = device
        self.channel = channel
        self.debug = debug
        self.midiin.ignore_types(sysex=False)
        self.midiin.set_callback(self._msg_callback)
        self.timeout = timeout
        self.queue = Queue()

    def _send(self, msg):
        if self.debug:
            print("SEND:", msg)
        if self.midiout:
            self.midiout.send_message(msg)

    def dump_request(self, address=ADDRESS_HEADER, device=None):
        if device is None:
            device = self.device
        msg = bytearray(DUMP_REQUEST)
        msg[2] |= device
        msg[6] = address[0]
        msg[7] = address[1]
        msg[8] = address[2]
        self._send(msg)

    def patch_request(self, device=None):
        self.dump_request(device=device, address=ADDRESS_HEADER)
        patch = bytearray()
        try:
            for address in ADDRESSES_VOICE_BLOCK:
                part = self.queue.get(timeout=self.timeout)
                if is_bulk_dump(part, address=address):
                    patch += bytearray(part)
        except Empty:
            raise TimeoutError
        else:
            return patch

    def _msg_callback(self, event, data):
        msg, delta = event
        if msg[0] == SYSTEM_EXCLUSIVE:
            if self.debug:
                print("RECV:", msg)
            self.queue.put(msg)

    def send_patch(self, data):
        for msg in split_sysex(data):
            self._send(msg)

    def send_patchfile(self, *names):
        path = join(*names)
        with open(path, 'rb') as syx:
            for msg in split_sysex(syx.read()):
                self._send(msg)

    def send_program_change(self, program, channel=None):
        if channel is None:
            channel = self.channel
        self._send([PROGRAM_CHANGE | (channel & 0xF), program & 0x7F])
