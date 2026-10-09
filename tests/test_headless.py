#!/usr/bin/env python3
"""Headless test: runs the coordinator and an editor proxy (with real nano)
inside pseudo-terminals, types into them, and checks what happens.
Needs a running sway (for its IPC socket) but opens no windows.

    make test
"""
import fcntl
import importlib.machinery
import importlib.util
import os
import pty
import select
import struct
import sys
import tempfile
import termios
import time

WORK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "work")
loader = importlib.machinery.SourceFileLoader("work", WORK)
work = importlib.util.module_from_spec(importlib.util.spec_from_loader("work", loader))
loader.exec_module(work)

output = {}  # pty fd -> everything it printed


def run(*argv):
    pid, fd = pty.fork()
    if pid == 0:
        os.environ["TERM"] = "foot"
        fcntl.ioctl(0, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 40, 0, 0))
        os.execv(sys.executable, [sys.executable, WORK, *argv])
    output[fd] = b""
    return pid, fd


def pump(seconds):
    end = time.time() + seconds
    while time.time() < end:
        ready, _, _ = select.select(list(output), [], [], 0.05)
        for fd in ready:
            try:
                output[fd] += os.read(fd, 65536)
            except OSError:
                pass


def check(name, condition):
    print(("ok    " if condition else "FAIL  ") + name)
    if not condition:
        check.failed = True


check.failed = False


def main():
    check("parse_keys ^S", work.parse_keys("^S") == "\x13")
    check("parse_keys <C-\\><C-N>:q!<CR>", work.parse_keys(r"<C-\><C-N>:q!<CR>") == "\x1c\x0e:q!\r")

    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.realpath(tmp)
        os.mkdir(os.path.join(root, "src"))
        a = os.path.join(root, "src", "a.py")
        b = os.path.join(root, "notes.md")
        for path in (a, b):
            with open(path, "w") as f:
                f.write("text\n")
        project = work.project_id(root)
        sock = work.socket_path(project)

        def status():
            return work.request(sock, {"cmd": "status"}) or {}

        def editor(path, tag):
            return run("--edit", sock, f"work-{project}-{tag}", path, "--",
                       "nano", "--ignorercfiles", "--locking", path)

        coordinator, cfd = run("--coordinator", root)
        pump(1.0)
        check("coordinator answers", status().get("ok"))

        pid, efd = editor(a, "aaaaaa")
        pump(1.2)
        check("editor registers", [t["path"] for t in status()["tabs"]] == [a])

        os.write(efd, b"hello ")
        pump(1.2)
        check("typing marks it unsaved", status()["tabs"][0]["dirty"])
        check("tab title gets a *", b"\x1b]2;* src/a.py" in output[efd])

        os.write(cfd, b"s")
        pump(1.2)
        check("s saves", not status()["tabs"][0]["dirty"] and open(a).read() == "hello text\n")

        os.write(efd, b"more ")
        pump(1.2)
        output[cfd] = b""
        os.write(cfd, b"x")
        pump(0.8)
        check("x asks about unsaved changes", b"unsaved changes" in output[cfd])
        os.write(cfd, b"d")
        pump(1.5)
        check("d discards and closes", not status()["tabs"] and open(a).read() == "hello text\n")
        check("editor exited cleanly", os.waitpid(pid, os.WNOHANG) == (pid, 0))
        check("no lock file left", not os.path.exists(os.path.join(root, "src", ".a.py.swp")))

        pid, efd = editor(b, "bbbbbb")
        pump(1.2)
        os.write(efd, b"edited ")
        pump(1.2)
        output[cfd] = b""
        os.write(cfd, b"q")
        pump(0.8)
        check("q asks about unsaved changes", b"unsaved changes" in output[cfd])
        os.write(cfd, b"s")
        pump(2.0)
        check("s saves before quitting", open(b).read() == "edited text\n")
        check("coordinator exits", os.waitpid(coordinator, os.WNOHANG) == (coordinator, 0))
        check("socket removed", not os.path.exists(sock))

    sys.exit(1 if check.failed else 0)


if __name__ == "__main__":
    main()
