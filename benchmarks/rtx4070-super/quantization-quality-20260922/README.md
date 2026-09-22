# Qwen3-1.7B quantization prefix pilot

See the [validation report](../../../docs/validation-quantization-20260922.md)
and [predeclared protocol](../../../docs/quantization-methodology.md).

- `preparation/`: exact conversion commands/logs, derived artifact lineage and corpus fingerprint.
- `preparation-invalid-pilot/`: original conversion records before the storage-order fingerprint correction; no quality score was admitted from this preparation.
- `quality/`: accepted F16, Q8_0, Q4_K_M and F16-repeat likelihood lifetimes.
- `quality-invalid-pilot/`: the original F16 run rejected for missing effective-configuration logging; not used in comparisons.
- `performance/`: nine independent 2K lifetimes in the recorded rotating order.
- `performance-controller.py`: the exact local controller used for that sequence, retained as provenance; the reusable setup instructions are in the experiment recipe.
- `summary.json`: arithmetic summaries and paired prediction differences, retaining separate quality/deployment resource scopes.
- `publication.json`: copied byte identities and six intentionally omitted tokenizer stdout files (three from each study attempt).

The BF16/F16/quantized model files, Parquet corpus, extracted text and
reconstructible token arrays are not distributed here. They remain local inputs
under their upstream terms. The publication inventory records the omitted token
files; it does not promise that this public subset contains every local file.

This is one uncontrolled Windows RTX 4070 SUPER, one community-parent model and
an English test-prefix diagnostic. PPL percentage change is not percentage of
overall quality lost. Other hardware, tasks and languages remain untested.
