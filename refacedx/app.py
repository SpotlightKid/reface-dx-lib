#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys

from functools import partial
from os.path import basename, dirname, join, splitext

from PyQt5.QtCore import QSettings, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow, QMenu, QMessageBox

from .midithread import MidiWorker
from .model import Author, Patch, Session, Tag, configure_session, create_test_data, initdb
from .refacedxlib_ui import Ui_MainWindow
from .util import is_reface_dx_voice, get_patch_name
from .viewmodel import PatchlistTableModel


log = logging.getLogger('refacedx')


class RefaceDXLibMainWin(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up the user interface from Designer.
        self.setupUi(self)
        # Set the size and title
        self.setMinimumSize(800, 600)
        self.setWindowTitle("Reface DX Lib")
        self.midiin_menu = QMenu(self.menu_MIDI)
        self.midiin_menu.setTitle("&Input port")
        self.menu_MIDI.addMenu(self.midiin_menu)
        self.midiout_menu = QMenu(self.menu_MIDI)
        self.midiout_menu.setTitle("&Output port")
        self.menu_MIDI.addMenu(self.midiout_menu)

    def set_patchtable_model(self, value):
        self._model = value
        self.table_patches.setModel(self._model)
        self._model.adapt_view(self.table_patches)
        self.selection = self.table_patches.selectionModel()
        self.selection.selectionChanged.connect(self.set_send_action_enabled)
        self.set_send_action_enabled()

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_send_action_enabled(self, enable=None):
        if enable is None:
            enable = self.selection.hasSelection()
        self.action_send.setEnabled(enable)


class RefaceDXLibApp(QApplication):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.setOrganizationName('chrisarndt.de')
        self.setOrganizationDomain('chrisarndt.de')
        self.setApplicationName('Reface DX Lib')
        QSettings.setDefaultFormat(QSettings.IniFormat)
        self.config = QSettings()
        self.config.setIniCodec('UTF-8')
        QIcon.setThemeSearchPaths([join(dirname(__file__), "icons")])
        QIcon.setThemeName(self.config.value('gui/icon_theme', "Faenza"))
        self.debug = self.config.value('application/debug', False)
        logging.basicConfig(level=logging.DEBUG if self.debug else logging.INFO,
                            format='%(levelname)s - %(message)s')

        self.mainwin = RefaceDXLibMainWin()
        db_uri = 'sqlite:///{}'.format(self.config.value('database/last_opened', 'refacedx.db'))
        self.session = initdb(db_uri, debug=self.config.value('database/debug', False))
        self.patches = PatchlistTableModel(self.session)
        self.mainwin.set_patchtable_model(self.patches)

        self.setup_midi_thread()

        # signal connections
        self.aboutToQuit.connect(self.quit)
        self.mainwin.action_quit.triggered.connect(self.quit)
        self.mainwin.action_import.triggered.connect(self.import_patches)
        self.mainwin.action_send.triggered.connect(self.send_patches)
        self.mainwin.action_request.triggered.connect(self.receive_patch)
        self.mainwin.action_delete.triggered.connect(self.delete_patches)

        self.mainwin.show()

    def setup_midi_thread(self):
        self.midithread = QThread()
        self.midiworker = MidiWorker(self.config)
        self.midiworker.moveToThread(self.midithread)

        self.midithread.started.connect(self.midiworker.initialize)
        self.midiworker.send_start.connect(partial(self.mainwin.set_send_action_enabled, False))
        self.midiworker.send_complete.connect(partial(self.mainwin.set_send_action_enabled, True))
        self.midiworker.input_ports_changed.connect(self.set_midi_input_menu)
        self.midiworker.output_ports_changed.connect(self.set_midi_output_menu)

        # Start thread
        self.midithread.start()
        self.timer = QTimer()
        self.timer.timeout.connect(self.midiworker.scan_ports.emit)
        self.timer.start(3000)

    @pyqtSlot('PyQt_PyObject')
    def set_midi_input_menu(self, ports):
        self.mainwin.midiin_menu.clear()
        for port in ports:
            func = partial(self.midiworker.set_input_port.emit, port)
            self.mainwin.midiin_menu.addAction(port, func)

    @pyqtSlot('PyQt_PyObject')
    def set_midi_output_menu(self, ports):
        self.mainwin.midiout_menu.clear()
        for port in ports:
            func = partial(self.midiworker.set_output_port.emit, port)
            self.mainwin.midiout_menu.addAction(port, func)

    # action handlers
    def quit(self):
        self.midithread.exit()
        self.mainwin.close()

    def receive_patch(self):
        self.midiworker.scan_ports.emit()

    def delete_patches(self):
        if self.mainwin.selection.hasSelection():
            rows = sorted([r.row() for r in self.mainwin.selection.selectedRows()])
            patches = tuple(self.patches.get_row(r).displayname for r in rows)
            msg_box = QMessageBox()

            if len(rows) == 1:
                msg_box.setText("Delete patch '{}'?".format(patches[0]))
            else:
                msg_box.setText("Delete {} patches?".format(len(rows)))
                msg_box.setDetailedText('\n'.join(patches))

            msg_box.setInformativeText("Patches can only be restored by re-importing them.");
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel);
            msg_box.setDefaultButton(QMessageBox.Cancel);
            msg_box.setIcon(QMessageBox.Warning)

            if msg_box.exec_() == QMessageBox.Yes:
                with self.session.begin():
                    for n, row in enumerate(rows):
                        self.patches.removeRows(row - n)

    def import_patches(self):
        options = QFileDialog.Options()

        if not self.config.value('native_dialogs', False):
            options |= QFileDialog.DontUseNativeDialog

        files, dummy = QFileDialog.getOpenFileNames(self.mainwin, "Import SysEx patches",
            self.config.value('paths/last_import_path', ''), "SysEx Files (*.syx);;All Files (*)",
            options=options)
        log.debug("Dummy: %r", dummy)

        if files:
            self.config.setValue('paths/last_import_path', dirname(files[0]))

            for file in files:
                with open(file, 'rb') as syx:
                    data = syx.read()

                assert len(data) == 241
                if is_reface_dx_voice(data):
                    self.session.begin()
                    name = get_patch_name(data)
                    displayname = splitext(basename(file))[0]
                    patch = Patch(name=name, displayname=displayname, data=data)
                    self.session.add(patch)
                    self.session.commit()

            self.patches._update()
            self.patches.layoutChanged.emit()

    def send_patches(self):
        if self.mainwin.selection.hasSelection():
            for row in self.mainwin.selection.selectedRows():
                patch = self.patches.get_row(row)
                self.midiworker.send_midi.emit(patch.data)


def main(args=None):
    app = RefaceDXLibApp(args if args is not None else sys.argv)
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main(sys.argv) or 0)
