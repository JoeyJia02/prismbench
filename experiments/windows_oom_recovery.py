"""Opt-in, bounded Windows VRAM allocation-failure experiment, outside the package.

Run with the installed release's Python and -I. This controller temporarily
subclasses private 0.1.0a1 Job internals ONLY to cap its child CLI before resume;
the CLI and model server run the unchanged installed package in another process.
An allocation failure is not a speed or maximum-context measurement.
"""

from __future__ import annotations

import argparse
import ctypes
import importlib.metadata
import json
import math
import os
import re
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

import prismbench
from prismbench.backends import process as owned
from prismbench.config import load_config
from prismbench.hardware import sample
from prismbench.io import hash_file, save_json

GIB = 1024 ** 3
MODEL_SHA = "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"
SERVER_SHA = "aa2e1f5c67be55f11be26ae58d643a545ca07c6de498f6f870330ac2f4dfec73"
PROTOCOL = {"version": 1, "baseline_samples": 5, "sample_interval_s": 1,
            "watchdog_interval_s": 0.1, "minimum_start_available_ram_bytes": 12 * GIB,
            "minimum_run_available_ram_bytes": 8 * GIB, "job_commit_limit_bytes": 8 * GIB,
            "maximum_tree_rss_bytes": 8 * GIB, "outer_wall_limit_s": 120,
            "post_chain_samples": 15, "settle_last_samples": 3, "settle_tolerance_mib": 256}


def validate_config(config):
    expected = {"backend": "llama_cpp", "repetitions": 1, "seed": 42, "gpu_index": 0,
                "load_timeout_seconds": 30, "request_timeout_seconds": 15,
                "sample_interval_seconds": 0.5, "quality": False, "quality_suite": None,
                "expected_model_sha256": MODEL_SHA}
    expected_case = {"context_size": 524288, "prompt_tokens": 128, "output_tokens": 16,
                     "gpu_layers": 99, "threads": 6, "batch_size": 128, "ubatch_size": 64,
                     "cache_type_k": "f16", "cache_type_v": "f16", "flash_attention": "on",
                     "fallbacks": [{"context_size": 2048}]}
    if any(getattr(config, k) != v for k, v in expected.items()) or len(config.cases) != 1:
        raise ValueError("Configuration does not match the fixed, bounded experiment protocol")
    if any(getattr(config.cases[0], k) != v for k, v in expected_case.items()):
        raise ValueError("Case must be the exact 524288 -> 2048 context-only fallback protocol")


def guard_reason(available_ram, tree_rss, elapsed):
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0
           for v in (available_ram, tree_rss, elapsed)):
        return "watchdog input unavailable or invalid"
    if available_ram < PROTOCOL["minimum_run_available_ram_bytes"]:
        return "host available RAM below 8 GiB"
    if tree_rss > PROTOCOL["maximum_tree_rss_bytes"]:
        return "owned tree RSS above 8 GiB (shared pages may be double-counted)"
    if elapsed >= PROTOCOL["outer_wall_limit_s"]:
        return "outer CLI wall deadline reached"
    return None


def finite_memory(row):
    value = row.get("vram_used_mib")
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def admission(baseline):
    return (len(baseline) == PROTOCOL["baseline_samples"]
            and all(finite_memory(s) and s.get("gpu_uuid") for s in baseline)
            and len({s["gpu_uuid"] for s in baseline}) == 1
            and all(s.get("system_ram_available_mib", 0) * 1024 ** 2 >=
                    PROTOCOL["minimum_start_available_ram_bytes"] for s in baseline))


def settled(baseline, post):
    if not admission(baseline) or len(post) < PROTOCOL["post_chain_samples"]:
        return False
    ceiling = statistics.median(s["vram_used_mib"] for s in baseline) + 256
    return all(finite_memory(s) and s.get("gpu_uuid") == baseline[0]["gpu_uuid"]
               and s["vram_used_mib"] <= ceiling for s in post[-3:])


def cuda_allocation_failure(log):
    """Generic OOM, bad_alloc, host memory and HTTP errors cannot prove VRAM OOM."""
    return bool(re.search(r"\bcudaMalloc[^\r\n]*\bout of memory\b", log, re.IGNORECASE))


def check_chain(result, oom_log):
    rows = result.get("attempts", [])
    if result.get("synthetic") is not False or len(rows) != 2:
        return False
    first, second = rows
    return (first.get("status") == "OOM" and second.get("status") == "SUCCESS"
            and first.get("cleanup_confirmed") is True and second.get("cleanup_confirmed") is True
            and first.get("attempt_index") == 0 and second.get("attempt_index") == 1
            and first.get("parent_attempt_id") is None and first.get("attempt_id")
            and second.get("parent_attempt_id") == first["attempt_id"]
            and first.get("requested", {}).get("context_size") == 524288
            and second.get("requested", {}).get("context_size") == 2048
            and second.get("runtime", {}).get("effective", {}).get("context_size") == 2048
            and second.get("metrics", {}).get("prompt_tokens") == 128
            and second.get("metrics", {}).get("generated_tokens") == 16
            and second.get("metrics", {}).get("cache_tokens") == 0
            and cuda_allocation_failure(oom_log))


