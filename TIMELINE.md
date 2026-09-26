# Project Timeline & Decision Log

Chronological record of work done, decisions made, and what drove each
decision. Newest entries at the bottom. Each decision gets an ID (`D#`) and
each open question an ID (`O#`) so later entries can reference them.

---

## Index

### Decisions

| ID | Date | Decision | Decided by | Entry |
|----|------------|-----------------------------------------------------------------------|------------|-------|
| D1 | 2026-09-23 | Isotopes: Y-90, Pb-212, At-211 | User | E2 |
| D2 | 2026-09-23 | Required production activity computed per patient (not last-served) | User | E2 |
| D3 | 2026-09-23 | Patient administration times are fixed inputs set by the clinic | User | E2 |
| D4 | 2026-09-23 | Dose tolerance band grounded in NRC 10 CFR 35.63 (±20% default) | User | E2 |
| D5 | 2026-09-23 | Split deliveries allowed; model must *conclude* when not to split — no hard no-split constraint | User | E2 |
| D6 | 2026-09-23 | Solver: Gurobi (Northeastern academic license, gurobipy) | User | E2 |
| D7 | 2026-09-23 | Maintain this timeline document | User | E2 |
| D8 | 2026-09-24 | Dose target = prescribed dose; band [L, U] stays a hard constraint. *Amended by D24: Phases 2–6 deliver exactly x_p; soft target → Phase 7* | User | E3, E11 |
| D9 | 2026-09-24 | Robustness analysis is a planned deliverable: find solutions that are feasible *only because* doses sit at the band's lower limit, then stress-test them. *Amended by D24: delay budgets/stress tests stay (Phase 3); the "lower-band" case → Phase 7* | User | E3, E11 |
| D10 | 2026-09-24 | Split-delivery ties and hidden per-visit costs accepted as-is (no per-visit cost term) | User | E3 |
| D11 | 2026-09-24 | ~~Arrival time irrelevant to dosing~~ (superseded by D13); hard lead time kept: each dose on location ≥ 2 h before its patient's scheduled time | User | E4, E6 |
| D12 | 2026-09-24 | Truck capacity set per isotope; A2 kept as a (expected non-binding) per-package check | User | E4 |
| D13 | 2026-09-24 | **Framing:** production batched per truck, batch finish time `P_k` is a decision and is limited by the route, so routing determines produced activity. Slots discretize `P_k` | Claude (delegated by user) | E6 |
| D14 | 2026-09-24 | Unit doses: one vial per patient | Claude (delegated by user) | E6 |
| D15 | 2026-09-24 | Truck capacity unit = count of unit-dose vials per isotope | Claude (delegated by user) | E6 |
| D16 | 2026-09-24 | Phase 1 started (user approval); Python 3.12 venv + Gurobi 13.0.3 | User | E7 |
| D17 | 2026-09-24 | Future-adoption demand scenario for alpha therapies (assumption A16) | Claude (delegated) — flagged for user review | E7 |
| D18 | 2026-09-25 | Use restricted Gurobi license until campus activation; project put under git | User | E8 |
| D19 | 2026-09-25 | Fleet cap K as an optional hard constraint: ≤ K trips on the road at once | User (implied by D21) / Claude | E9 |
| D20 | 2026-09-25 | Dispatch limit m per slot, **shared across isotopes** (loading dock); default m = 2 | User | E9 |
| D21 | 2026-09-25 | Multi-trip vehicles; isotope may change between trips; 30-min turnaround; vehicles and drivers interchangeable | User (industry-confirmed) | E9 |
| D22 | 2026-09-25 | Phase 2 staged: 2a core model → 2b fleet/dispatch/multi-trip | User | E10 |
| D23 | 2026-09-25 | Placeholder constants (incl. D17 demand, low-confidence params, m = 2) accepted provisionally; revisit only if one drives infeasibility or dominates results | User | E10 |
| D24 | 2026-09-25 | **Manufacturing-side modelling deferred to a new Phase 7** (capacity, soft doses, sequencing, …). Batch timing stays as the routing output | User | E11 |
| D25 | 2026-09-25 | Phase 2a MILP formulation fixed (DESIGN_NOTES §5.7): exact doses, dose-equivalent waste, one-sided batch linking, trips = patients | Claude (trimmed from the draft the user reviewed) | E11 |
| D26 | 2026-09-25 | Phase 2a implemented; default weights w_over/w_dist/w_trip = 100/1/20; post-solve batch re-timing | Claude (delegated) | E12 |
| D27 | 2026-09-25 | Keep 40 km/h average speed for now; conservative peak-hour speed is a later feature; time-dependent travel not needed | User | E14 |
| D28 | 2026-09-25 | Visualise trips on numbered trucks/drivers via post-solve interval assignment (model unchanged) | User (request) / Claude (method) | E14 |
| D29 | 2026-09-25 | Phase 2 work lives on branch `phase-2`; merged to `main` only when all of Phase 2 is done | User | E14 |

