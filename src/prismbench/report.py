"""Validate and export deployment evidence without mixing changed configurations."""

import csv
import json
import os
from collections import Counter, defaultdict
from importlib.resources import files
from pathlib import Path, PurePosixPath, PureWindowsPath
from statistics import mean, stdev
from urllib.parse import quote

from jsonschema import Draft202012Validator, FormatChecker

from .io import canonical, save_json

METRICS = (
    "load_time_s", "ttft_s", "total_latency_s", "prompt_tokens_per_second",
    "generation_tokens_per_second", "prompt_tokens", "generated_tokens", "cache_tokens",
    "baseline_vram_mib", "loaded_idle_vram_mib", "peak_vram_mib",
    "peak_process_rss_mib", "peak_system_ram_used_mib",
)
SETTINGS = (
    "context_size", "prompt_tokens", "output_tokens", "gpu_layers", "threads",
    "batch_size", "ubatch_size", "cache_type_k", "cache_type_v", "flash_attention",
)


def validate_result(session: dict) -> None:
    """Reject invalid evidence, including relational constraints JSON Schema cannot express."""
    canonical(session)  # Reject NaN and Infinity, including in extension fields.
    schema = json.loads(files("prismbench").joinpath("data/result.schema.json").read_text("utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(session)
    seen = {}
    for attempt in session["attempts"]:
        ident = attempt["attempt_id"]
        if ident in seen:
            raise ValueError(f"duplicate attempt_id: {ident}")
        if attempt["synthetic"] != session["synthetic"]:
            raise ValueError("attempt synthetic flag must match its session")
        if attempt["repetition"] > session["config"]["repetitions"]:
            raise ValueError("attempt repetition exceeds the configured repeat count")
        request = attempt["requested"]
        if request["name"] != attempt["case_name"]:
            raise ValueError("requested name must match case_name")
        if request["prompt_tokens"] + request["output_tokens"] + 8 > request["context_size"]:
            raise ValueError("requested workload exceeds its context budget")
        if request["ubatch_size"] > request["batch_size"]:
            raise ValueError("requested ubatch_size exceeds batch_size")
        evidence_dir = attempt["evidence_dir"].replace("\\", "/")
        if (PurePosixPath(evidence_dir).is_absolute() or PureWindowsPath(evidence_dir).drive
                or ".." in PurePosixPath(evidence_dir).parts):
            raise ValueError("evidence_dir must be a relative path within the evidence root")
        parent_id = attempt["parent_attempt_id"]
        if (parent_id is None) != (attempt["attempt_index"] == 0):
            raise ValueError("only the first attempt may omit parent_attempt_id")
        if parent_id is not None:
            parent = seen.get(parent_id)
            if parent is None:
                raise ValueError("parent_attempt_id must identify an earlier attempt")
            if (parent["case_name"], parent["repetition"]) != (
                attempt["case_name"], attempt["repetition"]
            ):
                raise ValueError("fallback parent must belong to the same case and repetition")
            if parent["attempt_index"] + 1 != attempt["attempt_index"]:
                raise ValueError("fallback attempt_index must be consecutive")
            if parent["status"] != "OOM" or not parent["cleanup_confirmed"]:
                raise ValueError("fallback parent must be an OOM with confirmed cleanup")
        metrics = attempt["metrics"]
        if attempt["status"] == "SUCCESS":
            if attempt["runtime"]["effective"]["context_size"] != request["context_size"]:
                raise ValueError("SUCCESS effective context does not match requested context")
            for actual, requested in (("prompt_tokens", "prompt_tokens"),
                                      ("generated_tokens", "output_tokens")):
                if metrics[actual] != request[requested]:
                    raise ValueError(f"SUCCESS has mismatched {actual}")
            if metrics["ttft_s"] > metrics["total_latency_s"]:
                raise ValueError("TTFT exceeds total latency")
        seen[ident] = attempt


def _md(value) -> str:
    text = str(value).replace("\r", " ").replace("\n", " ")
    for char in ("\\", "`", "*", "_", "[", "]", "|", "<", ">"):
        text = text.replace(char, "\\" + char)
    return text


def _csv(value):
    if value is None:
        return ""
    if isinstance(value, str) and (value.lstrip().startswith(("=", "+", "-", "@"))
                                  or value.startswith(("\t", "\r", "\n"))):
        return "'" + value
    return value


def _number(value, digits=3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _config_key(attempt):
    return (attempt["case_name"], canonical(attempt["requested"]),
            canonical(attempt["runtime"].get("effective", {})),
            canonical(attempt["runtime"].get("prompt_sha256")),
            canonical(attempt["runtime"].get("runtime_version")))


def _table(headers, rows):
    return ["| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |"] + [
                "| " + " | ".join(row) + " |" for row in rows]


def _summary(attempts):
    good = [item for item in attempts if item["status"] == "SUCCESS"]
    result = {
        key: mean(item["metrics"][key] for item in good) if good else None
        for key in ("ttft_s", "generation_tokens_per_second")
    }
    result["generation_stdev"] = (stdev(item["metrics"]["generation_tokens_per_second"]
                                        for item in good) if len(good) > 1 else None)
    return result


def _evidence_target(relative: str, report_dir: Path | None, evidence_root: Path | None):
    target = relative.replace("\\", "/")
    if report_dir is not None and evidence_root is not None:
        source = evidence_root.resolve() / target
        try:
            target = Path(os.path.relpath(source, report_dir.resolve())).as_posix()
        except ValueError:  # Windows volumes cannot have a relative path between them.
            target = source.as_posix()
    if not target.startswith(("/", ".")) and not PureWindowsPath(target).drive:
        target = "./" + target
    return quote(target, safe="/:")


def render_markdown(session: dict, *, report_dir: Path | None = None,
                    evidence_root: Path | None = None) -> str:
    """Render a session already checked by validate_result."""
    attempts = session["attempts"]
    synthetic = session["synthetic"]
    groups = defaultdict(list)
    for attempt in attempts:
        groups[_config_key(attempt)].append(attempt)
    group_ids = {key: f"C{index}" for index, key in enumerate(groups, 1)}
    lines = ["# PrismBench deployment report", "",
             f"Session: {_md(session['session_id'])} · {_md(session['created_at'])}", "",
             f"Model: {_md(session['config'].get('model_id', 'unknown'))} · "
             f"Quantization: {_md(session['config'].get('quantization', 'unknown'))}", ""]
    if evidence_root is not None and report_dir is not None and evidence_root.resolve() != report_dir.resolve():
        target = _evidence_target(".", report_dir, evidence_root)
        lines += [f"Evidence remains in the [original run directory]({target}); "
                  "this export contains reports only.", ""]
    if synthetic:
        lines += ["**SYNTHETIC DEMO — no model inference or hardware performance was measured.**",
                  "No hardware recommendation can be made from this session.", ""]
    else:
        lines += ["**Local observations; results apply to this model, runtime, hardware and workload.**",
                  "VRAM values are sampled whole-device usage, including other applications; "
                  "sampling can miss short peaks. Process RSS and system RAM are separate metrics.",
                  "TTFT is client-observed; PP and generation throughput come from the engine. "
                  "Load time measures process start to ready, including startup overhead.", ""]
    counts = Counter(item["status"] for item in attempts)
    lines += ["Attempt outcomes: " + (", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
                                     or "no attempts recorded") + ".", ""]
    good = [item for item in attempts if item["status"] == "SUCCESS"]
    if good and not synthetic:
        maximum = max(item["requested"]["context_size"] for item in good)
        lines += [f"Largest successfully **tested allocated context: {maximum} tokens**. "
                  "This is not a discovered maximum or evidence that every token in the window "
                  "was used. See actual input/output lengths below.", ""]
    else:
        lines += ["No real successful context measurement is available.", ""]

    lines += ["## Exact deployment configurations", "",
              "Each row keeps one case, exact requested configuration, observed effective "
              "settings, prompt hash and runtime version. Changed fallback configurations have separate rows; failed attempts "
              "remain in the ledger.", ""]
    rows = []
    for key, items in groups.items():
        request = items[0]["requested"]
        summary = _summary(items)
        rows.append([group_ids[key], _md(items[0]["case_name"]),
                     f"{request['context_size']}/{request['prompt_tokens']}/{request['output_tokens']}",
                     str(request["gpu_layers"]),
                     f"{request['cache_type_k']}/{request['cache_type_v']}",
                     f"{request['threads']}/{request['batch_size']}/{request['ubatch_size']}",
                     request["flash_attention"],
                     f"{sum(x['status'] == 'SUCCESS' for x in items)}/{len(items)}",
                     _number(summary["ttft_s"]),
                     _number(summary["generation_tokens_per_second"], 2),
                     _number(summary["generation_stdev"], 2)])
    lines += _table(["ID", "Case", "Context/input/output", "GPU layers requested", "K/V",
                     "Threads/batch/micro", "FA", "Success/attempts", "Mean TTFT s",
                     "Mean generation tok/s", "Sample SD tok/s"], rows) + [""]

    lines += ["## Matched workload comparison", ""]
    matched = defaultdict(list)
    repetitions = session["config"].get("repetitions", 3)
    if not synthetic:
        for key, items in groups.items():
            if (len(items) == repetitions and all(x["status"] == "SUCCESS" for x in items)
                    and len({x["repetition"] for x in items}) == repetitions):
                request = items[0]["requested"]
                workload = (*tuple(request[field] for field in (
                    "context_size", "prompt_tokens", "output_tokens")),
                    items[0]["runtime"]["prompt_sha256"],
                    items[0]["runtime"]["runtime_version"])
                if len({x["runtime"]["prompt_sha256"] for x in items}) != 1:
                    continue
                matched[workload].append((group_ids[key], _summary(items)))
    comparable = [items for items in matched.values() if len(items) >= 2]
    if comparable:
        lines += ["Only complete successful repeat sets within the same session model, "
                  "runtime version, context, input and output lengths and prompt hash are ordered below. "
                  "This is a generation-speed comparison, not a quality or value recommendation.", ""]
        for items in comparable:
            ordered = sorted(items, key=lambda item: item[1]["generation_tokens_per_second"],
                             reverse=True)
            lines += [" → ".join(f"{ident}: {_number(values['generation_tokens_per_second'], 2)} tok/s"
                                 for ident, values in ordered), ""]
    else:
        lines += ["No recommendation: there are fewer than two complete, successful, real "
                  "configurations with a matching workload.", ""]

    lines += ["## Attempt ledger", ""]
    rows = []
    for attempt in attempts:
        metrics = attempt["metrics"]
        effective = attempt["runtime"].get("effective", {})
        layers = (f"{effective.get('gpu_layers_loaded', '—')}/"
                  f"{effective.get('gpu_layers_total', '—')}")
        target = _evidence_target(attempt["evidence_dir"], report_dir, evidence_root)
        link = f"[{_md(attempt['attempt_id'])}]({target})"
        rows.append([link, group_ids[_config_key(attempt)], str(attempt["repetition"]),
                     str(attempt["attempt_index"]), _md(attempt["status"]),
                     _number(metrics["ttft_s"]), _number(metrics["generation_tokens_per_second"], 2),
                     _number(metrics["peak_vram_mib"], 1), _md(layers),
                     _md(effective.get("cpu_offload", "unknown")), str(attempt["cleanup_confirmed"]),
                     _md(attempt["error"] or "—")])
    lines += _table(["Attempt/evidence", "Config", "Repeat", "Try", "Status", "TTFT s",
                     "Generation tok/s", "Peak VRAM MiB", "GPU layers loaded/total",
                     "CPU offload", "Cleanup", "Error"], rows) + [""]
    lines += ["## Quality and limitations", "",
              "Lightweight quality probes are regression checks, not a model capability score. "
              "Quantization quality loss is unmeasured without a paired reference evaluation. "
              "No percentage quality-loss claim or universal best configuration is inferred.", ""]
    quality_rows = []
    for attempt in attempts:
        quality = attempt["quality"]
        if quality is not None:
            quality_rows.append([_md(attempt["attempt_id"]),
                                 _md(quality.get("suite_id", "unknown")),
                                 _md(quality.get("passed", "unknown")),
                                 _md(quality.get("probe_count", "unknown"))])
    if quality_rows:
        lines += _table(["Attempt", "Probe suite", "Passed", "Probe count"], quality_rows) + [""]
    warnings = list(session["warnings"])
    for attempt in attempts:
        warnings.extend(f"{attempt['attempt_id']}: {warning}" for warning in attempt["warnings"])
    if warnings:
        lines += ["Recorded warnings:", ""] + [f"- {_md(warning)}" for warning in warnings] + [""]
    lines += ["Full metrics, requested and runtime settings, provenance, quality probe output "
              "and all failures are preserved in [results.json](results.json) and "
              "[results.csv](results.csv). Missing metrics are null in JSON and blank in CSV.", ""]
    return "\n".join(lines)


def write_reports(session: dict, out: Path, evidence_root: Path | None = None) -> None:
    """Validate first, then write JSON, a complete attempt CSV, and a readable report."""
    validate_result(session)
    out = Path(out)
    evidence_root = Path(evidence_root) if evidence_root is not None else out
    out.mkdir(parents=True, exist_ok=True)
    save_json(out / "results.json", session)
    columns = ["session_id", "model_id", "quantization", "attempt_id", "parent_attempt_id",
               "case_name", "repetition", "attempt_index", "status", "error", "synthetic",
               *SETTINGS, *METRICS, "cleanup_confirmed", "evidence_dir", "warnings"]
    with (out / "results.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for attempt in session["attempts"]:
            row = {key: attempt.get(key) for key in columns}
            row.update({key: attempt["requested"].get(key) for key in SETTINGS})
            row.update({key: attempt["metrics"].get(key) for key in METRICS})
            row.update({"session_id": session["session_id"],
                        "model_id": session["config"].get("model_id"),
                        "quantization": session["config"].get("quantization"),
                        "warnings": "; ".join(attempt["warnings"])})
            writer.writerow({key: _csv(value) for key, value in row.items()})
    (out / "report.md").write_text(render_markdown(session, report_dir=out,
                                                  evidence_root=evidence_root), encoding="utf-8")
