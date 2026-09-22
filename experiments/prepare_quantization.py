"""Prepare one pinned, local BF16 -> F16 -> Q8/Q4 experiment; no downloads."""

import argparse
import importlib.metadata
import os
import time
from collections import Counter
from pathlib import Path

import psutil

from prismbench.backends.process import OwnedProcess
from prismbench.io import digest, hash_file, save_json

PARENT_SHA = "199b4df12194e24ac097d4fcbd279ce62bd4959bed9f0d4719d05a6ab1501861"
PARQUET_SHA = "5f1bea067869d04849c0f975a2b29c4ff47d867f484f5010ea5e861eab246d91"
MODEL_REVISION = "dcb19155b962dbb6389f4691a982043a8e651022"
CORPUS_REVISION = "b08601e04326c79dfdd32d625aee71d232d685c3"
TOOLS = {
    "llama-perplexity.exe": "cc9b6422ac9bb7aaba390ecf19fc3d6d73e38072cfc87cae5e0ed6d7087f3c39",
    "llama-quantize.exe": "ff306a447997d2c1deed5b02d1347580ea41dc8c3803fa33b93686ef91700653",
    "llama-tokenize.exe": "49ac76768cc968b55096c3a2e97e7d5a5f1078c76f8ab06e1f79461eb9543fbb",
    "llama-server.exe": "aa2e1f5c67be55f11be26ae58d643a545ca07c6de498f6f870330ac2f4dfec73",
}


def corpus_bytes(rows):
    """Keep dataset order and blank rows; remove terminal LF characters only."""
    if not rows or not all(isinstance(row, str) for row in rows):
        raise ValueError("Corpus must be a nonempty sequence of text rows")
    value = "\n\n".join(rows).rstrip("\n").encode("utf-8")
    if not value or value.endswith((b"\n", b"\r")):
        raise ValueError("Corpus must end in text, not a line terminator")
    return value


def inspect_gguf(path):
    # Optional, preparation-only dependencies; never installed by PrismBench.
    from gguf import GGUFReader

    reader = GGUFReader(path)
    tokenizer = {name: {"types": [int(t) for t in field.types], "value": field.contents()}
                 for name, field in sorted(reader.fields.items()) if name.startswith("tokenizer.")}
    if not tokenizer or "tokenizer.ggml.tokens" not in tokenizer:
        raise ValueError("Missing tokenizer metadata")
    if tokenizer.get("tokenizer.ggml.add_eos_token", {}).get("value", False):
        raise ValueError("Pinned non-strided PPL protocol requires add_eos=false")
    # Quantization may reorder tensor storage. Match identities, not physical order.
    shape = {tensor.name: tensor.shape.tolist() for tensor in reader.tensors}
    if len(shape) != len(reader.tensors):
        raise ValueError("Duplicate GGUF tensor names")
    architecture = reader.fields["general.architecture"].contents()
    return {"tokenizer_sha256": digest(tokenizer), "tensor_shape_sha256": digest(shape),
            "tensor_count": len(shape), "tensor_types": dict(Counter(t.tensor_type.name for t in reader.tensors)),
            "architecture": architecture,
            "general_file_type": reader.fields["general.file_type"].contents(),
            "add_bos_token": tokenizer.get("tokenizer.ggml.add_bos_token", {}).get("value"),
            "add_eos_token": tokenizer.get("tokenizer.ggml.add_eos_token", {}).get("value"),
            "tokenizer_fingerprint_rule": "canonical JSON of every tokenizer.* typed metadata value"}


def validate_lineage(parent, child, label):
    for field in ("tokenizer_sha256", "tensor_shape_sha256", "tensor_count", "architecture"):
        if parent[field] != child[field]:
            raise ValueError(f"{label}: changed {field}")
    types = set(child["tensor_types"])
    expected = {"F16": {"F16", "F32"}, "Q8_0": {"Q8_0", "F32"},
                "Q4_K_M": {"Q4_K", "Q6_K", "F32"}}[label]
    if not types <= expected or label.split("_M")[0] not in types:
        raise ValueError(f"{label}: unexpected tensor types {sorted(types)}")


