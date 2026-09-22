"""Pinned, external llama.cpp perplexity recipe; not an installed backend.

Run from a checkout with ``python -m experiments.quantization_study MANIFEST
--output NEWDIR``. Corpus-derived tokenizer stdout is retained locally and must
not be redistributed under the tool's MIT license.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import psutil

from prismbench.backends.process import OwnedProcess
from prismbench.hardware import Collector, detect, sample
from prismbench.io import digest, hash_file, save_json

PROTOCOL = {"context_size": 2048, "chunks": 32, "batch_size": 512,
            "ubatch_size": 128, "threads": 6, "gpu_layers": 99, "parallel": 1,
            "cache_type_k": "f16", "cache_type_v": "f16", "flash_attention": "on",
            "fit": "off", "escape": False, "parse_special": False, "stride": 0,
            "gpu_index": 0, "timeout_seconds": 600, "tokenize_timeout_seconds": 30,
            "sample_interval_seconds": 0.5, "minimum_start_ram_gib": 10,
            "minimum_start_free_vram_gib": 7, "minimum_run_ram_gib": 6,
            "token_prefix_length": 65536}
LABELS = ("F16", "Q8_0", "Q4_K_M")
SHA = re.compile(r"[0-9a-f]{64}\Z")


def _sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError("Expected a lowercase SHA256 digest")
    return value


def _absolute_file(value):
    if not isinstance(value, str) or not Path(value).is_absolute() or not Path(value).is_file():
        raise ValueError(f"Expected an existing absolute file path: {value!r}")
    return Path(value)


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "1":
        raise ValueError("Expected manifest schema_version '1'")
    if manifest.get("model_id") != "Qwen/Qwen3-1.7B":
        raise ValueError("This recipe is pinned to Qwen/Qwen3-1.7B")
    runtime = Path(manifest.get("runtime_dir", ""))
    if not runtime.is_absolute() or not runtime.is_dir():
        raise ValueError("runtime_dir must be an existing absolute directory")
    hashes = manifest.get("expected_runtime")
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError("expected_runtime must inventory the tools and adjacent DLLs")
    if len({name.casefold() for name in hashes}) != len(hashes):
        raise ValueError("Runtime filenames collide ignoring case")
    for name, sha in hashes.items():
        if not isinstance(name, str) or Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("Runtime inventory must use filenames, not paths")
        _sha(sha)
        _absolute_file(str(runtime / name))
    if not {"llama-perplexity.exe", "llama-tokenize.exe"}.issubset(hashes):
        raise ValueError("Missing pinned perplexity/tokenize executable")
    if {p.name.casefold() for p in runtime.glob("*.dll")} - {n.casefold() for n in hashes}:
        raise ValueError("Every adjacent runtime DLL must be pinned")
    corpus = manifest.get("corpus")
    if not isinstance(corpus, dict) or not isinstance(corpus.get("source"), dict) or not corpus["source"]:
        raise ValueError("Corpus requires source/license provenance")
    _absolute_file(corpus.get("path"))
    _sha(corpus.get("sha256"))
    models = manifest.get("models")
    if not isinstance(models, list) or len(models) != 3 or any(not isinstance(m, dict) for m in models):
        raise ValueError("Exactly three model records are required")
    if {m.get("label") for m in models} != set(LABELS):
        raise ValueError("Exactly F16, Q8_0 and Q4_K_M labels are required")
    for model in models:
        _absolute_file(model.get("path"))
        for field in ("sha256", "parent_sha256", "tokenizer_sha256"):
            _sha(model.get(field))
    by_label = {m["label"]: m for m in models}
    reference = by_label["F16"]
    if any(by_label[label]["parent_sha256"] != reference["sha256"] for label in LABELS[1:]):
        raise ValueError("Quantized models must derive from this exact F16 reference")
    if len({m["tokenizer_sha256"] for m in models}) != 1:
        raise ValueError("Tokenizer metadata identities differ")
    if len({m["sha256"] for m in models}) != 3:
        raise ValueError("Three distinct model artifacts are required")
    return by_label


def verify_assets(manifest):
    """Hash everything before any model process; don't trust a label alone."""
    validate_manifest(manifest)
    receipts = {"runtime": {}, "models": {}, "corpus": None}
    for name, expected in manifest["expected_runtime"].items():
        actual = hash_file(Path(manifest["runtime_dir"]) / name)
        if actual != expected:
            raise ValueError(f"Runtime hash mismatch: {name}")
        receipts["runtime"][name] = actual
    for model in manifest["models"]:
        path = Path(model["path"])
        actual = hash_file(path)
        if actual != model["sha256"]:
            raise ValueError(f"Model hash mismatch: {model['label']}")
        receipts["models"][model["label"]] = {"sha256": actual, "size_bytes": path.stat().st_size}
    corpus = Path(manifest["corpus"]["path"])
    actual = hash_file(corpus)
    if actual != manifest["corpus"]["sha256"]:
        raise ValueError("Corpus hash mismatch")
    with corpus.open("rb") as stream:
        if not corpus.stat().st_size:
            raise ValueError("Corpus is empty")
        stream.seek(-1, 2)
        if stream.read(1) in (b"\n", b"\r"):
            raise ValueError("Corpus must not end with newline: upstream trims trailing LF")
    receipts["corpus"] = {"sha256": actual, "size_bytes": corpus.stat().st_size}
    return receipts


