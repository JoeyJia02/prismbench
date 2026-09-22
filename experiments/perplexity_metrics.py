"""Parse the pinned llama.cpp perplexity log and compare paired corpus chunks.

This is an experiment helper, not a general parser for arbitrary llama.cpp builds.
The caller must separately verify identical corpus bytes, tokenizer, and runtime
settings. A log alone does not establish those identities.
"""

import math
import random
import re
from statistics import fmean

PROTOCOL = "llama.cpp-b10964-non-strided-ppl-output-type-1"
_HEADER = re.compile(
    r"perplexity: calculating perplexity over (\d+) chunks, "
    r"n_ctx=(\d+), batch_size=(\d+), n_seq=(\d+)"
)
_FINAL = re.compile(r"Final estimate: PPL = (\S+) \+/- (\S+)")
_NLL_HALF_UNIT = 0.0000005
_PPL_HALF_UNIT = 0.00005
_FINAL_ERROR_HALF_UNIT = 0.000005
ROUNDING_CAVEAT = (
    "Cumulative mean NLL is printed to six decimals. Reconstructed chunk means "
    "amplify this rounding: the absolute bound for zero-based chunk i is "
    "(2*i+1)*0.0000005 nats/token. Paired chunk differences have twice that bound; "
    "the overall paired mean has a 0.000001 nats/token rounding bound. "
    "Bootstrap intervals do not incorporate this rounding uncertainty."
)


