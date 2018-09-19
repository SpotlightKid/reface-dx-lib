#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt5.QtCore import QObject, Qt, pyqtSignal, pyqtSlot

from .midiio import RefaceDX


class MidiWorker(QObject):
    """Background worker for MIDI output.

    This will be run in a QThread when the application starts.

    """

    send_start = pyqtSignal()
    send_complete = pyqtSignal()
    send_midi = pyqtSignal(bytes)
    set_device = pyqtSignal('PyQt_PyObject')

    def __init__(self, config, *args, **kw):
        super().__init__(*args, **kw)
        self.config = config
        self._midi = None
        self.set_device.connect(self.do_set_device)
        self.send_midi.connect(self.do_send_midi, type=Qt.QueuedConnection)

    @pyqtSlot()
    def initialize(self):
        print('Initializing')
        self.do_set_device(self.config.get('midi_device'))

    @pyqtSlot('PyQt_PyObject')
    def do_set_device(self, device=None):
        if self._midi:
            self._midi.close_port()
            del self._midi

        self._midi = RefaceDX(device)

    @pyqtSlot(bytes)
    def do_send_midi(self, data):
        self.send_start.emit()
        print('Sending MIDI data:', data)
        self._midi.send_patch(data)
        self.send_complete.emit()
