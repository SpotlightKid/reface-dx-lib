#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

from os.path import basename, dirname, join, splitext

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QFileDialog, QMainWindow

from .model import Author, Patch, Session, Tag, configure_session, create_test_data
from .util import is_reface_dx_voice, get_patch_name
from .refacedxlib_ui import Ui_MainWindow
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

        self.config = {
            'db_uri': 'sqlite:///data.sqlite',
            #'debug': True,
            'debug': False,
            'native_dialogs': False,
        }
        create_test_data(self.config)
        self.session = configure_session(self.config['db_uri'], debug=self.config['debug'])
        self.model = PatchlistTableModel(self.session, view=self.table_patches)
        self.last_import_path = ''
        self.action_quit.triggered.connect(self.quit)
        self.action_import.triggered.connect(self.import_patches)
        self.action_send.triggered.connect(self.send_patches)

    def quit(self):
        self.close()

    def import_patches(self):
        options = QFileDialog.Options()

        if not self.config.get('native_dialogs', False):
            options |= QFileDialog.DontUseNativeDialog

        files, _ = QFileDialog.getOpenFileNames(self, "Import SysEx patches",
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
            print(self.model.selection.selectedRows())


def main(args=None):
    app = QApplication(args if args is not None else sys.argv)
    window = RefaceDXLibMainWin()
    window.show()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main(sys.argv) or 0)