def _integer(value, name, *, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def _printed_number(text, places, name, *, positive=False):
    if not re.fullmatch(rf"-?\d+\.\d{{{places}}}", text):
        raise ValueError(f"{name} must have exactly {places} decimal places")
    value = float(text)
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return value


def _ppl_interval(nll):
    try:
        return math.exp(nll - _NLL_HALF_UNIT), math.exp(nll + _NLL_HALF_UNIT)
    except OverflowError as exc:
        raise ValueError("NLL is too large for a finite perplexity") from exc


def _overlap(left, right):
    # The small margin covers floating-point arithmetic, not extra printed digits.
    return max(left[0], right[0]) <= min(left[1], right[1]) + 1e-12


def _check_ppl(ppl, nll):
    interval = _ppl_interval(nll)
    if not _overlap(interval, (ppl - _PPL_HALF_UNIT, ppl + _PPL_HALF_UNIT)):
        raise ValueError("PPL and mean NLL disagree beyond their printed precision")
    return interval


def parse_perplexity(text, *, context_size, chunks, batch_size):
    """Require one complete type-1 evaluation with the requested dimensions.

    For this pinned non-strided implementation the scored next-token targets are
    ``context_size - context_size // 2 - 1`` per chunk, not half the context.
    The upstream final PPL standard error is retained as a diagnostic only. It is
    not used as a paired uncertainty estimate or an IID-token confidence interval.
    """
    _integer(context_size, "context_size", minimum=3)
    _integer(chunks, "chunks")
    _integer(batch_size, "batch_size")
    if batch_size > context_size:
        raise ValueError("This parser requires batch_size <= context_size and n_seq=1")
    headers = list(_HEADER.finditer(text))
    finals = list(_FINAL.finditer(text))
    if len(headers) != 1 or len(finals) != 1:
        raise ValueError("Expected exactly one perplexity header and final estimate")
    header, final = headers[0], finals[0]
    dimensions = tuple(map(int, header.groups()))
    if dimensions != (chunks, context_size, batch_size, 1):
        raise ValueError("Perplexity header differs from the requested protocol")
    if final.start() <= header.end():
        raise ValueError("Final estimate must follow the perplexity header")

    cumulative = []
    for line in text[header.end():final.start()].splitlines():
        if not re.match(r"\s*[+-]?\d+(?:\s|$)", line):
            continue
        columns = line.split()
        if len(columns) != 4 or not columns[0].isdigit():
            raise ValueError("Malformed perplexity progress row")
        offset = int(columns[0])
        if offset != len(cumulative) * context_size:
            raise ValueError("Progress row offsets are missing, duplicated, or out of order")
        ppl = _printed_number(columns[1], 4, "row PPL", positive=True)
        nll = _printed_number(columns[2], 6, "row mean NLL")
        standard_error = _printed_number(columns[3], 6, "row NLL standard error")
        _check_ppl(ppl, nll)
        cumulative.append({"offset": offset, "ppl": ppl, "mean_nll": nll,
                           "nll_standard_error": standard_error})
    if len(cumulative) != chunks:
        raise ValueError(f"Expected {chunks} progress rows, found {len(cumulative)}")
    outside = text[:header.start()] + "\n" + text[final.end():]
    if re.search(r"(?m)^\s*[+-]?\d+\s+\S+\s+\S+\s+\S+\s*$", outside):
        raise ValueError("Unexpected progress-like row outside the evaluation")

    final_ppl = _printed_number(final.group(1), 4, "final PPL", positive=True)
    final_error = _printed_number(final.group(2), 5, "final PPL standard error")
    last = cumulative[-1]
    if final_ppl != last["ppl"]:
        raise ValueError("Final PPL does not match the final progress row")
    ppl_interval = _check_ppl(final_ppl, last["mean_nll"])
    se = last["nll_standard_error"]
    implied_error = (max(0, se - _NLL_HALF_UNIT) * ppl_interval[0],
                     (se + _NLL_HALF_UNIT) * ppl_interval[1])
    if not _overlap(implied_error, (final_error - _FINAL_ERROR_HALF_UNIT,
                                   final_error + _FINAL_ERROR_HALF_UNIT)):
        raise ValueError("Final PPL standard error is inconsistent with the final NLL row")

    chunk_means = []
    previous_sum = 0.0
    for i, row in enumerate(cumulative):
        current_sum = (i + 1) * row["mean_nll"]
        reconstructed = current_sum - previous_sum
        if reconstructed < -(2 * i + 1) * _NLL_HALF_UNIT - 1e-12:
            raise ValueError("Cumulative NLL implies a negative chunk NLL beyond rounding")
        # Preserve small rounding-induced negatives rather than changing the sum.
        chunk_means.append(reconstructed)
        previous_sum = current_sum
    targets = context_size - context_size // 2 - 1
    return {
        "protocol": PROTOCOL, "context_size": context_size, "chunks": chunks,
        "batch_size": batch_size, "n_seq": 1, "targets_per_chunk": targets,
        "total_scored_tokens": targets * chunks, "cumulative": cumulative,
        "chunk_mean_nll": chunk_means, "mean_nll": last["mean_nll"],
        "perplexity": final_ppl, "final_ppl_standard_error": final_error,
        "upstream_error_interpretation": "Unpaired upstream diagnostic; not a confidence interval.",
        "rounding_caveat": ROUNDING_CAVEAT,
    }


def _validate_parsed(result):
    if result.get("protocol") != PROTOCOL or result.get("n_seq") != 1:
        raise ValueError("Comparison requires the pinned non-strided type-1 protocol")
    context = _integer(result.get("context_size"), "context_size", minimum=3)
    chunks = _integer(result.get("chunks"), "chunks")
    batch = _integer(result.get("batch_size"), "batch_size")
    targets = context - context // 2 - 1
    if (batch > context or result.get("targets_per_chunk") != targets
            or result.get("total_scored_tokens") != targets * chunks):
        raise ValueError("Parsed token counts or batch size are inconsistent")
    means = result.get("chunk_mean_nll")
    if not isinstance(means, list) or len(means) != chunks:
        raise ValueError("Parsed chunk count is inconsistent")
    for i, value in enumerate(means):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < -(2 * i + 1) * _NLL_HALF_UNIT - 1e-12):
            raise ValueError("Invalid reconstructed chunk mean NLL")
    mean = result.get("mean_nll")
    if (isinstance(mean, bool) or not isinstance(mean, (int, float))
            or not math.isfinite(mean) or mean < 0
            or not math.isclose(fmean(means), mean, abs_tol=1e-12, rel_tol=0)):
        raise ValueError("Parsed overall mean does not match reconstructed chunks")
    ppl = result.get("perplexity")
    if (isinstance(ppl, bool) or not isinstance(ppl, (int, float))
            or not math.isfinite(ppl) or ppl <= 0):
        raise ValueError("Invalid parsed perplexity")
    _check_ppl(ppl, mean)


