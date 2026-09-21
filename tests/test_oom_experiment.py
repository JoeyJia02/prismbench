"""Hardware-free checks for the opt-in experiment's admission and evidence rules."""

import importlib.util
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from prismbench.config import Case, Config

SPEC = importlib.util.spec_from_file_location(
    "oom_experiment", Path(__file__).parents[1] / "experiments" / "windows_oom_recovery.py")
experiment = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(experiment)


def protocol_config():
    return Config(backend="llama_cpp", expected_model_sha256=experiment.MODEL_SHA,
                  repetitions=1, quality=False, load_timeout_seconds=30,
                  request_timeout_seconds=15,
                  cases=[Case(context_size=524288, prompt_tokens=128, output_tokens=16,
                              batch_size=128, ubatch_size=64,
                              fallbacks=[{"context_size": 2048}])])


@pytest.mark.parametrize("change", [{"quality": True}, {"repetitions": 2},
                                    {"request_timeout_seconds": 120}, {"gpu_index": 1},
                                    {"expected_model_sha256": "0" * 64}])
def test_experiment_refuses_expanded_or_unpinned_configuration(change):
    experiment.validate_config(protocol_config())
    with pytest.raises(ValueError):
        experiment.validate_config(replace(protocol_config(), **change))


@pytest.mark.parametrize("change", [{"context_size": 1048576}, {"prompt_tokens": 2048},
                                    {"gpu_layers": 0}, {"cache_type_k": "q8_0"},
                                    {"fallbacks": [{"context_size": 2048, "gpu_layers": 0}]},
                                    {"fallbacks": []}])
def test_experiment_refuses_different_allocation_or_fallback_protocol(change):
    config = protocol_config()
    with pytest.raises(ValueError):
        experiment.validate_config(replace(config, cases=[replace(config.cases[0], **change)]))


def test_watchdog_protects_host_before_wall_deadline_and_does_not_abort_normal_run():
    gib = experiment.GIB
    assert experiment.guard_reason(12 * gib, 2 * gib, 1) is None
    assert "RAM" in experiment.guard_reason(8 * gib - 1, gib, 1)
    assert "RSS" in experiment.guard_reason(12 * gib, 8 * gib + 1, 1)
    assert "deadline" in experiment.guard_reason(12 * gib, gib, 120)


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), -1, "unknown"])
def test_watchdog_fails_closed_when_input_is_unavailable(bad):
    assert "invalid" in experiment.guard_reason(bad, 0, 0)
    assert "invalid" in experiment.guard_reason(12 * experiment.GIB, bad, 0)
    assert "invalid" in experiment.guard_reason(12 * experiment.GIB, 0, bad)


def memory_samples(count=5, vram=900):
    return [{"gpu_uuid": "GPU-fixture", "vram_used_mib": vram,
             "system_ram_available_mib": 16 * 1024} for _ in range(count)]


def test_admission_requires_all_baseline_samples_and_adequate_host_memory():
    baseline = memory_samples()
    assert experiment.admission(baseline)
    assert not experiment.admission(baseline[:-1])
    baseline[2]["system_ram_available_mib"] = 12 * 1024 - 1
    assert not experiment.admission(baseline)


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), -1, "900"])
def test_missing_or_invalid_gpu_memory_cannot_prove_admission_or_settling(bad):
    baseline, after = memory_samples(), memory_samples(15)
    after[-1]["vram_used_mib"] = bad
    assert not experiment.settled(baseline, after)
    baseline[-1]["vram_used_mib"] = bad
    assert not experiment.admission(baseline)


def test_settling_requires_last_three_samples_not_a_single_low_sample():
    baseline, after = memory_samples(), memory_samples(15)
    after[0]["vram_used_mib"] = 8000
    assert experiment.settled(baseline, after)  # Early post-chain release may be delayed.
    after[-2]["vram_used_mib"] = 900 + 257
    assert not experiment.settled(baseline, after)
    after[-2]["vram_used_mib"] = 900
    after[-1]["gpu_uuid"] = "GPU-another-device"
    assert not experiment.settled(baseline, after)
    assert not experiment.settled(baseline, after[:3])


