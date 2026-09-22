"""Hardware-free evidence and lifecycle checks for the external PPL recipe."""

import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from prismbench.io import hash_file

SPEC = importlib.util.spec_from_file_location(
    "quantization_study", Path(__file__).parents[1] / "experiments" / "quantization_study.py")
study = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(study)

EFFECTIVE = """load_tensors: offloaded 29/29 layers to GPU
llama_context: n_ctx = 2048
llama_context: flash_attn = enabled
llama_kv_cache: K (f16): 100 MiB, V (f16): 100 MiB
"""
VERSION = "version: 0.4.1-dev (build 10964, commit b29c606e2)"


@pytest.fixture
def manifest(tmp_path):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    for name in ("llama-perplexity.exe", "llama-tokenize.exe", "ggml.dll"):
        (runtime / name).write_text(name, encoding="utf-8")
    corpus = tmp_path / "corpus.txt"
    corpus.write_text("A generated test corpus", encoding="utf-8")
    models = []
    for label in study.LABELS:
        p = tmp_path / f"{label}.gguf"
        p.write_text(label, encoding="utf-8")
        models.append({"label": label, "path": str(p), "sha256": hash_file(p),
                       "parent_sha256": "a" * 64, "tokenizer_sha256": "b" * 64})
    for model in models[1:]:
        model["parent_sha256"] = models[0]["sha256"]
    return {"schema_version": "1", "model_id": "Qwen/Qwen3-1.7B", "runtime_dir": str(runtime),
            "expected_runtime": {p.name: hash_file(p) for p in runtime.iterdir()},
            "corpus": {"path": str(corpus), "sha256": hash_file(corpus),
                       "source": {"license": "generated fixture"}}, "models": models,
            "preparation": {"fixture": True}}


def baseline():
    return {"gpu_uuid": "GPU-fixture", "system_ram_available_mib": 16384,
            "vram_total_mib": 12288, "vram_used_mib": 1024}


def test_manifest_and_hash_receipts_cover_every_asset(manifest):
    receipts = study.verify_assets(manifest)
    assert receipts["runtime"] == manifest["expected_runtime"]
    assert set(receipts["models"]) == set(study.LABELS)
    assert receipts["corpus"]["sha256"] == manifest["corpus"]["sha256"]


@pytest.mark.parametrize("change", ["schema", "model_id", "relative", "traversal", "missing_tool",
                                    "unlisted_dll", "duplicate_label", "parent", "tokenizer", "same_weights"])
def test_bad_manifest_rejected(manifest, change):
    m = deepcopy(manifest)
    if change == "schema":
        m["schema_version"] = 1
    elif change == "model_id":
        m["model_id"] = "different/model"
    elif change == "relative":
        m["models"][0]["path"] = "relative.gguf"
    elif change == "traversal":
        m["expected_runtime"]["../outside.dll"] = "a" * 64
    elif change == "missing_tool":
        del m["expected_runtime"]["llama-tokenize.exe"]
    elif change == "unlisted_dll":
        (Path(m["runtime_dir"]) / "unknown.dll").write_bytes(b"fixture")
    elif change == "duplicate_label":
        m["models"][2]["label"] = "Q8_0"
    elif change == "parent":
        m["models"][1]["parent_sha256"] = "c" * 64
    elif change == "tokenizer":
        m["models"][1]["tokenizer_sha256"] = "c" * 64
    elif change == "same_weights":
        m["models"][1]["sha256"] = m["models"][0]["sha256"]
    with pytest.raises(ValueError):
        study.validate_manifest(m)


@pytest.mark.parametrize("kind", ["model", "runtime", "corpus", "trailing_newline"])
def test_mismatched_assets_or_upstream_trimming_are_rejected(manifest, kind):
    if kind == "model":
        path = Path(manifest["models"][1]["path"])
    elif kind == "runtime":
        path = Path(manifest["runtime_dir"]) / "ggml.dll"
    else:
        path = Path(manifest["corpus"]["path"])
    path.write_bytes(path.read_bytes() + b"\n")
    if kind == "trailing_newline":
        manifest["corpus"]["sha256"] = hash_file(path)
    with pytest.raises(ValueError):
        study.verify_assets(manifest)


@pytest.mark.parametrize("field,value", [("system_ram_available_mib", 10239),
                                        ("vram_used_mib", 5121), ("vram_total_mib", None),
                                        ("gpu_uuid", None), ("vram_used_mib", float("nan"))])
def test_memory_admission_fails_closed(field, value):
    row = baseline()
    study.admission(row)
    row[field] = value
    with pytest.raises(ValueError):
        study.admission(row)


