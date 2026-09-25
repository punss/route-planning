# Design Notes — Decay-Constrained VRP for Radiopharmaceutical Delivery

Living document: this is the source of truth for **notation, formulation,
assumptions and parameter choices**. `plan.md` holds the project brief;
`TIMELINE.md` holds the history of how each decision here was reached (the
`D#` / `O#` IDs refer to it).

Status: **Phase 1 (data generator)**. Formulation sections are written so
Phase 2 can build on them directly. Decision variables are sketched but not
finalised.

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
| `K_i` | Candidate trucks (= routes = production batches) for isotope i |
| `S` | Batch-finish time slots `{P_min, P_min+Δ, …, P_max}` |

### Parameters
| Symbol | Meaning | Source / default |
|---|---|---|
| `T½_i`, `λ_i = ln2 / T½_i` | Half-life, decay constant | §6 |
| `A2_i` | Type A package limit (per vial here) | 49 CFR 173.435 |
| `Q_i` | Vials per truck for isotope i | §6 (assumption) |
| `C_i` | Daily production cap, isotope i (MBq) | `κ · LB_i` (§5.4) |
| `h(p)`, `i(p)` | Patient p's hospital and isotope | generated |
| `x_p` | Prescribed activity | §6 dose models |
| `[L_p, U_p]` | Tolerance band = `[(1−β)x_p, (1+β)x_p]` | β = 0.20 (D4) |
| `τ_p` | Clinic-scheduled treatment time (fixed input, D3) | generated |
| `ℓ` | Lead time: vial on site ≥ ℓ before τ_p | 120 min (D11) |
| `q` | QC/release + packaging time between batch finish and departure | 60 min |
| `[P_min, P_max]` | Production window for batch finish times | 03:00–12:00 |
| `t_{uv}`, `d_{uv}` | Travel time (min) and distance (km), u,v ∈ V | §4 |
| `σ_h` | Service time at hospital (receipt, survey, paperwork) | 15 min |
| `e_h` | Hospital's earliest receiving time (hot-lab opens) | 06:00 |
| `K`, `m_s` | Fleet cap, dispatch capacity per slot — **placeholders, O2** | unset |

### Derived per patient
- Deadline: `δ_p = τ_p − ℓ` (vial must arrive by then).
- Production multiplier for a batch finishing at time `P`:
  `μ_p(P) = exp(λ_{i(p)} · (τ_p − P))`, so produced activity = `x_p · μ_p(P)`.

### Decision variables (sketch — finalised in Phase 2)
- Routing: which hospitals truck k visits, in what order.
- Assignment: which patients' vials ride on truck k (enables split
  deliveries, D5).
- Batch time: `P_k ∈ S` (discretized, §5.3).
- Delivered activity `y_p ∈ [L_p, U_p]` with deviation `|y_p − x_p|`
  penalised (soft target, D8).

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

The daily cap is set relative to this bound, `C_i = κ · LB_i`, so tightness
is comparable across instance sizes. κ < 1 is provably infeasible; κ = 1.5
is loose; κ ≈ 1.1 forces consolidation to be efficient.

### 5.5 Objectives (plan §5; weighting left open)
1. Over-production: `Σ_p (produced_p − x_p)`, reported split per §5.4.
2. Total distance.
3. Number of trucks/routes.

The worked example in TIMELINE.md E6 shows these objectives genuinely
conflict for At-211, and barely conflict for Y-90.

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
| Capacity factor κ | 1.5 | Design choice (§5.4) |

---

## 7. Assumptions register

Each is a deliberate simplification. "Breaks when" says what would force a
revisit.

| ID | Assumption | Why | Breaks when |
|---|---|---|---|
| A1 | Single depot, single metro | Scope (plan §3–4) | Multi-site networks, inter-city supply |
| A2 | Deterministic decay, demand, travel | Decay truly is deterministic; others are simplified for Phase 2 | No-shows, traffic, QC failures (R1–R3) |
| A3 | Great-circle × circuity travel, time-invariant | No road data until Phase 5 | Rush hour, bridges/tunnels, harbour |
| A4 | One isotope per truck | Plan §3 (shielding/regulatory separation) | Mixed-load packaging becomes allowed |
| A5 | One production batch per truck, finish time free within window | Makes routing drive production (D13) | Real hot cells run batches in sequence; limited runs per day |
| A6 | Batches of the same drug can overlap in time | Keep manufacturing simple (plan §1) | Single synthesis module per isotope |
| A7 | Unit doses, one vial per patient (D14) | Matches therapeutic practice | Bulk/multi-dose supply to hospital pharmacies |
| A8 | Capacity = vial count per isotope (D15) | Simplest per-isotope capacity | Radiation-based (transport index) limits bind first |
| A9 | Daily cap in MBq, per isotope, not shared (plan §3) | Lightweight | Shared cyclotron/beam time across isotopes |
| A10 | τ_p fixed by clinic (D3) | Realistic, and keeps the coupling clean | Clinics re-schedule around deliveries |
| A11 | Fixed lead time ℓ and QC time q | Simplicity | Variable QC time; per-hospital prep times |
| A12 | No storage cost at hospital (O6 open) | Not yet decided | Hot-lab space/shielding limited |
| A13 | No fleet cap, no dispatch limit, no multi-trip (O2, O5 open) | Deferred | Discussed before Phase 2 |
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
| R2 | Boston morning traffic; time-dependent travel | Deadlines may be missed; circuity × constant speed is optimistic in rush hour |
| R3 | QC release time varies; a batch can fail release (out-of-spec) | No backup batch in the model; a failed At-211 batch likely means cancelled treatments |
| R4 | Production runs are sequential on real equipment | Several batches finishing at the same time may be physically impossible (A6) |
| R5 | Y-90 microspheres are in reality produced centrally, often weekly, with vials calibrated to a reference day (hospitals choose larger vials later in the week) | Daily local Y-90 production is unrealistic; Pb-212 (generator-based, regional) and At-211 (cyclotron, local) fit this model far better |
| R6 | Dose calibrator uncertainty (a few %) and residual activity in syringes/lines | Eats into the ±20% band; motivates D9 robustness analysis |
| R7 | Receipt rules: packages must be surveyed on receipt (10 CFR 20.1906), hot-lab hours limited | Service time and receiving window are real constraints, possibly larger than modelled |
| R8 | Vehicle limits are radiation-based (transport index, 49 CFR 173.441); driver dose (ALARA) | Vial count (A8) is a proxy |
| R9 | Split deliveries have hidden handling costs at the hospital (D10) | Model may split when reality wouldn't |
| R10 | Pb-212 daughters (Bi-212, Tl-208) grow in after purification, so external dose rate *rises* for hours | Shielding/transport index isn't a simple function of Pb-212 activity |
| R11 | Vehicle breakdown, weather, driver availability | No recourse or backup routing |
| R12 | Weight-based doses need current patient weight; prescriptions change | Demand data 2 days ahead may be stale |
| R13 | Clinic delays: late treatment ⇒ patient receives less than prescribed | Delay budget `ln(x_p/L_p)/λ`: Y-90 ≈ 20.6 h, Pb-212 ≈ 3.4 h, At-211 ≈ 2.3 h (D9) |
| R14 | Crude coastline mask, synthetic hospital locations | Distances plausible in scale only |

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
