"""Quality tests use deterministic fake answers, never real performance evidence."""

import copy
import json

import pytest

from prismbench.config import Case
from prismbench.quality import compare_quality, load_suite, normalize, run_quality


class ProbeBackend:
    def __init__(self, suite, *, wrong=(), token_count=16):
        self.answers = {p["prompt"]: "wrong" if p["id"] in wrong else p["expected"] for p in suite["probes"]}
        self.token_count = token_count
        self.calls = []

    def tokenize(self, text):
        return list(range(self.token_count))

    def erase(self):
        self.calls.append("erase")

    def probe(self, prompt, n_predict, seed, timeout_s):
        self.calls.append((prompt, n_predict, seed, timeout_s))
        return self.answers[prompt]


def make_session(*, wrong=()):
    suite = load_suite()
    quality = run_quality(ProbeBackend(suite, wrong=wrong), suite, 42, 10, context_size=2048)
    case = Case()
    from dataclasses import asdict
    return {
        "synthetic": False,
        "config": {"backend": "llama_cpp", "model_id": "test/base@revision", "seed": 42, "quantization": "F16"},
        "provenance": {"model_sha256": "a" * 64, "server_sha256": "b" * 64, "runtime_library_sha256": {}},
        "attempts": [{
            "attempt_id": "one", "case_name": "default", "status": "SUCCESS", "synthetic": False,
            "cleanup_confirmed": True, "requested": asdict(case), "quality": quality,
            "runtime": {"runtime_version": "test-version", "effective": {
                "context_size": 2048, "gpu_layers_loaded": 33, "gpu_layers_total": 33, "cpu_offload": False,
            }},
        }],
    }


def test_bundled_suite_is_small_and_strict():
    suite = load_suite()
    assert 4 <= len(suite["probes"]) <= 12
    assert len({p["id"] for p in suite["probes"]}) == len(suite["probes"])


def test_normalization_is_exact_after_unicode_and_whitespace():
    assert normalize(" ４２\n") == "42"
    assert normalize("lantern.") != normalize("lantern")
    assert normalize("Lantern") != normalize("lantern")
    assert normalize("a\n\t b") == "a b"


def test_scores_and_cache_erasure_are_per_probe():
    suite = load_suite()
    backend = ProbeBackend(suite, wrong=(suite["probes"][0]["id"],))
    result = run_quality(backend, suite, 17, 12, context_size=128)
    assert result["probe_count"] == 8
    assert result["passed"] == 7
    assert result["score"] == 7 / 8
    assert result["generation"]["prompt_format"] == "raw_completion"
    assert "not general model quality" in result["limitation"]
    assert len(backend.calls) == 16
    for idx in range(0, len(backend.calls), 2):
        assert backend.calls[idx] == "erase"
        assert backend.calls[idx + 1][1:] == (64, 17, 12)


def test_suite_hash_ignores_json_spacing(tmp_path):
    suite = load_suite()
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite, indent=7), encoding="utf-8")
    left = run_quality(ProbeBackend(suite), suite, 42, 10)
    right = run_quality(ProbeBackend(suite), load_suite(path), 42, 10)
    assert left["suite_sha256"] == right["suite_sha256"]


@pytest.mark.parametrize("change", [
    lambda s: s.update(extra=True),
    lambda s: s.update(version=1),
    lambda s: s.update(probes=[]),
    lambda s: s["probes"].append(s["probes"][0]),
    lambda s: s["probes"][0].update(expected=["42"]),
    lambda s: s["probes"][0].update(prompt=" " * 3),
    lambda s: s["probes"][0].update(prompt="x" * 8193),
    lambda s: s["probes"][0].update(extra="ignored?"),
])
def test_invalid_suites_are_rejected(tmp_path, change):
    suite = load_suite()
    change(suite)
    path = tmp_path / "suite.json"
    path.write_text(json.dumps(suite), encoding="utf-8")
    with pytest.raises(ValueError):
        load_suite(path)


