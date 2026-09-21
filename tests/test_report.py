"""Reports must not erase failures, mix workloads or turn demo fixtures into advice."""

import copy
import csv
import json
from dataclasses import asdict

import pytest
from jsonschema import ValidationError

from prismbench.config import Case, Config
from prismbench.report import METRICS, validate_result, write_reports


def attempt(name="case", repetition=1, index=0, parent=None, status="SUCCESS", **settings):
    case = Case(name=name, **settings)
    metrics = dict.fromkeys(METRICS)
    if status == "SUCCESS":
        metrics.update(load_time_s=0.1, ttft_s=0.05, total_latency_s=3.225,
                       prompt_tokens_per_second=1000.0, generation_tokens_per_second=40.0,
                       prompt_tokens=case.prompt_tokens, generated_tokens=case.output_tokens,
                       cache_tokens=0)
    ident = f"{name}-r{repetition}-a{index}"
    return {"attempt_id": ident, "case_name": name, "repetition": repetition,
            "attempt_index": index, "parent_attempt_id": parent, "status": status,
            "error": None if status == "SUCCESS" else "example failure", "synthetic": True,
            "requested": asdict(case),
            "runtime": {"effective": {"context_size": case.context_size}, "prompt_sha256": "c" * 64}
            if status == "SUCCESS" else {},
            "metrics": metrics, "quality": None,
            "cleanup_confirmed": status != "CLEANUP_FAILED", "evidence_dir": f"attempts/{ident}",
            "warnings": []}


def session(*attempts, synthetic=True):
    data = {"schema_version": "1.0", "tool_version": "0.1.0a1", "session_id": "example",
            "created_at": "2026-09-21T12:00:00+00:00", "synthetic": synthetic,
            "config": Config().to_dict(), "hardware": {},
            "provenance": {"model_sha256": None, "model_size_bytes": None, "server_sha256": None},
            "attempts": list(attempts), "warnings": []}
    for item in data["attempts"]:
        item["synthetic"] = synthetic
    if not synthetic:
        data["config"].update(backend="llama_cpp", model_id="test-model", quantization="Q4_K_M")
        data["provenance"].update(model_sha256="a" * 64, server_sha256="b" * 64,
                                  model_size_bytes=1000)
    return data


