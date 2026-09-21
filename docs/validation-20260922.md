# Same-machine reproduction and bounded CUDA failure, 2026-09-22

Two follow-up experiments exercised the **published 0.1.0a1 wheel** on the original Windows RTX 4070 SUPER. Neither modifies the [original 21-run evidence](validation.md), adds another GPU, or claims a clean operating-system installation.

## Fresh installation from the public release

Created a new directory outside the checkout and a new Python **3.14.5** virtual environment, with system site-packages disabled. Imported PrismBench from that environment's site-packages. The release wheel hash is `7488f2378bc6dabbf045dd6c5d2e775dd5f5be1b17d69f3c25234178e51b44d9`; an anonymous download from the public release URL matched it. Dependency checks, the synthetic demo and report export passed.

The approximately 5 GB model was copied from cache and verified; both runtime ZIPs were copied, verified and freshly extracted. This avoids a redundant large download but means this is **not a test of downloading all large assets anew**. Model, executable, all 33 DLLs and all 14 Python source hashes match the original benchmark. The two packaged JSON resources match the measured wheel.

The machine inherits NVIDIA driver 610.88 and Visual C++ runtime DLLs version 14.51.36247.0. A new venv does not isolate those dependencies. Independent review found the missing Visual C++ prerequisite in the original onboarding instructions; the [quickstart](quickstart-rtx4070-super.md) now names the x64 Redistributable and missing-DLL troubleshooting. No driver or system runtime was installed or replaced for this experiment.

The published quickstart's unchanged 2K workload completed **three independent successful lifetimes**: 1,792 fresh input tokens, 128 output tokens, zero cache reuse, no truncation, effective context 2,048 and GPU layers 37/37. All owned processes were cleaned up. The mean first-text TTFT was **0.433653 s**, mean engine generation throughput **77.6735 token/s**, and maximum sampled whole-device memory **6,268 MiB**. These are uncontrolled desktop observations, not acceptance tolerances against the earlier timing numbers.

Evidence: [report](../benchmarks/rtx4070-super/fresh-install-20260922/report.md), [raw results](../benchmarks/rtx4070-super/fresh-install-20260922/results.json), [installation receipt](../benchmarks/rtx4070-super/fresh-install-20260922/onboarding/verification.json), and [inherited OS runtime identities](../benchmarks/rtx4070-super/fresh-install-20260922/onboarding/os-runtime-dependencies.json).

## Real CUDA allocator rejection and explicit fallback

The [opt-in supervisor](../experiments/README.md) launched the unchanged installed CLI under an external **8 GiB Windows Job committed-memory cap**. Before execution, an independent reviewer verified the code and ran 41 hardware-free tests, including an actual Windows Job cap/cleanup/sentinel test. The executed helper SHA256 was `4ff903467ba219331d0a8615632cc3fe989c009e075825b671c0e2c24c002411`.

The one initial case requested context **524,288** with f16 KV and full GPU placement. The configured input/output was only 128/16 tokens. This intentionally requests an oversized context allocation, far beyond the model's training context of 40,960; it does not evaluate answer quality at that context. The actual server log records:

```text
allocating 73728.00 MiB on device 0: cudaMalloc failed: out of memory
```

The CLI recorded **OOM**, confirmed cleanup, and applied its single explicit fallback to context **2,048**. The fallback completed **SUCCESS** with 128/16 tokens, zero cache reuse and confirmed cleanup. The parent attempt remains in JSON/CSV/Markdown and is linked to the successful fallback. The CLI exited 0 after the recovered chain; the failed attempt's timing metrics remain null.

| Observation | Recorded result |
|---|---|
| External CLI wall time, including hashes/preflight | 13.174 seconds |
| Baseline device memory, five samples | 1,303 MiB each |
| Failed attempt sampled device peak | 5,920 MiB |
| Fallback sampled device peak | 6,250 MiB |
| After-chain device memory, 15 samples at nominal 1 Hz | 1,303 MiB each |
| Minimum available host RAM in 124 watchdog samples | 14.268 GiB |
| Maximum sampled owned-tree RSS | 4.827 GiB |
| Watchdog abort / remaining owned processes | None / none |
| Separate sentinel after child Job cleanup | Alive, then separately cleaned up |

Evidence: [supervisor audit](../benchmarks/rtx4070-super/oom-recovery-20260922/audit.json), [CLI report](../benchmarks/rtx4070-super/oom-recovery-20260922/benchmark/report.md), [result ledger](../benchmarks/rtx4070-super/oom-recovery-20260922/benchmark/results.json), and [original CUDA diagnostic](../benchmarks/rtx4070-super/oom-recovery-20260922/benchmark/attempts/kv-allocation-recovery-r1-a0/server.stderr.log).

## What this establishes and what remains open

The recorded CUDA error, failure classification, cleanup and context-only fallback are real observations from the released backend. The external guard did not report an abort. The **8 GiB Job cap can nevertheless contribute to CUDA allocation rejection**, so the cause cannot be attributed solely to physical VRAM exhaustion; `physical_vram_oom_proven` is false. Sampled peaks do not show that all 12 GB was filled. This is a bounded allocator-rejection/recovery test, not an unconfounded physical-capacity experiment.

Fifteen post-chain samples support return to the observed baseline after this chain. They do not prove stable memory recovery before fallback: the current CLI proceeds once owned-process cleanup is confirmed and has no pre-retry settling gate. A separate sentinel establishes preservation of that one process, not every desktop application. Only one guarded failure/fallback cycle was performed.

External GPU/Linux reproduction, ordinary VRAM pressure without this host cap, recovery admission policy and higher-precision quantization quality comparisons remain open. [Issue #2](https://github.com/JoeyJia02/prismbench/issues/2) is only partially addressed; [external installation feedback](https://github.com/JoeyJia02/prismbench/issues/4) still requires another user. The [independent follow-up review](reviews/reproduction-oom-20260922.md) records the evidence audit.
