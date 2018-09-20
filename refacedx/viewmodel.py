# -*- coding: utf-8 -*-
#
# refacedx/viewmodel.py

import logging

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant
from PyQt5.QtWidgets import QHeaderView, QAbstractItemView

from sqlalchemy import desc, inspect

from .model import Author, Patch


log = logging.getLogger(__name__)


class SQLAlchemyTableModel(QAbstractTableModel):
    fields = None
    list_order = None
    sort_relations = {}

    def __init__(self, session, sa_model=None, parent=None):
        super().__init__(parent)
        self._session = session

        if sa_model:
            self.sa_model = sa_model

        if self.sa_model and self.fields is None:
            mapper = inspect(self.sa_model)
            self.fields = mapper.column_attrs.keys()

        log.debug("Fields: %r", self.fields)
        self.fields = tuple((f, f.capitalize()) if isinstance(f, str) else f
                            for f in self.fields or [])
        self._update()

    def adapt_view(self, view):
        """Adapt table view display options according to model fields."""
        header = view.horizontalHeader()
        for i, (field, _) in enumerate(self.fields):
            mode = self.resize_mode.get(field, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(i, mode)

    def _update(self, order=None, desc_=False):
        query = self.get_list_query()
        if not order and self.list_order:
            if isinstance(self.list_order, str) and self.list_order.endswith('-'):
                desc_ = True
                order = self.list_order[-1:]
            else:
                order = self.list_order

        if order:
            field = getattr(self.sa_model, order)
            relation = self.sort_relations.get(order)
            if relation:
                query.outerjoin(field).order_by(desc(relation) if desc_ else relation)
            else:
                query = query.order_by(desc(field) if desc_ else field)

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

    def get_row(self, row):
        if isinstance(row, QModelIndex):
            row = row.row()
        return self._rows[row]

    def get_list_query(self):
        return self._session.query(self.sa_model)

    def rowCount(self, parent):
        return len(self._rows)

    def columnCount(self, parent):
        return len(self.fields)

    def flags(self, index):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

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

    def sort(self, col, order):
        """Sort table by given column number col"""
        self.layoutAboutToBeChanged.emit()
        self._update(order=self.fields[col][0], desc_=order == Qt.DescendingOrder)
        self.layoutChanged.emit()

    # INSERTING & REMOVING

    def removeRows(self, row, numrows=1, index=QModelIndex()):
        log.debug("Removing %i rows at row: %s", numrows, row)
        self.beginRemoveRows(QModelIndex(), row, row + numrows - 1)
        for i in range(row, row + numrows):
            item = self._rows.pop(i)
            self._session.delete(item)
        self.endRemoveRows()
        return True

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
    sa_model = Patch
    datetime_fmt = "%Y-%m-%d %H:%M:%S"
    resize_mode = {'displayname': QHeaderView.Stretch}
    list_order = 'displayname'
    sort_relations = {
        'author': Author.name
    }

    def display_created(self, index, value):
        return value.strftime(self.datetime_fmt)

    def display_author(self, index, value):
        return value.name if value else ''

    def tooltip_displayname(self, index, value):
        return self._rows[index.row()].name