@pytest.mark.parametrize("diagnostic", ["std::bad_alloc", "failed to allocate host memory",
    "HTTP 500", "CUDA out of memory", "cudaMalloc failed\nunrelated out of memory",
    "cudaMalloc failed: invalid argument", "out of memory"])
def test_generic_or_host_errors_cannot_be_called_cuda_vram_allocation_failure(diagnostic):
    assert not experiment.cuda_allocation_failure(diagnostic)


def complete_chain():
    return {"synthetic": False, "attempts": [
        {"attempt_id": "memory-r1-a0", "attempt_index": 0, "parent_attempt_id": None,
         "status": "OOM", "cleanup_confirmed": True, "requested": {"context_size": 524288}},
        {"attempt_id": "memory-r1-a1", "attempt_index": 1, "parent_attempt_id": "memory-r1-a0",
         "status": "SUCCESS", "cleanup_confirmed": True, "requested": {"context_size": 2048},
         "runtime": {"effective": {"context_size": 2048}},
         "metrics": {"prompt_tokens": 128, "generated_tokens": 16, "cache_tokens": 0}}]}


def test_successful_fallback_alone_does_not_prove_cuda_oom_recovery():
    chain = complete_chain()
    diagnostic = "ggml_backend_cuda_buffer_type_alloc_buffer: cudaMalloc failed: out of memory"
    assert experiment.check_chain(chain, diagnostic)
    assert not experiment.check_chain(chain, "std::bad_alloc")
    chain["synthetic"] = True
    assert not experiment.check_chain(chain, diagnostic)


@pytest.mark.parametrize("row,key,value", [
    (0, "cleanup_confirmed", False), (0, "status", "TIMEOUT"),
    (1, "parent_attempt_id", "another-attempt"), (1, "status", "ERROR"),
    (1, "metrics", {"prompt_tokens": 128, "generated_tokens": 15, "cache_tokens": 0}),
    (1, "metrics", {"prompt_tokens": 128, "generated_tokens": 16, "cache_tokens": 1}),
    (1, "runtime", {"effective": {"context_size": 4096}}),
])
def test_broken_cleanup_lineage_or_workload_prevents_pass(row, key, value):
    chain = deepcopy(complete_chain())
    chain["attempts"][row][key] = value
    assert not experiment.check_chain(chain, "cudaMalloc failed: out of memory")


def test_private_job_override_is_restored_even_when_startup_fails(monkeypatch):
    original = experiment.owned._WindowsJob

    def launch(*args, **kwargs):
        assert experiment.owned._WindowsJob is experiment.CappedJob
        raise OSError("fixture failure before process creation")

    monkeypatch.setattr(experiment.owned, "OwnedProcess", launch)
    with pytest.raises(OSError):
        experiment.start_capped(["fixture"])
    assert experiment.owned._WindowsJob is original


@pytest.mark.skipif(os.name != "nt", reason="Native Windows Job safety check; no GPU involved")
def test_native_capped_job_contains_only_its_child_and_cleanup_preserves_sentinel():
    child = sentinel = None
    command = [sys.executable, "-I", "-c", "import time; time.sleep(30)"]
    try:
        sentinel = experiment.owned.OwnedProcess(command, stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL)
        child = experiment.start_capped(command, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)
        limits = child._job.confirmed_limits
        assert limits["job_memory_limit_bytes"] == 8 * experiment.GIB
        assert limits["limit_flags"] & 0x2200 == 0x2200
        assert child.pid in child.pids()
        assert sentinel.pid not in child.pids()
        assert child.close()["success"]
        assert sentinel.poll() is None
    finally:
        if child:
            child.close()
        if sentinel:
            assert sentinel.close()["success"]
