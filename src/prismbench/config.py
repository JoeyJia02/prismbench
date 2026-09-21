"""Strict, small JSON configuration. Paths resolve relative to the config file."""

import json
import math
import re
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path


def integer(name, value, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} must be an integer in [{low}, {high}]")


def number(name, value, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be a finite number in [{low}, {high}]")


@dataclass(frozen=True)
class Case:
    name: str = "default"
    context_size: int = 2048
    prompt_tokens: int = 1792
    output_tokens: int = 128
    gpu_layers: int = 99
    threads: int = 6
    batch_size: int = 512
    ubatch_size: int = 128
    cache_type_k: str = "f16"
    cache_type_v: str = "f16"
    flash_attention: str = "on"
    fallbacks: list[dict] = field(default_factory=list)

    def validate(self):
        if not isinstance(self.name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", self.name):
            raise ValueError("case name must be a short ASCII identifier")
        for key, low, high in [("context_size", 128, 1048576), ("prompt_tokens", 1, 1048576),
                               ("output_tokens", 2, 65536), ("gpu_layers", 0, 999),
                               ("threads", 1, 256), ("batch_size", 1, 65536),
                               ("ubatch_size", 1, 65536)]:
            integer(key, getattr(self, key), low, high)
        if self.prompt_tokens + self.output_tokens + 8 > self.context_size:
            raise ValueError("context_size must reserve prompt_tokens + output_tokens + 8")
        if self.ubatch_size > self.batch_size:
            raise ValueError("ubatch_size cannot exceed batch_size")
        if self.flash_attention not in ("on", "off"):
            raise ValueError("flash_attention must be on or off")
        for key in ("cache_type_k", "cache_type_v"):
            if getattr(self, key) not in ("f16", "bf16", "q8_0", "q4_0"):
                raise ValueError(f"unsupported {key}; use f16, bf16, q8_0 or q4_0")
        if not isinstance(self.fallbacks, list) or len(self.fallbacks) > 8:
            raise ValueError("fallbacks must be a list of at most eight explicit overrides")
        for item in self.fallbacks:
            allowed = {"gpu_layers", "context_size", "prompt_tokens", "cache_type_k", "cache_type_v"}
            if not isinstance(item, dict) or not item or set(item) - allowed:
                raise ValueError("fallback supports only placement, context, prompt and KV overrides")
            replace(self, fallbacks=[], **item).validate()
        return self

    def attempts(self):
        yield replace(self, fallbacks=[])
        for item in self.fallbacks:
            yield replace(self, fallbacks=[], **item)


@dataclass(frozen=True)
class Config:
    backend: str = "synthetic"
    server: str | None = None
    model: str | None = None
    model_id: str = "synthetic-demo"
    quantization: str = "synthetic"
    expected_model_sha256: str | None = None
    cases: list[Case] = field(default_factory=lambda: [Case()])
    repetitions: int = 3
    seed: int = 42
    gpu_index: int = 0
    load_timeout_seconds: float = 180
    request_timeout_seconds: float = 120
    sample_interval_seconds: float = 0.5
    quality: bool = True
    quality_suite: str | None = None
    notes: str = "Uncontrolled local environment; no clean-room qualification asserted."

    def validate(self):
        if self.backend not in ("synthetic", "llama_cpp"):
            raise ValueError("backend must be synthetic or llama_cpp")
        for key in ("model_id", "quantization", "notes"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise ValueError(f"{key} must be nonempty text")
        for key, low, high in [("repetitions", 1, 100), ("seed", 0, 2147483647), ("gpu_index", 0, 31)]:
            integer(key, getattr(self, key), low, high)
        for key, low, high in [("load_timeout_seconds", 1, 3600),
                               ("request_timeout_seconds", 1, 3600),
                               ("sample_interval_seconds", 0.1, 10)]:
            number(key, getattr(self, key), low, high)
        if type(self.quality) is not bool:
            raise ValueError("quality must be boolean")
        if not isinstance(self.cases, list) or not 1 <= len(self.cases) <= 64:
            raise ValueError("cases must contain 1 to 64 entries")
        for case in self.cases:
            case.validate()
        if len({c.name.casefold() for c in self.cases}) != len(self.cases):
            raise ValueError("case names must be unique ignoring case (Windows portability)")
        if self.expected_model_sha256 is not None and (not isinstance(self.expected_model_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", self.expected_model_sha256)):
            raise ValueError("expected_model_sha256 must be 64 lowercase hex characters")
        if self.backend == "llama_cpp":
            for key in ("server", "model"):
                value = getattr(self, key)
                if not isinstance(value, str) or not Path(value).is_file():
                    raise ValueError(f"{key} must name an existing local file")
            if Path(self.model).suffix.lower() != ".gguf":
                raise ValueError("v0.1 accepts local GGUF files only")
        if self.quality_suite is not None and not Path(self.quality_suite).is_file():
            raise ValueError("quality_suite must name an existing JSON file")
        return self

    def to_dict(self):
        return asdict(self)


def from_dict(raw: dict, base: Path | None = None) -> Config:
    if not isinstance(raw, dict):
        raise ValueError("configuration must be a JSON object")
    data = dict(raw)
    base = base or Path.cwd()
    try:
        if "cases" in data:
            if not isinstance(data["cases"], list):
                raise ValueError("cases must be a list")
            data["cases"] = [Case(**c) for c in data["cases"]]
        for key in ("server", "model", "quality_suite"):
            if data.get(key) is not None:
                if not isinstance(data[key], str):
                    raise ValueError(f"{key} must be a path string")
                data[key] = str((base / data[key]).resolve())
        return Config(**data).validate()
    except TypeError as exc:
        raise ValueError(f"invalid or unknown configuration field: {exc}") from exc


def load_config(path: Path) -> Config:
    return from_dict(json.loads(path.read_text(encoding="utf-8")), path.resolve().parent)
