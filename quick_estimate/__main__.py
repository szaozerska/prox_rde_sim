"""python3 -m quick_estimate INPUT.json --out RESULT.json"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from .model import estimate


def main():
    parser = argparse.ArgumentParser(description="Offline algebraic RDE wave-count screening")
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, help="new JSON result file, never overwritten")
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        result = estimate(json.loads(raw))
        result["provenance"] = {"input_sha256":hashlib.sha256(raw).hexdigest(),
            "model_sha256":hashlib.sha256(Path(__file__).with_name("model.py").read_bytes()).hexdigest(),
            "python_version":sys.version.split()[0]}
        encoded = json.dumps(result, indent=2, allow_nan=False)+"\n"
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            with args.out.open("x") as f:
                f.write(encoded)
        print(f"{result['status']}: nominal modes={result['nominal_candidate_wave_counts']}; "
              f"coefficient-range modes={result['possible_candidate_wave_counts']}; "
              f"refill capacity={result['continuous_refill_capacity']:.3f}", file=sys.stderr)
        if not args.out:
            print(encoded, end="")
    except (ValueError, OSError, OverflowError, ZeroDivisionError) as exc:
        parser.exit(2, f"quick_estimate: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
