"""Phase 2a MILP: routing + vial-to-trip assignment + batch timing (DESIGN_NOTES §5.7).

Constraint labels (C1-C11) match the design notes. Scope: no shared
resources (fleet cap, dispatch limit -> Phase 2b) and no manufacturing
constraints (-> Phase 7). Without shared resources the model separates by
isotope; it is still built as one model because 2b links the isotopes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import gurobipy as gp
import numpy as np
from gurobipy import GRB

from .checker import Trip, latest_batch
from .decay import production_multiplier
from .instance import DEPOT, Instance

# Only matters if two stops are 0 min apart with 0 service time: keeps the
# time-propagation constraints (C7) strict so they still rule out subtours.
_EPS_MIN = 0.01


@dataclass
class SolveSettings:
    w_over: float = 100.0      # per dose-equivalent of decay waste
    w_dist: float = 1.0        # per km
    w_trip: float = 20.0       # per trip used
    mode: str = "weighted"     # "weighted" | "lexicographic"
    priority: tuple[str, ...] = ("over", "dist", "trip")  # lexicographic order, highest first
    reltol: float = 0.0        # lexicographic: allowed relative loss on higher-priority objectives
    time_limit: float = 60.0
    mip_gap: float = 1e-4
    verbose: bool = False


@dataclass
class SolveResult:
    status: str
    trips: list[Trip]
    objectives: dict[str, float] = field(default_factory=dict)   # over (dose-eq), dist (km), trip
    claimed_produced: dict[str, float] = field(default_factory=dict)
    mip_gap: float = float("nan")
    runtime_s: float = float("nan")
    n_vars: int = 0
    n_constrs: int = 0


class Phase2aModel:
    def __init__(self, inst: Instance, settings: SolveSettings | None = None):
        self.inst, self.s = inst, settings or SolveSettings()
        self.env = gp.Env(params={"OutputFlag": int(self.s.verbose)})
        self.m = gp.Model(f"phase2a_{inst.name}", env=self.env)
        self._build()

    # ----------------------------------------------------------------- build
    def _build(self) -> None:
        inst, m, ops = self.inst, self.m, self.inst.ops
        pts, nodes, t, d = inst.patients, inst.nodes, inst.travel_min, inst.dist_km
        slots = ops.batch_slots
        self.x, self.y, self.z, self.a, self.n, self.u = {}, {}, {}, {}, {}, {}
        self.groups: dict[str, dict] = {}
        over_terms, n_patients = [], 0

        for iso in inst.isotopes.index:
            P = list(pts.index[pts["isotope"] == iso])
            if not P:
                continue
            lam = inst.isotopes.at[iso, "lambda_per_h"]
            Q = int(inst.isotopes.at[iso, "vials_per_truck"])
            H = sorted(pts.loc[P, "hospital"].unique())
            N = [DEPOT] + H
            K = list(range(len(P)))                     # one candidate trip per patient
            at_h = {h: [p for p in P if pts.at[p, "hospital"] == h] for h in H}
            S_p = {p: [s for s in slots if s <= pts.at[p, "latest_direct_batch_min"]] for p in P}
            n_max = max(slots.index(S_p[p][-1]) for p in P)
            b_max = slots[n_max]
            a_lo = {h: float(nodes.at[h, "receiving_open_min"]) for h in H}
            a_hi = {h: float(pts.loc[at_h[h], "deadline_min"].max()) for h in H}
            self.groups[iso] = dict(P=P, H=H, K=K, at_h=at_h, S_p=S_p)

            for k in K:
                self.y[iso, k] = m.addVar(vtype=GRB.BINARY, name=f"y[{iso},{k}]")
                self.n[iso, k] = m.addVar(vtype=GRB.INTEGER, lb=0, ub=n_max, name=f"n[{iso},{k}]")
                for uu in N:
                    for vv in N:
                        if uu != vv:
                            self.x[iso, uu, vv, k] = m.addVar(vtype=GRB.BINARY, name=f"x[{iso},{uu},{vv},{k}]")
                for h in H:
                    self.a[iso, h, k] = m.addVar(lb=a_lo[h], ub=a_hi[h], name=f"a[{iso},{h},{k}]")
                for p in P:
                    self.z[p, k] = m.addVar(vtype=GRB.BINARY, name=f"z[{p},{k}]")
            for p in P:
                for s in S_p[p]:
                    self.u[p, s] = m.addVar(vtype=GRB.BINARY, name=f"u[{p},{s}]")

            x, y, z, a, n, u = self.x, self.y, self.z, self.a, self.n, self.u
            B = {k: ops.prod_start_min + ops.batch_slot_min * n[iso, k] for k in K}

            for p in P:
                m.addConstr(gp.quicksum(z[p, k] for k in K) == 1, f"C1[{p}]")
                m.addConstr(gp.quicksum(u[p, s] for s in S_p[p]) == 1, f"C9[{p}]")
            for k in K:
                for p in P:
                    h = pts.at[p, "hospital"]
                    m.addConstr(z[p, k] <= gp.quicksum(x[iso, uu, h, k] for uu in N if uu != h), f"C2[{p},{k}]")
                    # C8: per-vial deadline; M = latest possible arrival at h minus this deadline
                    m.addConstr(a[iso, h, k] <= pts.at[p, "deadline_min"]
                                + (a_hi[h] - pts.at[p, "deadline_min"]) * (1 - z[p, k]), f"C8[{p},{k}]")
                    # C10: vial not produced later than its trip's batch; M = latest slot - first slot
                    m.addConstr(gp.quicksum(s * u[p, s] for s in S_p[p])
                                <= B[k] + (S_p[p][-1] - ops.prod_start_min) * (1 - z[p, k]), f"C10[{p},{k}]")
                m.addConstr(gp.quicksum(z[p, k] for p in P) <= Q * y[iso, k], f"C3[{iso},{k}]")
                m.addConstr(gp.quicksum(x[iso, DEPOT, h, k] for h in H) == y[iso, k], f"C4out[{iso},{k}]")
                m.addConstr(gp.quicksum(x[iso, h, DEPOT, k] for h in H) == y[iso, k], f"C4in[{iso},{k}]")
                for h in H:
                    inflow = gp.quicksum(x[iso, uu, h, k] for uu in N if uu != h)
                    m.addConstr(inflow == gp.quicksum(x[iso, h, vv, k] for vv in N if vv != h), f"C5flow[{iso},{h},{k}]")
                    m.addConstr(inflow <= 1, f"C5once[{iso},{h},{k}]")
                    # C6: first stop; M chosen so the constraint is slack when the arc is unused
                    lead = ops.qc_min + t.at[DEPOT, h]
                    M6 = b_max + lead - a_lo[h]
                    m.addConstr(a[iso, h, k] >= B[k] + lead - M6 * (1 - x[iso, DEPOT, h, k]), f"C6[{iso},{h},{k}]")
                    for vv in H:
                        if vv != h:
                            gap = max(nodes.at[h, "service_min"] + t.at[h, vv], _EPS_MIN)
                            M7 = a_hi[h] + gap - a_lo[vv]
                            m.addConstr(a[iso, vv, k] >= a[iso, h, k] + gap - M7 * (1 - x[iso, h, vv, k]),
                                        f"C7[{iso},{h},{vv},{k}]")
                if k + 1 < len(K):
                    m.addConstr(y[iso, k] >= y[iso, k + 1], f"C11[{iso},{k}]")

            for p in P:
                mu = production_multiplier(lam, pts.at[p, "time_min"], np.array(S_p[p]))
                over_terms += [float(mu_s) * u[p, s] for mu_s, s in zip(mu, S_p[p])]
            n_patients += len(P)

        self.obj = {
            "over": gp.quicksum(over_terms),     # + constant (-n_patients) added back in reporting
            "dist": gp.quicksum(d.at[k[1], k[2]] * v for k, v in self.x.items()),
            "trip": gp.quicksum(self.y.values()),
        }
        self._over_const = -n_patients
        w = {"over": self.s.w_over, "dist": self.s.w_dist, "trip": self.s.w_trip}
        if self.s.mode == "weighted":
            m.setObjective(gp.quicksum(w[k] * e for k, e in self.obj.items()), GRB.MINIMIZE)
        elif self.s.mode == "lexicographic":
            m.ModelSense = GRB.MINIMIZE
            top = len(self.s.priority)
            for idx, key in enumerate(self.s.priority):
                m.setObjectiveN(self.obj[key], index=idx, priority=top - idx, weight=1.0,
                                reltol=self.s.reltol, name=key)
        else:
            raise ValueError(f"unknown mode {self.s.mode}")
        m.Params.TimeLimit = self.s.time_limit
        m.Params.MIPGap = self.s.mip_gap
        m.update()

    # ----------------------------------------------------------------- solve
    def solve(self) -> SolveResult:
        m = self.m
        try:
            m.optimize()
        except gp.GurobiError as e:
            if "size-limited" not in str(e):
                raise
            # Restricted pip license: <= 2,000 variables and constraints (TIMELINE O10).
            return SolveResult(status="license_limit", trips=[], n_vars=m.NumVars, n_constrs=m.NumConstrs)
        status = {GRB.OPTIMAL: "optimal", GRB.TIME_LIMIT: "time_limit",
                  GRB.INFEASIBLE: "infeasible"}.get(m.Status, f"status_{m.Status}")
        res = SolveResult(status=status, trips=[], n_vars=m.NumVars, n_constrs=m.NumConstrs,
                          runtime_s=m.Runtime)
        if m.SolCount == 0:
            return res
        res.mip_gap = m.MIPGap if m.IsMIP and self.s.mode == "weighted" else float("nan")
        res.trips = self._extract_trips()
        res.objectives = {"over": self.obj["over"].getValue() + self._over_const,
                          "dist": self.obj["dist"].getValue(), "trip": self.obj["trip"].getValue()}
        pts = self.inst.patients
        for (p, s), v in self.u.items():
            if v.X > 0.5:
                res.claimed_produced[p] = float(pts.at[p, "dose_mbq"] * production_multiplier(
                    self.inst.isotopes.at[pts.at[p, "isotope"], "lambda_per_h"], pts.at[p, "time_min"], s))
        return res

    def _extract_trips(self) -> list[Trip]:
        ops, trips = self.inst.ops, []
        for iso, g in self.groups.items():
            for k in g["K"]:
                if self.y[iso, k].X < 0.5:
                    continue
                stops, cur = [], DEPOT
                while True:
                    nxt = next(v for v in [DEPOT] + g["H"]
                               if v != cur and self.x[iso, cur, v, k].X > 0.5)
                    if nxt == DEPOT:
                        break
                    stops.append(nxt)
                    cur = nxt
                drops = {h: [p for p in g["at_h"][h] if self.z[p, k].X > 0.5] for h in stops}
                batch = ops.prod_start_min + ops.batch_slot_min * int(round(self.n[iso, k].X))
                trip = Trip(isotope=iso, batch_min=batch, stops=stops, drops=drops)
                # B_k isn't in the objective (only the vials' slots are), so the solver may leave it
                # earlier than the route allows. Re-time each trip to its latest feasible slot: a free
                # improvement that never breaks a deadline (DESIGN_NOTES §5.2).
                latest = latest_batch(self.inst, trip)
                trip.batch_min = max([s for s in ops.batch_slots if s <= latest + 1e-6] + [batch])
                trips.append(trip)
        return trips


def solve(inst: Instance, settings: SolveSettings | None = None) -> SolveResult:
    return Phase2aModel(inst, settings).solve()
