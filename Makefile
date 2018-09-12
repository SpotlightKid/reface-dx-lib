PROJECT = refacedxlib
PKG_DIR = refacedx
UI_DIR = ui
_PYUI_FILES = $(PROJECT)_ui.py
PYUI_FILES = $(patsubst %,$(PKG_DIR)/%,$(_PYUI_FILES))

PYUIC ?= pyuic5

all: $(PYUI_FILES)

$(PKG_DIR)/%_ui.py: $(UI_DIR)/%.ui
	$(PYUIC) $< > $@
