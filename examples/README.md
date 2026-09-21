# Example configurations

`synthetic.json` runs without weights or a GPU and demonstrates the report/fallback ledger.

The Qwen examples are editable **local-file** configurations. Their relative paths resolve from this directory; change `server` and `model` for your machine. Linux/WSL must use a Linux binary. Windows releases need all matching bundled DLLs beside the executable. No example automatically downloads assets.

The context-sweep hash identifies `Qwen/Qwen3-8B-GGUF`, revision `7c41481f57cb95916b40956ab2f0b139b296d974`, file `Qwen3-8B-Q4_K_M.gguf` (5,027,783,488 bytes). Source: [publisher revision](https://huggingface.co/Qwen/Qwen3-8B-GGUF/tree/7c41481f57cb95916b40956ab2f0b139b296d974). If using another artifact, change both its model identity and expected hash; never bypass a hash mismatch for the same claimed artifact.

The fallback example tries GPU layers 99, then 20, then 0, then a shorter context at 0 layers, **only after confirmed OOM and owned cleanup**. It is not a promise that a specific device needs or benefits from this sequence. Ordinary errors do not downgrade. Do not combine measurements across changed contexts.

Both configuration and model paths may contain spaces. Extra arbitrary runtime flags are intentionally not supported in v0.1 because they can invalidate controlled workload assumptions.
