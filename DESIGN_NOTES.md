# Design Notes — Decay-Constrained VRP for Radiopharmaceutical Delivery

Living document: this is the source of truth for **notation, formulation,
assumptions and parameter choices**. `plan.md` holds the project brief;
`TIMELINE.md` holds the history of how each decision here was reached (the
`D#` / `O#` IDs refer to it).

Status: **Phase 1 complete; Phase 2a formulation fixed (§5.7).**
Manufacturing-side modelling is deferred to **Phase 7** and collected in §10
(D24). Phases 2–6 treat the manufacturer as a customer of the routing
output: each trip hands over a production order (isotope, ready-by time,
activity per vial).

---

## 1. Problem in one paragraph

Each morning a single depot produces three therapeutic radiopharmaceuticals
(Y-90, Pb-212, At-211) and trucks deliver them to hospitals in the Boston
metro area. Every patient has a clinic-scheduled treatment time and a
prescribed activity, and gets their own vial. A truck carries one isotope
only. **Each truck's vials are produced as one batch, finished just in time
for that truck's route** (D13). The route fixes how early the truck must
leave, which fixes how early its batch must be made, which fixes how much
extra activity has to be produced to cover the decay. Routing is therefore
an input to production dosing. That coupling is the research question.

---

## 2. Units and terminology (E5)

| Symbol / term | Meaning | Unit in code |
|---|---|---|
| Activity | Decays per second (A = λN), i.e. how much radioactive material | **MBq** |
| `x_p` | Prescribed activity for patient p, *at* their treatment time | MBq |
| Produced activity | Activity at batch finish that decays to `x_p` at τ_p | MBq |
| Time | Clock time of the delivery day | **minutes after midnight** |
| Distance | Road distance estimate | km |
| Absorbed dose (Gy/rad) | Energy deposited in tissue | *not modelled* |

Volume and concentration are packaging details and are not modelled.
Manufacturers usually fix concentration and vary volume (e.g. Pluvicto:
1,000 MBq/mL, 7.5–12.5 mL); the activity maths is unaffected.

---

## 3. Notation

### Sets
| Symbol | Meaning |
|---|---|
| `I` | Isotopes (drugs). Currently {Y-90, Pb-212, At-211} |
| `H` | Hospitals; node `0` is the depot; `V = {0} ∪ H` |
| `E ⊆ H × I` | Eligibility: hospital h can administer isotope i |
| `P` | Patients; `P_i` those needing isotope i; `P_{h,i}` those at h needing i |
| `K_i` | Candidate trips for isotope i (1 trip = 1 route = 1 production batch; a vehicle may do several trips, D21) |
| `S` | Batch-finish time slots `{P_min, P_min+Δ, …, P_max}` |

### Parameters
| Symbol | Meaning | Source / default |
|---|---|---|
| `T½_i`, `λ_i = ln2 / T½_i` | Half-life, decay constant | §6 |
| `A2_i` | Type A package limit (per vial here) | 49 CFR 173.435 |
| `Q_i` | Vials per truck for isotope i | §6 (assumption) |
| `C_i` | Daily production cap, isotope i (MBq) — **Phase 7 only** (§10) | `κ · LB_i` (§5.4) |
| `h(p)`, `i(p)` | Patient p's hospital and isotope | generated |
| `x_p` | Prescribed activity | §6 dose models |
| `[L_p, U_p]` | Tolerance band = `[(1−β)x_p, (1+β)x_p]`. Phases 2–6: robustness analysis only; Phase 7: constraint (§10) | β = 0.20 (D4) |
| `τ_p` | Clinic-scheduled treatment time (fixed input, D3) | generated |
| `ℓ` | Lead time: vial on site ≥ ℓ before τ_p | 120 min (D11) |
| `q` | QC/release + packaging time between batch finish and departure | 60 min |
| `[P_min, P_max]` | Production window for batch finish times | 03:00–12:00 |
| `t_{uv}`, `d_{uv}` | Travel time (min) and distance (km), u,v ∈ V | §4 |
| `σ_h` | Service time at hospital (receipt, survey, paperwork) | 15 min |
| `e_h` | Hospital's earliest receiving time (hot-lab opens) | 06:00 |
| `K` | Fleet cap: max trips on the road at once (optional, D19) | unset (off) |
| `m` | Dispatch limit: trucks loaded/released per slot, shared across isotopes (D20) | 2 |
| `ρ` | Depot turnaround between trips (unload, survey, reload) (D21) | 30 min |

