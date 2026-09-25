"""Generate an instance from a config, save it, print a summary, optionally plot.

    .venv/bin/python scripts/generate.py configs/small.yaml --plots
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radvrp import generate, load_config  # noqa: E402
from radvrp import viz  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("config")
    ap.add_argument("--out", help="output directory (default data/<name>)")
    ap.add_argument("--plots", action="store_true", help="write plots to outputs/<name>/")
    args = ap.parse_args()

    inst = generate(load_config(args.config))
    out = inst.save(args.out or ROOT / "data" / inst.name)
    print(inst.summary())
    print(f"\nSaved to {out}")

    issues = inst.validate()
    print("Validation:", "OK" if not issues else f"{len(issues)} issue(s)")
    for msg in issues:
        print("  -", msg)

    if args.plots:
        for p in viz.save_all(inst, ROOT / "outputs" / inst.name):
            print("Plot:", p)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
