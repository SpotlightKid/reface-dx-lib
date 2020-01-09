#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# refacedx/app.py

import logging
import sys

from datetime import datetime
from functools import partial
from os.path import basename, dirname, join, splitext

from PyQt5.QtCore import QSettings, QThread, QTimer, Qt, pyqtSlot
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QComboBox, QCompleter, QDialog, QFileDialog,
                             QMainWindow, QMessageBox)

from .midithread import MidiWorker
from .model import Author, Device, Manufacturer, Patch, initdb, get_or_create
from .util import is_reface_dx_voice, get_fullname, get_patch_name, set_patch_name
from .viewmodel import AuthorListModel, DeviceListModel, ManufacturerListModel, PatchlistTableModel

from .adddialog_ui import Ui_AddPatchDialog
from .refacedxlib_ui import Ui_MainWindow
from .style import DarkAppStyle


log = logging.getLogger('refacedx')


class AddPatchDialog(QDialog, Ui_AddPatchDialog):
    def __init__(self, app, *args, **kwargs):
        super().__init__(app.mainwin, *args, **kwargs)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.created_dt.setCalendarPopup(True)

        # auto-completion set up
        self.name_completer = QCompleter(app.patches, self.name_entry)
        self.name_completer.setCompletionColumn(0)
        self.name_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.name_entry.setCompleter(self.name_completer)

        self.shortname_completer = QCompleter(app.patches, self.shortname_entry)
        self.shortname_completer.setCompletionColumn(1)
        self.shortname_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.shortname_entry.setCompleter(self.shortname_completer)

        self.author_model = AuthorListModel(app.session)
        self.author_cb.setModel(self.author_model)
        self.author_cb.setModelColumn(2)

        self.manufacturer_model = ManufacturerListModel(app.session)
        self.manufacturer_cb.setModel(self.manufacturer_model)
        self.manufacturer_cb.setModelColumn(3)

        self.device_model = DeviceListModel(app.session)
        self.device_cb.setModel(self.device_model)
        self.device_cb.setModelColumn(3)

        self._last_author = None

    def new_from_data(self, data, title=None):
        if title:
            self.setWindowTitle(title)

        if self._last_author is None:
            self._last_author = get_fullname()

        name = get_patch_name(data)
        self.name_entry.setText(name)
        self.shortname_entry.setText(name)
        self.created_dt.setDateTime(datetime.now())
        self.rating_cb.setCurrentIndex(0)
        self.tags_entry.setText('')
        self.description_entry.setPlainText('')

        author_idx = self.author_cb.findText(self._last_author)
        if author_idx != -1:
            self.author_cb.setCurrentIndex(author_idx)
        else:
            self.author_cb.setCurrentText(self._last_author)

        self.manufacturer_cb.setEnabled(False)
        self.device_cb.setEnabled(False)

        if self.exec_() == QDialog.Accepted:
            author = self.author_cb.currentText()
            self._last_author = author
            return dict(
                name=self.shortname_entry.text(),
                displayname=self.name_entry.text(),
                author=author,
                manufacturer=self.manufacturer_cb.currentText(),
                device=self.device_cb.currentText(),
                rating=self.rating_cb.currentIndex(),
                tags=self.tags_entry.text(),
                description=self.description_entry.toPlainText()
            )

