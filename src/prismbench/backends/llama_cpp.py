"""Version-checked, owned local llama.cpp server adapter."""

from __future__ import annotations

import json
import os
import queue
import re
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from prismbench.backends.base import BackendError
from prismbench.backends.process import OwnedProcess
from prismbench.config import Case, Config
from prismbench.io import save_json


def is_oom(text: str) -> bool:
    """Positive allocation evidence only; HTTP 500/exit codes alone are ambiguous."""
    return bool(re.search(
        r"\bout of memory\b|\bCUDA_ERROR_OUT_OF_MEMORY\b|\bcudaMalloc[^\n]*(?:failed|error)"
        r"|failed to allocate (?:CUDA|GPU|device|host|CPU|memory)"
        r"|\bstd::bad_alloc\b", text, re.IGNORECASE))


def parse_effective(log: str, slots: list, expected_context: int,
                    requested_layers: int | None = None) -> dict:
    if (not isinstance(slots, list) or len(slots) != 1
            or slots[0].get("n_ctx") != expected_context
            or slots[0].get("speculative", False)):
        raise BackendError("INVALID_WORKLOAD", "Effective slot/context differs from requested case")
    matches = re.findall(r"offloaded\s+(\d+)/(\d+)\s+layers to GPU", log)
    loaded, total = (map(int, matches[-1]) if matches else (None, None))
    if loaded is not None and requested_layers is not None and loaded != min(requested_layers, total):
        raise BackendError("INVALID_WORKLOAD", "Effective GPU layer placement differs from request")
    warnings = [] if loaded is not None else ["Effective GPU layer counts unavailable in runtime logs"]
    return {"context_size": slots[0]["n_ctx"], "parallel": 1,
            "gpu_layers_loaded": loaded, "gpu_layers_total": total,
            "cpu_offload": loaded < total if loaded is not None else None,
            "automatic_fit": False, "prompt_cache": False, "context_shift": False,
            "verification_warnings": warnings}