### Derived per patient
- Deadline: `δ_p = τ_p − ℓ` (vial must arrive by then).
- Production multiplier for a batch finishing at time `P`:
  `μ_p(P) = exp(λ_{i(p)} · (τ_p − P))`, so produced activity = `x_p · μ_p(P)`.

### Decision variables
Fixed for Phase 2a in §5.7. In short: routes, vial→trip assignment and
batch time per trip. Every patient receives exactly `x_p` in Phases 2–6.
The soft dose target (D8) belongs to Phase 7 (§10).

---

## 4. Geography and travel

- Metro: Boston. Centre (42.3601, −71.0589). Depot default (42.53, −71.20),
  near Burlington on the Route 128 corridor, north-west of the city. This is
  a plausible industrial location, **not** a real facility. Configurable.
- Hospitals are of two types:
  - *Academic* hospitals cluster near the centre (radius ~ |N(0, 3 km)|;
    think Longwood Medical Area).
  - *Community* hospitals are spread uniformly by area over a 5–40 km ring.
- A crude coastline mask (piecewise-linear longitude limit by latitude)
  rejects points that fall in Massachusetts Bay.
- Travel time = great-circle distance × **circuity factor 1.3** ÷
  **40 km/h**. Circuity is the ratio of road distance to straight-line
  distance; empirical studies put it at roughly 1.2–1.4 for road networks.
  Symmetric and time-invariant. Phase 5 replaces this with real road data.

---

## 5. Formulation core

### 5.1 Route invariance for a fixed batch time (E3)
For a vial produced at `P` and administered at `τ_p`, decay depends only on
`τ_p − P`:

`exp(λ(a − P)) · exp(λ(τ_p − a)) = exp(λ(τ_p − P))` for any arrival `a`.

*Consequence:* once `P_k` is fixed, where the vial spends its time (truck
or hospital shelf) doesn't matter. The route matters only because it limits
`P_k`.

### 5.2 Latest feasible batch time for a route
Let truck k visit stops `j_1, …, j_n` and let `T_k(j)` be the time from
departure until arrival at stop j (travel plus service at earlier stops).
Truck k departs at `P_k + q`, and every vial it carries must meet its
deadline:

`P_k + q + T_k(h(p)) ≤ δ_p   for all p on truck k`

`⇒ P_k ≤ P*_k := min_{p on k} ( δ_p − T_k(h(p)) ) − q`,  also `P_k ≤ P_max`.

Over-production is decreasing in `P_k`, so the optimum sets
`P_k = min(P*_k, P_max)`, or the latest slot at or below it once
discretized. The truck may wait at a hospital if it arrives before `e_h`.
Waiting never hurts dosing (§5.1).

**Intuition (interview version):** *the most time-critical stop on a
route sets the production time for every vial on that truck.* One early
patient on a long route inflates the activity of all the other vials.

### 5.3 Discretization (the MILP approximation)
`x_p · exp(λ(τ_p − P_k))` with continuous `P_k`, multiplied by binary
assignment variables, is nonlinear. We restrict `P_k` to slots `s ∈ S`
(default Δ = 30 min) and precompute

`c_{p,s} = x_p · exp(λ_{i(p)} (τ_p − s))`.

Rounding `P*_k` down to a slot is conservative: always feasible, slightly
over-producing. Worst-case over-production from rounding is a factor of
`exp(λΔ)`: At-211 ≈ 4.9%, Pb-212 ≈ 3.3%, Y-90 ≈ 0.5% at Δ = 30 min. This is
the "discretization error" Phase 3 will measure and Phase 4 will remove.

### 5.4 Irreducible vs routing-induced over-production
The latest any vial could ever be produced is if it had a truck to itself
and drove straight there:

`P^direct_p = min( δ_p − t_{0,h(p)} − q, P_max )`

`LB_p = x_p · exp(λ (τ_p − P^direct_p))`  (minimum possible production for p)

`LB_i = Σ_{p ∈ P_i} LB_p`.

Any solution's over-production splits into:
1. **Irreducible** part, `LB_p − x_p`: caused by lead time, QC and direct
   travel. No routing can remove it.
2. **Routing-induced** part, `(produced_p − LB_p)`: the cost of sharing a
   truck, i.e. consolidation.

Only part 2 is something routing can change. Reporting both keeps
optimisation claims honest.

