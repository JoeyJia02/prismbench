# First-user preparation audit, 2026-09-22

Scope: make the existing experimental alpha easier to try and prepare factual
community launch drafts. This change adds no runtime feature, package dependency,
model download service, telemetry upload, release tag or new backend. Published
alpha assets and raw benchmark evidence are unchanged.

## Delivered paths

- [First run](../first-run.md): pinned public wheel, synthetic demo, existing local
  model/runtime, one 2K smoke attempt, optional three-repeat follow-up and failure
  interpretation. Windows and Linux commands use explicit virtual-environment paths.
- [First-run feedback](../../.github/ISSUE_TEMPLATE/first_run.md): a short report
  accepts installation failure or confusing instructions without a GPU or attachment.
- [Sharing results](../sharing-results.md): local paths, GPU UUID, recoverable token
  text, localhost server credentials, reviewed copies and redaction/hash boundaries.
- [English/Chinese drafts](../launch-posts.md) and [first-user plan](../community-launch.md):
  measured F16/Q8/Q4 results, source-only PPL recipe limits and optional invitations.
  No external community post or direct message was sent.

## Validation performed

- A new Python **3.14.5** virtual environment was created in a new temporary
  directory outside the repository on the existing Windows machine. The actual
  public `v0.1.0a1` wheel was installed with the guide's HTTPS URL and pinned
  SHA256 `7488f2378bc6dabbf045dd6c5d2e775dd5f5be1b17d69f3c25234178e51b44d9`.
  Dependencies were resolved normally, with pip cache reuse. This is not a fresh
  operating system, independent user installation or offline dependency test.
- `pip check`, CLI version, synthetic `demo` and saved-result `report` passed.
  The demo kept **SUCCESS / OOM / SUCCESS**, synthetic labels and confirmed
  cleanup. Reusing the demo output path was rejected with exit code 2.
- The published wheel's `init` was executed against existing local runtime/model
  paths. Its defaults (`quality: true`, three repetitions) were checked, then the
  documented edits (`quality: false`, one repetition, 2048/1792/128, no fallback)
  were loaded and validated. Runtime `--version` reported b10964. No model was
  started for these documentation checks and no new GPU benchmark is claimed.
- **61 relevant CLI/config/report tests passed** locally. Fifteen PowerShell
  blocks in the first-run guide, README and pinned quickstart parsed successfully.
  Five `sh` blocks passed `bash -n` using Git for Windows; that is syntax checking,
  not execution on Linux or WSL.
- Relative documentation links were checked for existing targets. The draft's
  six bilingual table rows were checked against the recorded machine-readable
  quantization summary. No measurement was regenerated, rounded into a new claim
  or promoted into evidence of general model quality.

The existing GitHub workflow runs all tests and an installed-wheel demo/report
on Windows/Linux with Python 3.10, 3.12 and 3.14. The pull request's checks are the
authority for this change's CI status; the local checks above do not claim that
an unobserved remote job passed.

## Independent review and boundaries

A read-only newcomer reviewer identified inconsistent activation assumptions,
the enabled-by-default quality probes, overly demanding initial feedback,
incomplete sharing advice, early failures without reports and stale OOM wording.
The delivered guide/templates address those findings. A separate final reviewer
inspected the integrated instructions, templates, implementation and immutable
measurement summary: **PASS, no actionable P1/P2 findings**. Neither reviewer
changed implementation or ran a new GPU experiment for this documentation review.

The project remains a one-maintainer-machine experimental alpha. Independent
installs, other GPU/OS combinations, ordinary VRAM-pressure recovery and repeat
use by external developers are still unobserved. Existing issues #1 and #4 stay
open. The launch targets are goals; download counts and maintainer reruns are not
adoption. Community drafts still need the human maintainer's review, current
venue-rule checks and an actual posting window with follow-up availability.
