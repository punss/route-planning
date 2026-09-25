"""The Instance data model: everything a solver needs for one delivery day.

Tables (pandas):
    isotopes    index=isotope   half_life_h, lambda_per_h, a2_mbq, vials_per_truck, daily_cap_mbq
    nodes       index=node_id   kind (depot/hospital), type, lat, lon, receiving_open_min,
                                service_min, eligible_<isotope> (bool)
    patients    index=patient_id  hospital, isotope, weight_kg, dose_mbq, time_min + derived
    travel_min  node x node travel times (minutes)
    dist_km     node x node road distances (km)

Derived patient columns (DESIGN_NOTES §5.4):
    lower_mbq, upper_mbq      tolerance band [L_p, U_p]
    deadline_min              tau_p - lead time
    latest_direct_batch_min   latest batch finish if p had a truck to itself
    lb_mbq                    minimum activity p could ever require (irreducible)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import min_to_hhmm
from .decay import delay_budget_h, production_multiplier

DEPOT = "DEPOT"


@dataclass
class Operations:
    lead_time_min: int
    qc_min: int
    prod_start_min: int
    prod_end_min: int
    batch_slot_min: int
    dose_tolerance: float
    capacity_factor: float
    fleet_size: int | None = None          # O2 placeholder
    dispatch_per_slot: int | None = None   # O2 placeholder

    @property
    def batch_slots(self) -> list[int]:
        """Discretized batch finish times S (DESIGN_NOTES §5.3)."""
        return list(range(self.prod_start_min, self.prod_end_min + 1, self.batch_slot_min))


@dataclass
class Instance:
    name: str
    config: dict
    ops: Operations
    isotopes: pd.DataFrame
    nodes: pd.DataFrame
    patients: pd.DataFrame
    travel_min: pd.DataFrame
    dist_km: pd.DataFrame

    # ------------------------------------------------------------------ sets
    @property
    def hospitals(self) -> list[str]:
        return [n for n in self.nodes.index if n != DEPOT]

    def eligible(self, hospital: str, isotope: str) -> bool:
        return bool(self.nodes.at[hospital, f"eligible_{isotope}"])

    def eligible_pairs(self) -> list[tuple[str, str]]:
        """The set E of (hospital, isotope) pairs."""
        return [(h, i) for h in self.hospitals for i in self.isotopes.index if self.eligible(h, i)]

    # ---------------------------------------------------------- derivations
    def add_derived(self) -> None:
        """(Re)compute derived patient columns and per-isotope daily caps."""
        p, ops = self.patients, self.ops
        lam = p["isotope"].map(self.isotopes["lambda_per_h"])
        direct = np.array([self.travel_min.at[DEPOT, h] for h in p["hospital"]])

        p["lower_mbq"] = (1 - ops.dose_tolerance) * p["dose_mbq"]
        p["upper_mbq"] = (1 + ops.dose_tolerance) * p["dose_mbq"]
        p["deadline_min"] = p["time_min"] - ops.lead_time_min
        p["direct_travel_min"] = direct
        # Latest batch finish if the vial had its own truck and drove straight there.
        p["latest_direct_batch_min"] = np.minimum(
            p["deadline_min"] - direct - ops.qc_min, ops.prod_end_min
        )
        p["lb_mbq"] = p["dose_mbq"] * production_multiplier(
            lam, p["time_min"], p["latest_direct_batch_min"]
        )
        # Daily cap relative to the provable lower bound (DESIGN_NOTES §5.4).
        lb_by_iso = p.groupby("isotope")["lb_mbq"].sum()
        self.isotopes["daily_cap_mbq"] = ops.capacity_factor * lb_by_iso.reindex(self.isotopes.index).fillna(0.0)

    # ------------------------------------------------------------ validation
    def validate(self) -> list[str]:
        """Return a list of problems (empty = instance is consistent and feasible per patient)."""
        issues: list[str] = []
        p, ops = self.patients, self.ops

        nodes = list(self.nodes.index)
        for name, m in (("travel_min", self.travel_min), ("dist_km", self.dist_km)):
            if list(m.index) != nodes or list(m.columns) != nodes:
                issues.append(f"{name} rows/cols do not match nodes")
            elif (m.values < 0).any() or not np.allclose(np.diag(m.values), 0):
                issues.append(f"{name} has negative entries or non-zero diagonal")

        for pid, r in p.iterrows():
            if r["hospital"] not in self.nodes.index:
                issues.append(f"{pid}: unknown hospital {r['hospital']}")
                continue
            if not self.eligible(r["hospital"], r["isotope"]):
                issues.append(f"{pid}: {r['hospital']} not eligible for {r['isotope']}")
            if r["deadline_min"] < self.nodes.at[r["hospital"], "receiving_open_min"]:
                issues.append(f"{pid}: deadline {min_to_hhmm(r['deadline_min'])} before receiving opens")
            if r["latest_direct_batch_min"] < ops.prod_start_min:
                issues.append(f"{pid}: unreachable even by a direct truck from the first batch")

        # A2 is a per-package limit; each vial is a package (A14). Worst case = earliest batch.
        lam = p["isotope"].map(self.isotopes["lambda_per_h"])
        worst = p["upper_mbq"] * production_multiplier(lam, p["time_min"], ops.prod_start_min)
        a2 = p["isotope"].map(self.isotopes["a2_mbq"])
        for pid in p.index[worst > a2]:
            issues.append(f"{pid}: worst-case vial activity exceeds A2")
        return issues

    # --------------------------------------------------------------- summary
    def summary(self) -> str:
        p, iso, ops = self.patients, self.isotopes, self.ops
        lam = p["isotope"].map(iso["lambda_per_h"])
        worst = p["upper_mbq"] * production_multiplier(lam, p["time_min"], ops.prod_start_min)
        p_a2 = worst / p["isotope"].map(iso["a2_mbq"])

        lines = [
            f"Instance '{self.name}': {len(self.hospitals)} hospitals, {len(p)} patients, "
            f"{len(iso)} isotopes",
            f"  depot->hospital travel: mean {self.travel_min.loc[DEPOT, self.hospitals].mean():.0f} min, "
            f"max {self.travel_min.loc[DEPOT, self.hospitals].max():.0f} min",
            f"  batch window {min_to_hhmm(ops.prod_start_min)}-{min_to_hhmm(ops.prod_end_min)} "
            f"({len(ops.batch_slots)} slots of {ops.batch_slot_min} min), lead {ops.lead_time_min} min, "
            f"QC {ops.qc_min} min",
            "",
            f"  {'isotope':8} {'hosp':>4} {'pts':>4} {'prescribed':>11} {'LB':>11} {'irreduc.':>9} "
            f"{'cap':>11} {'max vial/A2':>11} {'delay budget':>12}",
        ]
        for i, r in iso.iterrows():
            pi = p[p["isotope"] == i]
            n_h = sum(self.eligible(h, i) for h in self.hospitals)
            presc, lb = pi["dose_mbq"].sum(), pi["lb_mbq"].sum()
            irr = f"{(lb / presc - 1) * 100:.1f}%" if presc else "-"
            a2 = f"{p_a2[pi.index].max() * 100:.2f}%" if len(pi) else "-"
            lines.append(
                f"  {i:8} {n_h:>4} {len(pi):>4} {presc:>9.0f} MBq {lb:>7.0f} MBq {irr:>9} "
                f"{r['daily_cap_mbq']:>7.0f} MBq {a2:>11} "
                f"{delay_budget_h(r['lambda_per_h'], ops.dose_tolerance):>10.1f} h"
            )
        lines += [
            "",
            "  LB = minimum production if every vial had its own direct truck at the latest batch.",
            "  irreduc. = over-production no routing can remove (lead time + QC + direct travel).",
        ]
        return "\n".join(lines)

    # -------------------------------------------------------------------- I/O
    def save(self, out_dir: str | Path) -> Path:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        meta = {"name": self.name, "ops": asdict(self.ops), "config": self.config}
        (out / "instance.json").write_text(json.dumps(meta, indent=2, default=str))
        self.isotopes.to_csv(out / "isotopes.csv")
        self.nodes.to_csv(out / "nodes.csv")
        self.patients.to_csv(out / "patients.csv")
        self.travel_min.to_csv(out / "travel_min.csv")
        self.dist_km.to_csv(out / "dist_km.csv")
        return out

    @classmethod
    def load(cls, in_dir: str | Path) -> "Instance":
        d = Path(in_dir)
        meta = json.loads((d / "instance.json").read_text())
        read = lambda f: pd.read_csv(d / f, index_col=0)  # noqa: E731
        nodes = read("nodes.csv")
        for c in [c for c in nodes.columns if c.startswith("eligible_")]:
            nodes[c] = nodes[c].astype(bool)
        return cls(
            name=meta["name"], config=meta["config"], ops=Operations(**meta["ops"]),
            isotopes=read("isotopes.csv"), nodes=nodes, patients=read("patients.csv"),
            travel_min=read("travel_min.csv"), dist_km=read("dist_km.csv"),
        )