def _percentile(sorted_values, probability):
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    fraction = position - lower
    upper = min(lower + 1, len(sorted_values) - 1)
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def compare_perplexity(reference, candidate, *, bootstrap_seed=42,
                       bootstrap_samples=10000, block_chunks=4):
    """Compare equally scored, paired chunks using an exploratory block bootstrap.

    Resampling units are fixed, disjoint contiguous groups of ``block_chunks``
    corpus chunks. Both models always share the same resampled groups. This is a
    percentile interval over eight blocks for the planned 32-chunk experiment;
    it is not an IID-token interval or evidence about general model quality.
    """
    _validate_parsed(reference)
    _validate_parsed(candidate)
    keys = ("protocol", "context_size", "chunks", "batch_size", "n_seq",
            "targets_per_chunk", "total_scored_tokens")
    if any(reference[key] != candidate[key] for key in keys):
        raise ValueError("Reference and candidate protocols/counts differ")
    _integer(bootstrap_seed, "bootstrap_seed", minimum=0)
    _integer(bootstrap_samples, "bootstrap_samples", minimum=2)
    _integer(block_chunks, "block_chunks")
    chunks = reference["chunks"]
    if chunks % block_chunks or chunks // block_chunks < 2:
        raise ValueError("Bootstrap requires at least two complete blocks; no chunks are dropped")
    differences = [candidate_value - reference_value for reference_value, candidate_value in
                   zip(reference["chunk_mean_nll"], candidate["chunk_mean_nll"])]
    block_means = [fmean(differences[start:start + block_chunks])
                   for start in range(0, chunks, block_chunks)]
    rng = random.Random(bootstrap_seed)
    samples = sorted(fmean(rng.choice(block_means) for _ in block_means)
                     for _ in range(bootstrap_samples))
    interval = [_percentile(samples, 0.025), _percentile(samples, 0.975)]
    delta = candidate["mean_nll"] - reference["mean_nll"]
    ratio = math.exp(delta)
    ratio_interval = [math.exp(value) for value in interval]
    return {
        "protocol": PROTOCOL, "reference_perplexity": reference["perplexity"],
        "candidate_perplexity": candidate["perplexity"], "delta_mean_nll": delta,
        "perplexity_ratio": ratio, "perplexity_change_percent": math.expm1(delta) * 100,
        "paired_chunk_delta_mean_nll": differences,
        "exploratory_block_bootstrap": {
            "seed": bootstrap_seed, "samples": bootstrap_samples,
            "block_chunks": block_chunks, "blocks": len(block_means),
            "paired_block_delta_mean_nll": block_means, "confidence_level": 0.95,
            "delta_mean_nll_interval": interval, "perplexity_ratio_interval": ratio_interval,
            "perplexity_change_percent_interval": [math.expm1(value) * 100 for value in interval],
            "method": "Percentile bootstrap of paired, disjoint contiguous chunk blocks.",
            "interpretation": (
                "Exploratory corpus-block interval, conditional on this corpus and protocol. "
                "The small number of blocks and dependence between blocks limit coverage; "
                "not an IID-token interval, run-to-run uncertainty, or general-quality estimate."
            ),
        },
        "metric_interpretation": (
            "Positive delta NLL means worse next-token likelihood on this corpus. "
            "The PPL ratio is exp(delta mean NLL) from rounded NLL values. "
            "PPL percentage change is not percentage loss in general model quality."
        ),
        "pairing_requirement": (
            "Caller must independently verify identical corpus bytes, tokenizer, token "
            "positions, and runtime configuration; the log does not establish these identities."
        ),
        "rounding_caveat": ROUNDING_CAVEAT,
    }