*Illustrative magnitudes* (ℓ = 2 h, q = 1 h, 30 min direct drive, i.e.
3.5 h minimum from batch to treatment): irreducible over-production is
~3.9% for Y-90, ~25.6% for Pb-212 and ~40% for At-211. **For At-211, the
2 h lead time alone costs ~21%.** In a real deployment, cutting lead time
or QC time may be worth more than any routing improvement (R3, R7).

*(Phase 7)* A daily cap can be set relative to this bound,
`C_i = κ · LB_i`, so tightness is comparable across instance sizes (§10).

### 5.5 Shared resources: fleet, dispatch, multi-trip (D19–D21)
These are the only constraints linking the isotopes. Without them the
problem splits into one independent problem per isotope.

- **Trip interval.** Trip k occupies a vehicle from departure `P_k + q`
  until it returns and finishes turnaround:
  `[P_k + q, P_k + q + D_k + ρ)`, where `D_k` is the route duration.
- **Fleet cap (multi-trip).** For every time slot t:
  `#{trips k active at t} ≤ K`.
  *Why this is exact:* vehicles are identical and every trip starts and
  ends at the depot, so trips form an interval graph. The minimum number of
  vehicles needed = the maximum number of overlapping intervals.
  Assigning trips to vehicles greedily by start time achieves it. So no
  trip→vehicle variables are needed; the vehicle schedule is recovered
  after solving. Drivers work the same way.
- **Dispatch limit.** For every slot s: `#{trips with P_k = s} ≤ m`,
  summed over **all** isotopes (one loading dock). Second trips count too:
  every departure needs a dock slot.
- **Effect.** Both constraints make isotopes compete. The model should give
  late (low-decay) slots and extra vehicles to the isotope with the most to
  lose from decay. The dual values of these constraints price one more
  vehicle / one more dock slot in MBq of avoided waste.
- **Toy check (one vehicle, E6 data):** without multi-trip, K = 1 is
  infeasible (two isotopes, single-isotope trips). With multi-trip, 4
  trips: At-211 at its lower bound (560 MBq), Y-90 trips moved earlier
  (422 vs 415 MBq). Planned as a Phase 2b test.
- **Column-generation view (candidate for Phase 4).** Fleet and dispatch
  constraints (plus, in Phase 7, production caps) are the linking rows of a Dantzig–Wolfe
  master over trips. Pricing is one subproblem per (isotope, batch slot).
  With the slot fixed, each patient's production cost is a constant, so
  pricing is a standard elementary shortest path with time windows. The
  exponential nonlinearity disappears.

### 5.6 Objectives (plan §5; weighting left open)
1. Over-production (decay waste caused by batch timing), in **dose
   equivalents**: `Σ_p (produced_p − x_p) / x_p`. Reported split per §5.4.
2. Total distance.
3. Number of vehicles, i.e. peak simultaneous trips (with multi-trip, not
   the number of trips). In Phase 2a, where fleet is not yet modelled, this
   is the number of trips.

The worked example in TIMELINE.md E6 shows these objectives genuinely
conflict for At-211, and barely conflict for Y-90.

*Why dose equivalents, not MBq:* a Y-90 dose is ~10× the MBq of a Pb-212 or
At-211 dose, so summing MBq would let Y-90 dominate once isotopes compete
(2b). One "extra dose" means the same thing for every isotope. Isotope
costs per MBq could replace this in Phase 7.

### 5.7 Phase 2a MILP (D25)
Scope: routing, vial→trip assignment and batch timing. No shared
resources (fleet, dispatch → 2b) and no manufacturing constraints
(→ Phase 7). Without shared resources the model splits by isotope, but it
is built as one model because 2b needs that.

**Sets and constants** (per isotope i)

| Symbol | Meaning |
|---|---|
| `H_i`, `N_i = {0} ∪ H_i` | hospitals with ≥ 1 patient for i; plus depot |
| `K_i = {1…|P_i|}` | candidate trips. One per patient, so "every vial on its own truck" (the §5.4 lower bound) is representable |
| `S_p = {s ∈ S : s ≤ P^direct_p}` | slots at which p could still be served on time |
| `c_ps = x_p·exp(λ_i(τ_p − s))`, `μ_ps = c_ps / x_p` | activity to produce (absolute, per unit dose) |
| `δ_p = τ_p − ℓ` | per-vial deadline |

**Variables**

