import sys

from PyQt5.QtGui import *
from PyQt5.QtWidgets import QApplication, QWidget, QTreeView, QHBoxLayout


class MainFrame(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        tree = {
            'root': {
                "1": ["A", "B", "C"],
                "2": {
                    "2-1": ["G", "H", "I"],
                    "2-2": ["J", "K", "L"]
                },
                "3": ["D", "E", "F"],
            }
        }

        self.tree = QTreeView(self)
        layout = QHBoxLayout(self)
        layout.addWidget(self.tree)

        root_model = QStandardItemModel()
        self.tree.setModel(root_model)
        self._populateTree(tree, root_model.invisibleRootItem())

    def _populateTree(self, children, parent):
        for child in sorted(children):
            child_item = QStandardItem(child)
            parent.appendRow(child_item)
            if isinstance(children, dict):
                self._populateTree(children[child], child_item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = MainFrame()
    main.show()
    app.exec_()
