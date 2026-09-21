# Experimental alpha publication audit

## Scope and decision

Target: public repository `JoeyJia02/prismbench`, prerelease tag `v0.1.0a1`. The user authorized public repository creation, remote CI validation, an experimental GitHub Release and initial issues. No PyPI publication or stable support claim is included.

Publication is in progress. This record will be completed with observed CI and installation evidence before tagging.

## Independent review

Two independent reviewers inspected publication content/history and installation/CI readiness. Both identified ambiguous wording that made third-party reproduction appear to block every alpha release. The checklist now separates the authorized experimental alpha from future stable claims. Historical local audits remain explicitly labeled snapshots.

The history scan examined all seven original commits and 979 unique blobs (about 10.6 MB), with a largest blob of approximately 214 KB. No binary blobs, common GitHub/OpenAI/AWS credentials, private keys or credential-bearing URLs were found. This is a bounded review, not proof that arbitrary secrets cannot exist. Commit authors use the GitHub noreply address. Models, runtimes, local authorization files and the preserved laboratory are excluded from the tracked project.

Published benchmark commands contain per-attempt keys for terminated localhost servers and original local paths as documented in `benchmarks/README.md`. They are not external account credentials. Benchmark bytes and the historical measured wheel identity remain unchanged.

## Evidence to complete before release

- Public repository and exact tested commit.
- Six remote CI jobs, with their actual outcomes and a run link.
- Release wheel/sdist inspection, checksums and a clean installation from outside the checkout.
- Source/data comparison with the measured wheel and hardware provenance.
- Final independent review of the publication changes.

## Boundaries

The hardware validation remains 21 final successful attempts on one Windows RTX 4070 SUPER/Qwen3-8B Q4_K_M combination. The eight single-line probes compare weight placement only. They do not measure general model quality or quantization loss. Real hardware OOM recovery, other GPU capacities and Linux GPU execution remain unvalidated. Remote CPU CI cannot fill those gaps. Independent reproduction, runtime compatibility and stronger quality evaluation belong in the public issue backlog.