### Open questions

| ID | Opened | Question | Status |
|----|------------|----------------------------------------------------------------------|--------|
| O1 | 2026-09-23 | Fixed production end + fixed administration times ⇒ decay is route-independent. How do we restore the decay↔routing coupling? | Closed 2026-09-24 → D11 (coupling via arrival time dropped; see O7) |
| O2 | 2026-09-23 | Fleet-size cap and depot dispatch limits as cross-drug coupling (Dantzig–Wolfe structure) | Closed 2026-09-25 → D19, D20 |
| O3 | 2026-09-23 | Dose target within the tolerance band (lower / nominal / upper) | Closed 2026-09-24 → D8 |
| O4 | 2026-09-23 | How to model A2 (per-package) limits and real truck capacity | Closed 2026-09-24 → D12 (capacity *unit* still open → O8) |
| O5 | 2026-09-23 | Can a truck make multiple trips (possibly with different isotopes)? | Closed 2026-09-25 → D21 |
| O6 | 2026-09-24 | Storage at the hospital has a (not necessarily monetary) cost: hot-lab space, shielding, staffing | Open — user wants to think about it |
| O7 | 2026-09-24 | D11 removes the plan's stated core question (decay↔routing coupling) and the reason for time-slot discretization. How should plan.md §2 tractability note and Phases 3–4 be reframed? | Closed 2026-09-24 → D13 (framing restored; slots kept, moved to batch time) |
| O8 | 2026-09-24 | Truck capacity unit: package count vs. activity/radiation (TI) on board at departure | Closed 2026-09-24 → D15 |
| O9 | 2026-09-24 | Packaging model: per-patient unit doses vs. a shared bulk vial per hospital | Closed 2026-09-24 → D14 |
| O10 | 2026-09-24 | Activate Gurobi academic license (only restricted pip license active) | Open — user needs campus network; restricted license in use meanwhile (E8) |
| O11 | 2026-09-25 | Phase 2 staging: 2a core model (no linking constraints) → 2b add fleet/dispatch/multi-trip | Closed 2026-09-25 → D22 |
| O12 | 2026-09-25 | Phase order for the interview: 2a → 2b → light Phase 3 → real roads + map (5/6), Phase 4 as discussion topic | Proposed — awaiting user |

---

## E1 — 2026-09-23 — Project kickoff and initial review

**What happened.** User wrote `plan.md` describing a decay-constrained VRP
for radiopharmaceutical delivery (single depot, one metro area, 3 isotopes,
patient-level demand, time-slot-discretized MILP, then a metaheuristic).
Claude reviewed it and raised the observations below before any code.

**Observations raised.**
1. *Coupling strength depends on half-life.* With the candidate isotopes in
   the plan (Lu-177, Y-90, I-131, Ac-225 — all ≥ 2.7 days), a 3-hour
   delivery window changes required activity by only ~1–3%. The
   decay↔routing question would look trivial. Suggested including a
   short-lived therapeutic isotope (Pb-212, 10.6 h; At-211, 7.2 h).
2. *Per-drug decomposability.* Single-drug trucks + per-drug production
   caps + additive objectives ⇒ the problem separates into one independent
   VRP per drug unless some resource is shared (fleet, depot dispatch,
   production line).
3. *Per-patient vs last-served decay.* Using the last-served patient's
   elapsed time for the whole batch over-estimates required activity. The
   exact requirement is `Σ_p x_p exp(λ(τ_p − t_prod))`. Side note: if
   administration times were free to assign, the rearrangement inequality
   says highest-dose-first minimises total required activity.
4. *A2 is a per-package limit, not per-shipment/per-truck.* Exceeding it
   means more packages (or a Type B package), not infeasibility.
5. *Dose band has a regulatory basis* (NRC 10 CFR 35.63).

**Result.** Questions sent to user; no code written.

---

## E2 — 2026-09-23 — First round of decisions

**Decisions.**

- **D1 — Isotopes: Y-90, Pb-212, At-211.** Half-lives 64.1 h / 10.64 h /
  7.21 h. *Why:* spread of decay rates (λ ≈ 0.011, 0.065, 0.096 per hour, i.e. ~1.1%, ~6.3%, ~9.2% lost per hour) tests
  how the solver and formulation behave as decay goes from mild to severe.
  A1/A2 values verified against 49 CFR 173.435:

  | Isotope | Half-life | A1 (TBq) | A2 (TBq) | Note |
  |---------|-----------|----------|----------|------|
  | Y-90    | 64.1 h    | 0.3      | 0.3      | pure β⁻ emitter |
  | Pb-212  | 10.64 h   | 0.7      | 0.2      | (a) includes short-lived daughters |
  | At-211  | 7.21 h    | 20       | 0.5      | (a) includes short-lived daughters |

