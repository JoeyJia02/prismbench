# First external users

Status: preparation only. The [English and Chinese posts](launch-posts.md) are
drafts; no community post, direct message or recruitment campaign has been sent
as part of this work. PrismBench remains **0.1.0a1, an experimental alpha**.
We have evidence from one maintainer-owned GPU, not independent GPU validation.

## Who should try it first

Start with 3–5 developers who already run a local GGUF with llama.cpp and want
to compare a concrete deployment choice: context size, GPU layers or a
quantization. They can reuse their working runtime and model instead of first
downloading several gigabytes. Seek 8 GB, 16 GB and 24 GB NVIDIA GPUs, plus
Linux/WSL, but accept another 12 GB machine: an independent installation is
useful too. The current GPU memory collector uses NVIDIA `nvidia-smi`.

The immediate benefit is **a report for their own model and machine**, including
the actual workload, latency, memory and failed attempts. Do not promise a
universally best configuration, a maximum-context prediction or a precise
percentage of quality retained. GPU telemetry can be unavailable; that is a
documented outcome, not a zero-memory result.

## Prepare, invite, support

1. **Make trying it concrete.** Point every invitation to the
   [first-run guide](first-run.md), the
   [published alpha](https://github.com/JoeyJia02/prismbench/releases/tag/v0.1.0a1)
   and an [actual result](validation-20260922.md). Explain that the offline demo
   is synthetic. Real measurements require a compatible local runtime and GGUF;
   download time and inference time depend on the user's setup.
2. **Share one useful technical result.** Use the measured F16/Q8/Q4 pilot in
   [the draft posts](launch-posts.md). Include the method and limitations beside
   the table, not only behind a link. The study uses source-checkout helpers;
   installing the wheel does not install a general perplexity benchmark.
3. **Choose one relevant channel first.** Review the current community rules
   and recent discussions before posting. The first candidate is
   [llama.cpp Show and tell](https://github.com/ggml-org/llama.cpp/discussions/categories/show-and-tell).
   A later adapted post may suit
   [r/LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/); read its current rules and
   [moderator guidance](https://www.reddit.com/r/LocalLLaMA/comments/1su3ao4/rlocalllama_rule_updates/)
   first. These links identify candidate venues, not moderator permission.
   Do not paste promotion into unrelated benchmark threads, send unsolicited
   bulk messages or ask for votes. A broad launch is not needed for this pilot.
4. **Ask for one bounded action.** Invite a developer to complete the 2K first
   run on a model they already use, then report whether installation and the
   result were understandable. A different model or quantization is useful
   compatibility evidence, not a direct replication of our numerical result.
   The first-run guide disables the separate quality probes and uses one
   lifetime to reduce the initial work. A user can optionally rerun three
   lifetimes into a fresh output directory for comparison evidence. A single,
   partial or failed run is useful feedback and must be labeled accordingly.
5. **Support each early attempt.** Triage environment/setup issues before
   requesting another benchmark. Record the exact failing step and fix the
   earliest repeated source of confusion. Ask whether the report helped them
   make their original deployment choice. Do not require a pull request.

## Feedback and evidence

- Installation or explanation problems:
  [short first-run feedback form](https://github.com/JoeyJia02/prismbench/issues/new?template=first_run.md).
  No GPU result or attachment is required. Existing onboarding work is tracked
  in [issue #4](https://github.com/JoeyJia02/prismbench/issues/4).
- A real measurement on another machine:
  [external reproduction issue #1](https://github.com/JoeyJia02/prismbench/issues/1).
- Include OS, GPU/VRAM, Python and runtime versions, model identity/hash,
  relevant configuration, the command/step and the observed outcome. Note
  background GPU applications and any changed workload.
- Follow [sharing results](sharing-results.md) before attaching files. Results,
  logs, commands, configurations and prompts can contain local paths, GPU UUIDs,
  account names or private text. Token IDs can reconstruct text. Start with the
  smallest relevant excerpt and inspect it before posting. There is no automatic
  anonymization guarantee.
  Preserve the original evidence locally; disclose redactions in shared copies.
  Full raw artifacts are optional for initial support. Without enough evidence,
  label a report unverified instead of presenting it as validated replication.
- Never request model weights, credentials, tokens or private datasets. Do not
  ask early users to deliberately exhaust GPU or host memory.

## What success means

For the first two weeks **after a maintainer actually posts an invitation**, aim
for the following. These are proposed targets, not completed results or
forecasts.

| Target | Evidence to retain |
|---|---|
| 3 independent installations reach the demo | User-confirmed OS/Python/package versions and outcome; demo is synthetic |
| 2 external machines produce real reports | Runtime/model identity, workload, outcomes and inspectable evidence; state gaps |
| 1 developer uses it again for their own comparison | Their stated deployment question, changed config and usefulness of the report |
| Every reported blocker gets triaged | Issue link, reproduction status, fix or documented limitation |

Track only information people choose to provide publicly. Use existing GitHub
issues; no mailing list, analytics service, account system or new dashboard is
needed. Stars and page views are not substitutes for these outcomes.

If relevant developers do not try it, first learn which step or value proposition
failed. If users try it but do not reuse it, investigate the decision the report
failed to support. Add a backend only when observed user work justifies it.

## Maintainer checklist before posting

- [x] Real, scoped measurements and public evidence are available.
- [x] English and Chinese drafts disclose alpha status and AI-assisted development.
- [x] First-run and feedback links are specified.
- [ ] The maintainer has reviewed the final text and can explain its method.
- [ ] The linked first-run instructions and feedback entry points are live on GitHub.
- [ ] Current rules and category fit have been checked in the chosen community.
- [ ] The maintainer has chosen a time when follow-up questions can be answered.
- [ ] The maintainer has published the chosen post and recorded its URL here.
- [ ] Actual external-user outcomes have been recorded in issues.

Development and these drafts were assisted by OpenAI Codex. Human maintainer
review and community posting remain separate actions; this document does not
claim either happened.