def admission(row):
    values = [row.get(k) for k in ("system_ram_available_mib", "vram_total_mib", "vram_used_mib")]
    if any(type(v) not in (int, float) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError("Memory telemetry is missing or invalid")
    if not isinstance(row.get("gpu_uuid"), str) or not row["gpu_uuid"].startswith("GPU-"):
        raise ValueError("Selected GPU UUID is unavailable")
    if values[0] < 10 * 1024 or values[1] - values[2] < 7 * 1024:
        raise ValueError("Need at least 10 GiB available RAM and 7 GiB free device memory")


def environment(uuid):
    prefixes = ("LLAMA_", "GGML_", "CUDA_", "CUBLAS_", "MTMD_")
    removed = sorted(k for k in os.environ if k.startswith(prefixes))
    env = {k: v for k, v in os.environ.items() if k not in removed}
    env["CUDA_VISIBLE_DEVICES"] = uuid
    return env, {"removed_names": removed, "explicit": {"CUDA_VISIBLE_DEVICES": uuid}}


def run_command(argv, directory, runtime, env, timeout, *, collect=False, merge_stderr=False):
    """Bounded owned process with failure evidence even when launch fails."""
    directory.mkdir(parents=True, exist_ok=False)
    row = {"argv": argv, "cwd": str(runtime), "status": "ERROR", "error": None,
           "exit_code": None, "timeout_seconds": timeout, "wall_s": None,
           "cleanup": {"success": True, "remaining_pids": [], "errors": [], "not_started": True},
           "resources": {}, "guards": [],
           "streams": "stdout.log merges stdout and stderr" if merge_stderr else "separate stdout.log and stderr.log"}
    save_json(directory / "command.json", row)
    child = collector = None
    started = time.monotonic()
    try:
        with (directory / "stdout.log").open("wb") as stdout, (directory / "stderr.log").open("wb") as stderr:
            child = OwnedProcess(argv, stdout=stdout,
                                 stderr=subprocess.STDOUT if merge_stderr else stderr,
                                 cwd=str(runtime), env=env)
            if collect:
                collector = Collector(directory / "telemetry.jsonl", 0, 0.5, lambda: child.pid)
                collector.phase = "perplexity"
                collector.start()
            while child.poll() is None:
                elapsed = time.monotonic() - started
                available = psutil.virtual_memory().available
                row["guards"].append({"elapsed_s": elapsed, "available_ram_bytes": available})
                if available < 6 * 1024 ** 3:
                    row.update(status="RAM_GUARD", error="Available host RAM below 6 GiB")
                    break
                if elapsed >= timeout:
                    row.update(status="TIMEOUT", error="Owned process exceeded wall deadline")
                    break
                time.sleep(0.1)
            else:
                row["exit_code"] = child.poll()
                row["status"] = "SUCCESS" if row["exit_code"] == 0 else "ERROR"
                if row["exit_code"]:
                    row["error"] = f"Process exited {row['exit_code']}"
    except (Exception, KeyboardInterrupt) as exc:
        row.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "ERROR",
                   error=f"{type(exc).__name__}: {exc}")
    finally:
        if child:
            try:
                row["cleanup"] = child.close()
            except Exception as exc:
                row["cleanup"] = {"success": False, "remaining_pids": None, "errors": [str(exc)]}
            if not row["cleanup"].get("success"):
                row.update(status="CLEANUP_FAILED", error="Owned process cleanup was not confirmed")
        if collector:
            try:
                collector.close()
                row["resources"] = collector.metrics()
                if collector._thread.is_alive():
                    raise RuntimeError("Telemetry thread failed to stop")
            except Exception as exc:
                row["telemetry_error"] = str(exc)
                if row["status"] == "SUCCESS":
                    row.update(status="ERROR", error="Telemetry finalization failed")
        row["wall_s"] = time.monotonic() - started
        save_json(directory / "command.json", row)
    return row


