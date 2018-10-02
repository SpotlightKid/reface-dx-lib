#! /usr/bin/env python3
# -*- coding: utf-8 -*-
#
# refacdedx/style.py

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor


def css_rgb(color, a=None):
    """Get a CSS `rgb` or `rgba` string from a QColor ot Qt.GlobalColor."""
    if isinstance(color, Qt.GlobalColor):
        color = QColor(color)
    return ("rgba({}, {}, {}, {})" if a else
            "rgb({}, {}, {})").format(*color.getRgb())


class AppStyle:
    """Palette for a Qt application meant to be used with the Fusion theme."""

    STYLESHEET = """\
    QToolTip {{
        color: {secondary};
        background-color: {tertiary};
        border: 1px solid {secondary};
    }}
    """
    PRIMARY = QColor(192, 192, 192)
    SECONDARY = QColor(16, 16, 16)
    TERTIARY = QColor(64, 64, 64)
    DISABLED = Qt.darkGray
    styles = ()

    def __init__(self, app):
        """Set the Fusion theme and palette on a QApplication."""
        app.setStyle("Fusion")
        self.set_palette(app)
        self.set_stylesheet(app)

    def set_palette(self, app):
        """Set the widget color palette on a QApplication."""
        palette = QPalette()
        for style in self.styles:
            element = getattr(QPalette, style[0], None)
            if element:
                palette.setColor(element, style[1])
                if len(style) == 3:
                    palette.setColor(QPalette.Disabled, element, style[2])
        app.setPalette(palette)

    def set_stylesheet(self, app):
        """Set the tooltip stylesheet on a QApplication."""
        app.setStyleSheet(self.STYLESHEET.format(secondary=css_rgb(self.SECONDARY),
                                                 tertiary=css_rgb(self.TERTIARY)))


class DarkAppStyle(AppStyle):
    """Dark palette."""

    PRIMARY = QColor(53, 53, 53)
    SECONDARY = QColor(35, 35, 35)
    TERTIARY = QColor(42, 130, 218)

    styles = (
        ("AlternateBase", PRIMARY),
        ("Base", SECONDARY),
        ("BrightText", Qt.red),
        ("Button", PRIMARY),
        ("ButtonText", Qt.white, AppStyle.DISABLED),
        ("HighlightedText", Qt.black),
        ("Highlight", TERTIARY),
        ("Link", TERTIARY),
        ("Text", Qt.white, AppStyle.DISABLED),
        ("ToolTipBase", Qt.white),
        ("ToolTipText", Qt.white),
        ("Window", PRIMARY),
        ("WindowText", Qt.white, AppStyle.DISABLED),
    )