| Variable | Type | Meaning |
|---|---|---|
| `x_uvk` | binary | trip k drives u → v |
| `y_k` | binary | trip k is used |
| `z_pk` | binary | p's vial rides on trip k |
| `a_hk` | continuous ∈ [e_h, max deadline at h] | arrival of trip k at h |
| `n_k` | integer ∈ {0,…,|S|−1} | batch slot index; `B_k = P_min + Δ·n_k` |
| `u_ps` | binary | p's vial is produced at slot s |

Produced activity (expression): `A_p = Σ_s c_ps·u_ps`.

**Objective (weighted form; hierarchical form is a config switch via
Gurobi multi-objective)**

```
min  w_over · Σ_p ( Σ_s μ_ps·u_ps − 1 )  +  w_dist · Σ d_uv·x_uvk  +  w_trip · Σ y_k
```

**Constraints**

```
(C1)  Σ_k z_pk = 1                                  ∀p     every vial on exactly one trip
(C2)  z_pk ≤ Σ_u x_{u,h(p),k}                       ∀p,k   only on a trip that visits its hospital
(C3)  Σ_p z_pk ≤ Q_i · y_k                          ∀k     vial capacity per isotope (D15)
(C4)  Σ_v x_0vk = y_k,  Σ_u x_u0k = y_k             ∀k     used trip leaves and returns once
(C5)  Σ_u x_uhk = Σ_v x_hvk ≤ 1                     ∀h,k   flow conservation; ≤ 1 visit per trip
(C6)  a_hk ≥ B_k + q + t_0h − M(1 − x_0hk)          ∀h,k   first stop
(C7)  a_vk ≥ a_uk + σ_u + t_uv − M(1 − x_uvk)       ∀u≠v∈H_i,k   later stops (also removes subtours)
(C8)  a_{h(p),k} ≤ δ_p + M(1 − z_pk)                ∀p,k   per-vial deadline
(C9)  Σ_{s∈S_p} u_ps = 1                            ∀p     one production slot per vial
(C10) Σ_s s·u_ps ≤ B_k + M(1 − z_pk)                ∀p,k   vial not produced later than its trip's batch
(C11) y_k ≥ y_{k+1}                                 ∀k     symmetry breaking (identical trips)
```

Waiting is allowed (arrival constraints are ≥). Every big-M is set per
constraint from data bounds (latest deadline, window width), not one
global constant, because tighter M means a tighter LP relaxation.

**Design choices**
1. *Exact prescribed dose.* Delivering more only adds waste; delivering
   less is a clinical decision the routing layer doesn't make. The band is
   used for robustness analysis (delay budgets), not as a decision.
2. *C10 is one-sided.* Producing a vial earlier than its trip's batch only
   increases production, so the objective never chooses it. "No later
   than" is enough and halves the linking constraints.
3. *Split deliveries are neither forced nor forbidden* (D5). Vials are
   assigned individually and several trips may visit one hospital.
4. *Batch slots* are the §5.3 discretization. The trip's batch time is an
   integer slot index; the per-vial `u_ps` looks up the exponential.

**Validation plan**
1. Toy E6, waste-heavy weights → 4 trips; At-211 560.0 MBq, Y-90 415.4 MBq
   (= lower bound).
2. Toy E6, distance/trip-heavy weights → 2 trips; 691.1 and 424.6 MBq.
3. Capacity-forced split: 7 Pb-212 vials at one hospital, Q = 6 → split.
   Same data, large Q → no split.
4. Deadline-driven split: one hospital with 08:00 and 15:00 patients. (Renamed
   from "deadline-forced": nothing makes one trip infeasible; the split is
   driven by waste, so it appears only when waste is weighted enough.)
5. **Independent solution checker:** recomputes every arrival time,
   deadline and activity from the routes alone, without the MILP, and
   checks all rules. It catches formulation bugs that the solver would
   report as "optimal".
6. **Waste report** per solution: irreducible (lead time + QC + direct
   drive) / discretization (rounding to slots) / routing-induced.

**Implementation notes (Phase 2a, E12)**
- Code: `radvrp/model.py` (MILP), `radvrp/checker.py` (independent
  simulator + checker), `radvrp/report.py` (trip table, waste split),
  `scripts/solve.py` (CLI), plots in `radvrp/viz.py` (routes, schedule).
- *Batch re-timing.* `B_k` does not appear in the objective; only the vials'
  slots `u_ps` do, and those are capped by `B_k`. So a solver can leave `B_k`
  earlier than the route allows without changing the objective. After
  solving, each trip's batch is moved to its latest feasible slot (backward
  pass of §5.2). This never breaks a deadline and never increases waste.