def parse_version(text):
    if not re.search(r"\bbuild\s+10964\b", text) or not re.search(r"\bcommit\s+b29c606(?:e2[a-f0-9]*)?\b", text):
        raise ValueError("Runtime must be llama.cpp build 10964, commit b29c606e2")
    return text.strip()


def parse_tokens(text):
    try:
        tokens = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError("Tokenizer stdout is not one JSON token array") from exc
    if not isinstance(tokens, list) or any(type(t) is not int or t < 0 for t in tokens):
        raise ValueError("Tokenizer must return nonnegative integer token IDs")
    if len(tokens) < PROTOCOL["token_prefix_length"]:
        raise ValueError("Corpus has fewer than 65,536 tokens; cannot evaluate 32 complete chunks")
    return tokens


def token_fingerprint(tokens):
    return {"total_tokens": len(tokens), "total_token_sha256": digest(tokens),
            "prefix_tokens": 65536, "prefix_token_sha256": digest(tokens[:65536]),
            "hash_encoding": "SHA256 of compact JSON integer array",
            "add_special": True, "parse_special": False, "escape": False,
            "stdout_rights": "Corpus-derived token IDs; local-only, not licensed under tool MIT"}


def parse_effective(text, argv):
    """Require logged settings, not merely successful process termination."""
    def unique(pattern, expected, label):
        values = re.findall(pattern, text, re.MULTILINE)
        if not values or set(values) != {expected}:
            raise ValueError(f"Missing or unexpected effective {label}: {values}")
    unique(r"\bn_ctx\s*=\s*(\d+)\s*$", "2048", "context")
    unique(r"\bflash_attn\s*=\s*(enabled|disabled)", "enabled", "Flash Attention")
    unique(r"\bK \(([^)]+)\):", "f16", "K cache")
    unique(r"\bV \(([^)]+)\):", "f16", "V cache")
    layers = re.findall(r"offloaded\s+(\d+)/(\d+)\s+layers to GPU", text)
    if not layers or any(int(a) <= 0 or a != b for a, b in layers):
        raise ValueError("Full GPU placement is missing or incomplete")
    if "--fit" not in argv or argv[argv.index("--fit") + 1:argv.index("--fit") + 2] != ["off"]:
        raise ValueError("Automatic fit was not explicitly disabled")
    if re.search(r"common_params_fit|fit_params|auto[- ]?fit|fitting.*memory", text, re.IGNORECASE):
        raise ValueError("Unexpected automatic-fit diagnostic")
    return {"context_size": 2048, "gpu_layers_loaded": int(layers[-1][0]),
            "gpu_layers_total": int(layers[-1][1]), "cache_type_k": "f16",
            "cache_type_v": "f16", "flash_attention": "on", "automatic_fit": False,
            "fit_verification": "explicit --fit off, pinned runtime, no fit diagnostic",
            "parallel": 1}


