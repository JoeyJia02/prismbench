import json
import subprocess
import sys

from prismbench.cli import main


def test_demo_as_cli_process(tmp_path):
    out = tmp_path / "output with spaces"
    result = subprocess.run([sys.executable, "-m", "prismbench", "demo", "--output", str(out)],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    data = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert data["synthetic"]
    assert [a["status"] for a in data["attempts"]] == ["SUCCESS", "OOM", "SUCCESS"]


def test_invalid_configuration_has_actionable_error(tmp_path, capsys):
    file = tmp_path / "invalid.json"
    file.write_text('{"repetitions": false}')
    assert main(["run", str(file), "--output", str(tmp_path / "out")]) == 2
    assert "repetitions" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()


def test_report_export_rebases_evidence(tmp_path):
    original = tmp_path / "original"
    exported = tmp_path / "export"
    assert main(["demo", "--output", str(original)]) == 0
    assert main(["report", str(original / "results.json"), "--output", str(exported)]) == 0
    report = (exported / "report.md").read_text(encoding="utf-8")
    assert "../original/attempts/demo-r1-a0" in report
