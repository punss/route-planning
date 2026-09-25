"""Phase 1: synthetic instance generator.

Two modes (DESIGN_NOTES §9):
    random  - sample a Boston-metro instance from distributions in the config
    manual  - build a hand-specified toy instance (explicit travel matrix/patients)

All randomness flows from one `seed`, so an instance is fully reproducible
from its config. Treatment times are sampled only where the patient is
servable by a direct truck, so every generated instance is feasible per
patient by construction (fleet/capacity feasibility is the solver's job).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import geo
from .config import hhmm_to_min
from .decay import decay_constant_per_h
from .instance import DEPOT, Instance, Operations


def generate(cfg: dict) -> Instance:
    isotopes = _isotope_table(cfg)
    ops = _operations(cfg)
    if cfg.get("mode", "random") == "manual":
        nodes, travel, dist, patients = _manual(cfg, isotopes)
    else:
        rng = np.random.default_rng(cfg["seed"])
        nodes = _sample_nodes(cfg, isotopes, rng)
        d, t = geo.road_matrices(nodes["lat"], nodes["lon"],
                                 cfg["geography"]["circuity"], cfg["geography"]["speed_kmh"])
        dist = pd.DataFrame(d, index=nodes.index, columns=nodes.index)
        travel = pd.DataFrame(t, index=nodes.index, columns=nodes.index)
        patients = _sample_patients(cfg, isotopes, ops, nodes, travel, rng)

    inst = Instance(name=cfg["name"], config=_public_config(cfg), ops=ops, isotopes=isotopes,
                    nodes=nodes, patients=patients, travel_min=travel, dist_km=dist)
    inst.add_derived()
    return inst


# --------------------------------------------------------------------- tables
def _isotope_table(cfg: dict) -> pd.DataFrame:
    rows = {}
    for name, d in cfg["isotope_data"].items():
        rows[name] = {
            "half_life_h": d["half_life_h"],
            "lambda_per_h": decay_constant_per_h(d["half_life_h"]),
            "a2_mbq": d["a2_tbq"] * 1e6,
            "vials_per_truck": d["vials_per_truck"],
        }
    df = pd.DataFrame.from_dict(rows, orient="index")
    df.index.name = "isotope"
    return df


def _operations(cfg: dict) -> Operations:
    o = cfg["operations"]
    start, end = (hhmm_to_min(t) for t in o["production_window"])
    return Operations(
        lead_time_min=o["lead_time_min"], qc_min=o["qc_min"],
        prod_start_min=start, prod_end_min=end, batch_slot_min=o["batch_slot_min"],
        dose_tolerance=o["dose_tolerance"], capacity_factor=o["capacity_factor"],
        fleet_size=o.get("fleet_size"), dispatch_per_slot=o.get("dispatch_per_slot"),
    )


def _public_config(cfg: dict) -> dict:
    return {k: v for k, v in cfg.items() if k != "isotope_data"}


# --------------------------------------------------------------- random mode
def _sample_point(rng, center, kind: str, g: dict, coast_mask: bool):
    for _ in range(1000):
        if kind == "academic":
            r = abs(rng.normal(0.0, g["academic_radius_sd_km"]))
        else:  # area-uniform in a ring: r = sqrt(U(r1^2, r2^2))
            r1, r2 = g["community_ring_km"]
            r = np.sqrt(rng.uniform(r1**2, r2**2))
        lat, lon = geo.offset(center, r, rng.uniform(0, 2 * np.pi))
        if not coast_mask or geo.on_land(lat, lon):
            return lat, lon
    raise RuntimeError("Could not sample a land point; check geography config")


def _sample_nodes(cfg: dict, isotopes: pd.DataFrame, rng) -> pd.DataFrame:
    g, n = cfg["geography"], cfg["network"]
    center = tuple(g["center"])
    recv = hhmm_to_min(n["receiving_open"])

    rows = [{"node_id": DEPOT, "kind": "depot", "type": "depot",
             "lat": g["depot"][0], "lon": g["depot"][1],
             "receiving_open_min": 0, "service_min": 0}]
    for kind, count, prefix in (("academic", n["n_academic"], "A"),
                                ("community", n["n_community"], "C")):
        for k in range(count):
            lat, lon = _sample_point(rng, center, kind, g, g.get("coast_mask", True))
            rows.append({"node_id": f"{prefix}{k + 1:02d}", "kind": "hospital", "type": kind,
                         "lat": lat, "lon": lon, "receiving_open_min": recv,
                         "service_min": n["service_min"]})
    nodes = pd.DataFrame(rows).set_index("node_id")

    # Eligibility: Bernoulli per (hospital, isotope) by hospital type.
    hosp = nodes.index[nodes["kind"] == "hospital"]
    for iso in isotopes.index:
        probs = nodes.loc[hosp, "type"].map(lambda t: n["eligibility_prob"][t][iso])
        elig = rng.random(len(hosp)) < probs.values
        if not elig.any():
            # Every isotope needs at least one eligible hospital: pick among the
            # hospitals of the type most likely to be eligible.
            best = probs.values == probs.values.max()
            elig[rng.choice(np.flatnonzero(best))] = True
        nodes[f"eligible_{iso}"] = False
        nodes.loc[hosp, f"eligible_{iso}"] = elig
    return nodes


def _sample_dose(model: dict, weight: float, rng) -> float:
    if model["kind"] == "lognormal":
        x = model["median_mbq"] * np.exp(model["sigma"] * rng.standard_normal())
        return float(np.clip(x, model["min_mbq"], model["max_mbq"]))
    if model["kind"] == "weight_based":
        x = rng.uniform(*model["mbq_per_kg"]) * weight
        return float(min(x, model["max_mbq"])) if model.get("max_mbq") else float(x)
    raise ValueError(f"Unknown dose model {model['kind']}")


def _sample_patients(cfg, isotopes, ops: Operations, nodes, travel, rng) -> pd.DataFrame:
    n, pc = cfg["network"], cfg["patients"]
    w = pc["weight_kg"]
    t_lo, t_hi = (hhmm_to_min(t) for t in pc["treatment_window"])
    grid = np.arange(t_lo, t_hi + 1, pc["treatment_grid_min"])
    hosp = nodes.index[nodes["kind"] == "hospital"]

    # Patient counts: Poisson per eligible (hospital, isotope).
    demand: list[tuple[str, str]] = []
    for h in hosp:
        for iso in isotopes.index:
            if nodes.at[h, f"eligible_{iso}"]:
                lam = n["patients_mean"][nodes.at[h, "type"]][iso] * n.get("demand_scale", 1.0)
                demand += [(h, iso)] * int(rng.poisson(lam))
    for iso in isotopes.index:
        eligible = [h for h in hosp if nodes.at[h, f"eligible_{iso}"]]
        while sum(d[1] == iso for d in demand) < n.get("min_patients_per_isotope", 0):
            demand.append((str(rng.choice(eligible)), iso))

    rows = []
    for k, (h, iso) in enumerate(demand):
        # Earliest treatment time servable by a direct truck from the first batch,
        # and not before the hot lab can receive (+ lead time).
        earliest = max(
            nodes.at[h, "receiving_open_min"] + ops.lead_time_min,
            ops.prod_start_min + ops.qc_min + travel.at[DEPOT, h] + ops.lead_time_min,
        )
        feasible = grid[grid >= earliest]
        if feasible.size == 0:
            raise ValueError(f"No feasible treatment time for {h} ({iso}); widen the treatment window")
        weight = float(np.clip(rng.normal(w["mean"], w["sd"]), w["min"], w["max"]))
        rows.append({
            "patient_id": f"P{k + 1:03d}", "hospital": h, "isotope": iso,
            "weight_kg": round(weight, 1),
            "dose_mbq": round(_sample_dose(cfg["isotope_data"][iso]["dose_model"], weight, rng), 1),
            "time_min": int(rng.choice(feasible)),
        })
    return pd.DataFrame(rows).set_index("patient_id")


# --------------------------------------------------------------- manual mode
def _manual(cfg: dict, isotopes: pd.DataFrame):
    m, n = cfg["manual"], cfg["network"]
    recv = hhmm_to_min(n["receiving_open"])

    rows = [{"node_id": DEPOT, "kind": "depot", "type": "depot", "lat": np.nan, "lon": np.nan,
             "receiving_open_min": 0, "service_min": 0}]
    for h in m["hospitals"]:
        rows.append({"node_id": h["id"], "kind": "hospital", "type": h["type"],
                     "lat": h.get("lat", np.nan), "lon": h.get("lon", np.nan),
                     "receiving_open_min": recv, "service_min": n["service_min"]})
    nodes = pd.DataFrame(rows).set_index("node_id")
    for iso in isotopes.index:
        nodes[f"eligible_{iso}"] = [False] + [iso in h["eligible"] for h in m["hospitals"]]

    ids = m["travel_min"]["nodes"]
    travel = pd.DataFrame(np.array(m["travel_min"]["matrix"], dtype=float), index=ids, columns=ids)
    travel = travel.loc[nodes.index, nodes.index]
    dist = travel / 60.0 * m["speed_kmh"]

    patients = pd.DataFrame([
        {"patient_id": p["id"], "hospital": p["hospital"], "isotope": p["isotope"],
         "weight_kg": p.get("weight_kg", np.nan), "dose_mbq": float(p["dose_mbq"]),
         "time_min": hhmm_to_min(p["time"])}
        for p in m["patients"]
    ]).set_index("patient_id")
    return nodes, travel, dist, patients
