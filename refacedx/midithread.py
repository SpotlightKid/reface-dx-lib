#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time

from PyQt5.QtCore import QSettings, QObject, Qt, pyqtSignal, pyqtSlot

from .midiio import RefaceDX

from rtmidi import MidiIn, MidiOut
from rtmidi.midiutil import get_api_from_environment


log = logging.getLogger(__name__)


class MidiWorker(QObject):
    """Background worker for MIDI in- and output.

    This will be run in a QThread when the application starts.

    """

    send_start = pyqtSignal()
    send_complete = pyqtSignal()
    send_midi = pyqtSignal(bytes)
    scan_ports = pyqtSignal()
    set_output_port = pyqtSignal('PyQt_PyObject')
    set_input_port = pyqtSignal('PyQt_PyObject')
    input_ports_changed = pyqtSignal('PyQt_PyObject')
    output_ports_changed = pyqtSignal('PyQt_PyObject')

    def __init__(self, config, *args, **kw):
        super().__init__(*args, **kw)
        self.config = QSettings()
        self.client_name = self.config.value('midi/client_name', 'Reface DX Lib')
        self.set_input_port.connect(self._set_input_port)
        self.set_output_port.connect(self._set_output_port)
        self.scan_ports.connect(self._scan_ports)
        self.send_midi.connect(self._send_midi, type=Qt.QueuedConnection)
        self.midiio = RefaceDX()

    @pyqtSlot()
    def initialize(self):
        log.debug('Initializing')
        self._set_input_port(self.config.value('midi/input_port', 'reface DX'))
        self._set_output_port(self.config.value('midi/output_port', 'reface DX'))
        self.input_ports_changed.emit(self._midiin_ports)
        self.output_ports_changed.emit(self._midiout_ports)

    @pyqtSlot('PyQt_PyObject')
    def _set_input_port(self, port=None):
        log.debug("_set_input_port")
        if getattr(self, '_midiin', None):
            self._midiin.close_port()
            del self._midiin

        try:
            self._midiin = MidiIn(get_api_from_environment(), name=self.client_name)
            self._midiin_ports = self._midiin.get_ports()
            for i, name in enumerate(self._midiin_ports):
                if (isinstance(port, int) and i == port) or port == name:
                    self._midiin.open_port(i, name='midi_in')
                    self.config.setValue('midi/input_port', name)
                    break
            else:
                self._midiin = self._midiin.open_virtual_port(name='midi_in')
        except Exception as exc:
            log.error("Could not open MIDI input port '%s': %s", port, exc)
            self.midiin = None

        self.midiio.midiin = self._midiin

    @pyqtSlot('PyQt_PyObject')
    def _set_output_port(self, port=None):
        log.debug("_set_output_port")
        if getattr(self, '_midiout', None):
            self._midiout.close_port()
            del self._midiout

        try:
            self._midiout = MidiOut(get_api_from_environment(), name=self.client_name)
            self._midiout_ports = self._midiout.get_ports()
            for i, name in enumerate(self._midiout_ports):
                if (isinstance(port, int) and i == port) or port == name:
                    self._midiout.open_port(i, name='midi_out')
                    self.config.setValue('midi/output_port', name)
                    break
            else:
                self._midiout.open_virtual_port(name='midi_out')
        except Exception as exc:
            log.error("Could not open MIDI output port '%s': %s", port, exc)
            self.midiout = None

        self.midiio.midiout = self._midiout

    @pyqtSlot(bytes)
    def _send_midi(self, data):
        log.debug("_send_midi")
        self.send_start.emit()
        self.midiio.send_patch(data)
        self.send_complete.emit()

    @pyqtSlot()
    def _scan_ports(self):
        log.debug("_scan_ports")
        ports = self._midiin.get_ports() if self._midiin else []
        if ports != self._midiin_ports:
            self._midiin_ports = ports
            self.input_ports_changed.emit(ports)

        ports = self._midiout.get_ports() if self._midiout else []
        if ports != self._midiout_ports:
            log.debug("MIDI output port list changed.")
            log.debug("Old: %s", self._midiout_ports)
            log.debug("New: %s", ports)
            self._midiout_ports = ports
            self.output_ports_changed.emit(ports)
