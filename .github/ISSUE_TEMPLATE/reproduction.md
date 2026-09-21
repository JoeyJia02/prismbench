---
name: Share a hardware reproduction
about: Report a measured result on another GPU, OS or runtime
---

## Environment and artifacts

- PrismBench version or commit, Python version, OS:
- GPU name/VRAM, driver, CPU and system RAM:
- llama.cpp version/commit and executable hash:
- Model publisher/revision, quantization and SHA256:
- Background GPU work and power/thermal settings, if known:

## Procedure and result

Include the exact config, command, number of repetitions, success/failure counts,
requested/effective context and GPU layers, and whether owned cleanup succeeded.
State whether this is a real GPU run or a synthetic fixture. Link a complete
experiment directory (results JSON, report, attempts and raw evidence); do not
upload model weights or runtime binaries.

Inspect prompts, paths and logs before sharing. Remove external credentials and
unnecessary personal identifiers from a copy, documenting exactly what was
redacted. Preserve numerical results and artifact hashes; keep the original
locally. An OOM/timeout report is useful even without a successful result.

## Interpretation

Which tested configuration completed? What differed from the published baseline?
Do not infer maximum context or general quality from a single successful point.
