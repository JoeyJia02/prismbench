"""Opt-in real hardware test; CI without explicit local assets never loads a GPU."""

import os
import re
from pathlib import Path

import pytest

from prismbench.config import Case, Config
from prismbench.runner import run


@pytest.mark.gpu
def test_local_gguf_real_gpu_lifetime(tmp_path):
    server = os.environ.get("PRISMBENCH_SERVER")
    model = os.environ.get("PRISMBENCH_MODEL")
    if not server or not model:
        pytest.skip("Set both PRISMBENCH_SERVER and PRISMBENCH_MODEL to opt into real inference")
    config = Config(
        backend="llama_cpp", server=str(Path(server).resolve()), model=str(Path(model).resolve()),
        model_id="local-integration-artifact", quantization="user-provided-GGUF",
        cases=[Case(name="gpu-smoke", context_size=1024, prompt_tokens=768,
                    output_tokens=64, gpu_layers=99)],
        repetitions=1, quality=False,
    )
    session = run(config, tmp_path / "out")
    assert session["synthetic"] is False
    assert len(session["attempts"]) == 1
    attempt = session["attempts"][0]
    assert attempt["status"] == "SUCCESS", attempt["error"]
    assert attempt["metrics"]["prompt_tokens"] == 768
    assert attempt["metrics"]["generated_tokens"] == 64
    assert attempt["metrics"]["cache_tokens"] == 0
    assert attempt["cleanup_confirmed"] is True
    assert attempt["runtime"]["effective"]["context_size"] == 1024
    assert re.fullmatch(r"[0-9a-f]{64}", session["provenance"]["model_sha256"])
    assert session["provenance"]["model_size_bytes"] == Path(model).stat().st_size