- **D2 — Per-patient decay.** `plan.md` §2 edited: production activity is
  the sum over patients of each dose decayed back from that patient's own
  administration time. The earlier "last-served patient" wording was an
  over-estimate. *Why:* user rejected the simplification.
- **D3 — Clinic sets administration times.** Removed the plan's
  "higher-dose patients first" sequencing statement; `τ_p` is an input.
- **D4 — Tolerance band** from NRC 10 CFR 35.63 (administered dose within
  ±20% of prescribed, unless the written directive specifies otherwise).
- **D5 — Split deliveries.** Multiple trucks may deliver the same
  drug to the same hospital. The model should *conclude* that
  splitting is wasteful when a single truck suffices, rather than having it
  forbidden by a hard constraint. (Formulation consequence: split-delivery
  VRP. Caveat noted: the model only avoids splits it can "see" the cost of —
  see chat notes on ties and per-visit handling costs.)
- **D6 — Gurobi** via gurobipy, Northeastern academic license.
- **D7 — This timeline** is to be maintained throughout.

**New finding raised by Claude (→ O1).** With the user's production model —
all production ends at a fixed time `T`, product is stored at the hospital
until each patient's fixed time `τ_p` — required activity is
`Σ_p x_p exp(λ(τ_p − T))`, which **does not depend on the route or arrival
time at all.** Decay runs the same whether the vial is on the truck or on
the hospital shelf; both endpoints of the elapsed time are fixed. Routing
then only has to satisfy "arrive before the first patient" (a plain VRPTW),
and the over-dose objective becomes a constant. Options to restore coupling
proposed to user (see O1).

**Scoped, deferred (→ O2).** Fleet cap `K` shared across drugs and depot
dispatch limits. Structure sketch:
- Per-drug blocks: routes for drug `i` only touch hospitals eligible for `i`.
- Linking constraints: `Σ_i (trucks used for drug i) ≤ K`;
  `Σ (routes departing in dispatch interval t) ≤ m_t`.
- Block-angular ⇒ Dantzig–Wolfe: master chooses routes (columns) under
  linking constraints; one pricing subproblem per drug (elementary
  shortest path with resource constraints). Leads to branch-and-price.
- Raises O5 (multi-trip trucks).

---

## E3 — 2026-09-24 — Second round: O1 challenged, dose target, split deliveries

**O1 challenged by user.** User's reasoning: once routing fixes the arrival
time `a`, dosing must cover transit decay (T → a) *and* storage decay
(a → τ_p), so arrival time seems to matter. Claude's response: both legs
are real, but they always sum to the same total, so `a` cancels:

`exp(λ(a − T)) · exp(λ(τ_p − a)) = exp(λ(τ_p − T))`

Worked example (At-211, λ = ln2 / 7.21 h ≈ 0.0961 /h; production ends
05:00; patient needs 200 MBq at 11:00):

| Arrival | Transit factor | Storage factor | Total factor | Activity at 05:00 |
|---------|----------------|----------------|--------------|-------------------|
| 07:00   | e^(0.0961·2) = 1.212 | e^(0.0961·4) = 1.469 | 1.780 | 356 MBq |
| 10:00   | e^(0.0961·5) = 1.617 | e^(0.0961·1) = 1.101 | 1.780 | 356 MBq |

Arrival time changes how the decay splits between truck and shelf, not how
much decay there is in total. Clarified how this differs from option B:
there, `τ_p` itself moves with `a` (τ_p = a + offset), so `a` no longer
cancels. Option C (storage cost) makes arrival time matter through the
*objective*, not through decay. User's storage-cost intuition logged as O6.

**Decisions.**
- **D8 — Target the prescribed dose.** Formulation note from Claude: if the
  target is a hard equality (delivered = x_p) the band never comes into
  play. For the band to mean anything, the target must be *soft*: penalise
  deviation from x_p in the objective and keep [L_p, U_p] as hard bounds.
  Then the band is used only when something forces it (e.g. a binding
  production cap).
- **D9 — Robustness analysis.** User wants to identify solutions that are
  feasible only because doses sit at the lower limit, then poke holes in
  them. User's framing: interview is closer to a testing role, so showing
  the model's weak spots is a feature. Planned analyses (Claude's
  proposal): (1) band-slack report per patient; (2) closed-form *delay
  budget*: a patient dosed at x_p tolerates a treatment delay of
  d ≤ ln(x_p / L_p) / λ before dropping below L_p (for ±20%:
  Y-90 ≈ 20.6 h, Pb-212 ≈ 3.4 h, At-211 ≈ 2.3 h); (3) Monte Carlo on
  travel times / dose-calibrator error.
