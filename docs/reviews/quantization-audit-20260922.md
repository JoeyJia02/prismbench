# Independent quantization study audit, 2026-09-22

Decision: **PASS for the scoped paired corpus-prediction and deployment claims**.
The experiment adds no installed backend, model downloader or general evaluation
platform. The published alpha artifacts and runtime source remain unchanged.

## Before evaluation

An ML reviewer checked the pinned llama.cpp source and identified the actual
1,023-target count per 2K chunk, cumulative rather than per-chunk NLL output,
default `parse_special=false`, and differing terminal-newline treatment between
the two upstream tools. The protocol fixes those choices, input hashes and
32-chunk prefix before scoring. Community-parent provenance and the dataset
license declarations remain explicit.

A separate reviewer checked preparation, statistics and process-lifecycle code.
It independently ran the relevant tests, verified the paired four-chunk block
resampling mathematics and required the intervals to remain exploratory. The
preparation's cleanup-exception receipt gap was fixed with a regression test.
An actual conversion exposed a storage-order fingerprint false positive; an
independent name/shape comparison found identical tensors, and the corrected
name-keyed identity plus duplicate rejection was independently reviewed and tested.

Commit `a91332bd8d87d00a664545905d48b465bccdd202` records the protocol and tools
before PPL evaluation. Commit `633e6be0b4db66b1ad54d153b03d76350c89322b` adds
explicit log verbosity after the first pilot correctly refused missing effective
configuration evidence. The original invalid pilot remains excluded from the
comparison. No corpus, scoring window or candidate selection changed.

## Actual artifacts and likelihood evidence

The independent reviewer rehashed the BF16 parent and all three derived files,
compared complete typed tokenizer metadata and all 311 tensor names/shapes,
checked the 37 runtime file hashes and verified all conversion commands and
cleanup records. Both quantized artifacts derive directly from the same F16
file. The pinned Parquet extraction was reproduced independently: 4,358 rows,
1,296,367 bytes, exact hash and no terminal newline.

The three complete tokenizer arrays agree: **299,078 tokens**, with a shared
65,536-token evaluated prefix. The reviewer independently reconstructed all
32 cumulative NLL rows per accepted run, the paired deltas and bootstrap
endpoints without using the experiment parser. The accepted four logs confirm
2K context, 512 batch, 128 microbatch, one sequence, F16 K/V, flash attention and
29/29 GPU layers. All 103 likelihood telemetry rows reproduce the recorded
resource maxima and all process cleanup records succeed.

F16 PPL is 15.0861, Q8_0 is 15.1083 and Q4_K_M is 16.3602. Q8's exploratory
relative-PPL interval includes zero; this does not establish equivalence. Q4's
8.4457% relative-PPL increase is a corpus-prediction observation, not a general
quality-loss percentage. The F16 repeat matches all printed cumulative NLL rows;
only agreement at the printed precision is established.

## Deployment evidence

The reviewer audited all nine independent lifetimes and their recorded rotating
order. The exact 1,792-token input hashes match, measured output counts are 128,
cache counts are zero and no run truncates. All **1,161** SSE/event records agree,
and first-text TTFT was reconstructed from arrival timestamps. All **85** resource
samples reproduce the stored baseline, idle and peak fields. Full 29/29 layer
placement, F16 K/V, 2K context and process cleanup are confirmed.

All fourteen runtime Python source hashes agree between the checkout, installed
environment and deployment provenance. Every performance lifetime has a warning
for pre-load GPU utilization above 5%. The report therefore describes an
uncontrolled desktop and avoids claiming strict speed rankings, exact memory
requirements or performance on other hardware.

## Publication and remaining gates

The public subset retains commands, scalar logs, failed/accepted ledgers and
byte hashes. It deliberately omits downloaded weights, corpus text and six
tokenizer stdout files containing reconstructible dataset tokens; both accepted
and invalid-pilot token hashes remain available. Those omissions are documented
in the publication inventory, not disguised as a complete raw-corpus release.

Local targeted checks passed during implementation; the final full suite passed
**330 tests with one opt-in GPU skip**, and Ruff passed. Clean-source packaging
and six Windows/Linux CI jobs must pass before merge. External GPU reproduction,
representative task accuracy and pre-retry memory recovery policy remain separate
open work.
