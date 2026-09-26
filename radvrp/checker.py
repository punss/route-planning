"""Independent solution checker and trip simulator (DESIGN_NOTES §5.7, validation item 5).

This module deliberately knows nothing about the MILP. It takes a plan --
for each trip: isotope, batch time, stop order, which vials are dropped
where -- and recomputes the physics from scratch: departure, arrivals
(waiting if a hot lab isn't open yet), deadlines, capacity, distances and
the activity each vial needs. If the MILP formulation has a bug, the solver
will still report "optimal"; this is what catches it.

It is also the single source of truth for reported times and activities,
so reports never depend on MILP variable values (which may carry slack).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .config import min_to_hhmm
from .decay import production_multiplier
from .instance import DEPOT, Instance

TOL = 1e-6


@dataclass
class Trip:
    isotope: str
    batch_min: int
    stops: list[str]                  # hospitals in visiting order
    drops: dict[str, list[str]]       # hospital -> patient ids dropped there

    @property
    def patients(self) -> list[str]:
        return [p for h in self.stops for p in self.drops.get(h, [])]


@dataclass
class TripSchedule:
    depart_min: float
    arrival_min: dict[str, float]     # hospital -> arrival time
    return_min: float
    distance_km: float
    latest_batch_min: float           # latest batch finish that keeps every deadline (P*_k)


def simulate(inst: Instance, trip: Trip) -> TripSchedule:
    """Forward pass: earliest schedule for a trip leaving at batch + QC."""
    t, d, nodes, ops = inst.travel_min, inst.dist_km, inst.nodes, inst.ops
    now = trip.batch_min + ops.qc_min
    depart, prev, dist, arrival = now, DEPOT, 0.0, {}
    for h in trip.stops:
        now = max(now + t.at[prev, h], nodes.at[h, "receiving_open_min"])  # wait for hot lab
        arrival[h] = now
        now += nodes.at[h, "service_min"]
        dist += d.at[prev, h]
        prev = h
    ret = now + t.at[prev, DEPOT]
    dist += d.at[prev, DEPOT]
    return TripSchedule(depart, arrival, ret, dist, latest_batch(inst, trip))


def latest_batch(inst: Instance, trip: Trip) -> float:
    """Backward pass (DESIGN_NOTES §5.2): latest continuous batch time meeting all deadlines.

    Waiting for a hot lab only happens when arriving early, and leaving later
    removes waiting, so the latest arrival allowed at each stop is limited only
    by its own deadlines and by the next stop's latest arrival.
    """
    t, nodes, ops, p = inst.travel_min, inst.nodes, inst.ops, inst.patients
    latest_next = np.inf
    for j in range(len(trip.stops) - 1, -1, -1):
        h = trip.stops[j]
        own = min((p.at[q, "deadline_min"] for q in trip.drops.get(h, [])), default=np.inf)
        if j + 1 < len(trip.stops):
            nxt = trip.stops[j + 1]
            latest_next = latest_next - nodes.at[h, "service_min"] - t.at[h, nxt]
        latest_next = min(own, latest_next)
    first = trip.stops[0] if trip.stops else DEPOT
    return min(latest_next - t.at[DEPOT, first] - ops.qc_min, ops.prod_end_min)


def produced_mbq(inst: Instance, patient: str, batch_min: float) -> float:
    r = inst.patients.loc[patient]
    lam = inst.isotopes.at[r["isotope"], "lambda_per_h"]
    return float(r["dose_mbq"] * production_multiplier(lam, r["time_min"], batch_min))


@dataclass
class CheckResult:
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def check(inst: Instance, trips: list[Trip], claimed_produced: dict[str, float] | None = None,
          claimed_distance_km: float | None = None) -> CheckResult:
    """Verify a plan against every rule. `claimed_*` are the solver's numbers, if any."""
    res, p, ops = CheckResult(), inst.patients, inst.ops
    seen: dict[str, int] = {}

    for n, trip in enumerate(trips):
        tag = f"trip {n} ({trip.isotope} @ {min_to_hhmm(trip.batch_min)})"
        if len(set(trip.stops)) != len(trip.stops):
            res.violations.append(f"{tag}: visits a hospital twice")
        if not trip.stops:
            res.violations.append(f"{tag}: no stops")
            continue
        if trip.batch_min not in ops.batch_slots:
            res.violations.append(f"{tag}: batch time not on the slot grid / outside window")
        cap = inst.isotopes.at[trip.isotope, "vials_per_truck"]
        if len(trip.patients) > cap:
            res.violations.append(f"{tag}: {len(trip.patients)} vials > capacity {cap}")
        for h, pids in trip.drops.items():
            if h not in trip.stops:
                res.violations.append(f"{tag}: drops at {h} which is not on the route")
            if pids and not inst.eligible(h, trip.isotope):
                res.violations.append(f"{tag}: {h} not eligible for {trip.isotope}")
            for q in pids:
                seen[q] = seen.get(q, 0) + 1
                if q not in p.index:
                    res.violations.append(f"{tag}: unknown patient {q}")
                    continue
                if p.at[q, "isotope"] != trip.isotope:
                    res.violations.append(f"{tag}: {q} needs {p.at[q, 'isotope']}")
                if p.at[q, "hospital"] != h:
                    res.violations.append(f"{tag}: {q} dropped at {h}, belongs to {p.at[q, 'hospital']}")

        sched = simulate(inst, trip)
        for h in trip.stops:
            for q in trip.drops.get(h, []):
                if q in p.index and sched.arrival_min[h] > p.at[q, "deadline_min"] + TOL:
                    res.violations.append(
                        f"{tag}: {q} arrives {min_to_hhmm(sched.arrival_min[h])}, "
                        f"deadline {min_to_hhmm(p.at[q, 'deadline_min'])}")
        if trip.batch_min > sched.latest_batch_min + TOL:
            res.violations.append(f"{tag}: batch later than latest feasible {min_to_hhmm(sched.latest_batch_min)}")
        if trip.stops and not any(trip.drops.get(h) for h in trip.stops):
            res.warnings.append(f"{tag}: carries no vials")
        for h in trip.stops:
            if not trip.drops.get(h):
                res.warnings.append(f"{tag}: visits {h} without dropping anything")

    for q in p.index:
        if seen.get(q, 0) != 1:
            res.violations.append(f"patient {q} delivered {seen.get(q, 0)} times")

    if claimed_produced:
        for trip in trips:
            for q in trip.patients:
                true = produced_mbq(inst, q, trip.batch_min)
                got = claimed_produced.get(q)
                if got is None:
                    continue
                if got < true * (1 - 1e-6):
                    res.violations.append(f"{q}: solver claims {got:.1f} MBq, physics needs {true:.1f}")
                elif got > true * (1 + 1e-6):
                    res.warnings.append(f"{q}: solver's slot is earlier than its trip's batch "
                                        f"({got:.1f} vs {true:.1f} MBq) - objective slack")
    if claimed_distance_km is not None:
        true = sum(simulate(inst, tr).distance_km for tr in trips)
        if abs(true - claimed_distance_km) > 1e-3 * max(1.0, true):
            res.violations.append(f"distance: solver claims {claimed_distance_km:.2f} km, routes give {true:.2f}")
    return res
