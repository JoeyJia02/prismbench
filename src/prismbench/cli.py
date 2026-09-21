"""Public command-line interface."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from jsonschema import ValidationError

from . import __version__
from .config import Case, Config, load_config
from .hardware import detect
from .io import save_json


def default_output():
    return Path("outputs") / datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="prismbench", description="Local deployment evidence for llama.cpp")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    doctor = commands.add_parser("doctor", help="Inspect hardware; does not load a model")
    doctor.add_argument("--gpu-index", type=int, default=0)
    demo = commands.add_parser("demo", help="Offline synthetic demo, including an OOM fallback")
    demo.add_argument("--output", type=Path)
    run_parser = commands.add_parser("run", help="Run local model configurations")
    run_parser.add_argument("config", type=Path)
    run_parser.add_argument("--output", type=Path)
    report = commands.add_parser("report", help="Validate and export a saved results.json")
    report.add_argument("result", type=Path)
    report.add_argument("--output", type=Path, required=True)
    compare = commands.add_parser("compare-quality", help="Compare matched probe scores, not general model quality")
    compare.add_argument("reference", type=Path)
    compare.add_argument("candidate", type=Path)
    compare.add_argument("--reference-attempt")
    compare.add_argument("--candidate-attempt")
    init = commands.add_parser("init", help="Write a small editable llama.cpp config; does not download models")
    init.add_argument("--model", type=Path, required=True)
    init.add_argument("--server", type=Path, required=True)
    init.add_argument("--model-id", required=True)
    init.add_argument("--quantization", required=True)
    init.add_argument("--output", type=Path, default=Path("prismbench.local.json"))
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            if args.gpu_index < 0:
                raise ValueError("gpu-index cannot be negative")
            print(json.dumps(detect(args.gpu_index), indent=2, ensure_ascii=False))
        elif args.command == "init":
            if args.output.exists():
                raise ValueError("Config already exists; refusing to overwrite")
            c = Config(backend="llama_cpp", model=str(args.model.resolve()), server=str(args.server.resolve()),
                       model_id=args.model_id, quantization=args.quantization).validate()
            save_json(args.output, c.to_dict())
            print(f"Created {args.output.resolve()}")
        elif args.command == "report":
            from .report import validate_result, write_reports
            data = json.loads(args.result.read_text(encoding="utf-8"))
            validate_result(data)
            args.output.mkdir(parents=True, exist_ok=False)
            write_reports(data, args.output, evidence_root=args.result.resolve().parent)
            print(f"Report: {(args.output / 'report.md').resolve()}; evidence remains beside the source result.")
        elif args.command == "compare-quality":
            from .quality import compare_quality
            result = compare_quality(json.loads(args.reference.read_text(encoding="utf-8")),
                                     json.loads(args.candidate.read_text(encoding="utf-8")),
                                     reference_attempt_id=args.reference_attempt,
                                     candidate_attempt_id=args.candidate_attempt)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            from .runner import run
            output = args.output or default_output()
            config = load_config(args.config) if args.command == "run" else Config(
                repetitions=1, quality=False,
                cases=[Case(name="demo"), Case(name="oom-demo", fallbacks=[{"gpu_layers": 16}])])
            session = run(config, output)
            print(f"Results: {(output / 'results.json').resolve()}")
            print(f"Report: {(output / 'report.md').resolve()}")
            # A recovered OOM still leaves a failure in the ledger. Only final attempts determine exit.
            finals = {}
            for row in session["attempts"]:
                finals[(row["case_name"], row["repetition"])] = row
            expected = len(config.cases) * config.repetitions
            return 0 if len(finals) == expected and all(r["status"] == "SUCCESS" for r in finals.values()) else 1
    except (ValueError, OSError, KeyError, ValidationError) as exc:
        print(f"prismbench: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    return 0
