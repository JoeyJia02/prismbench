import os
import subprocess
import sys
import time
from types import SimpleNamespace

import psutil
import pytest

from prismbench.backends.process import OwnedProcess


def wait_file(path, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists() and path.read_text():
            return int(path.read_text())
        time.sleep(.025)
    raise AssertionError("fixture did not write child PID")


def alive(pid):
    try:
        return psutil.Process(pid).is_running() and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def test_cleanup_kills_grandchild_and_preserves_unrelated_process(tmp_path):
    pidfile = tmp_path / "child.txt"
    code = ("import subprocess,sys,pathlib,time; "
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']); "
            "pathlib.Path(sys.argv[1]).write_text(str(p.pid));time.sleep(60)")
    other = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(60)"],
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    owned = OwnedProcess([sys.executable, "-c", code, str(pidfile)])
    try:
        child = wait_file(pidfile)
        assert child in owned.pids()
        cleanup = owned.close(timeout_s=1)
        assert cleanup["success"], cleanup
        assert not alive(child)
        assert other.poll() is None
        assert owned.close() == cleanup
    finally:
        owned.close()
        other.kill()
        other.wait(timeout=5)


@pytest.mark.skipif(os.name != "nt", reason="Windows Job crash-cleanup guarantee")
def test_windows_controller_crash_closes_job(tmp_path):
    pidfile = tmp_path / "crash-child.txt"
    script = tmp_path / "controller.py"
    source = str(__import__("pathlib").Path(__file__).parents[1] / "src")
    script.write_text(
        "import sys,os,time,pathlib\n"
        f"sys.path.insert(0,{source!r})\n"
        "from prismbench.backends.process import OwnedProcess\n"
        "p=OwnedProcess([sys.executable,'-c','import time;time.sleep(60)'])\n"
        f"pathlib.Path({str(pidfile)!r}).write_text(str(p.pid))\n"
        "time.sleep(.2)\nos._exit(0)\n"
    )
    controller = subprocess.Popen([sys.executable, str(script)], creationflags=subprocess.CREATE_NO_WINDOW)
    child = wait_file(pidfile)
    controller.wait(timeout=5)
    deadline = time.monotonic() + 5
    while alive(child) and time.monotonic() < deadline:
        time.sleep(.025)
    assert not alive(child)


def test_failed_assignment_closes_job_even_when_direct_kill_raises(monkeypatch):
    from prismbench.backends import process

    class FakeJob:
        closed = False

        def assign_and_resume(self, _proc):
            raise RuntimeError("fixture assignment failed")

        def close(self):
            self.closed = True

    class FakeProcess:
        def kill(self):
            raise RuntimeError("fixture direct kill failed")

    job = FakeJob()
    monkeypatch.setattr(process, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(process, "_WindowsJob", lambda: job)
    monkeypatch.setattr(process.subprocess, "CREATE_NO_WINDOW", 0, raising=False)
    monkeypatch.setattr(process.subprocess, "Popen", lambda *_args, **_kwargs: FakeProcess())
    with pytest.raises(RuntimeError, match="direct kill failed"):
        OwnedProcess(["fixture"])
    assert job.closed