class RefaceDXLibMainWin(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set up the user interface from Designer.
        self.setupUi(self)
        self.midi_setup.hide()
        self.action_midi.triggered.connect(self.toggle_midi_options)
        # Set the size and title
        self.setMinimumSize(800, 600)
        self.setWindowTitle("Reface DX Lib")

    @pyqtSlot()
    def toggle_midi_options(self):
        self.midi_setup.setVisible(not self.midi_setup.isVisible())

    def set_patchtable_model(self, value):
        self._model = value
        self.table_patches.setModel(self._model)
        self._model.adapt_view(self.table_patches)
        self.selection = self.table_patches.selectionModel()
        self.selection.selectionChanged.connect(self.set_send_action_enabled)
        self.set_send_action_enabled()

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_request_action_enabled(self, enable=True):
        self.action_request.setEnabled(enable)

    @pyqtSlot()
    @pyqtSlot(bool)
    def set_send_action_enabled(self, enable=None):
        if enable is None:
            enable = self.selection.hasSelection()
        self.action_send.setEnabled(enable)


class RefaceDXLibApp(QApplication):
    def __init__(self, args=None):
        if args is None:
            args = sys.argv

        super().__init__(args)
        self.setOrganizationName('chrisarndt.de')
        self.setOrganizationDomain('chrisarndt.de')
        self.setApplicationName('Reface DX Lib')
        QSettings.setDefaultFormat(QSettings.IniFormat)
        self.config = QSettings()
        self.config.setIniCodec('UTF-8')
        QIcon.setFallbackSearchPaths([join(dirname(__file__), "icons")])
        QIcon.setThemeName(self.config.value('gui/icon_theme', "Faenza"))
        self.debug = True if '-v' in args[1:] else self.config.value('application/debug', False)
        logging.basicConfig(level=logging.DEBUG if self.debug else logging.INFO,
                            format='%(levelname)s - %(message)s')

        self.mainwin = RefaceDXLibMainWin()
        db_uri = 'sqlite:///{}'.format(self.config.value('database/last_opened', 'refacedx.db'))
        self.session = initdb(db_uri, debug=self.config.value('database/debug', False))
        self.patches = PatchlistTableModel(self.session)
        self.mainwin.set_patchtable_model(self.patches)
        self.midiin_conn = None
        self.midiout_conn = None
        self.setup_midi_thread()

        # signal connections
        self.aboutToQuit.connect(self.quit)
        self.mainwin.action_quit.triggered.connect(self.quit)
        self.mainwin.action_import.triggered.connect(self.import_patches)
        self.mainwin.action_export.triggered.connect(self.export_patches)
        self.mainwin.action_send.triggered.connect(self.send_patches)
        self.mainwin.action_request.triggered.connect(self.request_patch)
        self.mainwin.action_delete.triggered.connect(self.delete_patches)

        # dialogs (initialized on-demand)
        self.add_patch_dialog = None

        self.style = DarkAppStyle(self)
        self.mainwin.show()

    def setup_midi_thread(self):
        self.midithread = QThread()
        self.midiworker = MidiWorker(self.config)
        self.midiworker.moveToThread(self.midithread)

        self.midithread.started.connect(self.midiworker.initialize)
        self.midiworker.send_patch_start.connect(
            partial(self.mainwin.set_send_action_enabled, False))
        self.midiworker.send_patch_complete.connect(
            partial(self.mainwin.set_send_action_enabled, True))
        self.midiworker.recv_patch_start.connect(
            partial(self.mainwin.set_request_action_enabled, False))
        self.midiworker.recv_patch_complete.connect(self.receive_patch)
        self.midiworker.recv_patch_failed.connect(
            partial(self.mainwin.set_request_action_enabled, True))
        self.midiworker.input_ports_changed.connect(self.build_midi_input_selector)
        self.midiworker.output_ports_changed.connect(self.build_midi_output_selector)

        # Start thread
        self.midithread.start()
        self.timer = QTimer()
        self.timer.timeout.connect(self.midiworker.scan_ports.emit)
        self.timer.start(3000)

    @pyqtSlot('PyQt_PyObject')
    def build_midi_input_selector(self, ports):
        log.debug("Building MIDI input selector...")
        cb = self.mainwin.midiin_cb

        if self.midiin_conn:
            cb.currentIndexChanged.disconnect(self.midiin_conn)

        cb.setEnabled(False)
        cb.clear()
        selected = -1

        for i, (port, is_open) in enumerate(ports):
            cb.addItem(port, port)

            if is_open:
                selected = i

        cb.setCurrentIndex(selected)
        self.midiin_conn = cb.currentIndexChanged.connect(self.set_midiin_port)
        cb.setEnabled(True)
        log.debug("MIDI input selector (re-)built.")

    @pyqtSlot('PyQt_PyObject')
    def build_midi_output_selector(self, ports):
        log.debug("Building MIDI output selector...")
        cb = self.mainwin.midiout_cb

        if self.midiout_conn:
            cb.currentIndexChanged.disconnect(self.midiout_conn)

        cb.setEnabled(False)
        cb.clear()
        selected = -1

        for i, (port, is_open) in enumerate(ports):
            cb.addItem(port, port)

            if is_open:
                selected = i

        cb.setCurrentIndex(selected)
        self.midiout_conn = cb.currentIndexChanged.connect(self.set_midiout_port)
        cb.setEnabled(True)
        log.debug("MIDI output selector (re-)built.")

    def set_midiin_port(self, index):
        log.debug("MIDI input selector index changed: %r", index)
        if index != -1:
            port = self.mainwin.midiin_cb.itemData(index)
            self.midiworker.set_input_port.emit(port)

    def set_midiout_port(self, index):
        log.debug("MIDI output selector index changed: %r", index)
        if index != -1:
            port = self.mainwin.midiout_cb.itemData(index)
            self.midiworker.set_output_port.emit(port)

    # action handlers
    def quit(self):
        self.midiworker.close.emit()
        self.midithread.quit()
        self.midithread.wait()
        self.mainwin.close()

    def save_patch(self, data, **meta):
        name = meta.get('name', '').strip()

        if not name:
            name = get_patch_name(data)

        with self.session.begin():
            author = meta.get('author', '').strip()
            if author:
                author, created = get_or_create(
                    self.session,
                    Author,
                    create_kwargs={'name': author},
                    displayname=author)
            else:
                author = None

            manufacturer = meta.get('manufacturer', '').strip()
            if manufacturer:
                manufacturer, created = get_or_create(
                    self.session,
                    Manufacturer,
                    create_kwargs={'name': manufacturer},
                    displayname=manufacturer)
            else:
                manufacturer = None

            device = meta.get('device', '').strip()
            if device:
                device, created = get_or_create(
                    self.session,
                    Device,
                    create_kwargs={'name': device},
                    displayname=device)
            else:
                device = None

            patch = Patch(
                name=name,
                displayname=meta.get('displayname', '').strip() or name,
                description=meta.get('description', '').strip() or None,
                rating=meta.get('rating', 0),
                author=author,
                manufacturer=manufacturer,
                device=device,
                created=meta.get('created', datetime.now()),
                data=set_patch_name(data, name))
            self.session.add(patch)

            tags = (tag.strip() for tag in meta.get('tags', '').split(','))
            patch.update_tags(self.session, (tag for tag in tags if tag))

    def request_patch(self):
        self.midiworker.request_patch.emit(None)

    def receive_patch(self, data):
        log.debug("Patch received: %s", get_patch_name(data))

        if self.add_patch_dialog is None:
            self.add_patch_dialog = AddPatchDialog(self)

        metadata = self.add_patch_dialog.new_from_data(data, "Add new patch")

        if metadata:
            log.debug("Patch meta data: %r", metadata)
            self.save_patch(data, **metadata)
            self.patches._update()
            self.patches.layoutChanged.emit()

        self.mainwin.set_request_action_enabled(True)

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

            msg_box.setInformativeText("Patches can only be restored by re-importing them.")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            msg_box.setDefaultButton(QMessageBox.Cancel)
            msg_box.setIcon(QMessageBox.Warning)

            if msg_box.exec_() == QMessageBox.Yes:
                with self.session.begin():
                    for n, row in enumerate(rows):
                        self.patches.removeRows(row - n)

    def import_patches(self):
        options = QFileDialog.Options()

        if not self.config.value('native_dialogs', False):
            options |= QFileDialog.DontUseNativeDialog

        files, _ = QFileDialog.getOpenFileNames(self.mainwin, "Import SysEx patches",
                                                self.config.value('paths/last_import_path', ''),
                                                "SysEx Files (*.syx);;All Files (*)",
                                                options=options)

        if files:
            self.config.setValue('paths/last_import_path', dirname(files[0]))

            self.patches.layoutAboutToBeChanged.emit()
            with self.session.begin():
                for file in files:
                    with open(file, 'rb') as syx:
                        data = syx.read()

                    assert len(data) == 241
                    if is_reface_dx_voice(data):
                        name = get_patch_name(data)
                        displayname = splitext(basename(file))[0].replace('_', ' ').strip()
                        patch = Patch(name=name, displayname=displayname, data=data)
                        self.session.add(patch)

            # TODO: check if any patches were actually added
            self.patches._update()
            self.patches.layoutChanged.emit()

    def export_patches(self):
        if self.mainwin.selection.hasSelection():
            options = QFileDialog.Options()

            if not self.config.value('native_dialogs', False):
                options |= (QFileDialog.DontUseNativeDialog | QFileDialog.ShowDirsOnly |
                            QFileDialog.DontResolveSymlinks)

            dir_ = QFileDialog.getExistingDirectory(
                self.mainwin,
                "Export SysEx patches",
                self.config.value('paths/last_export_path', ''),
                options=options)

            if dir_:
                self.config.setValue('paths/last_export_path', dir_)

                for row in self.mainwin.selection.selectedRows():
                    patch = self.patches.get_row(row)

                    try:
                        filename = patch.displayname.replace(' ', '_') + '.syx'
                        with open(join(dir_, filename), 'wb') as syx:
                            syx.write(patch.data)
                    except OSError as exc:
                        log.error("Could not write SysEx file at '%s': %s", filename, exc)


    def send_patches(self):
        if self.mainwin.selection.hasSelection():
            for row in self.mainwin.selection.selectedRows():
                patch = self.patches.get_row(row)
                self.midiworker.send_patch.emit(patch.data)
                log.debug("Sent patch: %s (%s)", patch.displayname, patch.name)


def main(args=None):
    app = RefaceDXLibApp(args)
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main() or 0)