- **D10 — Split deliveries.** Arbitrary tie-breaking is acceptable. Hidden
  per-visit costs are not modelled — the user considers them a
  production-time discovery. Logged here as a real-world gotcha only.

---

## E4 — 2026-09-24 — O1 and O4 resolved

**Decisions.**
- **D11 — Arrival time drops out of dosing.** User accepted the
  cancellation argument (E3) and dropped the requirement that arrival time
  drive dosing. The one timing rule: each patient's dose must be on location
  **at least 2 h before that patient's scheduled administration time**
  (covers receipt, assay and dose preparation). `plan.md` §2 updated.
- **D12 — Per-isotope truck capacity.** `plan.md` §3 updated; A2 note in
  §2 clarified (per-package check, expected non-binding).

**Consequences noted by Claude.**
1. *Structure of the problem now.* Dosing and routing separate. Required
   production per patient, `x_p·exp(λ(τ_p − T))`, is a precomputable
   constant. Routing becomes a split-delivery VRP with hard **deadlines**
   (per dose: arrive by `τ_p − 2 h`) plus per-isotope capacity, fleet
   coupling to follow (O2).
2. *Objective 1 (minimise over-production) drops out* as a routing
   objective: it is fixed by patient data and `T`. It only becomes a
   decision if the production cap binds and doses must be pulled down
   within the band. That is a dosing problem, separate from routing, and
   it is exactly where the D9 robustness analysis looks.
3. *Time-slot discretization loses its purpose.* It existed to linearise
   decay as a function of arrival time; nothing now depends on arrival time
   except deadline feasibility, which a standard VRPTW handles in
   continuous time. Phase 3's "discretization error" and Phase 4's "less
   discretized decay" motivations go with it → O7.
4. *Split deliveries can now arise from deadlines, not just capacity.* The
   deadline is per dose. If a hospital's patients are spread over the day
   and no single route reaches it in time for the earliest patient while
   also serving everyone else, the model may legitimately send an early
   truck for early doses and a later one for the rest. Consistent with D5:
   the model concludes this itself.
5. *Residual decay coupling depends on the capacity unit (O8).* If truck
   capacity counts packages, decay never touches routing. If it's measured
   in activity or radiation on board, a truck that leaves later carries
   decayed (lower) activity and so fits more doses. For At-211 that's ≈18%
   lower after 2 h, which brings back a weak, real coupling.
6. *Missing lower bound on arrival.* With no storage cost (O6) there is no
   earliest-arrival rule. Plan: model hot-lab receiving hours as the earliest
   arrival time, proposed as a Phase 1 parameter.

---

## E5 — 2026-09-24 — Terminology: activity vs volume vs dose

**What happened.** The user asked whether the "amount to produce" is a
volume (mL) and the dose a radiation level. Clarified and pinned down for
the rest of the project:

