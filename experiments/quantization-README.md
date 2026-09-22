# Qwen3-1.7B paired quantization pilot (Windows)

Read the [predeclared protocol](../docs/quantization-methodology.md) before using
the scores. This experiment reuses the installed PrismBench alpha and upstream
llama.cpp tools. It does not add dependencies to the PrismBench wheel.

Use a source checkout, 64-bit Python 3.12, the pinned Windows CUDA 12.4 b10964
runtime from the [quickstart](../docs/quickstart-rtx4070-super.md), and a GPU with
at least 7 GiB free device memory at admission. The reference host is a 12 GB
RTX 4070 SUPER with 32 GB RAM. The preparation requires 10 GiB available host
RAM and stops if available RAM falls below 6 GiB. Allow approximately 15 GB
free disk space for the parent, derived weights, runtime, environment and local
evidence. This is a planning estimate, not a measured minimum.

From the repository root, create a separate environment:

```powershell
python -m venv .venv-quality
.\.venv-quality\Scripts\python.exe -m pip install . -r experiments/requirements-quality.txt
New-Item -ItemType Directory -Force models/quality-study | Out-Null
```

Obtain the two public files below. Review the model's upstream terms and the
dataset's [license declarations](../docs/quantization-methodology.md#data-distribution-and-upstream-references).
The recipe does not require account credentials. Downloads are explicit:

```powershell
Invoke-WebRequest 'https://huggingface.co/bartowski/Qwen_Qwen3-1.7B-GGUF/resolve/dcb19155b962dbb6389f4691a982043a8e651022/Qwen_Qwen3-1.7B-bf16.gguf' -OutFile models/quality-study/parent-bf16.gguf
Invoke-WebRequest 'https://huggingface.co/datasets/Salesforce/wikitext/resolve/b08601e04326c79dfdd32d625aee71d232d685c3/wikitext-2-raw-v1/test-00000-of-00001.parquet' -OutFile models/quality-study/wikitext-test.parquet
```

The script checks both exact checksums before using them; an interrupted or
corrupt download fails validation. Model weights and corpus files are local
inputs, not project assets to commit. Prepare the F16 baseline and two derived
quantizations in a new output directory:

```powershell
.\.venv-quality\Scripts\python.exe -m experiments.prepare_quantization --parent models/quality-study/parent-bf16.gguf --parquet models/quality-study/wikitext-test.parquet --runtime runtimes/upstream --output outputs/quality-prepared
```

This Windows recipe pins the four executable hashes from the tested b10964
CUDA 12.4 archive and records all adjacent DLL hashes. It refuses to reuse output
directories. Conversion commands, logs, process cleanup, GGUF metadata summaries,
lineage, extraction rules and file hashes are preserved. No importance matrix
or second quantization of an already quantized tensor is used.

Run the four likelihood lifetimes (F16, Q8_0, Q4_K_M, F16 repeat):

```powershell
.\.venv-quality\Scripts\python.exe -m experiments.quantization_study outputs/quality-prepared/manifest.json --output outputs/quality-evaluation
```

The output contains a JSON ledger, CSV and Markdown report, exact commands,
runtime logs, token fingerprints and resource samples. Failure or cleanup errors
stop the queue and remain in the ledger. Timeouts are bounded. The final F16
repeat checks numerical drift; it is not extra independent evaluation text.

Likelihood evaluation and generation throughput are different workloads. For
deployment performance, use `prismbench run` with one of the prepared model
paths and its recorded SHA256; keep the standard 2K/1792-input/128-output recipe,
F16 KV, batch 512, microbatch 128, six threads and full GPU placement. Run three
separate lifetimes per variant in the rotating order specified in the protocol.
Do not treat perplexity elapsed time as generation throughput or mix the two
workloads' memory peaks.

Keep the downloaded corpus and `tokenization/*/stdout.log` local: token arrays
can reconstruct third-party text. Public evidence should include the scalar logs,
hashes/counts and an explicit publication inventory identifying those omissions.
Do not publish weights, full corpus, environment credentials or DLLs. Public
reports must name this as a **32-chunk prefix pilot with a derived F16 reference**,
and preserve the caveats about source identity, language, contamination, rounding
and the exploratory block interval.
