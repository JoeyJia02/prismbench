# Quality probe protocol revision — 2026-09-21

The version 1 raw-completion pilot returned 0/8 under whole-answer exact
matching. Inspection found correct first-line answers followed by continued
reasoning or new examples. The result was retained: it truthfully measures the
original unstopped output contract, but creates a floor that is unhelpful for
detecting elementary answer regressions.

The main engineer and independent methodology reviewer agreed to define
version 2 as **one-line completion** before release:

- Keep the same eight prompts, expected answers, greedy decoding, 64-token
  budget, raw-completion format and strict whole-answer normalization.
- Add the explicit generation stop `['\n']` and record it in request and
  quality provenance; increment the suite version and resulting content hash.
- Reject comparisons with absent, different, or additional stopping sequences.
- Preserve version 1 runs as pilot artifacts and run version 2 afresh. Do not
  truncate or rescore old answers. An unexpected multiline returned answer
  continues to fail whole-answer matching.

This is a change to the generation contract, not a favorable scoring exception.
It is informed by observed pilot behavior and therefore does not constitute an
independent held-out quality evaluation. Expected ceiling effects remain: eight
simple probes can expose basic breakage but cannot establish retained model
quality, isolated quantization loss, or broad instruction-following ability.

Quality module verification after the change: **44 tests passed**, including
different/missing stop rejection and continued failure of multiline answers;
lint passed. Backend request handling is reviewed independently by its owner.
Final hardware evidence must use the rebuilt version 2 wheel, with matching
source provenance across reference and candidate.