class LlamaCppBackend:
    def __init__(self, config: Config, case: Case, out: Path):
        self.config, self.case, self.out = config, case, out
        self.out.mkdir(parents=True, exist_ok=True)
        self._process: OwnedProcess | None = None
        self._sequence = 0
        self._base = ""
        self._api_key = uuid.uuid4().hex
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.cleanup = {"success": True, "remaining_pids": [], "exit_code": None, "errors": []}
        self._preflight_cleanup_failure: dict | None = None
        self._close_lock = threading.Lock()

    @property
    def pid(self) -> int | None:
        return self._process.pid if self._process else None

    def _logs(self) -> str:
        chunks = []
        for name in ("server.stdout.log", "server.stderr.log"):
            path = self.out / name
            if path.exists():
                # Error diagnostics and model-load evidence need only the log tail.
                with path.open("rb") as stream:
                    stream.seek(max(0, path.stat().st_size - 1024 * 1024))
                    chunks.append(stream.read().decode("utf-8", errors="replace"))
        return "\n".join(chunks)

    def _error(self, message: str) -> BackendError:
        return BackendError("OOM" if is_oom(message + "\n" + self._logs()) else "ERROR", message)

    def _runtime_info(self, option: str) -> str:
        path = self.out / ("runtime-" + option.lstrip("-") + ".txt")
        with path.open("wb") as output:
            process = OwnedProcess([self.config.server, option], cwd=str(Path(self.config.server).parent),
                                   stdout=output, stderr=subprocess.STDOUT, env=self._environment())
        try:
            deadline = time.monotonic() + 15
            while process.poll() is None and time.monotonic() < deadline:
                time.sleep(0.025)
            if process.poll() is None:
                raise BackendError("TIMEOUT", f"Runtime {option} timed out")
            if process.poll() != 0:
                raise BackendError("ERROR", f"Runtime {option} exited with {process.poll()}")
            return path.read_text(encoding="utf-8", errors="replace")
        finally:
            cleanup = process.close()
            if not cleanup["success"]:
                self._preflight_cleanup_failure = cleanup
                self.cleanup = cleanup
                raise BackendError("ERROR", f"Failed to clean up runtime {option}")

    def _environment(self) -> dict:
        prefixes = ("LLAMA_", "GGML_", "BONSAI_", "CUDA_", "CUBLAS_", "MTMD_")
        removed = sorted(key for key in os.environ if key.startswith(prefixes))
        environment = {key: value for key, value in os.environ.items() if key not in removed}
        device = str(self.config.gpu_index)
        resolved = False
        try:
            output = subprocess.run(
                ["nvidia-smi", f"--id={self.config.gpu_index}", "--query-gpu=uuid", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if output.returncode == 0 and re.fullmatch(r"GPU-[a-fA-F0-9-]+", output.stdout.strip()):
                device, resolved = output.stdout.strip(), True
        except (OSError, subprocess.TimeoutExpired):
            pass
        environment["CUDA_VISIBLE_DEVICES"] = device
        self._device = device
        save_json(self.out / "runtime-environment.json", {
            "explicit": {"CUDA_VISIBLE_DEVICES": device}, "gpu_uuid_resolved": resolved,
            "removed_override_names": removed,
        })
        return environment

    def start(self) -> dict:
        environment = self._environment()
        version = self._runtime_info("--version").strip()
        help_text = self._runtime_info("--help")
        required = ["--fit", "--cache-ram", "--no-context-shift", "--slots",
                    "--slot-save-path", "--flash-attn", "--no-warmup", "--api-key"]
        missing = [flag for flag in required if flag not in help_text]
        if missing:
            raise BackendError("ERROR", "Incompatible llama-server; missing flags: " + ", ".join(missing))
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        self._base = f"http://127.0.0.1:{port}"
        cache_dir = self.out / "slot-cache"
        cache_dir.mkdir(exist_ok=True)
        case = self.case
        argv = [self.config.server, "--model", self.config.model, "--host", "127.0.0.1",
                "--port", str(port), "--api-key", self._api_key,
                "--ctx-size", str(case.context_size), "--parallel", "1",
                "--n-gpu-layers", str(case.gpu_layers), "--threads", str(case.threads),
                "--batch-size", str(case.batch_size), "--ubatch-size", str(case.ubatch_size),
                "--cache-type-k", case.cache_type_k, "--cache-type-v", case.cache_type_v,
                "--flash-attn", case.flash_attention, "--fit", "off", "--cache-ram", "0",
                "--no-context-shift", "--no-warmup", "--slots", "--slot-save-path", str(cache_dir),
                "--verbosity", "4"]
        if "--no-webui" in help_text:
            argv.append("--no-webui")
        save_json(self.out / "command.json", argv)
        start = time.perf_counter()
        with (self.out / "server.stdout.log").open("wb") as stdout, \
                (self.out / "server.stderr.log").open("wb") as stderr:
            self._process = OwnedProcess(argv, cwd=str(Path(self.config.server).parent),
                                         env=environment, stdout=stdout, stderr=stderr)
        deadline = time.monotonic() + self.config.load_timeout_seconds
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                raise self._error(f"Server exited during load ({self._process.poll()}); inspect server logs")
            try:
                health = self._request("/health", timeout_s=min(2, max(.05, deadline-time.monotonic())),
                                       terminate_on_timeout=False)
                if health.get("status") == "ok":
                    break
            except BackendError:
                pass
            time.sleep(0.05)
        else:
            raise BackendError("TIMEOUT", "Model startup-to-ready deadline exceeded")
        load_time = time.perf_counter() - start
        # /health is public upstream; authenticated /props prevents accepting a
        # foreign server if another process won the ephemeral port race.
        self._request("/props", timeout_s=self.config.request_timeout_seconds)
        slots = self._request("/slots", timeout_s=self.config.request_timeout_seconds)
        log = self._logs()
        effective = parse_effective(log, slots, case.context_size, case.gpu_layers)
        for name, pattern, requested in (
                ("cache_type_k", r"K \(([^)]+)\):", case.cache_type_k),
                ("cache_type_v", r"V \(([^)]+)\):", case.cache_type_v),
                ("flash_attention", r"flash_attn\s*=\s*(enabled|disabled)", case.flash_attention)):
            values = re.findall(pattern, log)
            actual = values[-1] if values else None
            if name == "flash_attention" and actual is not None:
                actual = "on" if actual == "enabled" else "off"
            if actual is not None and actual != requested:
                raise BackendError("INVALID_WORKLOAD", f"Effective {name} differs from request")
            if actual is None:
                effective["verification_warnings"].append(f"Effective {name} unavailable in runtime logs")
            effective[name] = actual
        effective["gpu_device"] = self._device
        return {"load_time_s": load_time, "runtime_version": version, "argv": argv,
                "effective": effective}

    def _request(self, route: str, payload=None, timeout_s: float = 30,
                 stream: bool = False, terminate_on_timeout: bool = True):
        self._sequence += 1
        prefix = f"{self._sequence:04d}-{route.split('?')[0].strip('/').replace('/', '-')}"
        save_json(self.out / (prefix + "-request.json"), {"route": route, "body": payload})
        results: queue.Queue = queue.Queue(maxsize=1)

        def work():
            try:
                results.put((True, self._exchange(route, payload, timeout_s, stream, prefix)))
            except BaseException as exc:
                results.put((False, exc))

        threading.Thread(target=work, daemon=True, name="prismbench-http").start()
        try:
            success, value = results.get(timeout=timeout_s)
        except queue.Empty as exc:
            if terminate_on_timeout:
                self.close()
            raise BackendError("TIMEOUT", f"Request {route} exceeded {timeout_s}s wall deadline") from exc
        if not success:
            if isinstance(value, (TimeoutError, socket.timeout)):
                if terminate_on_timeout:
                    self.close()
                raise BackendError("TIMEOUT", f"Request {route} timed out") from value
            if isinstance(value, BackendError):
                raise value
            raise self._error(f"Request {route} failed: {value}") from value
        return value

    def _exchange(self, route, payload, timeout_s, stream, prefix):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(self._base + route, data=data,
                                        headers={"Content-Type": "application/json",
                                                 "Authorization": "Bearer " + self._api_key})
        started = time.perf_counter()
        raw_path = self.out / (prefix + ("-response.sse" if stream else "-response.json"))
        try:
            response = self._opener.open(request, timeout=timeout_s)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            raw_path.write_bytes(raw)
            raise self._error(f"HTTP {exc.code} {route}: {raw.decode('utf-8', errors='replace')[:4096]}") from exc
        with response, raw_path.open("wb") as evidence:
            if not stream:
                raw = response.read()
                evidence.write(raw)
                return json.loads(raw)
            events = []
            contents = []
            first_text = None
            terminal = None
            data_lines = []
            for raw in response:
                evidence.write(raw)
                evidence.flush()
                line = raw.decode("utf-8").rstrip("\r\n")
                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip(" "))
                elif not line and data_lines:
                    event_text = "\n".join(data_lines)
                    data_lines = []
                    if event_text == "[DONE]":
                        break
                    event = json.loads(event_text)
                    events.append(event)
                    if "error" in event:
                        raise self._error("Stream error: " + json.dumps(event["error"]))
                    content = event.get("content", "")
                    if not isinstance(content, str):
                        raise BackendError("ERROR", "Malformed streaming content")
                    if content:
                        # Some protocol variants attach aggregate text to the
                        # terminal record. It does not establish a first-text event.
                        if first_text is None and event.get("stop") is not True:
                            first_text = time.perf_counter() - started
                        contents.append(content)
                    if event.get("stop") is True:
                        terminal = event
                        break
            latency = time.perf_counter() - started
            save_json(self.out / (prefix + "-events.json"), events)
            if terminal is None:
                raise BackendError("ERROR", "Stream ended without a terminal completion event")
            timings = terminal.get("timings")
            if not isinstance(timings, dict):
                raise BackendError("ERROR", "Terminal completion event has no runtime timings")
            if type(terminal.get("truncated")) is not bool:
                raise BackendError("ERROR", "Terminal completion event has no truncation status")
            return {"ttft_s": first_text, "total_latency_s": latency, "timings": timings,
                    "content": "".join(contents), "truncated": terminal["truncated"],
                    "ttft_definition": "first_nonempty_generated_text_chunk"}

    def tokenize(self, text: str) -> list[int]:
        response = self._request("/tokenize", {"content": text, "add_special": True,
                                               "parse_special": False},
                                 timeout_s=self.config.request_timeout_seconds)
        tokens = response.get("tokens")
        if not isinstance(tokens, list) or not tokens or any(type(t) is not int for t in tokens):
            raise BackendError("INVALID_WORKLOAD", "Runtime tokenizer did not return integer token IDs")
        return tokens

    def erase(self) -> None:
        response = self._request("/slots/0?action=erase", {}, self.config.request_timeout_seconds)
        if (response.get("id_slot") != 0 or type(response.get("n_erased")) is not int
                or response["n_erased"] < 0):
            raise BackendError("INVALID_WORKLOAD", "Runtime did not confirm slot cache erasure")

    def complete(self, tokens: list[int], n_predict: int, seed: int, timeout_s: float) -> dict:
        return self._request("/completion", {
            "prompt": tokens, "n_predict": n_predict, "seed": seed, "temperature": 0,
            "cache_prompt": False, "id_slot": 0, "ignore_eos": True, "stream": True,
            "return_tokens": True,
        }, timeout_s, stream=True)

    def probe(self, prompt: str, n_predict: int, seed: int, timeout_s: float) -> str:
        # Feed the same tokenization policy used by quality preflight. Sending a
        # string would allow the runtime to reinterpret special-token spellings.
        tokens = self.tokenize(prompt)
        response = self._request("/completion", {
            "prompt": tokens, "n_predict": n_predict, "seed": seed, "temperature": 0,
            "cache_prompt": False, "stream": False, "ignore_eos": False,
            "id_slot": 0,
        }, timeout_s)
        timings = response.get("timings", {})
        if (timings.get("prompt_n") != len(tokens) or timings.get("cache_n") != 0
                or response.get("truncated") is not False):
            raise BackendError("INVALID_WORKLOAD", "Quality probe prompt/cache/truncation differs from request")
        try:
            content = response["content"]
        except (KeyError, TypeError) as exc:
            raise BackendError("ERROR", "Malformed completion probe response") from exc
        if not isinstance(content, str):
            raise BackendError("ERROR", "Completion probe content was not text")
        return content

    def close(self) -> bool:
        with self._close_lock:
            if self._process is not None:
                self.cleanup = self._process.close()
            if self._preflight_cleanup_failure is not None:
                failed = self._preflight_cleanup_failure
                self.cleanup = {
                    "success": False,
                    "remaining_pids": sorted(set(self.cleanup["remaining_pids"] + failed["remaining_pids"])),
                    "exit_code": self.cleanup["exit_code"],
                    "errors": sorted(set(self.cleanup["errors"] + failed["errors"])),
                }
            return self.cleanup["success"]
