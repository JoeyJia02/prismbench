"""Small fixed probes and conservative paired comparisons; never a capability score."""

import hashlib
import json
import math
import re
import unicodedata
from importlib.resources import files
from pathlib import Path

OUTPUT_TOKENS = 64
NORMALIZATION = "NFKC; collapse whitespace; case-sensitive exact match"
LIMITATION = (
    "Fixed-probe pass rate only; not general model quality or percent quality retained. "
    "The model_id is user asserted and does not verify a common base-model revision."
)


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _hash(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def normalize(text: str) -> str:
    """Normalize Unicode and whitespace only; punctuation and letter case still count."""
    if not isinstance(text, str):
        raise ValueError("probe answer must be text")
    return " ".join(unicodedata.normalize("NFKC", text).split())


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _validate_suite(suite):
    if not isinstance(suite, dict) or set(suite) != {"id", "version", "probes"}:
        raise ValueError("quality suite must contain exactly id, version, and probes")
    for key in ("id", "version"):
        if not isinstance(suite[key], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", suite[key]):
            raise ValueError(f"quality suite {key} must be a short ASCII identifier")
    probes = suite["probes"]
    if not isinstance(probes, list) or not 1 <= len(probes) <= 64:
        raise ValueError("quality suite must have between 1 and 64 probes")
    seen = set()
    for probe in probes:
        if not isinstance(probe, dict) or set(probe) != {"id", "prompt", "expected"}:
            raise ValueError("each probe must contain exactly id, prompt, and expected")
        if not isinstance(probe["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", probe["id"]):
            raise ValueError("probe id must be a short ASCII identifier")
        if probe["id"] in seen:
            raise ValueError("duplicate probe id: " + probe["id"])
        seen.add(probe["id"])
        for key, maximum in (("prompt", 8192), ("expected", 1024)):
            value = probe[key]
            if not isinstance(value, str) or not normalize(value) or len(value) > maximum:
                raise ValueError(f"probe {key} must be nonempty text of at most {maximum} characters")
    return suite


def load_suite(path: Path | None = None) -> dict:
    """Load a bounded strict suite; hash canonical parsed JSON, not incidental spacing."""
    source = Path(path) if path is not None else files("prismbench").joinpath("data/probes.json")
    with source.open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("quality suite exceeds 1 MiB")
    try:
        suite = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid quality suite JSON: {exc}") from exc
    return _validate_suite(suite)


def run_quality(backend, suite: dict, seed: int, timeout_s: float, *, context_size: int = 2048) -> dict:
    """Run EOS-enabled raw-completion probes after performance collection finishes.

    Backend.probe must use greedy sampling, a newline stop and no chat template. Errors propagate
    to the attempt controller; this function never turns partial probes into success.
    """
    _validate_suite(suite)
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError("quality seed must be a nonnegative 32-bit integer")
    if type(context_size) is not int or context_size < 128:
        raise ValueError("quality context_size must be an integer >= 128")
    if type(timeout_s) not in (int, float) or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("quality timeout must be a positive finite number")

    # Validate every prompt before the first probe to avoid a half-run custom suite.
    tokenizations = []
    for probe in suite["probes"]:
        token_ids = backend.tokenize(probe["prompt"])
        if not isinstance(token_ids, list) or not token_ids or any(type(t) is not int or t < 0 for t in token_ids):
            raise ValueError("backend returned invalid quality prompt token IDs")
        if len(token_ids) + OUTPUT_TOKENS + 8 > context_size:
            raise ValueError(f"quality probe {probe['id']} does not fit context including 64 output tokens + 8 margin")
        tokenizations.append(token_ids)

    items = []
    for probe, token_ids in zip(suite["probes"], tokenizations):
        backend.erase()
        actual = backend.probe(probe["prompt"], OUTPUT_TOKENS, seed, timeout_s)
        passed = normalize(actual) == normalize(probe["expected"])
        items.append({**probe, "prompt_tokens": len(token_ids), "prompt_sha256": _hash(token_ids),
                      "actual": actual, "passed": passed})
    passed = sum(item["passed"] for item in items)
    return {
        "suite_id": suite["id"], "suite_version": suite["version"], "suite_sha256": _hash(suite),
        "probe_count": len(items), "passed": passed, "score": passed / len(items), "items": items,
        "generation": {"seed": seed, "n_predict": OUTPUT_TOKENS, "context_size": context_size,
                       "temperature": 0, "ignore_eos": False, "prompt_format": "raw_completion",
                       "stop": ["\n"]},
        "normalization": NORMALIZATION, "limitation": LIMITATION,
    }


def _validated_quality(attempt):
    quality = attempt.get("quality")
    try:
        if not isinstance(quality, dict) or quality.get("normalization") != NORMALIZATION:
            raise ValueError("quality normalization/provenance is missing or unsupported")
        items = quality["items"]
        suite = {"id": quality["suite_id"], "version": quality["suite_version"],
                 "probes": [{k: item[k] for k in ("id", "prompt", "expected")} for item in items]}
        _validate_suite(suite)
        if _hash(suite) != quality["suite_sha256"]:
            raise ValueError("quality suite hash does not match saved prompts")
        for item in items:
            if type(item["prompt_tokens"]) is not int or item["prompt_tokens"] < 1:
                raise ValueError("quality prompt token count is invalid")
            if not isinstance(item["prompt_sha256"], str) or not re.fullmatch("[0-9a-f]{64}", item["prompt_sha256"]):
                raise ValueError("quality token-ID fingerprint is missing")
            if type(item["passed"]) is not bool or item["passed"] != (normalize(item["actual"]) == normalize(item["expected"])):
                raise ValueError("saved quality item score does not match its answer")
        count, passed = len(items), sum(item["passed"] for item in items)
        if type(quality["probe_count"]) is not int or quality["probe_count"] != count:
            raise ValueError("quality probe count is inconsistent")
        if type(quality["passed"]) is not int or quality["passed"] != passed:
            raise ValueError("quality passed count is inconsistent")
        if type(quality["score"]) not in (int, float) or not math.isfinite(quality["score"]) or quality["score"] != passed / count:
            raise ValueError("quality score is inconsistent")
        generation = quality["generation"]
        if set(generation) != {"seed", "n_predict", "context_size", "temperature", "ignore_eos", "prompt_format", "stop"}:
            raise ValueError("quality generation provenance is incomplete")
        if generation["temperature"] != 0 or generation["ignore_eos"] is not False or generation["prompt_format"] != "raw_completion":
            raise ValueError("quality generation protocol is unsupported")
        if generation["stop"] != ["\n"]:
            raise ValueError("quality one-line completion stop protocol is unsupported")
        if type(generation["seed"]) is not int or not 0 <= generation["seed"] <= 2147483647:
            raise ValueError("quality seed is invalid")
        if type(generation["n_predict"]) is not int or generation["n_predict"] != OUTPUT_TOKENS:
            raise ValueError("quality output budget is unsupported")
        if type(generation["context_size"]) is not int or generation["context_size"] < 128:
            raise ValueError("quality context size is invalid")
        if any(item["prompt_tokens"] + OUTPUT_TOKENS + 8 > generation["context_size"] for item in items):
            raise ValueError("quality prompt does not fit its recorded context")
        return quality
    except (KeyError, TypeError) as exc:
        raise ValueError("quality provenance is incomplete") from exc


def _select(session, attempt_id):
    if not isinstance(session, dict) or session.get("synthetic") is not False:
        raise ValueError("quality comparison requires explicitly nonsynthetic sessions")
    attempts = session.get("attempts", [])
    if not isinstance(attempts, list):
        raise ValueError("session attempts must be an array")
    eligible = [a for a in attempts if isinstance(a, dict) and a.get("quality") is not None]
    if attempt_id is not None:
        matches = [a for a in eligible if a.get("attempt_id") == attempt_id]
        if len(matches) != 1:
            raise ValueError(f"attempt {attempt_id!r} not found uniquely with quality results")
        selected = matches[0]
    else:
        success = [a for a in eligible if a.get("status") == "SUCCESS"]
        if len(success) != 1:
            raise ValueError("select an attempt explicitly: expected exactly one successful quality attempt")
        selected = success[0]
    if selected.get("status") != "SUCCESS" or selected.get("synthetic") is not False or selected.get("cleanup_confirmed") is not True:
        raise ValueError("selected quality attempt must be successful, nonsynthetic, and cleaned up")
    quality = _validated_quality(selected)
    # Repeats of one deployment must not be cherry-picked if their probe results disagree.
    for other in eligible:
        if (other is selected or other.get("status") != "SUCCESS"
                or other.get("case_name") != selected.get("case_name")
                or other.get("requested") != selected.get("requested")
                or other.get("runtime", {}).get("effective") != selected.get("runtime", {}).get("effective")):
            continue
        other_quality = _validated_quality(other)
        if other_quality["suite_sha256"] != quality["suite_sha256"] or other_quality["generation"] != quality["generation"]:
            raise ValueError("repeated quality measurements have mismatched protocols")
        if [(i["id"], i["passed"]) for i in other_quality["items"]] != [(i["id"], i["passed"]) for i in quality["items"]]:
            raise ValueError("repeated quality measurements disagree; inspect instability before comparison")
    return selected, quality


def compare_quality(reference_session: dict, candidate_session: dict, *,
                    reference_attempt_id: str | None = None, candidate_attempt_id: str | None = None) -> dict:
    """Compare selected paired probes; reject incompatible or incomplete evidence.

    Select attempts explicitly when a session has multiple successful probe runs.
    Different weight artifacts, GPU placement, and KV types are allowed and listed.
    This function reports percentage-point probe score change, never quality loss.
    """
    reference, rq = _select(reference_session, reference_attempt_id)
    candidate, cq = _select(candidate_session, candidate_attempt_id)
    try:
        rc, cc = reference_session["config"], candidate_session["config"]
        if not isinstance(rc["model_id"], str) or not rc["model_id"].strip() or rc["model_id"] != cc["model_id"]:
            raise ValueError("quality comparison requires the same user-declared model_id")
        if rc["backend"] != "llama_cpp" or cc["backend"] != "llama_cpp":
            raise ValueError("quality comparison requires llama_cpp real runs")
        if rc["seed"] != cc["seed"] or rq["generation"]["seed"] != rc["seed"] or cq["generation"]["seed"] != cc["seed"]:
            raise ValueError("quality seed differs or is inconsistent")
        if rq["suite_sha256"] != cq["suite_sha256"] or rq["generation"] != cq["generation"]:
            raise ValueError("quality suite or exact generation/context settings differ")
        if [i["prompt_tokens"] for i in rq["items"]] != [i["prompt_tokens"] for i in cq["items"]]:
            raise ValueError("quality prompt token counts differ; tokenizer equivalence is unverified")
        if [i["prompt_sha256"] for i in rq["items"]] != [i["prompt_sha256"] for i in cq["items"]]:
            raise ValueError("quality prompt token IDs differ; tokenizer equivalence is unverified")
        rp, cp = reference_session["provenance"], candidate_session["provenance"]
        for provenance in (rp, cp):
            for key in ("model_sha256", "server_sha256"):
                if not isinstance(provenance[key], str) or not re.fullmatch("[0-9a-f]{64}", provenance[key]):
                    raise ValueError("quality comparison needs model and runtime hashes")
        if rp["server_sha256"] != cp["server_sha256"]:
            raise ValueError("runtime binaries differ")
        for provenance in (rp, cp):
            libraries = provenance["runtime_library_sha256"]
            if not isinstance(libraries, dict) or any(not isinstance(v, str) or not re.fullmatch("[0-9a-f]{64}", v)
                                                      for v in libraries.values()):
                raise ValueError("runtime library hashes are invalid")
        if rp["runtime_library_sha256"] != cp["runtime_library_sha256"]:
            raise ValueError("runtime library binaries differ")
        rr, cr = reference["runtime"], candidate["runtime"]
        if not isinstance(rr["runtime_version"], str) or not rr["runtime_version"].strip() or rr["runtime_version"] != cr["runtime_version"]:
            raise ValueError("runtime versions differ or are unknown")
        fixed = ("context_size", "prompt_tokens", "output_tokens", "threads", "batch_size", "ubatch_size", "flash_attention")
        for key in fixed:
            if reference["requested"][key] != candidate["requested"][key]:
                raise ValueError(f"comparable workload setting differs: {key}")
        reffective, ceffective = rr["effective"], cr["effective"]
        for attempt, quality in ((reference, rq), (candidate, cq)):
            effective = attempt["runtime"]["effective"]
            if effective["context_size"] != quality["generation"]["context_size"]:
                raise ValueError("effective context and quality context differ")
            if effective["context_size"] != attempt["requested"]["context_size"]:
                raise ValueError("effective context and requested context differ")
            for key in ("gpu_layers_loaded", "gpu_layers_total"):
                if type(effective[key]) is not int or effective[key] < 0:
                    raise ValueError("effective GPU placement is unknown")
            if type(effective["cpu_offload"]) is not bool:
                raise ValueError("effective CPU offload is unknown")
            if effective["gpu_layers_loaded"] > effective["gpu_layers_total"]:
                raise ValueError("effective GPU layer counts are inconsistent")
        differences = []
        for label, left, right in [
            ("quantization", rc["quantization"], cc["quantization"]),
            ("model_sha256", rp["model_sha256"], cp["model_sha256"]),
            *[("requested." + key, reference["requested"][key], candidate["requested"][key])
              for key in ("gpu_layers", "cache_type_k", "cache_type_v")],
            *[("effective." + key, reffective[key], ceffective[key])
              for key in ("gpu_layers_loaded", "gpu_layers_total", "cpu_offload")],
        ]:
            if left != right:
                differences.append({"field": label, "reference": left, "candidate": right})
    except (KeyError, TypeError) as exc:
        raise ValueError("comparison provenance is incomplete") from exc

    paired = [{"id": ri["id"], "reference_passed": ri["passed"], "candidate_passed": ci["passed"],
               "reference_actual": ri["actual"], "candidate_actual": ci["actual"]}
              for ri, ci in zip(rq["items"], cq["items"])]
    return {
        "reference_attempt_id": reference["attempt_id"], "candidate_attempt_id": candidate["attempt_id"],
        "suite_id": rq["suite_id"], "suite_sha256": rq["suite_sha256"], "probe_count": rq["probe_count"],
        "reference_score": rq["score"], "candidate_score": cq["score"],
        "probe_score_delta_percentage_points": 100 * (cq["passed"] - rq["passed"]) / rq["probe_count"],
        "regressions": sum(i["reference_passed"] and not i["candidate_passed"] for i in paired),
        "improvements": sum(not i["reference_passed"] and i["candidate_passed"] for i in paired),
        "items": paired, "configuration_differences": differences, "limitation": LIMITATION,
    }