def test_environment_removes_overrides_without_recording_values(monkeypatch):
    monkeypatch.setenv("LLAMA_ARG_CTX_SIZE", "different")
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "wrong")
    monkeypatch.setenv("GGML_CUDA_ENABLE_UNIFIED_MEMORY", "1")
    env, receipt = study.environment("GPU-test")
    assert "LLAMA_ARG_CTX_SIZE" not in env and "GGML_CUDA_ENABLE_UNIFIED_MEMORY" not in env
    assert env["CUDA_VISIBLE_DEVICES"] == "GPU-test"
    assert "different" not in str(receipt) and "wrong" not in str(receipt)


@pytest.mark.parametrize("text", ["build 123 commit b29c606e2", "build 10964 commit aaaaaaa", ""])
def test_unpinned_version_rejected(text):
    assert study.parse_version(VERSION) == VERSION
    with pytest.raises(ValueError):
        study.parse_version(text)


@pytest.mark.parametrize("change", ["context", "layers", "unknown_cache", "bad_cache", "flash", "fit"])
def test_effective_configuration_requires_positive_evidence(change, manifest):
    argv = study.perplexity_argv(Path(manifest["runtime_dir"]), manifest["models"][0], manifest["corpus"]["path"])
    assert study.parse_effective(EFFECTIVE, argv)["gpu_layers_loaded"] == 29
    replacements = {"context": ("2048", "1024"), "layers": ("29/29", "20/29"),
                    "unknown_cache": ("K (f16)", "unknown"), "bad_cache": ("V (f16)", "V (q8_0)"),
                    "flash": ("enabled", "disabled"), "fit": ("offloaded", "auto-fit offloaded")}
    with pytest.raises(ValueError):
        study.parse_effective(EFFECTIVE.replace(*replacements[change]), argv)


@pytest.mark.parametrize("text", ["not JSON", "{}", "[true]", "[-1]", "[1, 2]", "[1.2]"])
def test_malformed_or_short_token_arrays_rejected(text):
    with pytest.raises(ValueError):
        study.parse_tokens(text)


def test_token_fingerprint_covers_full_array_and_exact_32chunk_prefix():
    tokens = list(range(65540))
    parsed = study.parse_tokens(json.dumps(tokens))
    receipt = study.token_fingerprint(parsed)
    assert receipt["total_tokens"] == 65540 and receipt["prefix_tokens"] == 65536
    tokens[-1] += 1
    changed = study.token_fingerprint(tokens)
    assert receipt["total_token_sha256"] != changed["total_token_sha256"]
    assert receipt["prefix_token_sha256"] == changed["prefix_token_sha256"]


@pytest.mark.parametrize("mode,expected", [("success", "SUCCESS"), ("nonzero", "ERROR"),
                                         ("timeout", "TIMEOUT"), ("ram", "RAM_GUARD"),
                                         ("cleanup", "CLEANUP_FAILED"), ("launch", "ERROR")])
def test_owned_process_failures_leave_evidence_and_cleanup(monkeypatch, tmp_path, mode, expected):
    children = []

    class FakeProcess:
        def __init__(self, argv, **kwargs):
            if mode == "launch":
                raise OSError("fixture launch failure")
            self.closed = False
            children.append(self)
            kwargs["stdout"].write(b"raw fixture output")

        def poll(self):
            return None if mode in ("timeout", "ram") else (7 if mode == "nonzero" else 0)

        def close(self):
            self.closed = True
            return {"success": mode != "cleanup", "remaining_pids": [123] if mode == "cleanup" else [], "errors": []}

    monkeypatch.setattr(study, "OwnedProcess", FakeProcess)
    monkeypatch.setattr(study.psutil, "virtual_memory", lambda: SimpleNamespace(available=(5 if mode == "ram" else 16) * 1024**3))
    out = tmp_path / "run"
    row = study.run_command(["fixture"], out, tmp_path, {}, 0 if mode == "timeout" else 30)
    assert row["status"] == expected
    assert (out / "command.json").exists() and (out / "stdout.log").exists()
    assert all(c.closed for c in children)
    assert json.loads((out / "command.json").read_text())["status"] == expected


@pytest.fixture
def mocked_study(monkeypatch, manifest, tmp_path):
    metrics_module = SimpleNamespace(
        parse_perplexity=lambda text, **kwargs: {"perplexity": 10, "mean_nll": 2.3},
        compare_perplexity=lambda ref, cand: {"delta_mean_nll": 0, "perplexity_ratio": 1})
    monkeypatch.setitem(sys.modules, "experiments.perplexity_metrics", metrics_module)
    monkeypatch.setattr(study, "detect", lambda index: {"snapshot": baseline()})
    monkeypatch.setattr(study, "sample", lambda index: baseline())
    monkeypatch.setattr(study.psutil, "process_iter", lambda fields: [])
    calls = []

    def command(argv, directory, runtime, env, timeout, **kwargs):
        calls.append(argv)
        directory.mkdir(parents=True)
        if "--version" in argv:
            stdout = VERSION
        elif "--ids" in argv:
            stdout = json.dumps([1] * 65536)
        else:
            stdout = EFFECTIVE
        (directory / "stdout.log").write_text(stdout, encoding="utf-8")
        (directory / "stderr.log").write_text("", encoding="utf-8")
        return {"status": "SUCCESS", "cleanup": {"success": True}, "resources": {"peak_vram_mib": 2000}, "wall_s": 1}

    monkeypatch.setattr(study, "run_command", command)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, tmp_path / "output", calls, command


