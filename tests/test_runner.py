from dataclasses import replace

import pytest

from prismbench.backends.base import BackendError
from prismbench.backends.synthetic import SyntheticBackend
from prismbench.config import Case, Config
from prismbench.runner import measured_metrics, run


def test_demo_fallback_retains_failed_attempt_and_does_not_overwrite(tmp_path):
    config = Config(repetitions=1, quality=False,
                    cases=[Case(name="oom-demo", fallbacks=[{"gpu_layers": 16}])])
    output = tmp_path / "demo"
    result = run(config, output, progress=lambda _: None)
    assert [r["status"] for r in result["attempts"]] == ["OOM", "SUCCESS"]
    assert result["attempts"][1]["parent_attempt_id"] == result["attempts"][0]["attempt_id"]
    assert result["attempts"][0]["requested"]["gpu_layers"] == 99
    assert result["attempts"][1]["requested"]["gpu_layers"] == 16
    assert result["synthetic"] is True
    assert "SYNTHETIC" in (output / "report.md").read_text(encoding="utf-8").upper()
    with pytest.raises(FileExistsError):
        run(config, output)


@pytest.mark.parametrize("status", ["TIMEOUT", "ERROR", "INVALID_WORKLOAD"])
def test_non_oom_does_not_trigger_fallback(tmp_path, status):
    class Broken(SyntheticBackend):
        def start(self):
            raise BackendError(status, "fixture")
    c = Config(repetitions=1, quality=False, cases=[Case(fallbacks=[{"gpu_layers": 0}])])
    result = run(c, tmp_path / "out", factory=Broken, progress=lambda _: None)
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["status"] == status
    assert result["attempts"][0]["cleanup_confirmed"]


def test_cleanup_failure_stops_entire_queue(tmp_path):
    class Unclean(SyntheticBackend):
        def close(self):
            return False
    result = run(Config(quality=False), tmp_path / "out", factory=Unclean, progress=lambda _: None)
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["status"] == "CLEANUP_FAILED"


def test_cancel_keeps_partial_results_and_cleans(tmp_path):
    class Cancel(SyntheticBackend):
        def start(self):
            raise KeyboardInterrupt
    result = run(Config(quality=False), tmp_path / "out", factory=Cancel, progress=lambda _: None)
    assert len(result["attempts"]) == 1
    assert result["attempts"][0]["status"] == "CANCELLED"
    assert (tmp_path / "out" / "results.json").is_file()


@pytest.mark.parametrize("field,value", [("prompt_n", 10), ("predicted_n", 3), ("cache_n", 1),
                                         ("cache_n", None), ("predicted_per_second", float("nan"))])
def test_workload_and_timing_validation(field, value):
    case = Case()
    backend = SyntheticBackend(Config(), case, None)
    response = backend.complete([1] * case.prompt_tokens, case.output_tokens, 42, 1)
    response["timings"][field] = value
    with pytest.raises(BackendError):
        measured_metrics(response, case)


def test_preserves_engine_tps_definition():
    c = replace(Case(), prompt_tokens=10)
    r = {"ttft_s": 0.1, "total_latency_s": 2.0, "truncated": False,
         "timings": {"prompt_n": 10, "predicted_n": 128, "cache_n": 0,
                     "prompt_per_second": 100, "predicted_per_second": 79.698726,
                     "predicted_ms": 1593.501}}
    assert measured_metrics(r, c)["generation_tokens_per_second"] == 79.698726


@pytest.mark.parametrize("load_time", [None, 0, float("nan")])
def test_bad_backend_startup_metrics_keep_failure_evidence(tmp_path, load_time):
    class BadTiming(SyntheticBackend):
        def start(self):
            return {**super().start(), "load_time_s": load_time}
    result = run(Config(quality=False, repetitions=1), tmp_path / "out", factory=BadTiming,
                 progress=lambda _: None)
    assert result["attempts"][0]["status"] == "INVALID_WORKLOAD"
    assert result["attempts"][0]["metrics"]["load_time_s"] is None
    assert (tmp_path / "out" / "results.json").is_file()


def test_telemetry_finalization_failure_preserves_completed_attempt(tmp_path, monkeypatch):
    """No real hardware/process runs: exercise only the resource finalization branch."""
    import json

    import prismbench.runner as runner

    class BrokenCollector:
        def __init__(self, *args):
            pass

        def start(self):
            pass

        def take(self, phase=None):
            return {"vram_used_mib": 100}

        def close(self):
            raise RuntimeError("fixture telemetry shutdown failure")

    model, server = tmp_path / "fixture.gguf", tmp_path / "fixture.exe"
    model.write_bytes(b"fixture only")
    server.write_bytes(b"fixture only")
    monkeypatch.setattr(runner, "detect", lambda _: {})
    monkeypatch.setattr(runner, "sample", lambda _: {"vram_used_mib": 100})
    monkeypatch.setattr(runner, "Collector", BrokenCollector)
    config = Config(backend="llama_cpp", model=str(model), server=str(server),
                    repetitions=1, quality=False)
    out = tmp_path / "out"
    result = run(config, out, factory=SyntheticBackend, progress=lambda _: None)
    row = result["attempts"][0]
    assert row["status"] == "SUCCESS"
    assert row["cleanup_confirmed"] is True
    assert any("Telemetry finalization failed" in warning for warning in row["warnings"])
    assert row["metrics"]["peak_vram_mib"] is None
    assert json.loads((out / "attempts/default-r1-a0/attempt.json").read_text())["status"] == "SUCCESS"
    assert json.loads((out / "results.json").read_text())["attempts"][0] == row
