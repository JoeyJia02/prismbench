"""Best-effort sampled telemetry with explicit device and process scopes."""

import csv
import io
import math
import platform
import subprocess
import threading
import time
from pathlib import Path

import psutil

from .io import canonical

MIB = 1024 * 1024


def smi_sample(index: int) -> dict:
    fields = "index,uuid,name,driver_version,memory.total,memory.used,utilization.gpu,temperature.gpu"
    try:
        p = subprocess.run(["nvidia-smi", f"--id={index}", f"--query-gpu={fields}",
                            "--format=csv,noheader,nounits"], capture_output=True,
                           encoding="utf-8", errors="replace", timeout=2,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if p.returncode:
            raise RuntimeError(p.stderr.strip()[:300])
        rows = list(csv.reader(io.StringIO(p.stdout)))
        if len(rows) != 1 or len(rows[0]) != 8:
            raise ValueError("unexpected nvidia-smi CSV shape")
        r = [v.strip() for v in rows[0]]
        result = dict(zip(("gpu_index", "gpu_uuid", "gpu_name", "driver_version"), r[:4]))
        unavailable = []
        for name, value in zip(("vram_total_mib", "vram_used_mib", "gpu_utilization_percent",
                                "gpu_temperature_c"), r[4:]):
            try:
                number = float(value)
                if not math.isfinite(number) or number < 0:
                    raise ValueError("nonfinite or negative telemetry")
                result[name] = number
            except ValueError:
                result[name] = None
                unavailable.append(name)
        result["gpu_telemetry_error"] = "Unavailable fields: " + ", ".join(unavailable) if unavailable else None
        return result
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        return {"gpu_index": str(index), "gpu_uuid": None, "gpu_name": None,
                "driver_version": None, "vram_total_mib": None, "vram_used_mib": None,
                "gpu_utilization_percent": None, "gpu_temperature_c": None,
                "gpu_telemetry_error": str(exc)}


def sample(index: int, pid: int | None = None) -> dict:
    row = {"monotonic_s": time.monotonic(), **smi_sample(index)}
    vm = psutil.virtual_memory()
    row.update(system_ram_total_mib=vm.total / MIB, system_ram_used_mib=vm.used / MIB,
               system_ram_available_mib=vm.available / MIB, process_tree_rss_mib=None)
    if pid is not None:
        try:
            root = psutil.Process(pid)
            rss = 0
            for process in [root] + root.children(recursive=True):
                try:
                    rss += process.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            row["process_tree_rss_mib"] = rss / MIB
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return row


def detect(index: int = 0) -> dict:
    return {"os": platform.platform(), "python": platform.python_version(),
            "cpu": platform.processor(), "logical_cpu_count": psutil.cpu_count(),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "telemetry_scope": "whole selected device; process-tree RSS may double-count shared pages",
            "snapshot": sample(index)}


class Collector:
    def __init__(self, out: Path, index: int, interval: float, pid_fn):
        self.out, self.index, self.interval, self.pid_fn = out, index, interval, pid_fn
        self.rows: list[dict] = []
        self.phase = "loading"
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def take(self, phase=None):
        with self._lock:
            row = sample(self.index, self.pid_fn())
            row["phase"] = phase or self.phase
            self.rows.append(row)
            with self.out.open("ab") as stream:
                stream.write(canonical(row) + b"\n")
            return row

    def start(self):
        self._thread.start()

    def _run(self):
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                self.take()
            except (OSError, psutil.Error) as exc:
                self.rows.append({"phase": self.phase, "telemetry_error": str(exc)})
            self._stop.wait(max(0.01, self.interval - (time.monotonic() - started)))

    def close(self):
        self._stop.set()
        self._thread.join(timeout=5)

    def metrics(self):
        def peak(key):
            values = [r[key] for r in self.rows if r.get(key) is not None]
            return max(values) if values else None
        return {"peak_vram_mib": peak("vram_used_mib"),
                "peak_process_rss_mib": peak("process_tree_rss_mib"),
                "peak_system_ram_used_mib": peak("system_ram_used_mib"),
                "telemetry_samples": len(self.rows),
                "sample_interval_seconds": self.interval,
                "gpu_process_vram_mib": None}
