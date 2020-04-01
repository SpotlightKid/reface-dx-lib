#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# refacedx/midithread.py

import logging

from PyQt5.QtCore import QSettings, QObject, Qt, pyqtSignal, pyqtSlot

from .midiio import RefaceDX, TimeoutError

from rtmidi import MidiIn, MidiOut
from rtmidi.midiutil import get_api_from_environment


log = logging.getLogger(__name__)


class MidiWorker(QObject):
    """Background worker for MIDI in- and output.

    This will be run in a QThread when the application starts.

    """
    close = pyqtSignal()
    send_patch = pyqtSignal(bytes)
    send_patch_start = pyqtSignal()
    send_patch_complete = pyqtSignal()
    request_patch = pyqtSignal('PyQt_PyObject')
    recv_patch_start = pyqtSignal()
    recv_patch_complete = pyqtSignal(bytearray)
    recv_patch_failed = pyqtSignal(str)
    scan_ports = pyqtSignal()
    set_output_port = pyqtSignal('PyQt_PyObject')
    set_input_port = pyqtSignal('PyQt_PyObject')
    input_ports_changed = pyqtSignal('PyQt_PyObject')
    output_ports_changed = pyqtSignal('PyQt_PyObject')

    def __init__(self, config, *args, **kw):
        super().__init__(*args, **kw)
        self.config = QSettings()
        self._midiin = None
        self._midiin_name = None
        self._midiout = None
        self._midiout_name = None
        self.client_name = self.config.value('midi/client_name', 'Reface DX Lib')
        self.device = self.config.value('midi/sysex_device', 0)
        self.channel = self.config.value('midi/channel', 0)
        self.close.connect(self._close)
        self.set_input_port.connect(self._set_input_port)
        self.set_output_port.connect(self._set_output_port)
        self.scan_ports.connect(self._scan_ports)
        self.send_patch.connect(self._send_patch, type=Qt.QueuedConnection)
        self.request_patch.connect(self._request_patch, type=Qt.QueuedConnection)

    @pyqtSlot()
    def initialize(self):
        log.debug('Initializing MidiWorker.')
        self.midiio = RefaceDX(channel=self.channel)
        self.set_input_port.emit(self.config.value('midi/input_port', 'reface DX'))
        self.set_output_port.emit(self.config.value('midi/output_port', 'reface DX'))
        self._scan_ports(init=True)

    def _close(self):
        try:
            if self._midiin:
                self._midiin.close_port()
                self.midiio.midiin = self._midiin = None
        except AttributeError:
            pass

        try:
            if self._midiout:
                self._midiout.close_port()
                self.midiio.midiout = self._midiout = None
        except AttributeError:
            pass

    def _filter_own_ports(self, port, suffix, prefix):
        try:
            client, name = port.split(':', 1)
        except (ValueError, TypeError):
            return False

        return client.startswith(self.client_name + suffix) and name.startswith(prefix)

    def get_input_ports(self):
        return [port for port in (self._midiin.get_ports() if self._midiin else [])
                if not self._filter_own_ports(port, ' Out', 'midi_out')]

    def get_output_ports(self):
        return [port for port in (self._midiout.get_ports() if self._midiout else [])
                if not self._filter_own_ports(port, ' In', 'midi_in')]

    @pyqtSlot('PyQt_PyObject')
    def _set_input_port(self, port=None):
        log.debug("Trying to open input port %s...", port)
        if self._midiin:
            self._midiin.close_port()

        try:
            self._midiin = MidiIn(get_api_from_environment(), name=self.client_name + ' In')
            self._midiin_ports = self.get_input_ports()

            for i, name in enumerate(self._midiin_ports):
                log.debug("Checking input port #%i %s", i, name)
                if (isinstance(port, int) and port == i) or port == name:
                    self._midiin.open_port(i, name='midi_in')
                    self.config.setValue('midi/input_port', name)
                    log.debug("Set MIDI input port to '%s'.", name)
                    break
            else:
                self._midiin = self._midiin.open_virtual_port(name='midi_in')
                name = "Virtual MIDI input"

            self._midiin_name = name
        except Exception as exc:
            log.error("Could not open MIDI input port '%s': %s", port, exc)
            self._midiin = self._midiin_name = None

        self.midiio.midiin = self._midiin

    @pyqtSlot('PyQt_PyObject')
    def _set_output_port(self, port=None):
        log.debug("Trying to open output port %s...", port)
        if self._midiout:
            self._midiout.close_port()

        try:
            self._midiout = MidiOut(get_api_from_environment(), name=self.client_name + ' Out')
            self._midiout_ports = self.get_output_ports()

            for i, name in enumerate(self._midiout_ports):
                log.debug("Checking output port #%i %s", i, name)
                if (isinstance(port, int) and port == i) or port == name:
                    self._midiout.open_port(i, name='midi_out')
                    self.config.setValue('midi/output_port', name)
                    log.debug("Set MIDI output port to '%s'.", name)
                    break
            else:
                self._midiout.open_virtual_port(name='midi_out')
                name = "Virtual MIDI output"

            self._midiout_name = name
        except Exception as exc:
            log.error("Could not open MIDI output port '%s': %s", port, exc)
            self.midiout = self._midiout_name = None

        self.midiio.midiout = self._midiout

    @pyqtSlot()
    @pyqtSlot(int)
    def _request_patch(self, program=None):
        if program is not None:
            log.debug("Sending program change %d (ch=%d).", program, self.channel)
            self.midiio.send_program_change(program, self.channel)

        self.recv_patch_start.emit()
        try:
            log.debug("Requesting current patch.")
            patch = self.midiio.patch_request(self.device)
        except TimeoutError as exc:
            log.error("Patch request timed out.")
            self.recv_patch_failed.emit(str(exc))
        else:
            log.debug("Patch data received.")
            self.recv_patch_complete.emit(patch)

    @pyqtSlot(bytes)
    def _send_patch(self, data):
        self.send_patch_start.emit()
        log.debug("Sending patch data.")
        self.midiio.send_patch(data)
        self.send_patch_complete.emit()

    @pyqtSlot()
    def _scan_ports(self, init=False):
        log.debug("Scanning MIDI input and output ports...")

        ports = self.get_input_ports()
        if init or ports != self._midiin_ports:
            if not init:
                log.debug("MIDI input ports changed.")
                log.debug("Old input port list: %r", self._midiin_ports)
                log.debug("New input port list: %r", ports)
                self._midiin_ports = ports

            self.input_ports_changed.emit([(port, port == self._midiin_name) for port in ports])

        ports = self.get_output_ports()
        if init or ports != self._midiout_ports:
            if not init:
                log.debug("MIDI output ports changed.")
                log.debug("Old output port list: %r", self._midiout_ports)
                log.debug("New output port list: %r", ports)
                self._midiout_ports = ports

            self.output_ports_changed.emit([(port, port == self._midiout_name) for port in ports])