class CappedJob(owned._WindowsJob):
    def __init__(self):
        super().__init__()
        limits = owned._ExtendedLimit()
        limits.BasicLimitInformation.LimitFlags = 0x2000 | 0x0200  # KILL_ON_CLOSE | JOB_MEMORY
        limits.JobMemoryLimit = PROTOCOL["job_commit_limit_bytes"]
        try:
            if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(limits),
                                                       ctypes.sizeof(limits)):
                raise ctypes.WinError(ctypes.get_last_error())
            actual = owned._ExtendedLimit()
            if not self.kernel.QueryInformationJobObject(self.handle, 9, ctypes.byref(actual),
                                                         ctypes.sizeof(actual), None):
                raise ctypes.WinError(ctypes.get_last_error())
            if (actual.BasicLimitInformation.LimitFlags & 0x2200 != 0x2200
                    or actual.JobMemoryLimit != PROTOCOL["job_commit_limit_bytes"]):
                raise RuntimeError("Windows did not confirm the commit limit and kill-on-close")
            self.confirmed_limits = {"limit_flags": actual.BasicLimitInformation.LimitFlags,
                                     "job_memory_limit_bytes": actual.JobMemoryLimit}
        except BaseException:
            self.close()
            raise


def start_capped(argv, **kwargs):
    original = owned._WindowsJob
    try:
        owned._WindowsJob = CappedJob
        return owned.OwnedProcess(argv, **kwargs)
    finally:
        owned._WindowsJob = original


def collect_samples(index, count, phase):
    rows = []
    for _ in range(count):
        started = time.monotonic()
        rows.append({"phase": phase, **sample(index)})
        time.sleep(max(0, 1 - (time.monotonic() - started)))
    return rows


def telemetry_loop(index, stop, path, rows):
    with path.open("w", encoding="utf-8") as stream:
        while not stop.is_set():
            started = time.monotonic()
            row = {"phase": "cli_chain", **sample(index)}
            rows.append(row)
            stream.write(json.dumps(row, allow_nan=False) + "\n")
            stream.flush()
            stop.wait(max(0, 1 - (time.monotonic() - started)))


def tree_rss(process):
    total = 0
    for pid in process.pids():
        try:
            total += psutil.Process(pid).memory_info().rss
        except psutil.NoSuchProcess:
            pass
    return total


