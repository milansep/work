# work

A small editor suite made from things you already have: **sway** does the
window layout, **foot** is the terminal, **nano** (or vim, or…) edits. It's
one Python file that only uses the standard library.

```
work ~/repos/myproject
```

opens a new sway workspace that looks like this:

```
┌─ myproject ── 2 open ─┬─[ src/main.py ]─[ * README.md ]──────────────┐
│ ▾ src/                │                                               │
│   • main.py           │   GNU nano 9.2         README.md   Modified   │
│     util.py           │                                               │
│ ▸ tests/              │   # myproject                                 │
│ • README.md *         │   ...                                         │
│   Makefile            │                                               │
│                       │                                               │
│ ? help                │                                               │
└───────────────────────┴───────────────────────────────────────────────┘
   file tree (~22%)       editors, one tab per file
```

* **Left:** the file tree. Arrow keys or the mouse to move around, Enter or a
  click opens a file or folds a folder.
* **Right:** every file opens in its own editor window, and they're all
  stacked in one tabbed pane. Opening a file that's already open jumps to its
  tab.
* **Unsaved changes** show up in the tree as an *italic name with an
  asterisk*, and as `* name` on the editor's tab.
* **Save all / close all / quit** from the tree. Closing asks about every file
  with unsaved changes: save, discard or cancel.

## Install

Requirements: sway, foot, python 3.9+, nano. Nothing else.

```sh
git clone https://github.com/milansep/work ~/repos/work
cd ~/repos/work
make link        # symlinks ./work to ~/.local/bin/work
# or: make install   (copies it instead)
```

Optional: a sway key binding, e.g. in your sway config

```
bindsym $mod+w exec work ~/repos
```

## Use

| command        | what it does                                                   |
| -------------- | -------------------------------------------------------------- |
| `work`         | open the current folder                                        |
| `work DIR`     | open DIR on the next free workspace (or jump to it if it's already open) |
| `work FILE`    | open FILE in the running session that contains it, e.g. from a shell |

Keys in the tree (also shown with `?`):

| key               | action                                        |
| ----------------- | --------------------------------------------- |
| `↑ ↓` / `j k`     | move                                          |
| `→` / `l`         | open folder / open file                       |
| `←` / `h`         | close folder, go to parent                    |
| `Enter`, `Space`, click | open file, fold/unfold folder           |
| `Tab`             | jump to the editors (sway `focus right`)      |
| `n`               | new file in the selected folder (end the name with `/` for a folder) |
| `s` / `Ctrl+S`    | save all                                      |
| `x`               | close all editors (asks about unsaved files)  |
| `q`               | close everything and quit (asks first)        |
| `.`               | show / hide dotfiles                          |
| `r`               | reload the tree (it also refreshes by itself) |

Inside an editor everything is plain nano; `^S` saves, `^X` closes the tab.

## Config

`~/.config/work/config` (optional). Start from the defaults:

```sh
mkdir -p ~/.config/work
work --default-config > ~/.config/work/config
```

```ini
[work]
editor = nano        # which [editor.NAME] section to use
tree_width = 22      # percent of the screen
show_hidden = no

[editor.nano]
command = nano --locking {file}
save = ^S
quit = ^X
discard = ^Xn
dirty = lockfile
lockfile = {dir}/.{name}.swp
```

Switching to another editor means adding an `[editor.NAME]` section that says
how to start it, which keys save, quit and discard, and where its lock file
lives. Then set `editor = NAME`. A vim profile is included but **not tested
yet**.

## How it works

```
work DIR ──► sway: new workspace "N:dir"
             └─ foot ─ work --coordinator DIR       (the tree, curses)
                          │  unix socket
             ┌────────────┴──────────────┐
  foot ─ work --edit ─ nano      foot ─ work --edit ─ nano   …
         (pty proxy)                    (pty proxy)
```

* **Layout.** The coordinator talks to sway over its IPC socket (the same
  protocol `swaymsg` uses). When the first editor window appears it splits
  it off next to the tree and sets that pane to `layout tabbed`. Later
  windows get moved into the pane with `move container to mark`. The tree is
  then resized to `tree_width` percent.
* **Save / close from the tree.** Each editor runs behind a small proxy that
  gives nano its own pseudo-terminal (pty) and copies bytes between it and
  foot. You don't notice it, but it lets the coordinator "type" into the
  editor: `^S` to save, `^X` to quit, `^X n` to quit without saving. It also
  sets the window title that sway shows on the tab.
* **Unsaved changes.** `nano --locking` writes a vim-style lock file
  (`.name.swp`) next to the file. Byte 1007 of that file is a "modified" flag.
  nano sets it but never clears it after saving, so a file counts as unsaved
  when the flag is set *and* the lock file is newer than the file (nano
  rewrites the lock file on the first change after each save). The tree
  checks twice a second.
* **Runtime files** live in `$XDG_RUNTIME_DIR/work/`: one socket per open
  project, plus a log of failed sway commands.

## Known limits

* Close editors with `^X` (or `x`/`q` in the tree), not with sway's kill
  binding. If the window is killed, nano gets a hang-up signal and saves your
  unsaved text to `name.save` instead.
* Killing the tree window with sway skips the unsaved-changes prompt. The
  editors stay open, and running `work DIR` again picks them back up.
* Save all works by typing `^S` into each editor. If nano is in the middle of
  one of its own prompts (search, …), the keystroke lands there instead.
* With no file open, the tree fills the whole workspace. That's just sway
  tiling a single window.

## Tests

```sh
make test
```

This runs the tree and an editor (real nano) in pseudo-terminals, types into
them, and checks saving, the prompts and quitting. It needs a running sway but
opens no windows.

## License

MIT