def test_duplicate_json_keys_are_rejected(tmp_path):
    path = tmp_path / "suite.json"
    path.write_text('{"id":"x","id":"y","version":"1","probes":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON"):
        load_suite(path)


def test_context_failure_happens_before_any_generation():
    suite = load_suite()
    backend = ProbeBackend(suite, token_count=57)
    with pytest.raises(ValueError, match="does not fit"):
        run_quality(backend, suite, 42, 10, context_size=128)
    assert backend.calls == []


def test_backend_error_is_not_converted_to_partial_quality_success():
    suite = load_suite()
    backend = ProbeBackend(suite)
    def fail(*_):
        raise TimeoutError("probe timed out")
    backend.probe = fail
    with pytest.raises(TimeoutError, match="probe timed out"):
        run_quality(backend, suite, 42, 10)


def test_pairwise_delta_is_percentage_points_and_lists_changed_configuration():
    reference = make_session()
    candidate = make_session(wrong=("copy_word",))
    candidate["config"]["quantization"] = "Q4_K_M"
    candidate["provenance"]["model_sha256"] = "c" * 64
    attempt = candidate["attempts"][0]
    attempt["requested"]["gpu_layers"] = 20
    attempt["requested"]["cache_type_k"] = "q8_0"
    attempt["runtime"]["effective"].update(gpu_layers_loaded=20, cpu_offload=True)
    result = compare_quality(reference, candidate)
    assert result["probe_score_delta_percentage_points"] == -12.5
    assert result["regressions"] == 1
    assert result["improvements"] == 0
    assert "quality_loss" not in result
    assert {d["field"] for d in result["configuration_differences"]} >= {
        "quantization", "model_sha256", "requested.gpu_layers", "requested.cache_type_k", "effective.cpu_offload",
    }


@pytest.mark.parametrize("change,match", [
    (lambda s: s.update(synthetic=True), "nonsynthetic"),
    (lambda s: s["attempts"][0].update(synthetic=True), "nonsynthetic"),
    (lambda s: s["attempts"][0].update(cleanup_confirmed=False), "cleaned up"),
    (lambda s: s["attempts"][0].update(status="OOM"), "successful"),
    (lambda s: s["config"].update(model_id="another-model"), "model_id"),
    (lambda s: s["config"].update(seed=99), "seed"),
    (lambda s: s["provenance"].update(model_sha256=None), "hashes"),
    (lambda s: s["provenance"].update(server_sha256="d" * 64), "binaries"),
    (lambda s: s["provenance"].update(runtime_library_sha256={"llama.dll": "d" * 64}), "library binaries"),
    (lambda s: s["attempts"][0]["runtime"].update(runtime_version="different"), "versions"),
    (lambda s: s["attempts"][0]["runtime"]["effective"].update(gpu_layers_loaded=None), "unknown"),
    (lambda s: s["attempts"][0]["runtime"]["effective"].update(context_size=4096), "context"),
    (lambda s: s["attempts"][0]["requested"].update(output_tokens=64), "output_tokens"),
    (lambda s: s["attempts"][0]["quality"].update(score=0.99), "score"),
    (lambda s: s["attempts"][0]["quality"].update(suite_sha256="e" * 64), "hash"),
    (lambda s: s["attempts"][0]["quality"]["items"][0].update(passed=False), "score"),
    (lambda s: s["attempts"][0]["quality"]["items"][0].update(prompt_tokens=17), "token counts"),
    (lambda s: s["attempts"][0]["quality"]["items"][0].update(prompt_sha256="c" * 64), "token IDs"),
])
def test_incompatible_or_corrupt_comparisons_are_rejected(change, match):
    reference, candidate = make_session(), make_session()
    change(candidate)
    with pytest.raises(ValueError, match=match):
        compare_quality(reference, candidate)


def test_selection_required_for_repeats_and_explicit_selection_works():
    reference, candidate = make_session(), make_session()
    repeat = copy.deepcopy(reference["attempts"][0])
    repeat["attempt_id"] = "two"
    reference["attempts"].append(repeat)
    with pytest.raises(ValueError, match="select an attempt"):
        compare_quality(reference, candidate)
    result = compare_quality(reference, candidate, reference_attempt_id="two")
    assert result["reference_attempt_id"] == "two"


def test_unstable_repeated_scores_cannot_be_cherry_picked():
    reference, candidate = make_session(), make_session()
    repeat = make_session(wrong=("copy_word",))["attempts"][0]
    repeat["attempt_id"] = "two"
    reference["attempts"].append(repeat)
    with pytest.raises(ValueError, match="disagree"):
        compare_quality(reference, candidate, reference_attempt_id="one")


def test_suite_change_is_not_quantization_change():
    reference, candidate = make_session(), make_session()
    suite = load_suite()
    suite["version"] = "2"
    candidate["attempts"][0]["quality"] = run_quality(ProbeBackend(suite), suite, 42, 10)
    with pytest.raises(ValueError, match="suite"):
        compare_quality(reference, candidate)

