# -*- coding: utf-8 -*-
#
# refacedx/viewmodel.py

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QHeaderView, QAbstractItemView

from sqlalchemy import inspect

from .model import Patch


class SQLAlchemyTableModel(QtCore.QAbstractTableModel):
    fields = None
    list_order = None

    def __init__(self, session, view, model=None, parent=None):
        QtCore.QAbstractTableModel.__init__(self, parent)
        self._session = session

        if model:
            self.model = model

        if self.fields is None:
            mapper = inspect(model)
            self.fields = mapper.column_attrs.keys()

        self.fields = tuple((f, f.capitalize()) if isinstance(f, str) else f
                             for f in self.fields)
        self._update()
        view.setModel(self)
        view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.selection = view.selectionModel()
        header = view.horizontalHeader()
        for i, (field, _) in enumerate(self.fields):
            mode = self.resize_mode.get(field, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(i, mode)

    def _update(self):
        query = self.get_list_query()
        if self.list_order:
            query = query.order_by(self.list_order)

        self._rows = query.all()

    def _get_field(self, index):
        name = self.fields[index.column()][0]
        return name, getattr(self._rows[index.row()], name)

    def _set_field(self, index, value):
        return setattr(self._rows[index.row()], self.fields[index.column()][0], value)

    def _display_field(self, index, name, value):
        f = getattr(self, 'display_' + name, None)
        if f:
            return f(index, value)
        return '' if value is None else str(value)

    def get_list_query(self):
        return self._session.query(self.model)

    def rowCount(self, parent):
        return len(self._rows)

    def columnCount(self, parent):
        return len(self.fields)

    def flags(self, index):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role):
        name, value = self._get_field(index)
        if role in (Qt.DisplayRole, Qt.EditRole):
            return self._display_field(index, name, value)

        if role == Qt.ToolTipRole:
            f = getattr(self, 'tooltip_' + name, None)
            if f:
                return f(index, value)

        if role == Qt.DecorationRole:
            f = getattr(self, 'icon_' + name, None)
            if f:
                return f(index, value)

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            self._set_field(index, value)
            self.dataChanged.emit(index, index)
            return True

        return False

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section < len(self.fields):
                    return self.fields[section][1]
            else:
                return "%i" % self._rows[section].id

# ~    #=====================================================#
# ~    #INSERTING & REMOVING
# ~    #=====================================================#

# ~    def insertRows(self, position, rows, parent=QtCore.QModelIndex()):
# ~        self.beginInsertRows(parent, position, position + rows - 1)

# ~        for i in range(rows):
# ~            self._patches.insert(position, patch)

# ~        self.endInsertRows()
# ~        return True


# ~    def insertColumns(self, position, columns, parent=QtCore.QModelIndex()):
# ~        self.beginInsertColumns(parent, position, position + columns - 1)
# ~        rowCount = len(self._patches)

# ~        for i in range(columns):
# ~            for j in range(rowCount):
# ~                self._patches[j].insert(position, QtGui.QColor("#000000"))

# ~        self.endInsertColumns()
# ~        return True


class PatchlistTableModel(SQLAlchemyTableModel):
    fields = (('displayname', 'Name'), 'author', 'revision', 'created')
    model = Patch
    datetime_fmt = "%Y-%m-%d %H:%M:%S"
    resize_mode = {'displayname': QHeaderView.Stretch}
    list_order = 'displayname'

    def display_created(self, index, value):
        return value.strftime(self.datetime_fmt)

    def display_author(self, index, value):
        return value.name if value else ''

    def tooltip_displayname(self, index, value):
        return self._rows[index.row()].name
