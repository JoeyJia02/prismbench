# Independent quality-module review

Reviewed 2026-09-21 by the system architecture role, independent of the author of `quality.py`. Reviewed the module, bundled eight-item suite, 37 quality tests, and its contract with the real backend. The quality tests pass. This review assesses the regression-check mechanism; it does not validate real model capability or a measured quantization loss.

**Decision: acceptable for the v0.1 fixed-probe scope after the adapter boundary correction below.** No evaluator framework, model downloader or external judge is introduced. The deliberately narrow exact-answer suite is inexpensive and suitable for checking obvious regressions, provided its limitations remain prominent.

## Findings and disposition

1. **P1, corrected — input fingerprint must identify what inference consumes.** The quality preflight tokenizes with special-token parsing disabled, while the original backend probe sent a string that the runtime could interpret differently. The adapter now submits tokenizer-produced token IDs, preserving the same raw-completion policy, and rejects nonzero cache counts, changed prompt counts or truncation. Backend fixture tests cover cached and truncated probe responses. This correction is in the backend boundary; the quality module itself was not modified by its reviewer.
2. **P2, documented limitation — suite scope is tiny.** Eight copying, extraction and arithmetic probes do not estimate general model quality or percentage of intelligence retained. Raw completion can expose formatting/EOS behavior, so an answer containing correct text plus commentary can fail exact matching. The result includes raw answers, normalization, item outcomes, sample count and the explicit limitation. This is appropriate; increasing apparent score through fuzzy matching would weaken reproducibility.
3. **P2, documented limitation — shared base-model identity is user asserted.** The comparison verifies a matching `model_id`, tokenizer fingerprints and runtime identity, but it cannot prove that two weight artifacts derive from the same base-model revision. Its result states this limitation and calls the difference a probe-score change in percentage points, not isolated quantization loss. Users must supply a valid reference for causal interpretation.
4. **P2, release documentation check — implementation and methodology must agree.** The package uses raw completion, 64 output tokens, greedy sampling, EOS enabled, Unicode NFKC plus whitespace normalization, and case-sensitive exact matching. No implicit chat template is applied. Custom prompt text follows the same literal tokenization policy; template special markers are not silently interpreted. Documentation should describe those actual rules.

## What the tests substantiate

- Strict bounded suites reject duplicate JSON fields, unsupported fields, duplicate probe IDs, empty/oversized prompts and malformed expected answers.
- Context budgets are validated before generating any probe, and every probe is preceded by cache erasure.
- Runtime errors propagate instead of converting partial probe runs into successful scores.
- Saved answer scores, counts, suite hashes, token fingerprints and generation provenance are checked before a comparison.
- Synthetic, unsuccessful or uncleaned attempts are excluded. Multiple successful attempts require explicit selection; inconsistent repeated probe outcomes prevent selecting a favorable repeat.
- Paired comparison requires matching runtime executable/library hashes and version, token IDs, suite, generation/context settings, and fixed batch/thread settings. Allowed weight/placement/KV changes are listed rather than silently attributed to quantization.

The adapter and process fixtures additionally test actual child lifetimes and HTTP behavior without model inference. They are synthetic protocol evidence, not real quality evidence. A real reference/candidate pair remains necessary before publishing any measured probe delta.

## Remaining release checks

Confirm the final README and methodology retain these limitations, preserve raw probe requests and answers in the published example, and distinguish an unpaired smoke score from a paired configuration comparison. No additional quality framework is required for this release.
