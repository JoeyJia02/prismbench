# Independent core review — 2026-09-21

Reviewer: methodology / test engineering agent, independent of the core author.
Scope: `runner.py`, `config.py`, `hardware.py`, CLI interfaces, and their tests.
No GPU workloads were run during review. The review used synthetic backends,
mocked system APIs, and temporary directories. Quality implementation is owned
by this reviewer and is not claimed as independently reviewed here.

## Findings sent to the core author

### P1 — Telemetry exceptions can erase the only record of a completed attempt

The attempt `finally` block calls `collector.close()`, `collector.metrics()`,
post-cleanup sampling, and resource-file writing before appending the attempt
and writing session reports. A telemetry failure escapes this block even after
the model process has been successfully reaped. Reproduction with a collector
whose `close()` raises `RuntimeError` produced neither `attempt.json` nor
`results.json`. This breaks failed-run evidence, the central product contract.

Recommendation: protect each best-effort telemetry operation, append an explicit
warning, and persist the attempt regardless. A model cleanup failure still
halts the queue; a telemetry failure should preserve the observed model outcome
and visibly incomplete resource evidence. Catch errors from explicit collector
samples too, and expose collector-thread errors in final warnings.

### P1 — Nonfinite GPU telemetry propagates into invalid JSON and lost reports

`smi_sample()` accepts every `float()` result including NaN and infinity, while
canonical JSON and result JSON deliberately reject nonfinite numbers. A mocked
valid-shape NVIDIA row with `memory.used=NaN` returned `vram_used_mib=nan` and
`gpu_telemetry_error=None`. This can terminate the collector or report writer.

Recommendation: finite/range-check numeric telemetry; preserve unavailable
values as `null` and add an explicit field/error marker. Test NaN, positive and
negative infinity, N/A, malformed numbers, and sensible numeric bounds. An
unavailable utilization field must not silently become a measured zero.

### P2 — Case-sensitive case-name uniqueness collides on Windows

`Config(cases=[Case(name="A"), Case(name="a")])` validates, then a synthetic run
fails with WinError 183 when creating the second attempt directory. The failure
occurs before the attempt's protected lifetime block. Earlier records survive,
but a valid-looking user configuration cannot complete on the primary platform.

Recommendation: require casefold-unique names on every platform for portable
configs and deterministic artifact paths. Add a configuration test rather than
relying on the filesystem to reject the second case.

## Positive findings

- Output roots use `exist_ok=False`, preventing accidental merge/overwrite.
- Each fallback has its own configuration, parent ID, and retained OOM row.
- Only OOM triggers the explicitly configured fallback list; cleanup failure
  halts the queue.
- Measured token counts, zero cache reuse, truncation, finite positive rates,
  and TTFT ordering are checked before a successful benchmark row is produced.
- Raw final timings remain authoritative; tests preserve the 127-interval /
  128-token decode convention observed in the existing laboratory evidence.
- Synthetic values are explicitly marked and excluded from real quality
  comparisons. Real provenance includes model and runtime hashes, including
  Windows DLLs rather than only the launcher executable.
- CLI installation/configuration/report commands remain small and discoverable;
  no service orchestration or frontend dependency is introduced.

## Validation observed

At review time, 35 quality tests plus 12 core runner tests passed together;
two additional quality provenance tests subsequently brought the independent
quality module total to 37. These are protocol tests, not hardware benchmark
results. Reproductions of the three issues above were executed successfully
with fake backends and mocked telemetry on Windows.

The author should record remediation and focused regression-test results below
before final release audit. This document is a point-in-time review and does
not assert that its original findings remain unresolved after later commits.

## Remediation verification

Independently rechecked after the author's fixes:

- Casefold duplicates are rejected by configuration validation.
- NaN/infinite/negative telemetry is converted to `null` with a visible reason.
- Collector finalization exceptions are retained as warnings and no longer
  prevent attempt/session serialization.

Added `test_telemetry_finalization_failure_preserves_completed_attempt` to the
core runner suite. It forces the resource path using fake files, fake sampling
and a synthetic backend, then checks both persisted JSON records and the
incomplete-telemetry warning. No real model or GPU executes in this test.

Focused verification: **29 passed** across configuration, hardware and runner
tests; the appended test passes lint. The P1/P2 findings above are resolved for
their reproduced conditions. Collector-thread errors remain inspectable in raw
samples rather than summarized individually; this is a reporting limitation,
not a claim of full telemetry availability. Methodology was aligned with the
implemented first-text TTFT, single-snapshot idle VRAM, mean/SD report, raw
quality probes, and cleanup scope.
