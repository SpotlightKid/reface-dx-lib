#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# refacedx/midiio.py

import logging

from os.path import join
from queue import Empty, Queue

from rtmidi.midiconstants import PROGRAM_CHANGE, SYSTEM_EXCLUSIVE

from .constants import ADDRESS_HEADER, ADDRESSES_VOICE_BLOCK, DUMP_REQUEST
from .util import is_reface_dx_bulk_dump, split_sysex


log = logging.getLogger(__name__)


class TimeoutError(Exception):
    """Raised when timeout occurs waiting for reception of a MIDI message."""
    pass


class RefaceDX:

    def __init__(self, midiin=None, midiout=None, device=0, channel=0, timeout=5.0, debug=False):
        self.midiin = midiin
        self.midiout = midiout
        self.device = device
        self.channel = channel
        self.debug = debug
        self.timeout = timeout
        self.queue = Queue()

    @property
    def midiin(self):
        return self._midiin

    @midiin.setter
    def midiin(self, value):
        self._midiin = value
        if self._midiin:
            self._midiin.ignore_types(sysex=False)
            self._midiin.set_callback(self._msg_callback)

    def _send(self, msg):
        if self.debug:
            log.debug("MIDI SEND: %r", msg)
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
                if is_reface_dx_bulk_dump(part, address=address):
                    patch += bytearray(part)
        except Empty:
            raise TimeoutError("No valid patch received within timeout (%s sec.)" % self.timeout)
        else:
            return patch

    def _msg_callback(self, event, data):
        msg, delta = event
        if msg[0] == SYSTEM_EXCLUSIVE:
            if self.debug:
                log.debug("MIDI RECV: %r", msg)
            self.queue.put(msg)

    def send_patch(self, data):
        for msg in split_sysex(data):
            self._send(msg)

    def send_patchfile(self, *names):
        path = join(*names)
        with open(path, 'rb') as syx:
            self.send_patch(syx.read())

    def send_program_change(self, program, channel=None):
        if channel is None:
            channel = self.channel
        self._send([PROGRAM_CHANGE | (channel & 0xF), program & 0x7F])
