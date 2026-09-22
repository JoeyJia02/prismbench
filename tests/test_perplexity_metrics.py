"""Checks for completeness, scored-token accounting, and paired uncertainty."""

import importlib.util
import math
from copy import deepcopy
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "perplexity_metrics", Path(__file__).parents[1] / "experiments" / "perplexity_metrics.py")
metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metrics)


def raw_log(chunk_means=None, *, context=2048, batch=512, standard_error=0.02):
    chunk_means = chunk_means if chunk_means is not None else [2 + i / 20 for i in range(32)]
    lines = ["ggml_cuda_init: found 1 CUDA devices:",
             "perplexity: tokenizing the input ..",
             f"perplexity: calculating perplexity over {len(chunk_means)} chunks, "
             f"n_ctx={context}, batch_size={batch}, n_seq=1",
             "perplexity: 1.00 seconds per pass - ETA 0.53 minutes"]
    total = 0
    for i, value in enumerate(chunk_means):
        total += value
        mean = total / (i + 1)
        lines.append(f"{i * context:8d}  {math.exp(mean):.4f}  "
                     f"{mean:4f}  {standard_error:4f}")
    lines += ["", f"Final estimate: PPL = {math.exp(mean):.4f} "
              f"+/- {standard_error * math.exp(mean):.5f}",
              "llama_perf_context_print:        load time = 300.00 ms"]
    return "\n".join(lines) + "\n"


def parse(text=None, **kwargs):
    return metrics.parse_perplexity(raw_log() if text is None else text,
                                    context_size=kwargs.get("context", 2048),
                                    chunks=kwargs.get("chunks", 32),
                                    batch_size=kwargs.get("batch", 512))


def test_complete_upstream_style_log_and_exact_target_accounting():
    result = parse(raw_log().replace("\n", "\r\n"))
    assert result["protocol"] == metrics.PROTOCOL
    assert result["chunks"] == 32
    assert result["targets_per_chunk"] == 1023
    assert result["total_scored_tokens"] == 32736
    assert result["chunk_mean_nll"] == pytest.approx([2 + i / 20 for i in range(32)])
    assert result["mean_nll"] == pytest.approx(2.775)
    assert result["perplexity"] == 16.0386
    assert len(result["cumulative"]) == 32
    assert "rounding" in result["rounding_caveat"]


def test_odd_context_uses_actual_pinned_target_formula():
    result = parse(raw_log(context=2049), context=2049)
    assert result["targets_per_chunk"] == 1024


@pytest.mark.parametrize("change", [
    lambda s: s.replace("over 32 chunks", "over 31 chunks"),
    lambda s: s.replace("n_ctx=2048", "n_ctx=4096"),
    lambda s: s.replace("batch_size=512", "batch_size=1024"),
    lambda s: s.replace("n_seq=1", "n_seq=2"),
    lambda s: s.replace("perplexity: calculating", "perplexity_v2: calculating"),
    lambda s: s[:s.index("Final estimate")],
    lambda s: s.replace("   63488", "   65536"),
    lambda s: "\n".join(line for line in s.splitlines() if not line.lstrip().startswith("4096 ")),
    lambda s: s.replace("    2048", "       0"),
    lambda s: s.replace("       0  ", "       0  garbage "),
    lambda s: s.replace("       0  ", "      -1  "),
    lambda s: s + "Final estimate: PPL = 16.0386 +/- 0.32077\n",
    lambda s: s + "perplexity: calculating perplexity over 32 chunks, "
                  "n_ctx=2048, batch_size=512, n_seq=1\n",
    lambda s: s + "65536 16.0386 2.775000 0.020000\n",
])
def test_rejects_truncated_duplicate_or_mismatched_runs(change):
    with pytest.raises(ValueError):
        parse(change(raw_log()))


@pytest.mark.parametrize("replacement", ["nan", "inf", "-1.0000", "0.0000", "8.0000",
                                          "7.389", "7.38906000"])
def test_rejects_invalid_or_inconsistent_progress_perplexity(replacement):
    with pytest.raises(ValueError):
        parse(raw_log().replace("7.3891", replacement, 1))


@pytest.mark.parametrize("replacement", ["nan", "inf", "-2.000000", "2.500000", "2.000"])
def test_rejects_invalid_or_inconsistent_nll(replacement):
    with pytest.raises(ValueError):
        parse(raw_log().replace("2.000000", replacement, 1))


@pytest.mark.parametrize("replacement", ["nan", "inf", "-0.020000", "0.02"])
def test_rejects_invalid_standard_error(replacement):
    with pytest.raises(ValueError):
        parse(raw_log().replace("0.020000", replacement, 1))


def test_requires_matching_final_perplexity_and_standard_error():
    with pytest.raises(ValueError, match="Final PPL does not match"):
        parse(raw_log().replace("Final estimate: PPL = 16.0386", "Final estimate: PPL = 16.0387"))
    with pytest.raises(ValueError, match="standard error is inconsistent"):
        parse(raw_log().replace("+/- 0.32077", "+/- 1.32077"))


