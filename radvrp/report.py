"""Solution reporting: trip schedules and the three-way waste split (DESIGN_NOTES §5.4, §5.7).

All numbers come from the independent simulator in `checker`, never from
MILP variable values.

For each vial, total over-production (produced − prescribed) splits into:
    irreducible     LB_p − x_p          lead time + QC + direct drive; no plan can avoid it
    routing         x_p·μ(P*_k) − LB_p  cost of sharing the trip (its latest continuous batch P*_k)
    discretization  x_p·μ(B_k) − x_p·μ(P*_k)  rounding the batch down to a 30-min slot
"""

from __future__ import annotations

import pandas as pd

from .checker import Trip, produced_mbq, simulate
from .config import min_to_hhmm
from .instance import Instance


def trip_table(inst: Instance, trips: list[Trip]) -> pd.DataFrame:
    rows = []
    for n, tr in enumerate(trips):
        sc = simulate(inst, tr)
        rows.append({
            "trip": n, "isotope": tr.isotope, "batch": min_to_hhmm(tr.batch_min),
            "latest_batch": min_to_hhmm(sc.latest_batch_min), "depart": min_to_hhmm(sc.depart_min),
            "route": " → ".join(["DEPOT"] + [f"{h}({min_to_hhmm(sc.arrival_min[h])})" for h in tr.stops] + ["DEPOT"]),
            "return": min_to_hhmm(sc.return_min), "vials": len(tr.patients),
            "km": round(sc.distance_km, 1),
        })
    return pd.DataFrame(rows).set_index("trip")


def waste_table(inst: Instance, trips: list[Trip]) -> pd.DataFrame:
    p, rows = inst.patients, []
    for n, tr in enumerate(trips):
        p_star = simulate(inst, tr).latest_batch_min
        for q in tr.patients:
            x, lb = p.at[q, "dose_mbq"], p.at[q, "lb_mbq"]
            produced, cont = produced_mbq(inst, q, tr.batch_min), produced_mbq(inst, q, p_star)
            rows.append({
                "patient": q, "trip": n, "isotope": tr.isotope, "hospital": p.at[q, "hospital"],
                "treatment": min_to_hhmm(p.at[q, "time_min"]), "dose_mbq": x,
                "produced_mbq": produced, "irreducible_mbq": lb - x,
                "routing_mbq": cont - lb, "discretization_mbq": produced - cont,
            })
    df = pd.DataFrame(rows).set_index("patient")
    for c in ("irreducible", "routing", "discretization"):
        df[f"{c}_doses"] = df[f"{c}_mbq"] / df["dose_mbq"]
    df["waste_doses"] = df[["irreducible_doses", "routing_doses", "discretization_doses"]].sum(axis=1)
    return df


def summary(inst: Instance, trips: list[Trip]) -> str:
    tt, wt = trip_table(inst, trips), waste_table(inst, trips)
    lines = [f"{len(trips)} trips, {tt['km'].sum():.1f} km", "", tt.to_string(), ""]
    g = wt.groupby("isotope")
    agg = pd.DataFrame({
        "vials": g.size(), "trips": tt.groupby("isotope").size(),
        "prescribed_MBq": g["dose_mbq"].sum().round(1), "produced_MBq": g["produced_mbq"].sum().round(1),
        "waste_doses": g["waste_doses"].sum().round(3),
        "irreducible": g["irreducible_doses"].sum().round(3), "routing": g["routing_doses"].sum().round(3),
        "discretization": g["discretization_doses"].sum().round(3),
    })
    agg.loc["TOTAL"] = agg.sum(numeric_only=True)
    lines += ["Waste in dose equivalents (1.0 = one extra patient dose produced):", agg.to_string()]
    return "\n".join(lines)
