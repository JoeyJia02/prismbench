# Release checklist

These gates distinguish the experimental alpha from a future stable release. Hardware evidence is recorded in [validation](validation.md); the [local audit](reviews/final-audit.md) is a historical snapshot. Current publication evidence belongs in the [publication audit](reviews/publication-audit.md).

- [x] Independent Phase 0 scope/competitor/methodology review.
- [x] Core and adapter review; all P1 findings resolved or release blocked.
- [x] Config, schema, stream, OOM, timeout, process-tree cleanup and quality tests pass.
- [x] Real new-runner GPU benchmark with immutable model/runtime identity and raw evidence.
- [x] Repeated tested contexts and explicit offload configuration; no extrapolated claims.
- [x] Install wheel into a clean environment and run demo from outside repository.
- [x] Built wheel/sdist exclude laboratory assets, credentials and binaries.
- [x] README commands, links, limits, issue templates, license and contribution guide verified.
- [x] Final audit covers functionality, methodology, usability, reproducibility and overdesign.
- [x] Check repository/package names: `JoeyJia02/prismbench` available; PyPI returned 404 on 2026-09-21. This is not a PyPI name reservation or trademark clearance.
- [x] Push to the public GitHub repository and observe all six Windows/Linux CI jobs (run linked in publication audit).
- [x] Build release artifacts from committed source and verify a clean installed-wheel demo/report and complete raw evidence.
- [x] Prepare **experimental `v0.1.0a1`** with a pinned quickstart, checksums and release notes; final tag-target CI must pass before upload.

The [release page](https://github.com/JoeyJia02/prismbench/releases/tag/v0.1.0a1) records actual publication time and final assets. This committed checklist is a readiness record, not a replacement for the release's tag, CI link or checksums.

## Gates for a future stable release

Independent GPU reproduction is follow-up work for the alpha, and a requirement before stable support claims. Experimental alpha publication permits those measurements to remain open when the limitation is explicit.

- [ ] Obtain independent GPU results and a documented runtime compatibility matrix.
- [ ] Validate real hardware OOM cleanup/recovery before promising tested hardware recovery.
- [ ] Establish a licensed, pinned high-precision comparison before claiming quantization quality loss.
- [ ] Resolve reported installation/reliability issues and define the exact stable support matrix.

## Codex for Open Source assessment

The project could be useful to maintainers who need reproducible consumer-GPU bug reports. A newly written local repository has no demonstrated adoption or maintenance track record yet. It should not claim program eligibility or build features merely to qualify.

The [official program page](https://developers.openai.com/community/codex-for-oss), checked 2026-09-21, invites maintainers of widely used public projects and allows projects with an important ecosystem role to explain their case. Credible application evidence would include public releases, independent reproductions, resolved user issues, useful upstream contributions and a concrete maintenance workflow. Those are future evidence, not existing achievements. No application was submitted.