def test_exports_preserve_oom_and_changed_fallback(tmp_path):
    failed = attempt(status="OOM")
    fallback = attempt(index=1, parent=failed["attempt_id"], gpu_layers=16,
                       context_size=1024, prompt_tokens=768)
    data = session(failed, fallback)
    write_reports(data, tmp_path)
    assert json.loads((tmp_path / "results.json").read_text("utf-8")) == data
    with (tmp_path / "results.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert [row["status"] for row in rows] == ["OOM", "SUCCESS"]
    assert rows[0]["generation_tokens_per_second"] == ""
    assert [row["context_size"] for row in rows] == ["2048", "1024"]
    report = (tmp_path / "report.md").read_text("utf-8")
    assert "SYNTHETIC DEMO" in report
    assert "No hardware recommendation" in report
    assert "| C1 |" in report and "| C2 |" in report
    assert "[case-r1-a0](./attempts/case-r1-a0)" in report
    assert "OOM" in report
    assert "Largest successfully" not in report


@pytest.mark.parametrize("status", ["OOM", "TIMEOUT", "ERROR", "INVALID_WORKLOAD",
                                     "CLEANUP_FAILED", "CANCELLED"])
def test_all_failure_statuses_are_exportable(tmp_path, status):
    write_reports(session(attempt(status=status)), tmp_path)
    assert status in (tmp_path / "report.md").read_text("utf-8")


@pytest.mark.parametrize("metric,value", [("ttft_s", None), ("ttft_s", 0),
                                            ("generation_tokens_per_second", -1),
                                            ("cache_tokens", 1), ("prompt_tokens", True)])
def test_success_cannot_claim_missing_or_invalid_metrics(metric, value):
    data = session(attempt())
    data["attempts"][0]["metrics"][metric] = value
    with pytest.raises(ValidationError):
        validate_result(data)


@pytest.mark.parametrize("field,value", [("error", "oops"), ("cleanup_confirmed", False),
                                           ("status", "success")])
def test_success_status_contract(field, value):
    data = session(attempt())
    data["attempts"][0][field] = value
    with pytest.raises(ValidationError):
        validate_result(data)


def test_relational_workload_and_identity_checks():
    valid = session(attempt())
    mutations = [
        lambda d: d["attempts"][0]["metrics"].update(generated_tokens=127),
        lambda d: d["attempts"][0]["metrics"].update(ttft_s=4),
        lambda d: d["attempts"][0]["requested"].update(context_size=128),
        lambda d: d["attempts"][0]["requested"].update(ubatch_size=513),
        lambda d: d["attempts"][0].update(synthetic=False),
        lambda d: d["attempts"].append(copy.deepcopy(d["attempts"][0])),
        lambda d: d["attempts"][0].update(parent_attempt_id="missing", attempt_index=1),
        lambda d: d["attempts"][0].update(attempt_index=1),
        lambda d: d["attempts"][0].update(repetition=4),
        lambda d: d["attempts"][0]["runtime"]["effective"].update(context_size=1024),
    ]
    for mutate in mutations:
        data = copy.deepcopy(valid)
        mutate(data)
        with pytest.raises(ValueError):
            validate_result(data)


def test_schema_rejects_unknown_required_shape_and_nonfinite(tmp_path):
    data = session(attempt())
    del data["attempts"][0]["metrics"]["peak_vram_mib"]
    with pytest.raises(ValidationError):
        write_reports(data, tmp_path)
    assert not list(tmp_path.iterdir())
    data = session(attempt())
    data["hardware"]["telemetry"] = float("nan")
    with pytest.raises(ValueError):
        validate_result(data)
    data = session(attempt(), synthetic=False)
    data["provenance"]["model_sha256"] = None
    with pytest.raises(ValidationError):
        validate_result(data)


def test_ranking_requires_matched_workload_and_complete_repeats(tmp_path):
    attempts = [attempt("fast", repetition=i, gpu_layers=99) for i in range(1, 4)]
    attempts += [attempt("short", repetition=i, gpu_layers=16,
                         context_size=1024, prompt_tokens=768) for i in range(1, 4)]
    data = session(*attempts, synthetic=False)
    write_reports(data, tmp_path)
    report = (tmp_path / "report.md").read_text("utf-8")
    assert "No recommendation" in report
    assert "tested allocated context: 2048 tokens" in report
    assert "not a discovered maximum" in report
    data["attempts"] += [attempt("partial", repetition=1, gpu_layers=0)]
    data["attempts"][-1]["synthetic"] = False
    write_reports(data, tmp_path)
    assert "No recommendation" in (tmp_path / "report.md").read_text("utf-8")


def test_matching_real_configs_are_compared_without_value_claim(tmp_path):
    data = session(*(attempt(name, repetition=i, gpu_layers=layers)
                     for name, layers in (("gpu", 99), ("offload", 16))
                     for i in range(1, 4)), synthetic=False)
    for item in data["attempts"][3:]:
        item["metrics"]["generation_tokens_per_second"] = 20
    write_reports(data, tmp_path)
    report = (tmp_path / "report.md").read_text("utf-8")
    assert "C1: 40.00 tok/s → C2: 20.00 tok/s" in report
    assert "not a quality or value recommendation" in report
    assert "quality loss is unmeasured" in report


def test_different_prompt_hashes_are_not_ranked(tmp_path):
    data = session(*(attempt(name, repetition=i, gpu_layers=layers)
                     for name, layers in (("gpu", 99), ("offload", 16))
                     for i in range(1, 4)), synthetic=False)
    for item in data["attempts"][3:]:
        item["runtime"]["prompt_sha256"] = "d" * 64
    write_reports(data, tmp_path)
    assert "No recommendation" in (tmp_path / "report.md").read_text("utf-8")


def test_effective_placement_changes_do_not_mix_repeat_means(tmp_path):
    data = session(*(attempt(repetition=i) for i in range(1, 4)), synthetic=False)
    data["attempts"][2]["runtime"]["effective"]["gpu_layers_loaded"] = 0
    write_reports(data, tmp_path)
    report = (tmp_path / "report.md").read_text("utf-8")
    assert "| C1 |" in report and "| C2 |" in report
    assert "No recommendation" in report


@pytest.mark.parametrize("parent_status", ["SUCCESS", "TIMEOUT", "ERROR", "CLEANUP_FAILED"])
def test_fallback_requires_cleaned_oom_parent(parent_status):
    parent = attempt(status=parent_status)
    child = attempt(index=1, parent=parent["attempt_id"])
    with pytest.raises(ValueError, match="parent must be an OOM"):
        validate_result(session(parent, child))


def test_fallback_indices_must_be_consecutive():
    parent = attempt(status="OOM")
    child = attempt(index=2, parent=parent["attempt_id"])
    with pytest.raises(ValueError, match="consecutive"):
        validate_result(session(parent, child))


def test_reexport_links_original_evidence_without_copying(tmp_path):
    original = tmp_path / "original"
    evidence = original / "attempts" / "case-r1-a0"
    evidence.mkdir(parents=True)
    (evidence / "raw.log").write_text("original evidence", encoding="utf-8")
    destination = tmp_path / "export"
    write_reports(session(attempt()), destination, evidence_root=original)
    report = (destination / "report.md").read_text("utf-8")
    assert "[case-r1-a0](../original/attempts/case-r1-a0)" in report
    assert "[original run directory](../original)" in report
    assert not (destination / "attempts").exists()
    assert (evidence / "raw.log").read_text("utf-8") == "original evidence"


@pytest.mark.parametrize("path", ["../../private", "/absolute", "C:\\private", "//remote/share"])
def test_evidence_paths_stay_relative(path):
    data = session(attempt())
    data["attempts"][0]["evidence_dir"] = path
    with pytest.raises(ValueError, match="relative path"):
        validate_result(data)


@pytest.mark.parametrize("dangerous", ["=HYPERLINK(\"https://example.com\")", " +1", "-1",
                                        "@SUM(1)", "\t=1", "\rtext", "\ntext"])
def test_csv_text_cannot_be_a_spreadsheet_formula(tmp_path, dangerous):
    data = session(attempt(status="ERROR"))
    data["config"]["model_id"] = dangerous
    data["attempts"][0]["error"] = dangerous
    write_reports(data, tmp_path)
    with (tmp_path / "results.csv").open(encoding="utf-8-sig", newline="") as stream:
        row = next(csv.DictReader(stream))
    assert row["model_id"] == "'" + dangerous
    assert row["error"] == "'" + dangerous
    assert json.loads((tmp_path / "results.json").read_text("utf-8"))["config"]["model_id"] == dangerous


def test_markdown_escapes_user_text_and_keeps_null_resources(tmp_path):
    data = session(attempt(status="ERROR"))
    data["config"]["model_id"] = "bad|column\n<script>"
    data["attempts"][0]["error"] = "[misleading](javascript:alert(1))"
    write_reports(data, tmp_path)
    report = (tmp_path / "report.md").read_text("utf-8")
    assert "bad\\|column \\<script\\>" in report
    assert "\\[misleading\\]" in report
    assert "| — | — | — |" in report


def test_empty_session_can_report_pre_attempt_state(tmp_path):
    write_reports(session(), tmp_path)
    assert "no attempts recorded" in (tmp_path / "report.md").read_text("utf-8")
