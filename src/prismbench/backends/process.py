"""Own only children we launch, including Windows launcher descendants."""

from __future__ import annotations

import ctypes
import os
import signal
import subprocess
import time
from ctypes import wintypes
from typing import Any

import psutil


class _BasicLimit(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount",
    )]


class _ExtendedLimit(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimit), ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _WindowsJob:
    def __init__(self) -> None:
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            "AssignProcessToJobObject": ([wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
            "OpenThread": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            "ResumeThread": ([wintypes.HANDLE], wintypes.DWORD),
            "QueryInformationJobObject": ([wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.kernel, name)
            fn.argtypes, fn.restype = args, result
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = _ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.get_last_error()
            self.close()
            raise ctypes.WinError(error)

    def assign_and_resume(self, proc: subprocess.Popen) -> None:
        if not self.kernel.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(proc._handle))):
            raise ctypes.WinError(ctypes.get_last_error())
        threads = psutil.Process(proc.pid).threads()
        if len(threads) != 1:
            raise RuntimeError("Expected one suspended primary thread at process startup")
        handle = self.kernel.OpenThread(0x0002, False, threads[0].id)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if self.kernel.ResumeThread(handle) != 1:
                raise RuntimeError("Could not resume the owned suspended process")
        finally:
            self.kernel.CloseHandle(handle)

    def pids(self) -> list[int]:
        # JobObjectBasicProcessIdList: two DWORDs then ULONG_PTR identifiers.
        # Enumerate the Job itself, even if an intermediate launcher has exited.
        size = 8 + ctypes.sizeof(ctypes.c_size_t) * 4096
        buffer = ctypes.create_string_buffer(size)
        if not self.kernel.QueryInformationJobObject(self.handle, 3, buffer, size, None):
            raise ctypes.WinError(ctypes.get_last_error())
        count = wintypes.DWORD.from_buffer(buffer, 4).value
        return list((ctypes.c_size_t * count).from_buffer(buffer, 8))

    def terminate(self) -> None:
        if self.handle and not self.kernel.TerminateJobObject(self.handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class OwnedProcess:
    """A kill-on-close Job on Windows; a dedicated process group on POSIX.

    Never fall back to launching an unowned Windows process. Explicit close is
    required on POSIX; an uncatchable controller kill is not crash-safe there.
    """

    def __init__(self, argv: list[str], **kwargs: Any) -> None:
        self._job = _WindowsJob() if os.name == "nt" else None
        self._closed: dict | None = None
        self.process: subprocess.Popen | None = None
        try:
            if self._job:
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | 0x00000004
            else:
                kwargs["start_new_session"] = True
            self.process = subprocess.Popen(argv, **kwargs)
            if self._job:
                self._job.assign_and_resume(self.process)
        except BaseException:
            try:
                if self.process is not None:
                    self.process.kill()
                    self.process.wait(timeout=5)
            finally:
                # Job closure is the final ownership guarantee even if direct
                # termination/reaping itself fails during partial construction.
                if self._job:
                    self._job.close()
            raise

    @property
    def pid(self) -> int:
        return self.process.pid

    def poll(self) -> int | None:
        return self.process.poll()

    def pids(self) -> list[int]:
        if self._closed is not None:
            return []
        if self._job:
            return self._job.pids()
        result = []
        for proc in psutil.process_iter(["pid", "status"]):
            try:
                if os.getpgid(proc.pid) == self.pid and proc.status() != psutil.STATUS_ZOMBIE:
                    result.append(proc.pid)
            except (OSError, psutil.Error):
                continue
        return result

    def close(self, timeout_s: float = 5) -> dict:
        if self._closed is not None:
            return self._closed
        errors = []
        remaining: list[int] = []
        try:
            if self._job:
                self._job.terminate()
            else:
                try:
                    os.killpg(self.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                self.process.poll()  # Reap our POSIX child as soon as it exits.
                remaining = self.pids()
                if not remaining:
                    break
                time.sleep(0.025)
            if remaining and not self._job:
                try:
                    os.killpg(self.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            self.process.wait(timeout=max(1, timeout_s))
            deadline = time.monotonic() + max(1, timeout_s)
            while time.monotonic() < deadline:
                remaining = self.pids()
                if not remaining:
                    break
                time.sleep(0.025)
        except (OSError, psutil.Error, subprocess.TimeoutExpired) as exc:
            errors.append(str(exc))
        finally:
            if self._job:
                self._job.close()
        self._closed = {"success": not remaining and not errors,
                        "remaining_pids": remaining, "exit_code": self.poll(), "errors": errors}
        return self._closed
