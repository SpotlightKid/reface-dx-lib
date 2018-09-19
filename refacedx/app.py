#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from os.path import basename, dirname, join, splitext

from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow

from .midithread import MidiWorker
from .model import Author, Patch, Session, Tag, configure_session, create_test_data, initdb
from .refacedxlib_ui import Ui_MainWindow
from .util import is_reface_dx_voice, get_patch_name
from .viewmodel import PatchlistTableModel


class RefaceDXLibMainWin(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        QIcon.setThemeSearchPaths([join(dirname(__file__), "icons")])
        QIcon.setThemeName("Faenza")

        # Set up the user interface from Designer.
        self.setupUi(self)
        # Set the size and title
        self.setMinimumSize(800, 600)
        self.setWindowTitle("Reface DX Patch Library")

    @pyqtSlot()
    def enable_send_action(self):
        self.action_send.setEnabled(True)

    @pyqtSlot()
    def disable_send_action(self):
        self.action_send.setEnabled(False)


class RefaceDXLibApp(QApplication):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.win = RefaceDXLibMainWin()

        self.config = {
            'db_uri': 'sqlite:///data.sqlite',
            #'debug': True,
            'debug': False,
            'native_dialogs': False,
            'midi_device': 'reface DX'
        }
        #create_test_data(self.config)
        initdb(self.config['db_uri'], self.config['debug'])
        self.session = configure_session(self.config['db_uri'], debug=self.config['debug'])
        self.model = PatchlistTableModel(self.session, view=self.win.table_patches)
        self.last_import_path = ''
        self.aboutToQuit.connect(self.quit)
        self.win.action_quit.triggered.connect(self.quit)
        self.win.action_import.triggered.connect(self.import_patches)
        self.win.action_send.triggered.connect(self.send_patches)
        self.setup_midi_thread()

        self.win.show()

    def quit(self):
        self.midithread.exit()
        self.win.close()

    def setup_midi_thread(self):
        self.midithread = QThread()
        self.midiworker = MidiWorker(self.config)
        self.midiworker.moveToThread(self.midithread)

        self.midithread.started.connect(self.midiworker.initialize)
        self.midiworker.send_start.connect(self.win.disable_send_action)
        self.midiworker.send_complete.connect(self.win.enable_send_action)

        # Start thread
        self.midithread.start()


    def import_patches(self):
        options = QFileDialog.Options()

        if not self.config.get('native_dialogs', False):
            options |= QFileDialog.DontUseNativeDialog

        files, _ = QFileDialog.getOpenFileNames(self.win, "Import SysEx patches",
            self.last_import_path, "SysEx Files (*.syx);;All Files (*)", options=options)

        if files:
            self.last_import_path = dirname(files[0])

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

            self.model._update()
            self.model.layoutChanged.emit()

    def send_patches(self):
        if self.model.selection.hasSelection():
            for row in self.model.selection.selectedRows():
                patch = self.model.get_row(row)
                self.midiworker.send_midi.emit(patch.data)


def main(args=None):
    app = RefaceDXLibApp(args if args is not None else sys.argv)
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main(sys.argv) or 0)
