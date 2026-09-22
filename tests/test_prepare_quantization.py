import json
import sys

import pytest

from experiments.prepare_quantization import (
    corpus_bytes,
    execute_quantize,
    inspect_gguf,
    validate_lineage,
)


def test_corpus_preserves_order_blank_rows_unicode_and_no_final_lf():
    assert corpus_bytes(["café\n", "", "last\n\n"]) == "café\n\n\n\n\nlast".encode()
    assert corpus_bytes(["x", "y"]) == b"x\n\ny"


@pytest.mark.parametrize("rows", [[], [None], [1], [""], ["\n"], ["text\r\n"]])
def test_corpus_rejects_ambiguous_or_empty_input(rows):
    with pytest.raises(ValueError):
        corpus_bytes(rows)


def metadata(types):
    return {"tokenizer_sha256": "tokens", "tensor_shape_sha256": "shapes",
            "tensor_count": 3, "architecture": "qwen3", "tensor_types": types}


@pytest.mark.parametrize("label,types", [("F16", {"F16": 2, "F32": 1}),
                                        ("Q8_0", {"Q8_0": 2, "F32": 1}),
                                        ("Q4_K_M", {"Q4_K": 1, "Q6_K": 1, "F32": 1})])
def test_lineage_allows_intended_mixed_precision(label, types):
    validate_lineage(metadata({"BF16": 2, "F32": 1}), metadata(types), label)


@pytest.mark.parametrize("field", ["tokenizer_sha256", "tensor_shape_sha256", "tensor_count", "architecture"])
def test_lineage_rejects_changed_model_or_tokenizer(field):
    parent = metadata({"BF16": 2})
    child = metadata({"F16": 2})
    child[field] = "changed"
    with pytest.raises(ValueError, match=field):
        validate_lineage(parent, child, "F16")


@pytest.mark.parametrize("label,types", [("F16", {"Q8_0": 2}), ("Q8_0", {"F16": 2}),
                                        ("Q4_K_M", {"Q4_K": 1, "Q2_K": 1}), ("F16", {})])
def test_lineage_rejects_unintended_precision(label, types):
    with pytest.raises(ValueError, match="tensor types"):
        validate_lineage(metadata({"BF16": 2}), metadata(types), label)


@pytest.fixture
def enough_ram(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("experiments.prepare_quantization.psutil.virtual_memory",
                        lambda: SimpleNamespace(available=16 * 1024**3))


def test_conversion_process_retains_command_logs_and_cleanup(tmp_path, enough_ram):
    output = tmp_path / "conversion"
    argv = [sys.executable, "-c", "print('conversion fixture')"]
    execute_quantize(argv, output)
    receipt = json.loads((output / "execution.json").read_text())
    assert receipt["status"] == "SUCCESS"
    assert receipt["exit_code"] == 0
    assert receipt["cleanup"]["success"]
    assert not receipt["cleanup"]["remaining_pids"]
    assert json.loads((output / "command.json").read_text()) == argv
    assert b"conversion fixture" in (output / "stdout.log").read_bytes()
    with pytest.raises(FileExistsError):
        execute_quantize(argv, output)


def test_failed_conversion_retains_exit_and_cleanup(tmp_path, enough_ram):
    output = tmp_path / "conversion"
    with pytest.raises(RuntimeError, match="exited 7"):
        execute_quantize([sys.executable, "-c", "raise SystemExit(7)"], output)
    receipt = json.loads((output / "execution.json").read_text())
    assert receipt["status"] == "ERROR"
    assert receipt["exit_code"] == 7
    assert receipt["cleanup"]["success"]


def test_conversion_timeout_kills_owned_child_and_keeps_receipt(tmp_path, enough_ram):
    output = tmp_path / "conversion"
    with pytest.raises(TimeoutError):
        execute_quantize([sys.executable, "-c", "import time; time.sleep(60)"], output, timeout=0.2)
    receipt = json.loads((output / "execution.json").read_text())
    assert receipt["status"] == "ERROR"
    assert receipt["cleanup"]["success"]
    assert not receipt["cleanup"]["remaining_pids"]


def test_memory_guard_retains_failure_and_cleans_up(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr("experiments.prepare_quantization.psutil.virtual_memory",
                        lambda: SimpleNamespace(available=5 * 1024**3))
    output = tmp_path / "conversion"
    with pytest.raises(RuntimeError, match="6 GiB"):
        execute_quantize([sys.executable, "-c", "import time; time.sleep(60)"], output)
    receipt = json.loads((output / "execution.json").read_text())
    assert receipt["cleanup"]["success"]
    assert "6 GiB" in receipt["error"]


def test_cleanup_exception_preserves_receipt_and_stops_queue(tmp_path, enough_ram, monkeypatch):
    from prismbench.backends.process import OwnedProcess

    original = OwnedProcess.close

    def close_then_raise(self):
        original(self)
        raise OSError("cleanup fixture")

    monkeypatch.setattr(OwnedProcess, "close", close_then_raise)
    output = tmp_path / "conversion"
    with pytest.raises(RuntimeError, match="cleanup failed"):
        execute_quantize([sys.executable, "-c", "pass"], output)
    receipt = json.loads((output / "execution.json").read_text())
    assert receipt["status"] == "CLEANUP_FAILED"
    assert receipt["cleanup"]["success"] is False
    assert receipt["cleanup"]["remaining_pids"] is None
    assert "cleanup fixture" in receipt["cleanup"]["errors"][0]


def test_tensor_identity_ignores_storage_order_but_preserves_shapes(monkeypatch):
    from types import SimpleNamespace

    def field(value):
        return SimpleNamespace(types=[1], contents=lambda: value)

    def tensor(name, shape):
        return SimpleNamespace(name=name, shape=SimpleNamespace(tolist=lambda: shape),
                               tensor_type=SimpleNamespace(name="F16"))

    tensors = [tensor("embedding", [8, 2]), tensor("output", [4, 2])]
    reader = SimpleNamespace(tensors=tensors, fields={
        "tokenizer.ggml.tokens": field(["a", "b"]),
        "general.architecture": field("qwen3"), "general.file_type": field(1)})
    monkeypatch.setitem(sys.modules, "gguf", SimpleNamespace(GGUFReader=lambda path: reader))
    original = inspect_gguf("fixture")
    reader.tensors = list(reversed(tensors))
    assert inspect_gguf("fixture")["tensor_shape_sha256"] == original["tensor_shape_sha256"]
    reader.tensors = [tensor("embedding", [9, 2]), tensor("output", [4, 2])]
    assert inspect_gguf("fixture")["tensor_shape_sha256"] != original["tensor_shape_sha256"]
    reader.tensors = [tensors[0], tensors[0]]
    with pytest.raises(ValueError, match="Duplicate"):
        inspect_gguf("fixture")