- *Independent checker.* It recomputes departure, arrivals (with waiting
  for hot-lab hours), deadlines, capacity, eligibility, grid, distance and
  activity from the trip list alone. It also flags a solver claim of less
  activity than physics requires. Tests break good plans on purpose (drop a
  vial, duplicate one, late batch, off-grid batch, wrong isotope, capacity,
  fake activity) and require the checker to catch each one.
- *Waste split* per vial: irreducible `LB_p − x_p`; routing
  `x_p·μ(P*_k) − LB_p`; discretization `x_p·μ(B_k) − x_p·μ(P*_k)`, where
  `P*_k` is the trip's latest continuous batch time. All three are ≥ 0 and
  sum to total waste (tested).
- *Truck view for presentation (D28).* `radvrp/fleet.py` assigns trips to
  numbered trucks (and drivers) after solving. It goes in order of
  departure and reuses any truck that is back and turned around. For
  interval graphs this greedy rule is optimal, so the truck count equals
  the peak overlap (tested against an independent sweep-line count). The
  model is unchanged. Plots: `schedule_by_truck.png` (for a third-party
  reader), `schedule_by_trip.png` (includes batch → QC), `routes.png`
  (trips labelled with their truck). On `small`, 5 trips need 3 trucks.

**Results (Phase 2a)**

| Case | Result |
|---|---|
| E6, waste-heavy | 4 trips; At-211 559.9 MBq (2 × 279.95), Y-90 415.4 = lower bound ✓ |
| E6, route-heavy | 2 trips; 691.1 / 424.6 MBq ✓ |
| E6, default weights (100 / 1 / 20) | At-211 split into 2 trips, Y-90 consolidated into 1: the isotope-dependent trade-off, found by the model ✓ |
| Capacity split (7 vials, Q = 6) | 2 trips to H1; with Q = 20, 1 trip ✓ |
| Deadline-driven split | waste-heavy → 2 trips; route-heavy → 1 ✓ |
| small | optimal, 0.15 s, 658 vars / 819 constraints; checker PASS |
| medium | optimal, 0.38 s, 806 vars / 955 constraints; checker PASS |
| large | 13,471 vars / 15,534 constraints: exceeds restricted license (O10) |

Waste on `small` at default weights: 5.48 dose-eq in total, of which
irreducible 3.78 (69%), routing 1.42 (26%), discretization 0.29 (5%). Routing
controls roughly a quarter of the waste; the 30-min slot grid costs about
5%. Pb-212 shows deadline-driven splits at realistic scale: two trips each
visit A01 and A02, one with an early batch, one with a late batch.

**Size** (restricted Gurobi license: ≤ 2,000 variables and constraints)

| Instance | ≈ variables | ≈ constraints | Fits |
|---|---|---|---|
| toy_e6 | 110 | 90 | yes |
| small | 660 | 870 | yes |
| medium | 810 | 1,030 | yes |
| large | 13,500 | 16,200 | no (needs full license, O10) |

---

## 6. Phase 1 parameter choices

Confidence: **H** = regulatory/physical fact, **M** = from clinical
literature, **L** = reasoned placeholder, should be revisited.

### Isotopes (D1)
| | Y-90 | Pb-212 | At-211 | Conf. |
|---|---|---|---|---|
| Half-life | 64.1 h | 10.64 h | 7.214 h | H |
| A2 (TBq) | 0.3 | 0.2 | 0.5 | H — 49 CFR 173.435 |
| Decay per hour | ~1.1% | ~6.3% | ~9.2% | H |
| Vials per truck `Q_i` | 20 | 6 | 10 | **L** — Y-90 is a pure β emitter (light shielding); Pb-212's Tl-208 daughter emits a 2.6 MeV γ (heavy shielding); At-211 emits ~77–92 keV X-rays (moderate) |

### Dose models
| Isotope | Model | Values | Conf. / source |
|---|---|---|---|
| Y-90 | Log-normal, fixed activity (radioembolization is dosed from liver volume, not body weight) | median 1,800 MBq, σ = 0.30, clipped to [500, 3,000] MBq | M — clinical median ~1.7 GBq (range 1.4–2.5); SIR-Spheres max 3 GBq |
| Pb-212 | Weight-based | 2.50 MBq/kg, cap 203.5 MBq (5.5 mCi) | M — ALPHAMEDIX-02 phase 2 regimen |
| At-211 | Weight-based, MBq/kg ~ U[1.25, 3.5] | → ~100–280 MBq for 80 kg | M — [²¹¹At]NaAt escalation 1.25–3.5 MBq/kg; [²¹¹At]MABG 0.65–2.1 MBq/kg |
| Weight | Normal(80, 15) kg, clipped to [45, 140] | | L |