def test_rounding_intervals_accept_valid_ppl_not_equal_to_exp_rounded_nll():
    values = [5.00000149] * 32
    result = parse(raw_log(values))
    assert result["mean_nll"] == 5.000001
    assert result["perplexity"] == 148.4134
    assert round(math.exp(result["mean_nll"]), 4) != result["perplexity"]
    with pytest.raises(ValueError, match="printed precision"):
        parse(raw_log(values).replace("148.4134", "148.4135"))


def test_reconstructed_chunks_keep_tiny_rounding_negatives_without_biasing_sum():
    result = parse(raw_log([0.00000051, 0, 0, 0, 0, 0, 0, 0], standard_error=1e-8), chunks=8)
    assert result["chunk_mean_nll"][1] == -0.000001
    assert sum(result["chunk_mean_nll"]) == 0


def test_rejects_cumulative_values_implying_negative_chunk_nll():
    log = raw_log([4, -3, 4, 4, 4, 4, 4, 4])
    with pytest.raises(ValueError, match="negative chunk NLL"):
        parse(log, chunks=8)


def test_pairing_and_transform_for_identical_models():
    reference = parse()
    compared = metrics.compare_perplexity(reference, deepcopy(reference))
    assert compared["delta_mean_nll"] == 0
    assert compared["perplexity_ratio"] == 1
    assert compared["perplexity_change_percent"] == 0
    interval = compared["exploratory_block_bootstrap"]
    assert interval["delta_mean_nll_interval"] == [0, 0]
    assert interval["perplexity_ratio_interval"] == [1, 1]
    assert interval["blocks"] == 8
    assert interval["samples"] == 10000
    assert "not percentage loss" in compared["metric_interpretation"]


def test_paired_block_bootstrap_is_deterministic_and_respects_equal_block_deltas():
    reference = parse(raw_log([2] * 32))
    # Alternating within-block differences cancel. IID chunk resampling would not.
    candidate = parse(raw_log([2.1, 1.9, 2.1, 1.9] * 8))
    first = metrics.compare_perplexity(reference, candidate)
    second = metrics.compare_perplexity(reference, candidate)
    assert first == second
    assert first["paired_chunk_delta_mean_nll"] == pytest.approx([0.1, -0.1, 0.1, -0.1] * 8,
                                                                 abs=0.00002)
    assert first["exploratory_block_bootstrap"]["delta_mean_nll_interval"] == [0, 0]


def test_nonconstant_blocks_give_seeded_exploratory_interval_and_ppl_transform():
    reference = parse(raw_log([2] * 32))
    candidate = parse(raw_log([2 + (i // 4) / 100 for i in range(32)]))
    compared = metrics.compare_perplexity(reference, candidate, bootstrap_samples=1000)
    assert compared == metrics.compare_perplexity(reference, candidate, bootstrap_samples=1000)
    assert compared["delta_mean_nll"] == pytest.approx(0.035)
    assert compared["perplexity_ratio"] == pytest.approx(math.exp(0.035))
    assert compared["perplexity_change_percent"] == pytest.approx(math.expm1(0.035) * 100)
    boot = compared["exploratory_block_bootstrap"]
    lower, upper = boot["delta_mean_nll_interval"]
    assert 0 <= lower < 0.035 < upper <= 0.07
    assert boot["perplexity_ratio_interval"] == pytest.approx([math.exp(lower), math.exp(upper)])
    changed = metrics.compare_perplexity(reference, candidate, bootstrap_seed=10,
                                         bootstrap_samples=1000)
    assert boot["delta_mean_nll_interval"] != changed["exploratory_block_bootstrap"][
        "delta_mean_nll_interval"]


@pytest.mark.parametrize("chunks", [4, 6, 9])
def test_bootstrap_requires_complete_blocks_and_at_least_two(chunks):
    result = parse(raw_log([2] * chunks), chunks=chunks)
    with pytest.raises(ValueError, match="at least two complete blocks"):
        metrics.compare_perplexity(result, result)


@pytest.mark.parametrize("kwargs", [{"bootstrap_samples": 1}, {"bootstrap_seed": -1},
                                    {"block_chunks": 0}, {"block_chunks": True}])
def test_bootstrap_rejects_invalid_options(kwargs):
    with pytest.raises(ValueError):
        metrics.compare_perplexity(parse(), parse(), **kwargs)


@pytest.mark.parametrize("change", [{"protocol": "other-build"}, {"total_scored_tokens": 32768},
                                    {"chunk_mean_nll": [2]}, {"mean_nll": 3}, {"n_seq": 2},
                                    {"perplexity": float("nan")}])
def test_comparison_rejects_inconsistent_parsed_records(change):
    candidate = parse()
    candidate.update(change)
    with pytest.raises(ValueError):
        metrics.compare_perplexity(parse(), candidate)


def test_comparison_rejects_individually_valid_but_different_protocols():
    with pytest.raises(ValueError, match="protocols/counts differ"):
        metrics.compare_perplexity(parse(), parse(raw_log(batch=256), batch=256))


@pytest.mark.parametrize("kwargs", [{"context": 2}, {"context": True}, {"chunks": 0},
                                    {"batch": 4096}, {"batch": 0}])
def test_parser_rejects_invalid_requested_protocol(kwargs):
    with pytest.raises(ValueError):
        parse(**kwargs)
