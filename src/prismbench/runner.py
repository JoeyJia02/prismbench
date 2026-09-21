"""Sequential, bounded model lifetimes and auditable fallback attempts."""

import math
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .backends.base import BackendError
from .config import Config
from .hardware import Collector, detect, sample
from .io import canonical, digest, hash_file, save_json

METRICS = ("load_time_s", "ttft_s", "total_latency_s", "prompt_tokens_per_second",
           "generation_tokens_per_second", "prompt_tokens", "generated_tokens", "cache_tokens",
           "baseline_vram_mib", "loaded_idle_vram_mib", "peak_vram_mib", "peak_process_rss_mib",
           "peak_system_ram_used_mib")


def backend_factory(config, case, out):
    if config.backend == "synthetic":
        from .backends.synthetic import SyntheticBackend
        return SyntheticBackend(config, case, out)
    from .backends.llama_cpp import LlamaCppBackend
    return LlamaCppBackend(config, case, out)


def workload_tokens(backend, count):
    # Public, generated corpus. Exact token IDs are frozen with each attempt.
    text = "".join(f"Record {i}: the blue box holds {i % 17 + 3} samples. "
                   "Measure memory and time; preserve every independent result.\n"
                   for i in range(max(128, count // 8)))
    tokens = backend.tokenize(text)
    if len(tokens) < count or not all(type(t) is int and t >= 0 for t in tokens):
        raise BackendError("INVALID_WORKLOAD", "Tokenizer could not supply exact input tokens")
    return tokens[:count]


def measured_metrics(response, case):
    t = response.get("timings", {})
    if (t.get("prompt_n") != case.prompt_tokens or t.get("predicted_n") != case.output_tokens
            or t.get("cache_n") != 0 or response.get("truncated", True)):
        raise BackendError("INVALID_WORKLOAD", "Actual prompt/output/cache/truncation differs from requested workload")
    values = {"ttft_s": response.get("ttft_s"), "total_latency_s": response.get("total_latency_s"),
              "prompt_tokens_per_second": t.get("prompt_per_second"),
              "generation_tokens_per_second": t.get("predicted_per_second")}
    for key, value in values.items():
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise BackendError("INVALID_WORKLOAD", f"Missing or invalid {key}")
    if values["ttft_s"] > values["total_latency_s"]:
        raise BackendError("INVALID_WORKLOAD", "TTFT exceeds total client latency")
    return {**values, "prompt_tokens": t["prompt_n"], "generated_tokens": t["predicted_n"],
            "cache_tokens": t["cache_n"]}


def provenance(config):
    data = {"model_sha256": None, "model_size_bytes": None, "server_sha256": None,
            "config_sha256": digest(config.to_dict())}
    if config.backend != "synthetic":
        model, server = Path(config.model), Path(config.server)
        data.update(model_sha256=hash_file(model), model_size_bytes=model.stat().st_size,
                    server_sha256=hash_file(server))
        if config.expected_model_sha256 and data["model_sha256"] != config.expected_model_sha256:
            raise ValueError("Model SHA256 does not match expected_model_sha256")
        # Windows releases put implementation in DLLs; executable hash alone is insufficient.
        data["runtime_library_sha256"] = {p.name: hash_file(p) for p in sorted(server.parent.glob("*.dll"))}
    package = Path(__file__).parent
    data["source_sha256"] = {p.relative_to(package).as_posix(): hash_file(p)
                             for p in sorted(package.rglob("*.py"))}
    return data


def run(config: Config, output: Path, *, factory=backend_factory, progress=print) -> dict:
    from .quality import load_suite, run_quality
    from .report import write_reports

    config.validate()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)  # Never merge with, or overwrite, an earlier run.
    synthetic = config.backend == "synthetic"
    session = {"schema_version": "1.0", "tool_version": __version__,
               "session_id": uuid.uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat(),
               "synthetic": synthetic, "config": config.to_dict(), "hardware": {} if synthetic else detect(config.gpu_index),
               "provenance": {}, "attempts": [],
               "warnings": ["SYNTHETIC DEMO: all performance values are fixtures; no hardware or quality conclusions."
                            if synthetic else config.notes]}
    session["provenance"] = provenance(config)
    suite = load_suite(Path(config.quality_suite) if config.quality_suite else None) if config.quality else None
    save_json(output / "config.resolved.json", config.to_dict())
    halted = False
    for original in config.cases:
        if halted:
            break
        for repetition in range(1, config.repetitions + 1):
            if halted:
                break
            parent = None
            for index, case in enumerate(original.attempts()):
                attempt_id = f"{case.name}-r{repetition}-a{index}"
                directory = output / "attempts" / attempt_id
                directory.mkdir(parents=True)
                backend = factory(config, case, directory)
                collector = None
                row = {"attempt_id": attempt_id, "case_name": case.name, "repetition": repetition,
                       "attempt_index": index, "parent_attempt_id": parent, "status": "ERROR",
                       "error": None, "synthetic": synthetic, "requested": asdict(case), "runtime": {},
                       "metrics": dict.fromkeys(METRICS), "quality": None, "cleanup_confirmed": False,
                       "evidence_dir": directory.relative_to(output).as_posix(), "warnings": []}
                progress(f"{attempt_id}: starting {config.backend}, context={case.context_size}, GPU layers={case.gpu_layers}")
                try:
                    if not synthetic:
                        baseline = sample(config.gpu_index)
                        save_json(directory / "baseline.json", baseline)
                        row["metrics"]["baseline_vram_mib"] = baseline["vram_used_mib"]
                        if baseline.get("gpu_telemetry_error"):
                            row["warnings"].append("GPU telemetry unavailable: " + baseline["gpu_telemetry_error"])
                        if (baseline.get("gpu_utilization_percent") or 0) > 5:
                            row["warnings"].append("Preload GPU utilization exceeds 5%; background load may affect results.")
                        collector = Collector(directory / "telemetry.jsonl", config.gpu_index,
                                              config.sample_interval_seconds, lambda: backend.pid)
                        collector.start()
                    runtime = backend.start()
                    try:
                        canonical(runtime)
                    except (ValueError, TypeError) as exc:
                        (directory / "invalid-runtime.txt").write_text(repr(runtime), encoding="utf-8")
                        raise BackendError("INVALID_WORKLOAD", "Backend startup returned non-JSON or nonfinite data") from exc
                    row["runtime"] = runtime
                    row["warnings"].extend(row["runtime"].get("effective", {}).get("verification_warnings", []))
                    load_time = row["runtime"].get("load_time_s")
                    if type(load_time) not in (int, float) or not math.isfinite(load_time) or load_time <= 0:
                        raise BackendError("INVALID_WORKLOAD", "Backend startup has no finite positive load time")
                    row["metrics"]["load_time_s"] = load_time
                    if row["runtime"].get("effective", {}).get("context_size") != case.context_size:
                        raise BackendError("INVALID_WORKLOAD", "Effective context does not match requested context")
                    if collector:
                        loaded = collector.take("loaded_idle")
                        row["metrics"]["loaded_idle_vram_mib"] = loaded["vram_used_mib"]
                        collector.phase = "warmup"
                    tokens = workload_tokens(backend, case.prompt_tokens)
                    save_json(directory / "tokens.json", tokens)
                    row["runtime"]["prompt_sha256"] = digest(tokens)
                    backend.erase()
                    backend.complete(tokens[:min(128, len(tokens))], min(16, case.output_tokens),
                                     config.seed, config.request_timeout_seconds)
                    backend.erase()
                    if collector:
                        collector.phase = "measure"
                    response = backend.complete(tokens, case.output_tokens, config.seed, config.request_timeout_seconds)
                    save_json(directory / "measured-response.json", response)
                    row["metrics"].update(measured_metrics(response, case))
                    if collector:
                        collector.take("measure_finished")
                    if config.quality:
                        if collector:
                            collector.phase = "quality"
                        row["quality"] = run_quality(backend, suite, config.seed,
                                                     config.request_timeout_seconds, context_size=case.context_size)
                    row["status"] = "SUCCESS"
                except KeyboardInterrupt:
                    row.update(status="CANCELLED", error="Interrupted by user")
                    halted = True
                except Exception as exc:
                    status = getattr(exc, "status", "ERROR")
                    row.update(status=status if status in ("OOM", "TIMEOUT", "INVALID_WORKLOAD") else "ERROR",
                               error=str(exc)[:4000])
                finally:
                    try:
                        row["cleanup_confirmed"] = backend.close()
                    except Exception as exc:
                        row["warnings"].append(f"Cleanup error: {exc}")
                    if collector:
                        try:
                            collector.close()
                            row["metrics"].update(collector.metrics())
                            row["metrics"]["peak_scope"] = "sampled whole device across load, warmup, measurement and quality"
                            after = sample(config.gpu_index)
                            save_json(directory / "after-cleanup.json", after)
                            row["metrics"]["after_cleanup_vram_mib"] = after["vram_used_mib"]
                        except Exception as exc:
                            row["warnings"].append(f"Telemetry finalization failed; measurements may be incomplete: {exc}")
                    if not row["cleanup_confirmed"]:
                        row.update(status="CLEANUP_FAILED", error="Owned process cleanup not confirmed; queue stopped")
                        halted = True
                    if hasattr(backend, "cleanup"):
                        row["runtime"]["cleanup"] = backend.cleanup
                    save_json(directory / "attempt.json", row)
                    session["attempts"].append(row)
                    write_reports(session, output)
                progress(f"{attempt_id}: {row['status']}")
                if row["status"] != "OOM" or halted:
                    break
                parent = attempt_id
                # CPU offload is a new configuration, never substituted into the failed row.
                if index < len(original.fallbacks):
                    progress(f"{attempt_id}: cleanup confirmed; trying next explicit OOM fallback")
    return session