### Network and demand
| Parameter | Default | Conf. |
|---|---|---|
| Eligibility P(academic): Y-90 / Pb-212 / At-211 | 0.9 / 0.8 / 0.6 | L — alpha therapies concentrate at specialised centres |
| Eligibility P(community) | 0.5 / 0.3 / 0.15 | L |
| Patients/day mean, academic (Poisson) | 2.0 / 2.0 / 1.5 | L — **future-adoption scenario (A16)** |
| Patients/day mean, community | 0.8 / 0.8 / 0.6 | L — A16 |
| Min patients per isotope | 2 | Design choice: every isotope present |
| `demand_scale` | 1.0 | Multiplies all means; varies demand independently of hospital count (Phase 3) |
| Treatment times | Uniform on 30-min grid, 08:00–15:00 | L |
| Service time σ_h | 15 min | L |
| Receiving opens e_h | 06:00 | L |

### Operations
| Parameter | Default | Conf. |
|---|---|---|
| Lead time ℓ | 2 h | User decision (D11) |
| QC + packaging q | 1 h | L — rapid release tests (radiochemical purity, pH, endotoxin) are tens of minutes; sterility testing is retrospective |
| Production window | 03:00–12:00 | L — upper bound honours "production ends by a fixed time" |
| Batch slot width Δ | 30 min | Design choice (§5.3) |
| Tolerance β | 0.20 | H — NRC 10 CFR 35.63 (D4) |
| Capacity factor κ | 1.5 | Design choice (§5.4). **Phase 7 only**: computed by the generator, unused by Phases 2–6 |

---

## 7. Assumptions register

Each is a deliberate simplification. "Breaks when" says what would force a
revisit.

| ID | Assumption | Why | Breaks when |
|---|---|---|---|
| A1 | Single depot, single metro | Scope (plan §3–4) | Multi-site networks, inter-city supply |
| A2 | Deterministic decay, demand, travel | Decay truly is deterministic; others are simplified for Phase 2 | No-shows, traffic, QC failures (R1–R3) |
| A3 | Great-circle × circuity travel, time-invariant | No road data until Phase 5. Swapping in a real road matrix is a **data change**: the model and checker already handle asymmetric matrices, and shortest-path road times keep the triangle inequality. **Time-dependent** travel (rush hour) would be a **model change** | Rush hour, bridges/tunnels, harbour |
| A4 | One isotope per truck | Plan §3 (shielding/regulatory separation) | Mixed-load packaging becomes allowed |
| A5 | One production batch per truck, finish time free within window | Makes routing drive production (D13) | Real hot cells run batches in sequence; limited runs per day |
| A6 | No explicit synthesis-line sequencing; the shared dispatch limit `m` caps batches finishing per slot (D20) | Manufacturing deferred to Phase 7 (D24) | Syntheses take longer than a slot and block the line |
| A7 | Unit doses, one vial per patient (D14) | Matches therapeutic practice | Bulk/multi-dose supply to hospital pharmacies |
| A8 | Capacity = vial count per isotope (D15) | Simplest per-isotope capacity | Radiation-based (transport index) limits bind first |
| A9 | **Manufacturer can fill any production order** (Phases 2–6). Capacity modelling deferred to Phase 7 (D24) | Keep the routing story focused; the manufacturer is a customer of the routing output | Scarce cyclotron/generator capacity (esp. At-211) makes the plan unproducible |
| A10 | τ_p fixed by clinic (D3) | Realistic, and keeps the coupling clean | Clinics re-schedule around deliveries |
| A11 | Fixed lead time ℓ and QC time q | Simplicity | Variable QC time; per-hospital prep times |
| A12 | No storage cost at hospital (O6 open) | Not yet decided | Hot-lab space/shielding limited |
| A13 | Vehicles and drivers are interchangeable; any vehicle can carry any isotope (shielding is in the packages) (D21) | Makes the interval-overlap fleet count exact (§5.5) | Isotope-specific vehicles → apply §5.5 per vehicle class |
| A14 | A2 treated as a per-vial check, expected non-binding | Doses ≪ A2 (§8 of summary output) | Consolidated bulk shipments |
| A15 | Same-day horizon; plan fixed 2 days ahead | Plan §3 | Cancellations after production (R1) |
| A16 | **Future-adoption demand:** alpha therapies (Pb-212, At-211) at routine volumes | At today's (mostly trial) volumes an instance has ~1 At-211 patient, which makes the most decay-sensitive isotope trivial to route | Calibrating to current real volumes — then At-211 routing is near-trivial |

