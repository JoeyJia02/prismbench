# Final independent source audit

Reviewed 2026-09-21 by the system architecture role. This reviewer authored the backend, so the independent review focuses on configuration, orchestration, schema, reports and CLI; backend independence is supplied by [the separate backend review](backend.md). The quality module was independently reviewed in [quality.md](quality.md).

**Disposition: no open P0/P1 source blocker found for a local experimental alpha release candidate.** This is not a claim of GitHub publication, remote CI success, broad platform certification or completed real GPU validation. The installed-wheel hardware runs and final evidence audit are separate gates. Do not promote this source review into a stable-release claim.

## Scope and useful behavior

The package implements a concrete consumer deployment workflow: local GGUF configuration, an owned llama.cpp server, exact workload verification, resource/timing evidence, finite failure recovery and exportable reports. This complements existing fit estimators, autotuners and engine microbenchmarks; it does not claim their features as novel. The first release deliberately has one real backend and a clearly synthetic offline demo. An exact maximum context, universal optimal quantization and general quality loss remain outside its claims.

No material overdesign was found. A small backend protocol, dataclasses, JSON, a sequential orchestrator, psutil sampling and report generation are proportionate. The Windows Job code and deadline handling are more involved than the rest because process ownership and recovery are core product requirements. No database, network service for the tool, dashboard, plugin-loading framework or distribution system has been introduced.

## Correctness and evidence review

- Configuration rejects unsupported fields, invalid numeric ranges, insufficient context budgets and ambiguous case names on Windows. Paths resolve against the config file; explicit fallback overrides are relative to the original case. It never downloads a smaller model or silently changes precision.
- The orchestrator gives every repetition and fallback a separate model lifetime and evidence directory. Successful measurements require finite positive timing values, exact prompt/output counts, zero reused prompt tokens and confirmed cleanup. Invalid startup metrics remain reportable failures.
- Only a confirmed OOM advances to an explicit bounded fallback. The schema/export layer checks cleaned OOM parentage and consecutive attempt indices. Non-OOM errors do not trigger downgrade. Cleanup failure stops the complete queue, and user cancellation retains a partial ledger.
- Backend cleanup is executed before telemetry finalization. A telemetry-finalization failure adds a warning instead of discarding an otherwise completed attempt. Missing resources stay unknown; successful inference does not certify a clean desktop or exact VRAM attribution.
- Reports retain unsuccessful attempts, separate effective configurations, require complete successful repeat sets and matching prompt hashes before a speed ordering, and exclude synthetic sessions from hardware recommendations. “Largest tested context” is explicitly distinguished from a discovered maximum.
- Re-export links point back to the original evidence root. Result validation rejects nonfinite values, impossible successful metrics, malformed lineage and evidence paths outside the declared relative root. CSV text and Markdown user fields receive output-format protection.
- Model/runtime/source hashes identify the tested assets. These hashes and schema checks support inspection and reproducibility; they are not signatures proving an imported result was measured. The original complete evidence directory remains the authority.
- The final adapter now appends and flushes per-event relative arrival timestamps in a separate JSONL file. TTFT uses the identical clock sample saved for the first nonempty nonterminal generated-text event. Raw event payloads remain unchanged, and partial timestamps survive a missing terminal event.

## Independent verification performed

The focused configuration, runner and report suite passed **69 tests** during this review. Six affected real-subprocess HTTP fixture tests passed after the event-timestamp addition, including exact TTFT/timestamp equality, monotonic event arrivals, partial-event retention, timeout and terminal-only text handling; Ruff passed. These tests do not load models or use a GPU. The main release audit owns the complete test count, clean-wheel installation and real hardware evidence.

Earlier P1 process issues were independently found and corrected: failed runtime-preflight cleanup cannot be erased by a later successful cleanup, and a partial constructor closes its Windows Job even when direct process termination raises. Their regression tests and independent closure are recorded in the backend review.

## Remaining small improvements and declared limits

Two nonblocking interface/report polish findings were sent to the maintainer for disposition before the final build: catch JSON Schema `ValidationError` at the CLI boundary so malformed input receives the documented input-error behavior, and include the prompt hash/runtime version in repeat-table grouping as well as comparison eligibility. The latter protects summaries of imported or inconsistent repeat data; the deterministic unchanged local workload already has stable fingerprints. Neither changes inference behavior.

Windows is the first validated real GPU target. POSIX explicit cleanup uses process groups, but SIGKILL of its controller is not crash-safe. Runtime library hashing currently covers bundled Windows DLLs, not arbitrary Linux shared-library dependency graphs. These are limitations of platform coverage, not reasons to claim Linux GPU validation prematurely.

The final release audit must verify the actual final wheel hashes, full test run, README commands, published example files and new GPU measurements. In particular, runs from a wheel preceding the timestamp addition must remain identified as earlier pilots; they cannot certify the final timestamp evidence format. No further inference feature expansion is required before the local alpha candidate is reviewed.

## Maintainer disposition before hardware validation

Both polish findings were fixed before the final installed-wheel runs: CLI catches schema validation failures as input errors; grouping and matched comparisons include prompt hash and runtime version. Focused regressions are included in the **142 passed, 1 optional GPU test skipped** complete run. The final code commit is `267f39b`; benchmark JSON additionally captures exact package source hashes. No benchmark scalar was backfilled into an earlier pilot.
