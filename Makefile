PREFIX ?= $(HOME)/.local
BIN = $(PREFIX)/bin

# copy the script into ~/.local/bin
install:
	install -Dm755 work $(BIN)/work

# symlink instead: edits in this repo take effect right away
link:
	mkdir -p $(BIN)
	ln -sf $(CURDIR)/work $(BIN)/work

uninstall:
	rm -f $(BIN)/work

test:
	python3 tests/test_headless.py

.PHONY: install link uninstall test
