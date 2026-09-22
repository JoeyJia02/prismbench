# Share a result without sharing your whole machine

Start with a short description in the [first-run form](https://github.com/JoeyJia02/prismbench/issues/new?template=first_run.md).
You do not need to upload logs to tell us that installation failed or a step was
confusing. Public GitHub issues are visible to everyone. PrismBench saves local
files and does not automatically upload or anonymize them.

## What the files can contain

Real experiment directories contain resolved local paths, model/runtime identity,
hardware details (including GPU UUID), requested/effective config, server commands
and logs, timestamps, prompts/token IDs, generated text and stream events.
Token IDs can reconstruct text; they are not anonymization. Logs may repeat paths
or identifiers, and exported Markdown/CSV/JSON can repeat them too.

Server commands also contain an ephemeral API key for the owned localhost
server. Confirm that server cleanup completed before sharing. This key is not
your GitHub/Hugging Face credential, but it still should not be published while
its server is alive. If cleanup is uncertain, submit a description first and
resolve that failure before sharing command evidence.

The default performance workload is generated public text. A custom quality suite
or private model may add information you cannot redistribute. Do not attach model
weights, DLLs, environment dumps, credentials or downloaded third-party corpora.

## Minimal report first

OS/Python, PrismBench/runtime versions, GPU model/VRAM, public model identity if
shareable, the step that failed and a short reviewed error excerpt are enough to
start triage. You can write "not collected" or "not shareable" for missing details.
Partial evidence can identify a problem; it cannot certify a hardware reproduction.

## When you choose to share evidence

1. Keep the original experiment directory untouched locally. Review a **copy**
   before uploading it. Include `results.json`, `results.csv`, `report.md`,
   `config.resolved.json` and the corresponding `attempts/` tree when shareable.
   A re-exported report alone does not contain the original evidence.
2. Inspect every file you intend to share for usernames/home paths, GPU UUIDs,
   private model names or locations, prompts/responses/token arrays, credentials
   and sensitive log text. A string search is useful but cannot prove absence.
3. Redact only the copy and add `REDACTIONS.md` listing which files/fields were
   changed or omitted and why. Do not include the removed private values in that
   note. Keep measured numbers, failures, workload settings and public artifact
   identities intact where possible; otherwise mark them as withheld.
4. Keep the original recorded hashes labeled as **original**. Redacting a config,
   token array or log changes its bytes, so a copied artifact may no longer match
   its recorded hash. If you compute hashes of the shared copy, label them
   separately. Do not silently rewrite provenance to make the edited copy look
   like untouched original evidence.
5. Preview the attachment/link and the issue text before submitting. If the
   evidence cannot be shared safely or under its license, submit the minimal
   report instead. A maintainer can ask for a smaller, reviewed excerpt.

The CLI's `report` command validates result schema and some consistency rules. It
does **not** scan for secrets, authenticate provenance or audit every raw file.
Redaction can prevent full reproduction; maintainers must record that limit
rather than count partial/redacted reports as fully verified replications.
