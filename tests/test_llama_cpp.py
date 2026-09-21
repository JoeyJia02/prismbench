import json
import sys
import time
from pathlib import Path

import pytest

from prismbench.backends import llama_cpp
from prismbench.backends.base import BackendError
from prismbench.backends.process import OwnedProcess
from prismbench.config import Case, Config


@pytest.fixture
def backend_factory(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / "fixtures" / "fake_llama_server.py"

    def start_fixture(argv, **kwargs):
        return OwnedProcess([sys.executable, str(fixture), *argv[1:]], **kwargs)

    monkeypatch.setattr(llama_cpp, "OwnedProcess", start_fixture)
    monkeypatch.setattr(llama_cpp.LlamaCppBackend, "_runtime_info", lambda self, option:
                        "fixture-v1 --fit --cache-ram --no-context-shift --slots "
                        "--slot-save-path --flash-attn --no-warmup --api-key")
    active = []

    def factory(mode="ok"):
        monkeypatch.setenv("PRISMBENCH_TEST_MODE", mode)
        config = Config(backend="llama_cpp", server=sys.executable, model="fixture.gguf",
                        load_timeout_seconds=5, request_timeout_seconds=2)
        backend = llama_cpp.LlamaCppBackend(config, Case(gpu_layers=5), tmp_path / mode)
        active.append(backend)
        return backend

    yield factory
    for backend in active:
        backend.close()


@pytest.mark.parametrize("reverse_evidence_order", [False, True], ids=["forward", "reverse"])
def test_real_subprocess_http_protocol_and_evidence(
        backend_factory, monkeypatch, reverse_evidence_order):
    backend = backend_factory()
    startup = backend.start()
    assert startup["effective"]["context_size"] == 2048
    assert startup["effective"]["gpu_layers_loaded"] == 5
    assert startup["effective"]["cpu_offload"] is True
    assert backend.tokenize("a b c") == [0, 1, 2, 3]
    backend.erase()
    result = backend.complete([0, 1, 2], 4, 42, 2)
    assert result["content"] == "Hello world"
    assert 0 < result["ttft_s"] < result["total_latency_s"]
    assert result["timings"]["prompt_n"] == 3
    assert result["timings"]["predicted_per_second"] == 40
    assert backend.probe("17+25=", 64, 42, 2) == "42"
    original_glob = Path.glob

    def enumerated_glob(path, pattern):
        return iter(sorted(original_glob(path, pattern), reverse=reverse_evidence_order))

    # Directory enumeration is unspecified and differed between Windows and Linux CI.
    monkeypatch.setattr(Path, "glob", enumerated_glob)
    assert list(backend.out.glob("*-response.sse"))
    completion_paths = sorted(backend.out.glob("*-completion-request.json"),
                              key=lambda path: int(path.name.split("-", 1)[0]))
    performance_path, probe_path = completion_paths
    performance, probe = [json.loads(path.read_text(encoding="utf-8"))
                          for path in (performance_path, probe_path)]
    assert performance["route"] == probe["route"] == "/completion"
    assert performance["body"]["prompt"] == [0, 1, 2]
    assert performance["body"]["n_predict"] == 4
    assert performance["body"]["ignore_eos"] is True
    assert probe["body"]["n_predict"] == 64
    assert probe["body"]["ignore_eos"] is False
    assert probe["body"]["stop"] == ["\n"]
    assert isinstance(probe["body"]["prompt"], list)
    assert result["ttft_definition"] == "first_nonempty_generated_text_chunk"
    arrival_path = performance_path.with_name(
        performance_path.name.replace("-request.json", "-events-arrival.jsonl"))
    arrivals = [json.loads(line) for line in arrival_path.read_text().splitlines()]
    assert [row["event_index"] for row in arrivals] == [0, 1, 2, 3]
    assert [row["elapsed_s"] for row in arrivals] == sorted(row["elapsed_s"] for row in arrivals)
    assert result["ttft_s"] == arrivals[1]["elapsed_s"]
    assert arrivals[-1]["elapsed_s"] <= result["total_latency_s"]
    assert backend.close()
    assert backend.cleanup["remaining_pids"] == []


@pytest.mark.parametrize("mode,status", [("oom_start", "OOM"), ("failed_start", "ERROR"),
                                        ("wrong_context", "INVALID_WORKLOAD")])
def test_start_failures_are_attributed(backend_factory, mode, status):
    backend = backend_factory(mode)
    with pytest.raises(BackendError) as error:
        backend.start()
    assert error.value.status == status
    assert backend.close()


@pytest.mark.parametrize("mode,status", [("oom_request", "OOM"), ("http500", "ERROR"),
                                        ("missing_terminal", "ERROR")])
def test_request_failures_retain_raw_evidence(backend_factory, mode, status):
    backend = backend_factory(mode)
    backend.start()
    with pytest.raises(BackendError) as error:
        backend.complete([1, 2, 3], 4, 42, 2)
    assert error.value.status == status
    assert list(backend.out.glob("*-response.sse"))
    if mode == "missing_terminal":
        arrival_path, = backend.out.glob("*-events-arrival.jsonl")
        arrivals = arrival_path.read_text(encoding="utf-8").splitlines()
        assert len(arrivals) == 3
    assert backend.close()


def test_slow_drip_stream_has_hard_wall_deadline(backend_factory):
    backend = backend_factory("slow_drip")
    backend.start()
    started = time.monotonic()
    with pytest.raises(BackendError) as error:
        backend.complete([1, 2], 4, 42, .25)
    assert error.value.status == "TIMEOUT"
    assert time.monotonic() - started < 2
    assert backend.close()


def test_terminal_aggregate_text_is_not_a_first_text_observation(backend_factory):
    backend = backend_factory("terminal_text_only")
    backend.start()
    result = backend.complete([1, 2], 4, 42, 2)
    assert result["ttft_s"] is None


@pytest.mark.parametrize("mode", ["probe_cached", "probe_truncated"])
def test_quality_probe_invalid_workload_is_rejected(backend_factory, mode):
    backend = backend_factory(mode)
    backend.start()
    with pytest.raises(BackendError) as error:
        backend.probe("test prompt", 64, 42, 2)
    assert error.value.status == "INVALID_WORKLOAD"


def test_one_line_probe_leading_newline_is_empty_and_fails_exact_match(backend_factory):
    from prismbench.quality import run_quality

    backend = backend_factory("probe_leading_newline")
    backend.start()
    suite = {"id": "empty-answer", "version": "2",
             "probes": [{"id": "addition", "prompt": "17 + 25 =", "expected": "42"}]}
    result = run_quality(backend, suite, 42, 2)
    assert result["items"][0]["actual"] == ""
    assert result["items"][0]["passed"] is False
    assert result["passed"] == 0


@pytest.mark.parametrize("message", ["HTTP 500", "server exited 137", "context exhausted",
                                     "no more memory slots", "unsupported tensor format"])
def test_ambiguous_failures_are_not_oom(message):
    assert not llama_cpp.is_oom(message)


@pytest.mark.parametrize("message", ["CUDA out of memory", "cudaMalloc failed",
                                     "std::bad_alloc", "failed to allocate GPU buffer"])
def test_positive_allocation_errors_are_oom(message):
    assert llama_cpp.is_oom(message)


def test_changed_or_unknown_layer_counts():
    with pytest.raises(BackendError) as error:
        llama_cpp.parse_effective("offloaded 5/7 layers to GPU", [{"n_ctx": 2048}], 2048, 7)
    assert error.value.status == "INVALID_WORKLOAD"
    effective = llama_cpp.parse_effective("", [{"n_ctx": 2048}], 2048, 7)
    assert effective["gpu_layers_loaded"] is None
    assert effective["cpu_offload"] is None
    assert effective["verification_warnings"]


def test_failed_runtime_preflight_cleanup_stays_failed(tmp_path, monkeypatch):
    failed = {"success": False, "remaining_pids": [987654321], "exit_code": 0,
              "errors": ["fixture: owned child did not exit"]}

    class FinishedProcess:
        def __init__(self, *_args, **_kwargs):
            pass

        def poll(self):
            return 0

        def close(self):
            return failed

    monkeypatch.setattr(llama_cpp, "OwnedProcess", FinishedProcess)
    backend = llama_cpp.LlamaCppBackend(Config(server=sys.executable), Case(), tmp_path)
    monkeypatch.setattr(backend, "_environment", lambda: {})
    with pytest.raises(BackendError, match="Failed to clean up runtime"):
        backend._runtime_info("--version")
    assert backend.close() is False
    assert backend.cleanup["remaining_pids"] == [987654321]
    # A later successful cleanup must not erase an unresolved earlier failure.
    backend._process = FinishedProcess()
    backend._process.close = lambda: {"success": True, "remaining_pids": [], "exit_code": 0, "errors": []}
    assert backend.close() is False
    assert backend.cleanup["errors"] == failed["errors"]
