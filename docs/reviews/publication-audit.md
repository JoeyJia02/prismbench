# Experimental alpha publication audit

## Scope and decision

Decision: **PASS for experimental alpha publication** after independent review, six successful remote CI jobs and clean installed-package verification. Target: public repository `JoeyJia02/prismbench`, prerelease tag `v0.1.0a1`. No PyPI publication or stable support claim is included.

The [public repository](https://github.com/JoeyJia02/prismbench) and [five initial issues](https://github.com/JoeyJia02/prismbench/issues) exist. The [GitHub alpha release](https://github.com/JoeyJia02/prismbench/releases/tag/v0.1.0a1) is the authority for publication time, tag target and downloadable artifacts; this audit records readiness before tagging.

## Independent review

Two independent reviewers inspected publication content/history and installation/CI readiness. Both identified ambiguous wording that made third-party reproduction appear to block every alpha release. The checklist now separates the authorized experimental alpha from future stable claims. Historical local audits remain explicitly labeled snapshots.

The history scan examined all seven original commits and 979 unique blobs (about 10.6 MB), with a largest blob of approximately 214 KB. No binary blobs, common GitHub/OpenAI/AWS credentials, private keys or credential-bearing URLs were found. This is a bounded review, not proof that arbitrary secrets cannot exist. Commit authors use the GitHub noreply address. Models, runtimes, local authorization files and the preserved laboratory are excluded from the tracked project.

The independent packaging reviewer also found that the source archive omitted the three benchmark CSV files. The manifest now includes them. The pinned quickstart was checked against the actual CLI, its seven PowerShell blocks parsed, all generated configs validated, and the same-session paired quality command executed on existing evidence without inference.

Published benchmark commands contain per-attempt keys for terminated localhost servers and original local paths as documented in `benchmarks/README.md`. They are not external account credentials. Benchmark bytes and the historical measured wheel identity remain unchanged.

## First external checks and repairs

The [first CI run](https://github.com/JoeyJia02/prismbench/actions/runs/35618109362) at `f135ff8` passed five jobs and failed Ubuntu/Python 3.12. An integration test read filesystem glob results as though enumeration order matched request order, mixing performance and probe requests. The failure was reproduced locally by reversing enumeration. The repaired test selects requests by their recorded sequence and links TTFT to the corresponding performance arrival file; both enumeration directions are now tested.

The first committed-source build also caught a byte-identity mismatch: Git normalized a single CRLF ending on the final line of `quality.py`. The measured wheel retained that ending. Runtime source/data now use exact-byte Git attributes, restoring the recorded bytes without changing Python behavior. Raw benchmark records are not rewritten or their hashes reinterpreted. The final package must match all 14 recorded Python hashes and both packaged data files exactly.

## Completed verification

- [CI run 35618753429](https://github.com/JoeyJia02/prismbench/actions/runs/35618753429), commit `0d2f29228b77b1d9af77e60c6520fc7f13187653`: **all six jobs succeeded** on Ubuntu/Windows with Python 3.10, 3.12 and 3.14. Each job ran Ruff, CPU/subprocess tests, build, and an installed-wheel console version/demo/report with `pip check` outside the checkout. GPU inference is not part of hosted CI.
- Local Windows/Python 3.12 suite after the repair: **151 passed, 1 opt-in GPU test skipped**, Ruff passed. The independent focused adapter/process checks passed 27 tests. The reverse-enumeration case was observed failing before the fix.
- Built wheel and source archive from `git archive` of the committed source, excluding untracked laboratory material. The wheel's **14 Python files and both packaged data files match the original measured wheel exactly**. All recorded source hashes in both final hardware sessions match.
- Source archive contains **2,964 byte-exact benchmark files**, including all **three CSV files**, plus docs, examples and test fixtures. No model weights, runtime executables/DLLs or preserved laboratory files are bundled.
- Installed the wheel in a newly created temporary virtual environment outside the checkout. Console version, dependency check, synthetic demo and report export passed. The demo retained `SUCCESS → OOM → SUCCESS`; invalid schema input returned exit 2 without traceback.
- An independent reviewer checked the publication changes and the repair commit, regenerated an archive to verify the 14 source hashes, compared the two data files, and verified that the restored line ending leaves the Python AST unchanged. **No open P0/P1 finding remains.**

The release artifacts are rebuilt after this documentation signoff. The exact tag target must also have successful CI before publication; its run is linked in the release notes. Downloadable `SHA256SUMS.txt` is the checksum authority for the final wheel/source archive. Their archive hashes can differ from the original measured wheel because packaging metadata, documentation and archive timestamps differ; the evaluator/source/data comparison above is the hardware-evidence identity check. No additional GPU measurements are claimed from these publication checks.

## Boundaries

The hardware validation remains 21 final successful attempts on one Windows RTX 4070 SUPER/Qwen3-8B Q4_K_M combination. The eight single-line probes compare weight placement only. They do not measure general model quality or quantization loss. Real hardware OOM recovery, other GPU capacities and Linux GPU execution remain unvalidated. Remote CPU CI cannot fill those gaps. Independent reproduction, runtime compatibility and stronger quality evaluation belong in the public issue backlog.