def execute(config_path, output):
    if os.name != "nt" or not sys.flags.isolated:
        raise ValueError("Requires Windows and python -I using the installed release environment")
    if (prismbench.__version__ != "0.1.0a1" or
            importlib.metadata.version("prismbench") != "0.1.0a1" or
            "site-packages" not in Path(prismbench.__file__).resolve().parts):
        raise ValueError("Requires installed PrismBench 0.1.0a1, not a source/editable checkout")
    config = load_config(config_path)
    validate_config(config)
    if output.exists():
        raise FileExistsError("Refusing an existing output directory")
    existing = [p.pid for p in psutil.process_iter(["name"])
                if (p.info["name"] or "").lower() in ("llama-server", "llama-server.exe")]
    if existing:
        raise ValueError(f"Existing llama-server processes found; leave them untouched: {existing}")
    if hash_file(Path(config.model)) != MODEL_SHA or hash_file(Path(config.server)) != SERVER_SHA:
        raise ValueError("Pinned model/runtime hashes differ; do not run this protocol on unknown assets")
    output.mkdir(parents=True, exist_ok=False)
    (output / "config.input.json").write_bytes(config_path.read_bytes())
    save_json(output / "config.resolved.json", config.to_dict())
    package = Path(prismbench.__file__).parent
    audit = {"protocol": PROTOCOL, "harness_sha256": hash_file(Path(__file__)),
             "source_sha256": {p.relative_to(package).as_posix(): hash_file(p)
                               for p in sorted(package.rglob("*.py"))},
             "python": sys.executable, "package_path": str(package), "tool_version": "0.1.0a1",
             "baseline": [], "samples": [], "guards": [], "post_chain": [],
             "abort_reason": None, "hard_limit_confirmed_before_resume": False,
             "cleanup": None, "sentinel_survived_cli_cleanup": False,
             "sentinel_cleanup": None, "chain_verified": False,
             "claim_scope": "Bounded CUDA allocator failure and fallback under an 8 GiB Windows "
             "Job commit cap; the cause cannot be attributed solely to physical VRAM exhaustion.",
             "physical_vram_oom_proven": False,
             "interpretation": "Whole-device sampled settling only; not every app's preservation, "
             "not VRAM release before fallback, not physical capacity or maximum usable context. "
             "Guard-triggered and host/Job memory failures are inconclusive, not VRAM OOM."}
    child = sentinel = None
    stop, telemetry = threading.Event(), None
    try:
        audit["baseline"] = collect_samples(config.gpu_index, 5, "baseline")
        if not admission(audit["baseline"]):
            raise RuntimeError("Admission refused: need five valid same-device samples and >=12 GiB available RAM")
        sentinel = owned.OwnedProcess([sys.executable, "-I", "-c", "import time; time.sleep(180)"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with (output / "cli.stdout.log").open("wb") as out, (output / "cli.stderr.log").open("wb") as err:
            started = time.monotonic()
            argv = [sys.executable, "-I", "-m", "prismbench", "run",
                    str(output / "config.resolved.json"), "--output", str(output / "benchmark")]
            audit["command"] = argv
            child = start_capped(argv, stdout=out, stderr=err, cwd=str(output))
            audit["hard_limit_confirmed_before_resume"] = True
            audit["windows_job_limits"] = child._job.confirmed_limits
            audit["sentinel_outside_cli_job"] = sentinel.pid not in child.pids()
            if not audit["sentinel_outside_cli_job"]:
                raise RuntimeError("Sentinel unexpectedly belongs to capped CLI job")
            telemetry = threading.Thread(target=telemetry_loop, args=(config.gpu_index, stop,
                                         output / "external-telemetry.jsonl", audit["samples"]), daemon=True)
            telemetry.start()
            while child.poll() is None:
                now = time.monotonic()
                available, rss = psutil.virtual_memory().available, tree_rss(child)
                audit["guards"].append({"monotonic_s": now, "available_ram_bytes": available,
                                        "owned_tree_rss_bytes": rss})
                reason = guard_reason(available, rss, now - started)
                if reason:
                    raise RuntimeError(reason)
                if not telemetry.is_alive():
                    raise RuntimeError("External telemetry thread failed")
                time.sleep(0.1)
            audit["cli_exit_code"] = child.poll()
            audit["cli_wall_s"] = time.monotonic() - started
    except (Exception, KeyboardInterrupt) as exc:
        audit["abort_reason"] = f"{type(exc).__name__}: {exc}"
    finally:
        if child:
            try:
                audit["cleanup"] = child.close()
            except Exception as exc:
                audit["cleanup"] = {"success": False, "error": str(exc)}
        stop.set()
        if telemetry:
            telemetry.join(timeout=5)
            audit["telemetry_stopped"] = not telemetry.is_alive()
        audit["sentinel_survived_cli_cleanup"] = sentinel is not None and sentinel.poll() is None
        try:
            audit["post_chain"] = collect_samples(config.gpu_index, 15, "post_chain")
        except Exception as exc:
            audit["post_sampling_error"] = str(exc)
        finally:
            if sentinel:
                try:
                    audit["sentinel_cleanup"] = sentinel.close()
                except Exception as exc:
                    audit["sentinel_cleanup"] = {"success": False, "error": str(exc)}
        audit["vram_settled"] = settled(audit["baseline"], audit["post_chain"])
        try:
            result = json.loads((output / "benchmark" / "results.json").read_text(encoding="utf-8"))
            first = result["attempts"][0]
            evidence = (output / "benchmark" / first["evidence_dir"]).resolve()
            evidence.relative_to((output / "benchmark").resolve())
            log = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                            for p in evidence.glob("server.*.log"))
            audit["chain_verified"] = bool(check_chain(result, log))
            audit["cuda_allocation_diagnostic"] = cuda_allocation_failure(log)
        except (OSError, ValueError, TypeError, KeyError, IndexError) as exc:
            audit["evidence_error"] = str(exc)
        passed = (not audit["abort_reason"] and audit["hard_limit_confirmed_before_resume"]
                  and (audit["cleanup"] or {}).get("success") and audit["cli_exit_code"] == 0
                  and audit["chain_verified"] and audit["vram_settled"]
                  and audit["sentinel_survived_cli_cleanup"] and audit.get("telemetry_stopped")
                  and bool(audit["samples"]) and bool(audit["guards"])
                  and (audit["sentinel_cleanup"] or {}).get("success"))
        audit["outcome"] = "PASS" if passed else "INCONCLUSIVE"
        save_json(output / "audit.json", audit)
    print(f"{audit['outcome']}: {output / 'audit.json'}")
    return 0 if audit["outcome"] == "PASS" else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-hardware-oom", action="store_true",
                        help="Explicitly opt in to a real, bounded GPU allocation-failure experiment")
    args = parser.parse_args()
    if not args.confirm_hardware_oom:
        parser.error("Real OOM experiment requires --confirm-hardware-oom")
    try:
        return execute(args.config.resolve(), args.output.resolve())
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Refused before launching: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
