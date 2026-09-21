from pathlib import Path

import pytest

from prismbench.config import Case, from_dict


@pytest.mark.parametrize("patch", [
    {"unknown": 4}, {"repetitions": True}, {"repetitions": 0},
    {"request_timeout_seconds": float("nan")}, {"quality": "yes"},
    {"cases": []}, {"cases": [{"name": "../escape"}]},
    {"cases": [{"prompt_tokens": 2000}]},
    {"cases": [{"fallbacks": [{"model": "other"}]}]},
    {"cases": [{"name": "a"}, {"name": "a"}]},
    {"cases": [{"name": "A"}, {"name": "a"}]},
])
def test_reject_invalid_configuration(patch):
    with pytest.raises(ValueError):
        from_dict(patch)


def test_fallbacks_are_explicit_independent_attempts():
    case = Case(fallbacks=[{"gpu_layers": 16}, {"context_size": 1024, "prompt_tokens": 768}])
    case.validate()
    points = list(case.attempts())
    assert len(points) == 3
    assert points[1].gpu_layers == 16
    assert points[2].gpu_layers == 99  # Each override is relative to the original case.
    assert points[2].context_size == 1024
    assert case.fallbacks


def test_paths_resolve_from_config_directory(tmp_path):
    (tmp_path / "server.exe").touch()
    (tmp_path / "model.gguf").touch()
    c = from_dict({"backend": "llama_cpp", "model": "model.gguf", "server": "server.exe"}, tmp_path)
    assert Path(c.model) == tmp_path / "model.gguf"
