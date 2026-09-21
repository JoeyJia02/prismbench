"""Small backend contract; no plugin framework or backend-specific core imports."""

from typing import Protocol


class BackendError(RuntimeError):
    def __init__(self, status: str, message: str):
        super().__init__(message)
        self.status = status


class Backend(Protocol):
    pid: int | None

    def start(self) -> dict:
        """Return load_time_s, runtime_version, argv, and effective settings."""
        ...

    def tokenize(self, text: str) -> list[int]: ...

    def erase(self) -> None: ...

    def complete(self, tokens: list[int], n_predict: int, seed: int, timeout_s: float) -> dict:
        """Return ttft_s, total_latency_s, timings, content, truncated; preserve raw data."""
        ...

    def probe(self, prompt: str, n_predict: int, seed: int, timeout_s: float) -> str: ...

    def close(self) -> bool:
        """Stop/reap owned process tree; return whether cleanup is confirmed."""
        ...
