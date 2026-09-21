# Independent Phase 0 review

Reviewed 2026-09-21 by the independent system architecture role before implementation. Scope: ADR 0001, existing laboratory evidence structure, upstream server interface and operating-system process ownership. This is a design review, not a claim that implementation or real benchmarks have passed.

**Decision: conditional GO with a deliberately narrow v0.1.** A consumer deployment evidence CLI can be useful if it makes workload validity, failed attempts and resource costs inspectable. Automatic configuration search alone is insufficient differentiation: the existing research snapshot of llama-autotune documents search, OOM constraints, hardware detection and exported profiles. Reuse llama.cpp inference and keep explicit cases; defer optimizers and additional backends until users need them.

## Findings that must be addressed

1. **P1 — own the process tree before execution.** Windows launchers can create children immediately. Assigning a running process to a Job after creation leaves a race; killing a parent PID is also insufficient. Use a suspended child, assign it to a kill-on-close Job, then resume it. Fail closed when assignment fails. POSIX uses a new session/process group and bounded group termination. Record cleanup failure and stop further cases if descendants remain. Microsoft documents inherited Job membership and termination on closing the last kill-on-close handle. [Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
2. **P1 — verify the workload that ran.** Startup success does not establish useful context capacity. Explicitly fix a single slot and context; inspect effective slot context; use exact input tokens; reject truncated output or nonzero reused prompt tokens; compare requested and actual generation counts. No successful context should be called a universal maximum.
3. **P1 — prevent implicit changes.** Runtime defaults vary. Fixed cases must disable automatic fitting and prompt caches, and explicitly select context-shift and sampling settings. Save the launch vector, runtime version/capabilities and effective configuration. Compatibility is a tested build contract; unsupported flags should report incompatibility rather than silently retry without them. [llama-server interface](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
4. **P1 — distinguish terminal states and evidence.** Classify OOM only from positive allocation evidence. A killed process, HTTP 500, timeout or exhausted context is not inherently OOM. A bounded fallback is a new attempt with its own configuration and cleanup record. Retain incomplete stream data and logs; all unsuccessful attempts remain reportable.
5. **P1 — benchmark definitions must limit claims.** Client TTFT ends at the first nonempty streamed content, includes loopback/serialization overhead and can lag a token with no printable text. Runtime prompt/decode throughput is a different metric. Peak GPU memory is a sampled whole-device maximum, including the desktop; process-tree RSS can double-count shared pages. Startup-to-ready includes runtime initialization/warmup and OS cache effects; it is not pure weight I/O. Missing telemetry remains unknown.
6. **P2 — probe scores cannot establish general quantization loss.** A small deterministic probe suite can identify regressions. Paired deltas require the same base-model family/revision, suite, prompt/template and generation settings. Report sample count and individual outcomes. Do not turn elementary factual/arithmetic checks into a model quality rating or performance ranking requirement.
7. **P2 — keep historical lab evidence separate.** Preserve all current files and the existing README; exclude large artifacts, credentials and local absolute-path configs from the new package. Reusing authored process utilities is reasonable after portable tests, but historical numbers cannot validate a new runner.

## Architecture assessment

The proposed configuration/parser, backend protocol, orchestrator, telemetry, schema/report and CLI modules are sufficient. A synthetic implementation is appropriate for offline demo and failure-path tests when every output labels it synthetic. A backend registry need not become a plugin loading framework. JSON configuration avoids another parser dependency; psutil is justified by cross-platform process and memory inspection. No service or database is warranted.

The result should preserve requested settings, effective settings, model/runtime identity, request hashes, phase timings, telemetry sampling interval and successful/failed attempt history. Summary recommendations can rank only matched measured workloads and must state exclusions.

## Phase acceptance checks

- Unit-test input validation, stream framing/terminal events, zero/unknown metric semantics, finite deadlines, OOM false positives and fallback bounds.
- Exercise Windows owned child/grandchild cleanup, abrupt controller exit, port conflict and partial startup; test POSIX process-group cleanup in Linux CI.
- Run a fresh wheel installation and the no-download synthetic demo outside the source tree.
- Run new real GGUF measurements with the new package; retain honest desktop contamination and sampling limitations.
- Review the final implementation independently before any release-complete claim. Remote GitHub CI and publication remain unverified until actually performed.