def test_complete_recipe_runs_exact_three_models_then_reference_repeat(mocked_study):
    path, out, calls, _ = mocked_study
    result = study.execute(path, out)
    assert result["status"] == "SUCCESS", result["error"]
    assert [(r["label"], r["repeat"]) for r in result["runs"]] == [("F16", 1), ("Q8_0", 1), ("Q4_K_M", 1), ("F16", 2)]
    assert len(calls) == 8
    assert all("--no-parse-special" in c for c in calls if "--ids" in c)
    assert len(result["comparisons"]) == 2 and result["reference_repeat"]
    assert all((out / name).exists() for name in ("results.json", "results.csv", "report.md"))


def test_no_overwrite_preserves_existing_results(mocked_study):
    path, out, calls, _ = mocked_study
    out.mkdir()
    (out / "sentinel").write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        study.execute(path, out)
    assert not calls and (out / "sentinel").read_bytes() == b"keep"


def test_hash_failure_prevents_every_process_and_writes_failure_receipt(mocked_study, manifest):
    path, out, calls, _ = mocked_study
    Path(manifest["models"][0]["path"]).write_bytes(b"changed")
    result = study.execute(path, out)
    assert result["status"] == "ERROR" and "hash mismatch" in result["error"]
    assert not calls and (out / "results.json").exists()


def test_malformed_manifest_is_a_recorded_failure_before_launch(mocked_study):
    path, out, calls, _ = mocked_study
    path.write_text("{broken", encoding="utf-8")
    result = study.execute(path, out)
    assert result["status"] == "ERROR" and not calls
    assert (out / "report.md").exists()


def test_existing_model_process_is_left_untouched(monkeypatch, mocked_study):
    path, out, calls, _ = mocked_study
    monkeypatch.setattr(study.psutil, "process_iter", lambda fields: [SimpleNamespace(pid=999, info={"name": "llama-server.exe"})])
    result = study.execute(path, out)
    assert result["status"] == "ERROR" and not calls and "untouched" in result["error"]


def test_failed_run_admission_still_has_a_valid_evidence_directory(monkeypatch, mocked_study):
    path, out, calls, _ = mocked_study
    monkeypatch.setattr(study, "sample", lambda index: {**baseline(), "system_ram_available_mib": 1})
    result = study.execute(path, out)
    assert result["status"] == "ERROR" and len(calls) == 4
    assert len(result["runs"]) == 1
    row = result["runs"][0]
    assert (out / row["evidence_dir"] / "attempt.json").exists()


@pytest.mark.parametrize("failure", ["tokens", "malformed", "version", "effective", "TIMEOUT", "CLEANUP_FAILED", "ERROR"])
def test_recipe_stops_queue_and_preserves_failure(monkeypatch, mocked_study, failure):
    path, out, calls, original = mocked_study

    def command(argv, directory, runtime, env, timeout, **kwargs):
        row = original(argv, directory, runtime, env, timeout, **kwargs)
        if failure == "version" and "--version" in argv:
            (directory / "stdout.log").write_text("wrong version")
        if directory.name == "Q8_0" and failure in ("tokens", "malformed"):
            (directory / "stdout.log").write_text(json.dumps([2] * 65536) if failure == "tokens" else "[broken")
        if directory.name == "F16-r1":
            if failure == "effective":
                (directory / "stdout.log").write_text(EFFECTIVE.replace("29/29", "0/29"))
            elif failure in ("TIMEOUT", "CLEANUP_FAILED", "ERROR"):
                row["status"] = failure
        return row

    monkeypatch.setattr(study, "run_command", command)
    result = study.execute(path, out)
    assert result["status"] == "ERROR"
    assert len(result["runs"]) <= 1 and not result["comparisons"]
    assert len(calls) <= 5 and (out / "results.json").exists()
    if failure in ("tokens", "malformed"):
        assert result["tokenization"][-1]["status"] == "INVALID_WORKLOAD"
    if failure in ("TIMEOUT", "CLEANUP_FAILED", "ERROR"):
        assert result["runs"][-1]["status"] == failure