---

## 8. Real-world issues register

Issues an academic model sweeps under the carpet. They are recorded, not
necessarily solved.

| ID | Issue | Effect on this model |
|---|---|---|
| R1 | Patient no-shows / cancellations after the plan (2 days ahead) or after production | Wasted short-lived product; deterministic model can't hedge |
| R2 | Boston morning traffic; time-dependent travel | Deadlines may be missed; circuity × constant speed is optimistic in rush hour. **Planned later feature (D27):** a conservative peak-hour average speed instead of the steady 40 km/h. It's a data change (one config value), so no model change. Fully time-dependent travel would be a model change and isn't planned |
| R3 | QC release time varies; a batch can fail release (out-of-spec) | No backup batch in the model; a failed At-211 batch likely means cancelled treatments |
| R4 | Production runs are sequential on real equipment | Several batches finishing at the same time may be physically impossible (A6) |
| R5 | Y-90 microspheres are in reality produced centrally, often weekly, with vials calibrated to a reference day (hospitals choose larger vials later in the week) | Daily local Y-90 production is unrealistic; Pb-212 (generator-based, regional) and At-211 (cyclotron, local) fit this model far better |
| R6 | Dose calibrator uncertainty (a few %) and residual activity in syringes/lines | Eats into the ±20% band; motivates D9 robustness analysis |
| R17 | The plan assumes the manufacturer can produce every order (A9); there is little wiggle room with the manufacturer in practice | Plan may be unproducible; Phase 7 adds capacity, soft doses, and a producibility check |
| R7 | Receipt rules: packages must be surveyed on receipt (10 CFR 20.1906), hot-lab hours limited | Service time and receiving window are real constraints, possibly larger than modelled |
| R8 | Vehicle limits are radiation-based (transport index, 49 CFR 173.441); driver dose (ALARA) | Vial count (A8) is a proxy |
| R9 | Split deliveries have hidden handling costs at the hospital (D10) | Model may split when reality wouldn't |
| R10 | Pb-212 daughters (Bi-212, Tl-208) grow in after purification, so external dose rate *rises* for hours | Shielding/transport index isn't a simple function of Pb-212 activity |
| R11 | Vehicle breakdown, weather, driver availability | No recourse or backup routing |
| R12 | Weight-based doses need current patient weight; prescriptions change | Demand data 2 days ahead may be stale |
| R13 | Clinic delays: late treatment ⇒ patient receives less than prescribed | Delay budget `ln(x_p/L_p)/λ`: Y-90 ≈ 20.6 h, Pb-212 ≈ 3.4 h, At-211 ≈ 2.3 h (D9) |
| R14 | Crude coastline mask, synthetic hospital locations | Distances plausible in scale only |
| R15 | Driver hours-of-service limits, shift changes, breaks | Not modelled (D21). A ~03:00–15:00 operating day is within federal limits, and drivers are interchangeable |
| R16 | Returning trucks and outgoing trucks compete for the dock; unloading may need its own dock time | Only departures consume dock capacity in the model; unloading is folded into turnaround ρ |

---

## 9. Phase 1 generator design

- **Config-driven** (`configs/*.yaml`); physics, regulatory and clinical
  data live in `configs/isotopes.yaml`, with sources in comments. Scaling
  = editing the config (hospital counts, demand rates), not code.
- **Two modes:** `random` (sampled Boston-metro instance) and `manual`
  (explicit hospitals, travel matrix and patients, for hand-checkable toy
  cases such as TIMELINE E6).
- **Reproducible:** a single `seed` controls all sampling.
- **Feasible by construction:** a treatment time is sampled only if the
  patient could be served by a direct truck within the production window
  and receiving hours. `Instance.validate()` re-checks everything.
- **Output** (`data/<name>/`): `instance.json` (scalars + config),
  `isotopes.csv`, `nodes.csv`, `patients.csv`, `travel_min.csv`,
  `dist_km.csv`. Patients carry derived columns (deadline, direct-batch
  latest time, LB).
