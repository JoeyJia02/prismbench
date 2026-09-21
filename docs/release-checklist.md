# Release checklist

This is a gate, not a claim that the release has happened. Final evidence is recorded in [validation](validation.md) and [final audit](reviews/final-audit.md).

- [ ] Independent Phase 0 scope/competitor/methodology review.
- [ ] Core and adapter review; all P1 findings resolved or release blocked.
- [ ] Config, schema, stream, OOM, timeout, process-tree cleanup and quality tests pass.
- [ ] Real new-runner GPU benchmark with immutable model/runtime identity and raw evidence.
- [ ] Repeated tested contexts and explicit offload configuration; no extrapolated claims.
- [ ] Install wheel into a clean environment and run demo from outside repository.
- [ ] Built wheel/sdist exclude laboratory assets, credentials and binaries.
- [ ] README commands, links, limits, issue templates, license and contribution guide verified.
- [ ] Final audit covers functionality, methodology, usability, reproducibility and overdesign.
- [ ] Choose/check repository and package names before remote publication.
- [ ] Push to a user-selected GitHub repository and observe Windows/Linux CI.
- [ ] Confirm third-party replication; then decide alpha vs stable version/tag.
- [ ] Publish release only after its declared gates are met; attach build hashes and changelog.

## Codex for Open Source assessment

The project could be useful to maintainers who need reproducible consumer-GPU bug reports. A newly written local repository has no demonstrated adoption or maintenance track record yet. It should not claim program eligibility or build features merely to qualify.

The [official program page](https://developers.openai.com/community/codex-for-oss), checked 2026-09-21, invites maintainers of widely used public projects and allows projects with an important ecosystem role to explain their case. Credible application evidence would include public releases, independent reproductions, resolved user issues, useful upstream contributions and a concrete maintenance workflow. Those are future evidence, not existing achievements. No application was submitted.
