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
| D8 | 2026-09-24 | Dose target = prescribed dose; band [L, U] stays a hard constraint | User | E3 |
| D9 | 2026-09-24 | Robustness analysis is a planned deliverable: find solutions that are feasible *only because* doses sit at the band's lower limit, then stress-test them | User | E3 |
| D10 | 2026-09-24 | Split-delivery ties and hidden per-visit costs accepted as-is (no per-visit cost term) | User | E3 |
| D11 | 2026-09-24 | ~~Arrival time irrelevant to dosing~~ (superseded by D13); hard lead time kept: each dose on location ≥ 2 h before its patient's scheduled time | User | E4, E6 |
| D12 | 2026-09-24 | Truck capacity set per isotope; A2 kept as a (expected non-binding) per-package check | User | E4 |
| D13 | 2026-09-24 | **Framing:** production batched per truck, batch finish time `P_k` is a decision and is limited by the route, so routing determines produced activity. Slots discretize `P_k` | Claude (delegated by user) | E6 |
| D14 | 2026-09-24 | Unit doses: one vial per patient | Claude (delegated by user) | E6 |
| D15 | 2026-09-24 | Truck capacity unit = count of unit-dose vials per isotope | Claude (delegated by user) | E6 |
| D16 | 2026-09-24 | Phase 1 started (user approval); Python 3.12 venv + Gurobi 13.0.3 | User | E7 |
| D17 | 2026-09-24 | Future-adoption demand scenario for alpha therapies (assumption A16) | Claude (delegated) — flagged for user review | E7 |
| D18 | 2026-09-25 | Use restricted Gurobi license until campus activation; project put under git | User | E8 |

### Open questions

| ID | Opened | Question | Status |
|----|------------|----------------------------------------------------------------------|--------|
| O1 | 2026-09-23 | Fixed production end + fixed administration times ⇒ decay is route-independent. How do we restore the decay↔routing coupling? | Closed 2026-09-24 → D11 (coupling via arrival time dropped; see O7) |
| O2 | 2026-09-23 | Fleet-size cap and depot dispatch limits as cross-drug coupling (Dantzig–Wolfe structure) | Scoped, deferred — user wants to discuss |
| O3 | 2026-09-23 | Dose target within the tolerance band (lower / nominal / upper) | Closed 2026-09-24 → D8 |
| O4 | 2026-09-23 | How to model A2 (per-package) limits and real truck capacity | Closed 2026-09-24 → D12 (capacity *unit* still open → O8) |
| O5 | 2026-09-23 | Can a truck make multiple trips (possibly with different isotopes)? | Open — raised with O2 |
| O6 | 2026-09-24 | Storage at the hospital has a (not necessarily monetary) cost: hot-lab space, shielding, staffing | Open — user wants to think about it |
| O7 | 2026-09-24 | D11 removes the plan's stated core question (decay↔routing coupling) and the reason for time-slot discretization. How should plan.md §2 tractability note and Phases 3–4 be reframed? | Closed 2026-09-24 → D13 (framing restored; slots kept, moved to batch time) |
| O8 | 2026-09-24 | Truck capacity unit: package count vs. activity/radiation (TI) on board at departure | Closed 2026-09-24 → D15 |
| O9 | 2026-09-24 | Packaging model: per-patient unit doses vs. a shared bulk vial per hospital | Closed 2026-09-24 → D14 |
| O10 | 2026-09-24 | Activate Gurobi academic license (only restricted pip license active) | Open — user needs campus network; restricted license in use meanwhile (E8) |

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
