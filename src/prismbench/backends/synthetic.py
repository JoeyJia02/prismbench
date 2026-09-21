"""Deterministic fixture data, never hardware measurements."""

from .base import BackendError


class SyntheticBackend:
    pid = None

    def __init__(self, config, case, out):
        self.config, self.case, self.out = config, case, out

    def start(self):
        # The demo deliberately exercises the fallback ledger without allocating GPU memory.
        if self.case.name.startswith("oom-demo") and self.case.gpu_layers > 16:
            raise BackendError("OOM", "Synthetic fixture: simulated allocation failure")
        return {"load_time_s": 0.1, "runtime_version": "synthetic-v1",
                "argv": [], "effective": {"context_size": self.case.context_size,
                "gpu_layers_loaded": min(self.case.gpu_layers, 32), "gpu_layers_total": 32,
                "cpu_offload": self.case.gpu_layers < 32}}

    def tokenize(self, text):
        return list(range(len(text.split())))

    def erase(self):
        pass

    def complete(self, tokens, n_predict, seed, timeout_s):
        return {"ttft_s": 0.05, "total_latency_s": 0.05 + (n_predict - 1) / 40,
                "content": "synthetic output", "truncated": False,
                "timings": {"prompt_n": len(tokens), "predicted_n": n_predict, "cache_n": 0,
                            "prompt_per_second": 1000.0, "predicted_per_second": 40.0}}

    def probe(self, prompt, n_predict, seed, timeout_s):
        return "synthetic fixture; no model quality was measured"

    def close(self):
        return True
