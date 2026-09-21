# Changelog

## 0.1.0a1 — local release candidate, 2026-09-21

- Installable CLI with JSON configs, offline synthetic demo and one real llama.cpp backend.
- Exact token workloads, independent model lifetimes, first-text latency with event timestamps, engine timings and explicitly scoped memory samples.
- Owned process cleanup, finite timeouts, positive-evidence OOM classification and a recorded explicit fallback sequence.
- Versioned result schema, JSON/CSV/Markdown evidence, conservative matched-workload comparisons and single-line smoke probes.
- Windows/Linux fixture CI definition, optional real-model integration, sample configs and contributor documentation.

This is not a GitHub/PyPI publication announcement. Validation and open release gates are in [the final audit](docs/reviews/final-audit.md). GPU measurements cover one Windows RTX 4070 SUPER and one Qwen3 GGUF; general quantization quality loss, other capacities and other backends remain unvalidated.
