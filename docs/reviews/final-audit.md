# Final release-readiness audit

Historical local audit at commit `720c445`, before remote publication. Subsequent release checks and status are in [publication audit](publication-audit.md); the local evidence below is retained as originally reviewed.

Decision: **PASS for an experimental 0.1.0a1 local release candidate** after independent review and final version 2 hardware evidence audit. This is not a declaration of stable v0.1 or public publication.

## Independent reviews

- [Phase 0 and architecture](phase0.md): conditional GO after comparison with existing tools.
- [Core](core.md): configuration/telemetry/evidence-loss findings reproduced and fixed.
- [Backend](backend.md): independent process-preflight and constructor cleanup findings fixed.
- [Quality](quality.md), [protocol correction](quality-protocol-v2.md): bounded single-line probes, preserved pilot and no general quality claim.
- [Final code](final-code.md): no open P0/P1 code blocker, proportionate architecture.
- [Release and installation](release-audit.md): clean package, CLI works outside checkout, no legacy assets bundled.
- [Benchmark credibility](benchmark-audit.md): final 21/21 attempts independently verified, including exact TTFT reconstruction and post-run asset hashes.

## Local engineering evidence

The final inference/evaluator source is commit `a87b244`; source hashes in each final result are the precise artifact identity. Complete local suite: **150 passed, 1 optional GPU test skipped** on Windows/Python3.12.3; Ruff passed. The opt-in test skip does not substitute for real validation: separately installed-wheel sessions exercise the actual GPU. No Linux GPU execution or remote CI result is asserted.

The built wheel was reinstalled with no source-tree import path. Its console CLI demo, packaged resources and dependency check passed. Earlier independent checks also ran the CLI from a temporary directory outside the repository. Source bytes match the installed distribution. Wheel SHA256: `07576ad9355c69a413581010a49250cb709c00a07c1ec1bbf1cace54cad0d349` (40,072 bytes). The wheel contains code, the two small data JSON files and metadata/license; the source distribution additionally includes docs, tests, examples and publishable benchmark evidence.

## Product assessment and boundaries

The useful contribution is inspectable deployment and failure evidence for explicit local configurations. General fit prediction and automated tuning already have alternatives; this project documents them rather than claiming an empty ecosystem. One sequential CLI and one real backend meet the first-release scope. The involved process lifecycle code is justified by recovery requirements; no service platform was introduced.

The result answers measured feasibility, timing, resource usage and explicit offload tradeoffs. It does not answer universal best quantization, exact maximum context, or broad quality loss. OOM/fallback behavior is covered by synthetic real-process integration tests; intentional hardware OOM and stable post-OOM memory recovery are unvalidated. Probe v1's 0/8 is retained as protocol feedback; v2 is a newly measured, versioned contract, not a rescore or evidence of improved model quality.

## Gates outside local readiness

There is no Git remote, public GitHub/PyPI release, observed remote CI run or third-party reproduction yet. Repository/package name availability also needs checking before publication. These remain explicit release/maintenance backlog items; no external credentials or destructive remote action were used. Codex for Open Source eligibility/adoption is not claimed, and no application was submitted.

## Final signoff

Final hardware results: **21/21 SUCCESS** (15 context runs and six v2 placement/probe runs), all owned processes cleaned up, no cache reuse or truncated performance workloads. The independent reviewer reconstructed every TTFT from raw event timing records and recomputed resource peaks, then rehashed the model, executable and all 33 DLLs. Model, runtime, evaluator and raw evidence identities matched. V2 probe outcomes were 8/8 for all six repeats; the paired placement comparison is 0 percentage points on this limited suite. The unhelpful original v1 pilot is retained separately, without rescoring.

README, methodology, ADR, contribution guide, roadmap, issue templates, CI definition, release checklist, source distribution and complete public evidence are present. The final package remains small: two direct runtime dependencies and a roughly 40 KB wheel. Its evidence-bearing source archive is approximately 1.5 MB compressed and excludes model/runtime binaries. No open P0/P1 review finding remains for the declared local alpha scope. External adoption, Windows/Linux remote CI and public release are still the explicitly unchecked gates.
