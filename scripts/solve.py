"""Generate an instance, solve the Phase 2a MILP, check and report.

    .venv/bin/python scripts/solve.py configs/toy_e6.yaml
    .venv/bin/python scripts/solve.py configs/small.yaml --w-over 100 --w-dist 1 --w-trip 20 --plots
    .venv/bin/python scripts/solve.py configs/small.yaml --mode lexicographic --priority over dist trip
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from radvrp import generate, load_config  # noqa: E402
from radvrp import report, viz  # noqa: E402
from radvrp.checker import check  # noqa: E402
from radvrp.model import SolveSettings, solve  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("--w-over", type=float, default=SolveSettings.w_over)
    ap.add_argument("--w-dist", type=float, default=SolveSettings.w_dist)
    ap.add_argument("--w-trip", type=float, default=SolveSettings.w_trip)
    ap.add_argument("--mode", choices=["weighted", "lexicographic"], default="weighted")
    ap.add_argument("--priority", nargs=3, default=list(SolveSettings.priority))
    ap.add_argument("--time-limit", type=float, default=SolveSettings.time_limit)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--plots", action="store_true")
    args = ap.parse_args()

    inst = generate(load_config(args.config))
    s = SolveSettings(w_over=args.w_over, w_dist=args.w_dist, w_trip=args.w_trip, mode=args.mode,
                      priority=tuple(args.priority), time_limit=args.time_limit, verbose=args.verbose)
    res = solve(inst, s)
    print(f"{inst.name}: {res.status} in {res.runtime_s:.2f}s "
          f"({res.n_vars} vars, {res.n_constrs} constraints, gap {res.mip_gap:.2%})")
    if res.status == "license_limit":
        print("Model exceeds the restricted Gurobi license (2,000 vars/constraints); "
              "needs the academic license (TIMELINE O10).")
    if not res.trips:
        return 1
    print(f"objectives: waste {res.objectives['over']:.3f} dose-eq, "
          f"{res.objectives['dist']:.1f} km, {res.objectives['trip']:.0f} trips\n")
    print(report.summary(inst, res.trips))

    chk = check(inst, res.trips, res.claimed_produced, res.objectives["dist"])
    print("\nIndependent check:", "PASS" if chk.ok else "FAIL")
    for v in chk.violations:
        print("  VIOLATION", v)
    for w in chk.warnings:
        print("  warning  ", w)

    if args.plots:
        for p in viz.save_solution(inst, res.trips, ROOT / "outputs" / inst.name):
            print("Plot:", p)
    return 0 if chk.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