def execute_quantize(argv, directory, timeout=600):
    directory.mkdir(parents=True, exist_ok=False)
    save_json(directory / "command.json", argv)
    environment = {k: v for k, v in os.environ.items() if not k.startswith("LLAMA_ARG_")}
    started = time.monotonic()
    process = None
    receipt = {"status": "ERROR", "exit_code": None, "cleanup": None}
    try:
        with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
            process = OwnedProcess(argv, cwd=str(Path(argv[0]).parent), env=environment,
                                   stdout=stdout, stderr=stderr)
            while process.poll() is None:
                if time.monotonic() - started > timeout:
                    raise TimeoutError("Quantization deadline exceeded")
                if psutil.virtual_memory().available < 6 * 1024**3:
                    raise RuntimeError("Available host RAM fell below 6 GiB")
                time.sleep(0.1)
            receipt["exit_code"] = process.poll()
            if receipt["exit_code"] != 0:
                raise RuntimeError(f"Quantizer exited {receipt['exit_code']}")
            receipt["status"] = "SUCCESS"
    except BaseException as exc:
        receipt["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        if process is not None:
            try:
                receipt["cleanup"] = process.close()
            except Exception as exc:
                receipt["cleanup"] = {"success": False, "remaining_pids": None,
                                      "errors": [f"{type(exc).__name__}: {exc}"]}
        receipt["wall_time_s"] = time.monotonic() - started
        if receipt["cleanup"] and not receipt["cleanup"]["success"]:
            receipt["status"] = "CLEANUP_FAILED"
        save_json(directory / "execution.json", receipt)
    if receipt["status"] != "SUCCESS":
        raise RuntimeError("Quantizer cleanup failed")


def prepare(parent, parquet, runtime, output):
    parent, parquet, runtime, output = [Path(p).resolve() for p in (parent, parquet, runtime, output)]
    if output.exists():
        raise ValueError("Refusing to reuse preparation output")
    if hash_file(parent) != PARENT_SHA or hash_file(parquet) != PARQUET_SHA:
        raise ValueError("Pinned parent or corpus checksum mismatch")
    for name, expected in TOOLS.items():
        if hash_file(runtime / name) != expected:
            raise ValueError(f"Pinned Windows b10964 tool checksum mismatch: {name}")
    if psutil.virtual_memory().available < 10 * 1024**3:
        raise ValueError("Preparation requires at least 10 GiB available host RAM")
    import pyarrow.parquet as pq

    parent_metadata = inspect_gguf(parent)
    if not set(parent_metadata["tensor_types"]) <= {"BF16", "F32"} or "BF16" not in parent_metadata["tensor_types"]:
        raise ValueError("Parent must contain only BF16/F32 tensors")
    rows = pq.read_table(parquet, columns=["text"])["text"].to_pylist()
    output.mkdir(parents=True, exist_ok=False)
    corpus = output / "wikitext-2-raw-test.txt"
    corpus.write_bytes(corpus_bytes(rows))
    preparation = {
        "parent": {"path": str(parent), "sha256": PARENT_SHA, "size_bytes": parent.stat().st_size,
                   "repo": "bartowski/Qwen_Qwen3-1.7B-GGUF", "revision": MODEL_REVISION,
                   "metadata": parent_metadata},
        "helper_sha256": hash_file(Path(__file__)),
        "dependencies": {name: importlib.metadata.version(name) for name in ("gguf", "numpy", "pyarrow", "prismbench")},
        "quantization": "BF16 -> F16; independently F16 -> Q8_0 and F16 -> Q4_K_M; no imatrix or requantize",
        "limitation": "Community BF16 parent; equality to the official checkpoint is not independently verified.",
    }
    manifest = {"schema_version": "1", "model_id": "Qwen/Qwen3-1.7B", "runtime_dir": str(runtime),
                "expected_runtime": {**TOOLS, **{p.name: hash_file(p) for p in sorted(runtime.glob("*.dll"))}},
                "corpus": {"path": str(corpus), "sha256": hash_file(corpus), "rows": len(rows),
                           "source": {"repo": "Salesforce/wikitext", "revision": CORPUS_REVISION,
                                      "file": "wikitext-2-raw-v1/test-00000-of-00001.parquet", "sha256": PARQUET_SHA,
                                      "extraction": "UTF-8 encode two-LF join of every text row in order; rstrip LF only",
                                      "license": "upstream metadata: CC BY-SA 3.0 + GFDL; prose links CC BY-SA 4.0; corpus is not MIT"}},
                "models": [], "preparation": preparation}
    save_json(output / "preparation.pending.json", manifest)
    f16 = output / "Qwen3-1.7B-F16.gguf"
    for label in ("F16", "Q8_0", "Q4_K_M"):
        source = parent if label == "F16" else f16
        destination = output / f"Qwen3-1.7B-{label}.gguf"
        print(f"Preparing {label}", flush=True)
        execute_quantize([str(runtime / "llama-quantize.exe"), "--max-buffer-size", "256",
                          str(source), str(destination), label, "6"], output / f"convert-{label}")
        metadata = inspect_gguf(destination)
        validate_lineage(parent_metadata, metadata, label)
        model = {"label": label, "path": str(destination), "sha256": hash_file(destination),
                 "parent_sha256": hash_file(source), "size_bytes": destination.stat().st_size, **metadata}
        manifest["models"].append(model)
        save_json(output / "preparation.pending.json", manifest)
    save_json(output / "manifest.json", manifest)
    print(f"Prepared {output / 'manifest.json'}", flush=True)
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("parent", "parquet", "runtime", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        prepare(args.parent, args.parquet, args.runtime, args.output)
    except (ValueError, OSError, RuntimeError, TimeoutError, ImportError) as exc:
        parser.exit(1, f"Preparation failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