def perplexity_argv(runtime, model, corpus):
    return [str(runtime / "llama-perplexity.exe"), "-m", model["path"], "-f", corpus,
            "-c", "2048", "-b", "512", "-ub", "128", "-t", "6", "-ngl", "99",
            "-fa", "on", "--fit", "off", "-ctk", "f16", "-ctv", "f16", "--chunks", "32",
            "--ppl-output-type", "1", "--no-escape"]


def _logs(directory):
    return "\n".join((directory / name).read_text(encoding="utf-8", errors="replace")
                     for name in ("stdout.log", "stderr.log"))


def write_reports(result, output):
    save_json(output / "results.json", result)
    columns = ["label", "repeat", "status", "ppl", "mean_nll", "peak_vram_mib", "wall_s", "cleanup", "error"]
    with (output / "results.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for run in result["runs"]:
            metrics, process = run.get("metrics", {}), run.get("process", {})
            error = run.get("error") or process.get("error") or ""
            if error and error[:1] in "=+-@\t\r":
                error = "'" + error
            writer.writerow({"label": run["label"], "repeat": run["repeat"], "status": run["status"],
                             "ppl": metrics.get("ppl", metrics.get("perplexity")),
                             "mean_nll": metrics.get("mean_nll"),
                             "peak_vram_mib": process.get("resources", {}).get("peak_vram_mib"),
                             "wall_s": process.get("wall_s"),
                             "cleanup": process.get("cleanup", {}).get("success"), "error": error})
    lines = ["# Quantization perplexity study", "", f"Status: **{result['status']}**", "",
             "Fixed raw-text corpus and 32 non-overlapping 2K chunks. These observations measure",
             "cross-entropy/perplexity on this corpus, not general intelligence or percent quality retained.",
             "", "| Model | Repeat | Status | PPL | Whole-device peak MiB | Evidence |",
             "|---|---:|---|---:|---:|---|"]
    for run in result["runs"]:
        metrics, process = run.get("metrics", {}), run.get("process", {})
        ppl = metrics.get("ppl", metrics.get("perplexity", "—"))
        peak = process.get("resources", {}).get("peak_vram_mib", "—")
        lines.append(f"| {run['label']} | {run['repeat']} | {run['status']} | {ppl} | {peak} | "
                     f"[logs]({run['evidence_dir']}) |")
    lines += ["", "Comparisons and paired corpus uncertainty are in [results.json](results.json).",
              "The additional F16 run measures numerical drift separately from corpus uncertainty.",
              "Whole-device sampled memory includes other applications and can miss transients.",
              "Tokenizer stdout is corpus-derived and remains local; it is not covered by the tool's MIT license."]
    if result.get("error"):
        lines += ["", "Failure: " + str(result["error"]).replace("\n", " ")]
    (output / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def execute(manifest_path, output):
    output.mkdir(parents=True, exist_ok=False)
    result = {"schema_version": "1", "created_at": datetime.now(timezone.utc).isoformat(),
              "protocol": PROTOCOL, "status": "RUNNING", "error": None, "manifest": None,
              "helper_sha256": hash_file(Path(__file__)), "tokenization": [], "runs": [],
              "comparisons": [], "reference_repeat": None, "preflight": []}
    try:
        from experiments.perplexity_metrics import compare_perplexity, parse_perplexity

        result["metrics_helper_sha256"] = hash_file(Path(__file__).with_name("perplexity_metrics.py"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        result["manifest"], result["manifest_sha256"] = manifest, hash_file(manifest_path)
        models = validate_manifest(manifest)
        result["asset_receipts"] = verify_assets(manifest)
        existing = [p.pid for p in psutil.process_iter(["name"])
                    if (p.info["name"] or "").lower() in
                    ("llama-server", "llama-server.exe", "llama-perplexity", "llama-perplexity.exe")]
        if existing:
            raise ValueError(f"Existing model work found; leave these processes untouched: {existing}")
        result["hardware"] = detect(0)
        baseline = result["hardware"]["snapshot"]
        admission(baseline)
        env, result["environment"] = environment(baseline["gpu_uuid"])
        runtime, corpus = Path(manifest["runtime_dir"]), manifest["corpus"]["path"]
        directory = output / "runtime-version"
        preflight = run_command([str(runtime / "llama-perplexity.exe"), "--version"],
                                directory, runtime, env, 30)
        result["preflight"].append(preflight)
        if preflight["status"] != "SUCCESS":
            raise ValueError("Runtime version preflight failed; queue stopped")
        result["runtime_version"] = parse_version(_logs(directory))
        reference_tokens = None
        for label in LABELS:
            directory = output / "tokenization" / label
            argv = [str(runtime / "llama-tokenize.exe"), "-m", models[label]["path"],
                    "-f", corpus, "--ids", "--no-escape", "--no-parse-special"]
            token_row = {"label": label, "status": "RUNNING", "evidence_dir": directory.relative_to(output).as_posix()}
            result["tokenization"].append(token_row)
            process = run_command(argv, directory, runtime, env, 30)
            token_row["process"] = process
            token_row["status"] = process["status"]
            if process["status"] != "SUCCESS":
                raise ValueError(f"{label} tokenizer failed; queue stopped")
            try:
                tokens = parse_tokens((directory / "stdout.log").read_text(encoding="utf-8"))
                token_row["fingerprint"] = token_fingerprint(tokens)
                if reference_tokens is not None and reference_tokens != tokens:
                    raise ValueError("Exact tokenizer token arrays differ")
                reference_tokens = tokens if reference_tokens is None else reference_tokens
            except ValueError as exc:
                token_row.update(status="INVALID_WORKLOAD", error=str(exc))
                raise
            write_reports(result, output)
        for label, repeat in [(label, 1) for label in LABELS] + [("F16", 2)]:
            row = {"label": label, "repeat": repeat, "status": "RUNNING", "metrics": {},
                   "error": None, "evidence_dir": f"perplexity/{label}-r{repeat}"}
            result["runs"].append(row)
            directory = output / row["evidence_dir"]
            try:
                row["baseline"] = sample(0)
                admission(row["baseline"])
                if row["baseline"]["gpu_uuid"] != baseline["gpu_uuid"]:
                    raise ValueError("Selected GPU identity changed")
                argv = perplexity_argv(runtime, models[label], corpus)
                row["process"] = run_command(argv, directory, runtime, env, 600,
                                             collect=True, merge_stderr=True)
                row["status"] = row["process"]["status"]
                if row["status"] != "SUCCESS":
                    raise ValueError(f"{label} perplexity process failed; queue stopped")
                text = _logs(directory)
                row["effective"] = parse_effective(text, argv)
                row["metrics"] = parse_perplexity(text, context_size=2048, chunks=32, batch_size=512)
                row["status"] = "SUCCESS"
            except (Exception, KeyboardInterrupt) as exc:
                if row["status"] in ("RUNNING", "SUCCESS"):
                    row["status"] = "CANCELLED" if isinstance(exc, KeyboardInterrupt) else "INVALID_WORKLOAD"
                row["error"] = str(exc)
                raise
            finally:
                directory.mkdir(parents=True, exist_ok=True)
                save_json(directory / "attempt.json", row)
                write_reports(result, output)
        reference = result["runs"][0]["metrics"]
        for candidate in result["runs"][1:3]:
            result["comparisons"].append({"reference": "F16-r1", "candidate": candidate["label"] + "-r1",
                                          "metrics": compare_perplexity(reference, candidate["metrics"])})
        repeat_comparison = compare_perplexity(reference, result["runs"][3]["metrics"])
        result["reference_repeat"] = {"reference": "F16-r1", "candidate": "F16-r2",
                                      "interpretation": "Numerical repeat drift; separate from corpus uncertainty",
                                      "metrics": {key: value for key, value in repeat_comparison.items()
                                                  if key != "exploratory_block_bootstrap"}}
        result["status"] = "SUCCESS"
    except (Exception, KeyboardInterrupt) as exc:
        result.update(status="CANCELLED" if isinstance(exc, KeyboardInterrupt) else "ERROR",
                      error=f"{type(exc).__name__}: {exc}")
    finally:
        write_reports(result, output)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = execute(args.manifest.resolve(), args.output.resolve())
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Cannot start study: {exc}\n")
    print(f"{result['status']}: {args.output.resolve() / 'results.json'}")
    return 0 if result["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
