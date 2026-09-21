import subprocess
from unittest.mock import patch

from prismbench.hardware import smi_sample


def test_no_gpu_is_unknown_not_zero():
    with patch("subprocess.run", side_effect=FileNotFoundError("not installed")):
        row = smi_sample(0)
    assert row["vram_used_mib"] is None
    assert row["gpu_telemetry_error"]


def test_selected_gpu_and_wddm_na():
    output = "1, GPU-uuid, NVIDIA RTX 4070 SUPER, 610.88, 12282, 1500, N/A, 45\n"
    with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, output, "")) as mock:
        row = smi_sample(1)
    assert "--id=1" in mock.call_args.args[0]
    assert row["vram_used_mib"] == 1500
    assert row["gpu_utilization_percent"] is None


def test_nonfinite_vram_stays_unknown():
    output = "0, GPU-uuid, NVIDIA, 610, 12282, nan, inf, 45\n"
    with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, output, "")):
        row = smi_sample(0)
    assert row["vram_used_mib"] is None
    assert row["gpu_utilization_percent"] is None
    assert row["gpu_telemetry_error"]