- **Diagnostics:** text summary (demand, LB split, A2 headroom) and plots
  (map, dose distributions, decay/production-multiplier curves).
- **Methodology note:** a single random instance per size is noisy (e.g.
  the 16-hospital `medium` preset drew fewer patients than `small`). Phase 3
  results should average over many seeds per size, not one instance.

### How to run

```bash
.venv/bin/python scripts/generate.py configs/small.yaml --plots   # -> data/small/, outputs/small/
.venv/bin/python -m pytest -q
```

---

## 10. Deferred to Phase 7: manufacturing integration (D24)

Everything here was designed and discussed, then deliberately removed from
Phases 2–6. The routing layer's contract with the manufacturer is:
**"here are the batches: isotope, ready-by time, activity per vial."**
Whether the manufacturer can meet that order is Phase 7's question.

*Interview line:* this was identified early. In practice there is little
wiggle room with the manufacturer, and how best to model their side is
still open, so routing was scoped to produce the production order and
treat the manufacturer's constraints separately.

### 10.1 What stays in Phases 2–6 (it is routing-consequential)
| Item | Role |
|---|---|
| Per-trip batch time `B_k` (D13) | The routing output that sets how much to produce |
| QC time `q`, production window `[P_min, P_max]` | Fixed inputs *from* the manufacturer |
| Decay-waste objective (§5.6) | Routing-driven waste; the core trade-off |
| Dispatch limit `m` (D20) | Loading dock = start of logistics, kept in 2b |

### 10.2 What moves to Phase 7
| # | Item | Status / design so far |
|---|---|---|
| M1 | **Daily production cap** per isotope, `Σ_{p∈P_i} A_p ≤ C_i`, with `C_i = κ·LB_i` so tightness is comparable across sizes (κ < 1 provably infeasible without under-dosing; κ = 1.5 loose; κ ≈ 1.1 tight) | Formulated; generator already computes `daily_cap_mbq` |
| M2 | **Soft dose target** (D8): deliver a fraction `φ_p ∈ [1−β, 1]` of `x_p` when the cap forces it. Upper band never used (over-dosing only adds waste) | Formulated, see 10.3 |
| M3 | **Under-dosing penalty** `w_dev`, set automatically above `w_over · max μ`, so the model never trades a patient's dose for waste unless the cap forces it (clinical cost > economic cost) | Formulated |
| M4 | **D9 case "feasible only because doses sit at the lower band"**: flag solutions where φ_p < 1, then stress-test them. The delay-budget and stress-test parts of D9 stay in Phase 3 | Designed |
| M5 | **Producibility check** (post-solve): given the manufacturer's real capacity, flag plans that ask for more (R17) | Designed |
| M6 | **Synthesis-line sequencing**: one synthesis at a time per module, runs longer than a slot (A6, R4). Dispatch limit covers only the per-slot part | Open |
| M7 | **Shared production capacity across isotopes** (e.g. one cyclotron's beam time for At-211 and others) (A9) | Open |
| M8 | **QC variability and batch failure** (R3): backup batches, recourse | Open |
| M9 | **Isotope cost per MBq** to replace dose-equivalent weighting (§5.6) | Open, needs data |
| M10 | **Packaging/regulatory**: A2 per-package limit (currently a check, non-binding, A14); volume/concentration and radiolysis (E5); radiation-based vehicle limits (R8, R10) | Check only |
| M11 | **Realistic production model for Y-90** (central, weekly, reference-day vials; R5) | Open |
| M12 | **Storage cost at hospital** (O6) — hospital-side, but sits with the handover model | Open |

### 10.3 Phase 7 formulation extension (M1–M3)
Adds to §5.7, without changing any existing constraint:

```
g_ps ∈ [0,1]                        fraction of x_p delivered if p is produced at slot s
φ_p = Σ_s g_ps                      delivered fraction
(1−β)·u_ps ≤ g_ps ≤ u_ps     ∀p,s   exact linearisation of φ_p·u_ps (u binary)
A_p = Σ_s c_ps·g_ps                 produced activity, replaces Σ_s c_ps·u_ps
Σ_{p∈P_i} A_p ≤ C_i          ∀i     daily cap
objective += w_dev · Σ_p (1 − φ_p)
```

Cost: about `Σ_p |S_p|` extra continuous variables and twice that in
constraints (roughly +200 variables and +400 constraints on `small`).