| Term (as used in this project) | Meaning | Unit |
|---|---|---|
| **Activity** | Decays per second — how much radioactive material there is (A = λN) | MBq / GBq (1 mCi = 37 MBq) |
| **Prescribed dose `x_p`** | Activity patient p must receive *at* τ_p (the NRC's "dosage") | MBq |
| **Produced activity** | Activity made at production end T so that, once decayed, it equals `x_p` at τ_p: `x_p·exp(λ(τ_p − T))` | MBq |
| **Concentration** | Activity per unit volume; falls with decay, volume doesn't | MBq/mL |
| **Absorbed dose** | Energy deposited in the patient's tissue — not modelled | Gy (rad) |

**Model rule.** Every quantity in the model is activity: prescribed doses,
production, daily capacity, A2 limits and (if O8 goes that way) truck
capacity. Volume and concentration are packaging details layered on top.

**Real-world reference.** The FDA label for Pluvicto (Lu-177; checked on
DailyMed) says the manufacturer fixes the *concentration* at calibration
(1,000 MBq/mL) and varies the *volume* (7.5–12.5 mL) so the vial holds
7.4 GBq at administration time. That is the opposite of the fixed-volume
assumption the user started from, but the activity maths is identical
either way.

**Raised → O9.** The user described a fixed dose per patient. That points
to a **unit-dose** model (one vial per patient, prepared at the depot),
not the "shared batch per hospital" wording in plan.md §2.

---

## E6 — 2026-09-24 — Framing fixed: routing drives production

**User's requirement.** "As long as we have to plan how much radiation the
isotope has at manufacturing contingent on the route (i.e. when it will be
delivered), making routing central to production, I'm happy with the
framing." User delegated the decisions needed to make this hold ("don't
overcomplicate"), overriding earlier statements where they conflict.

**What conflicted.** E4 had one production end time T for everything. With
T and τ_p both fixed, produced activity doesn't depend on the route (E3).
So "one production time for the day" had to go. Clinic-set τ_p (D3) and
the 2 h lead time (D11) were kept.

**Decisions (Claude, delegated).**
- **D13 — Per-truck production batches.** Truck k's vials are produced in
  one batch finishing at `P_k` (decision); departure = `P_k + q`. Produced
  activity per vial = `x_p·exp(λ(τ_p − P_k))`. The route bounds `P_k`:
  `P_k ≤ min over stops (τ_p − 2h − travel to stop) − q`. So the route
  decides how early production must finish, which decides how much
  activity to make. *Why this option:* it is the smallest change that
  satisfies the requirement, it keeps D3 and D11, and it matches how
  short-lived radiopharmaceuticals are actually produced (several runs a
  day, timed to routes). Rejected: option B (treatment time tied to
  arrival — contradicts D3); a full production-line scheduling model (too
  complex for §1's "keep manufacturing simple").
  *Resolves O7:* the plan's slot discretization is still justified —
  `exp(−λ P_k)` × assignment binaries is nonlinear. Slots now discretize
  batch finish / dispatch time instead of arrival time. Phases 3–4 keep
  their discretization-error motivation.
  *Simplification logged:* no sequencing between batches of the same drug
  (they can finish simultaneously).
- **D14 — Unit doses** (closes O9). Matches user's mental model and
  industry practice (Pluvicto, E5). Makes patient-level split deliveries
  natural.
- **D15 — Capacity = vial count per truck per isotope** (closes O8).
  Simplest option. D13 already supplies the coupling, so a radiation-based
  capacity isn't needed for the framing. Kept as a later realism upgrade.

**Worked example (hand-checkable; basis for a Phase 2 toy case).**
Two hospitals, each 30 min from the depot and 30 min apart. H1: one
patient at 09:00. H2: one patient at 13:00. Both need 200 MBq. q = 1 h,
lead time 2 h.

| Plan | Batches (P_k) | At-211 produced | Y-90 produced | Drive time |
|---|---|---|---|---|
| 1 truck, depot→H1→H2→depot | 05:30 | 280.0 + 411.1 = **691.1 MBq** | 207.7 + 216.9 = **424.6 MBq** | 1.5 h |
| 2 trucks, one per hospital | 05:30 and 09:30 | 280.0 + 280.0 = **560.0 MBq** | 207.7 + 207.7 = **415.4 MBq** | 2.0 h |
| Saving from 2nd truck | | 131 MBq (−19%) | 9 MBq (−2%) | +0.5 h, +1 truck |

With At-211 a second truck buys a large waste reduction; with Y-90 it
barely matters. The over-production vs. distance/vehicles trade-off
(plan §5) is now real and depends on the isotope — which is why D1
picked a half-life spread.

**plan.md updated:** §1 (coupling mechanism), §2 (unit doses, units,
per-truck batches, lead time, why routing drives production, tractability
note on batch-time slots), §3 (vial-count capacity, GBq production cap),
§4 (deadlines + receiving hours), §6 Phases 2 and 4 wording.

---

## E7 — 2026-09-24 — Phase 1: design notes, environment, generator

**User approved Phase 1** plus environment setup and Gurobi authentication (D16).

**Environment.** `.venv` with Python 3.12.9 (Homebrew; 3.14 avoided for
solver-wheel compatibility). numpy, pandas, matplotlib, pyyaml, pytest,
gurobipy 13.0.3. Gurobi runs, but only on the **restricted pip license**
(size-limited, ~2,000 variables/constraints). Full academic license needs
the user to authenticate with their Northeastern account — see open item
O10.

**Parameter research** (sources in DESIGN_NOTES §6):
- Pb-212: ALPHAMEDIX-02 regimen 2.50 MBq/kg, max 5.5 mCi (203.5 MBq).
- At-211: trial dose escalations 1.25–3.5 MBq/kg ([²¹¹At]NaAt) and
  0.65–2.1 MBq/kg ([²¹¹At]MABG).
- Y-90 radioembolization: median ~1.7 GBq (1.4–2.5); SIR-Spheres max 3 GBq.
  Also found that Y-90 microspheres are in reality produced centrally and
  often weekly, with vials sized to a reference day (R5). Daily local
  production fits Pb-212/At-211 much better than Y-90.

**Deliverables.**
- `DESIGN_NOTES.md`: notation, formulation core (route invariance,
  latest-batch rule, discretization error bound, irreducible vs
  routing-induced over-production), parameters with confidence levels,
  assumptions register A1–A16, real-world issues register R1–R14.
- `radvrp/` package: config (with `extends`), decay, geo (Boston metro,
  coastline mask), instance (data model, derived columns, validation,
  save/load), generator (random + manual modes), viz.
- Configs: `base`, `small` (6 hospitals), `medium` (16), `large` (40),
  `toy_e6` (hand-checkable E6 case).
- 23 tests passing, including the E6 hand calculations.

**Findings while building.**
1. *Irreducible over-production dominates for short isotopes.* In
   generated instances, lead time + QC + direct travel already forces
   ~4–5% (Y-90), ~27–29% (Pb-212) and ~42–48% (At-211) over-production
   before any routing choice. Routing can only affect what comes on top.
   Real-world corollary: shortening QC or lead time could beat route
   optimisation for At-211.
2. *A2 is confirmed non-binding.* The worst-case vial is ≤ 1.4% of A2
   across all instances.
3. *Demand realism vs. research value (→ D17).* With first-pass
   "realistic" rates, instances had 1–3 At-211 patients, so each At-211
   truck would carry a single patient and the most interesting isotope
   would be trivial. Switched to a future-adoption scenario (higher alpha
   eligibility and volumes), documented as A16. **Flagged for user
   review.**
4. *Instance variance.* The 16-hospital `medium` preset drew fewer patients
   than `small`. Phase 3 must average over multiple seeds; added
   `demand_scale` to vary demand independently of hospital count.
5. *Rounding check.* The E6 single-truck At-211 total is 691.1 MBq with the
   precise half-life (7.214 h), not 691.2 (7.21 h). Table corrected.

**New open item.**
- **O10 — Gurobi academic license** activation (user action).

---

## E8 — 2026-09-25 — Restricted Gurobi license; git initialised

**Context.** The user is off campus and can't activate the academic
license yet (O10). The restricted pip license will be used meanwhile (D18).

**Restricted license limits, measured:** exactly 2,000 variables and 2,000
linear constraints. 2,001 of either → "Model too large for size-limited
license".

**Will it be enough?** Rough size estimate for a plausible Phase 2
formulation (three-index arc variables per truck; patient→truck
assignment; batch-slot choice; trucks bounded by distinct (hospital,
treatment time) pairs). Not the final formulation:

| Instance | Est. variables | Est. constraints | Fits? |
|---|---|---|---|
| toy_e6 | ~210 | ~90 | Yes |
| small (6 hospitals, 19 patients) | ~1,220 | ~860 | Yes |
| medium (16 hospitals, 17 patients) | ~1,380 | ~1,020 | Yes, with little margin |
| large (40 hospitals, 53 patients) | ~14,500 | ~14,900 | **No** |

*Conclusion:* the restricted license covers Phase 2's purpose — correctness
on hand-checkable and small instances. Phase 3's scaling study is where the
full license becomes essential. Without a fleet cap (O2) the model splits
by isotope, which roughly divides the size by three, but a fleet cap would
re-couple the isotopes. Fallback if activation keeps slipping: an
open-source MILP solver (HiGHS) has no size limit, at some speed cost.

**Git.** Repository initialised; first commit contains the plan, timeline,
design notes, configs, `radvrp/` package and tests. Generated data,
plots, `.venv` and license files are git-ignored (they are reproducible
from configs and seeds).

---

## E9 — 2026-09-25 — Shared resources: fleet cap, dispatch, multi-trip

**Context.** Claude laid out O2 (fleet cap + dispatch limit) and O5
(multi-trip). Core point: without a shared resource, the three-isotope
problem is just three independent problems. These constraints are what
make the isotopes compete.

**Decisions.**
- **D20 — Dispatch limit shared across isotopes.** User's reasoning:
  whatever the synthesis lines can produce, the loading dock has a fixed
  number of bays, so at most m trucks load per slot. Since departure = batch
  finish + QC, this also caps batches finishing per slot. It effectively
  acts as a manufacturer-side throughput constraint and replaces
  simplification A6's "unlimited simultaneous batches". Default m = 2 per
  30-min slot (low confidence).
- **D21 — Multi-trip vehicles.** An industry contact confirmed multi-trip is
  expected practice. Isotope may change between trips (one isotope *per
  trip*). Turnaround 30 min. Drivers, like vehicles, are interchangeable
  and need not stay with one vehicle, so hours-of-service is out of scope
  (R15).
- **D19 — Fleet cap** kept as an optional hard constraint (off by default).
  Only meaningful together with D21.

**Key modelling result (Claude).** Vehicles and drivers are identical and
every trip starts and ends at the depot, so trips form an *interval graph*:
the minimum fleet = the maximum number of trips overlapping in time
(turnaround included), and greedy assignment by start time achieves it.
The fleet cap is therefore "≤ K trips active per slot", with no
trip→vehicle assignment variables. This avoids the usual difficulty of
multi-trip VRP formulations. Vehicle and driver schedules are recovered
after solving. Written up in DESIGN_NOTES §5.5.

**Planned test (Phase 2b).** E6 toy with one vehicle: infeasible without
multi-trip; with multi-trip, 4 trips, At-211 at its lower bound (560 MBq),
Y-90 moved earlier (422 vs 415 MBq). The model should favour the
short-lived isotope without being told to.

**Updated:** plan.md §2–3; DESIGN_NOTES §3 parameters, new §5.5,
objective 3 now counts vehicles (peak simultaneous trips) rather than
trips, assumptions A6/A13, issues R15–R16; `turnaround_min` added to
config and `Operations`.

---

## E10 — 2026-09-25 — Fleet-cap semantics, parameters, staging

- **Fleet cap semantics clarified.** User's first reading was "at most K
  dispatches per slot". Claude pointed out that this is weaker than what a
  K-truck fleet implies. Trips last longer than one slot, so trucks
  dispatched earlier may still be on the road. Example: K = 2, trips of
  2 h; dispatching 2 at 05:00 and 2 more at 05:30 satisfies "≤ 2 per slot"
  but needs 4 trucks. The correct rule (DESIGN_NOTES §5.5): **trips on the
  road (including turnaround) ≤ K in every slot**. Dispatches per slot are
  then bounded by K minus trucks already out, and separately by the dock
  limit m. **User confirmed** this is what they meant ("max K dispatches in
  any slot, contingent on availability").
- **m is a configurable parameter** (not a decision variable), expected to
  be one of the most influential constraints and swept in Phase 3.
- **D22:** two-stage Phase 2 accepted.
- **D23:** all placeholder constants accepted provisionally. They are
  config values, and none is structural. Revisit only if one turns out to
  drive infeasibility or dominate results. Older open items (O6 storage
  cost, O10 license) stay open.

---

## E11 — 2026-09-25 — Interview focus; manufacturing deferred to Phase 7

**Context (decision driver).** The project is the main talking point for
an **Esri interview on Monday 2026-09-28**, for a role that leans towards
testing. The user wants the routing work done and explainable by then,
without carrying extra material they would have to memorise.

**Sequence.**
1. Claude presented the Phase 2a MILP in chat. It included a daily
   production cap and a soft-dose mechanism (delivered fraction φ,
   under-dose penalty).
2. User: the job is to turn demand and timing into routes and tell the
   manufacturer how much to dose. Is the manufacturing side worth
   including?
3. Claude: the batch timing *is* that "how much to dose" output and must
   stay (it is the D13 coupling). The cap and soft doses exist only for
   "what if the manufacturer can't make it". Dropping them costs the
   "feasible only because of the lower band" part of D9.
4. Claude also suggested an interview narrative (problem → key insight →
   trade-off → two modelling tricks → validation story). It links the
   project to Esri Network Analyst's VRP solver (road-network cost matrix,
   insertion construction, tabu-search improvement; capacities, time
   windows) and proposes a phase order suited to Esri (→ O12).
5. **User decision (D24):** keep manufacturing, but as a later phase. The
   interview line: *"this was identified, but there is little wiggle room
   with the manufacturer and we're still working out how that part is best
   modelled."*

**Decisions.**
- **D24 — New Phase 7: manufacturing integration.** Moved there: daily
  production cap, soft dose target and under-dose penalty (D8 amended), the
  "lower-band" robustness case (D9 amended), producibility check,
  synthesis sequencing, shared production capacity, QC variability/batch
  failure, isotope cost per MBq, packaging/regulatory detail, realistic Y-90
  supply, hospital storage cost (O6). **Stays:** per-trip batch time
  (routing output), QC time and production window as fixed inputs,
  decay-waste objective, dispatch limit. New assumption A9: the manufacturer
  can fill any order. New issue R17.
- **D25 — Phase 2a formulation fixed** (DESIGN_NOTES §5.7), without the
  manufacturing terms: 6 variable families, constraints C1–C11, waste in
  dose equivalents. Size on `small` ≈ 660 variables / 870 constraints
  (restricted license fits toy/small/medium). The removed terms are kept as
  the Phase 7 extension in DESIGN_NOTES §10.3 (~+200 variables on `small`).

**Updated:** plan.md §1–3, §5–6 (new Phase 7; Phase 2 description);
DESIGN_NOTES status, §3, §5.4, §5.6 (dose equivalents), new §5.7, A6, A9,
R17, new §10; `capacity_factor` config comment. The generator still
computes `daily_cap_mbq` for Phase 7; no code changed.

---

## E12 — 2026-09-25 — Phase 2a implemented and validated

**Handover.** A forked session ("evaluating manufacturing aspect") made
D24–D25 with the user and pushed 45ed2b5. This session pulled it, confirmed
sync, and became the main development session again. The fork agreed to
make no further repo edits.

**Built** (DESIGN_NOTES §5.7 implementation notes): `radvrp/model.py`
(MILP C1–C11, weighted or lexicographic via Gurobi multi-objective),
`radvrp/checker.py` (independent simulator/checker), `radvrp/report.py`
(waste split), `scripts/solve.py`, route and schedule plots, two new toy
configs, 17 new tests (40 in total, all passing).

**D26 — defaults and one post-processing step (delegated).**
- Default weights 100 per dose-equivalent / 1 per km / 20 per trip. Chosen
  so the E6 toy reproduces the headline trade-off at default settings:
  split At-211 (saves 0.65 doses = 65 > 40 km + 1 trip = 60) but not Y-90
  (saves 0.05 doses = 5). Weights stay a tunable parameter (plan §5).
- Batch re-timing: `B_k` isn't in the objective, so the solver may leave it
  earlier than the route allows. After solving, each trip moves to its
  latest feasible slot. This never breaks a deadline and never increases
  waste.

**Findings.**
1. All hand-calculated toy results reproduced (At-211 total 559.9 MBq, not
   560.0: 2 × 279.95).
2. The model finds the isotope-dependent trade-off by itself: at default
   weights it gives At-211 a second truck and consolidates Y-90.
3. "Deadline-forced split" was a misnomer: nothing makes a single trip
   infeasible, the split is waste-driven. Renamed "deadline-driven".
4. `small`: 69% of waste is irreducible, 26% routing-induced, 5% from the
   30-min slot grid. Routing controls about a quarter of the waste, which
   is an honest framing for the interview.
5. Deadline-driven splits appear at realistic scale (Pb-212 on `small`).
6. Solve times: small 0.15 s, medium 0.38 s. `large` (≈13.5k variables)
   needs the academic license (O10). Handled with a clear message rather
   than a crash.

---

## E13 — 2026-09-25 — Road distances; schedule chart

- **User observation:** travel uses straight-line geometry, not real road
  distance, which is unrealistic. From the model's perspective only the
  output changes; in production, swapping in real distances does the job.
  *Clarified by Claude:* the matrix is great-circle × 1.3 circuity at
  40 km/h (A3), an estimate of road distance, not raw displacement. The
  user's point stands. Checked what a real road matrix would need:
  asymmetry (one-way streets) is already supported by the model and
  checker; shortest-path road times satisfy the triangle inequality the
  split reasoning relies on; **time-dependent travel would be a model
  change**, not a data swap. Maps directly onto Esri Network Analyst's
  OD cost matrix (Phase 5). A3 updated.
- **Schedule chart redesigned** at the user's request (first version was
  hard to read). Now: rows ordered by departure, segments for QC/loading,
  driving, stop, waiting, return. Stop labels alternate above/below and
  include vials dropped and slack to the earliest deadline, with a bracket
  from arrival to deadline.
- *Finding surfaced by the chart:* on `small`, trip T3 reaches A02 with 4
  min of slack, and T1 with 0 min (it leaves at the latest possible time
  by design). Minimising waste pushes every batch as late as possible, so
  **optimal plans are, by construction, the least robust to delay**. This
  is a concrete input for the D9 robustness analysis (Phase 3).

---

## E14 — 2026-09-25 — Speed assumption, truck view, phase-2 branch

- **D27 — Travel speed.** User doesn't need time-dependent travel and is
  happy to be conservative. Idea for later: use an estimated *peak-hour*
  average speed instead of a steady 40 km/h. That is one config value, so
  a data change rather than a model change. For now 40 km/h stays
  ("reasonable"). Recorded under R2.
- **D28 — Truck view.** User asked for a way to show trips on concrete
  trucks and drivers so a third person can read the plan, without changing
  the model. Implemented as a post-solve assignment (`radvrp/fleet.py`),
  greedy in departure order, which is optimal for interval graphs; it's
  the same argument that will let 2b model the fleet cap without
  trip→vehicle variables. New `schedule_by_truck.png`; route map labels
  trips with their truck. On `small`: 5 trips on 3 trucks (preview of what
  the 2b fleet cap will constrain).
- **D29 — Branching.** Phase 2 work is committed to a new branch
  `phase-2`; the user merges to `main` only after the whole of Phase 2
  (2a + 2b) is complete.
