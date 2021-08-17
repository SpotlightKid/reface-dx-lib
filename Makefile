PROJECT = refacedxlib
PKG_DIR = refacedx
UI_DIR = ui
_PYUI_FILES = $(PROJECT)_ui.py \
	adddialog_ui.py \
	importdialog_ui.py
PYUI_FILES = $(patsubst %,$(PKG_DIR)/%,$(_PYUI_FILES))
ICON_THEME = tango
PYRCC ?= pyrcc5

PYUIC ?= pyuic5

all: $(PYUI_FILES) $(PKG_DIR)/icons_rcc.py

$(PKG_DIR)/icons_rcc.py: icons/$(ICON_THEME)/index.theme
	./scripts/generate_rcc.py --rcc $(PYRCC) -o $@ $<

$(PKG_DIR)/%_ui.py: $(UI_DIR)/%.ui
	$(PYUIC) -o $@ $<
