# Project: Decay-Constrained Vehicle Routing for Radiopharmaceutical Delivery

## 1. Problem Context

We are modeling the daily distribution of radioactive cancer-treatment drugs
(radiopharmaceuticals) from a single manufacturing depot to hospitals/clinics
in a metro area. The defining feature that makes this different from a
standard VRP: **the product decays radioactively during transit**, so the
activity level a patient receives depends on *when* the drug is delivered.
This creates a feedback loop between manufacturing (how much activity to
produce) and routing (when a truck arrives), which is the central research
question of this project.

**Coupling mechanism (fixed 2026-09-24, TIMELINE.md D13):** each truck's
doses are produced as that truck's own production batch, finished just in
time for its route. The route determines how early the truck must leave, so
it determines when its batch must be finished, so it determines how much
activity must be produced. Routing is therefore an input to production
dosing.

This is being built as a portfolio/research project — the priority is a
rigorous, well-documented approach to the decay↔routing coupling, not
manufacturing-side realism. Manufacturing capacity constraints should be
present but simple; do not over-engineer that part.

## 2. Physical / Decay Model

- Radioactive decay is deterministic and exponential:
  `A(t) = A0 * exp(-λ * t)`, where `λ = ln(2) / half_life`.
- Start with **3 isotopes/drugs**, each with a distinct half-life. Use real
  half-life values for 3 actual therapeutic radiopharmaceutical isotopes
  (e.g., candidates: Lu-177, Y-90, I-131, Ac-225 — research and pick 3 with
  meaningfully different half-lives to make the problem interesting).
- Each patient at each hospital has a **required activity at time of
  administration**, `x`. Model demand as a **range/tolerance band**, not a
  bare "≥ x": each dose is produced so the patient receives their
  **prescribed dose** at their scheduled administration time, with the band
  `[L_p, U_p]` as hard bounds and deviation from the prescribed dose
  penalised (soft target). (Revised 2026-09-24: an earlier version targeted
  `upper_limit + delta` — see TIMELINE.md, D8.)
  Patient administration times are **set by the clinic** (an input to the
  model, not a decision).
- **Unit doses** (TIMELINE.md D14): each patient's dose is its own vial,
  prepared at the depot. A truck carries a set of patient vials; which
  vials go on which truck is a decision.
- **Units:** every quantity is **activity** (MBq/GBq) — prescribed doses,
  produced activity, production capacity, A2. Volume/concentration are
  packaging details and are not modelled (TIMELINE.md E5).
- **Demand is patient-level**: model individual patient dose requirements
  within each hospital, not just an aggregated hospital-drug-day total.
- **Production is batched per truck** (TIMELINE.md D13). Truck `k`'s vials
  are produced in one batch finishing at time `P_k` (a decision); the
  truck departs at `P_k + q` (`q` = QC/release + packaging time).
  Required activity for patient p on truck k:
  `a_p = x_p * exp(λ * (τ_p − P_k))`, where `τ_p` is patient p's
  clinic-scheduled administration time. Truck k's batch activity is the sum
  over its patients. (Revised 2026-09-23: an earlier version used the
  elapsed time to the *last-served* patient for the whole batch, which
  over-estimates required activity for every earlier patient.)
- **Lead-time requirement** (TIMELINE.md D11): each patient's vial must be
  on location at least **2 hours** before that patient's scheduled
  administration time.
- **Why routing drives production:** for a fixed `P_k`, the arrival time
  itself doesn't change decay (transit decay + storage decay always sum to
  `τ_p − P_k`; TIMELINE.md E3). What the route *does* fix is how late `P_k`
  can be: `P_k ≤ min over the truck's stops of (τ_p − 2h − travel time to
  that stop) − q`. A route with more stops, longer travel, or one stop with
  an early deadline forces an earlier batch, which inflates the activity of
  **every** vial on board. Minimising over-production therefore pushes
  toward trucks carrying patients with similar treatment times on short
  routes — in direct tension with minimising distance and vehicle count.
- **Simplification:** batches for the same drug may finish at any time,
  including simultaneously. There is no production-line sequencing (one
  hot cell running one synthesis at a time). This is deliberately left out
  per §1; a limit on batches per time slot is a natural extension (linked
  to depot dispatch limits, TIMELINE.md O2).
- **Manufacturing ceiling**: research and apply a real regulatory ceiling on
  producible/transportable activity per shipment — specifically the
  isotope-specific "A2 quantity" limits used in NRC/DOT Type A package
  regulations for Class 7 (radioactive) materials. Use actual A2 values (or
  well-sourced approximations) for the 3 chosen isotopes as the upper bound
  `A_max_i` on manufactured activity per shipment for drug `i`.
  (Clarified 2026-09-23/24: A2 caps activity per **package**, not per
  shipment or truck; exceeding it means more packages, not infeasibility.
  At realistic dose sizes it is expected to be non-binding and is kept as a
  check — see TIMELINE.md, E2 and D12.)
- **MILP tractability note**: `exp(−λ·P_k)` with continuous `P_k`,
  multiplied by binary "patient p on truck k" variables, is nonlinear. To
  avoid this, discretize the batch finish / dispatch time `P_k` into a small
  set of slots `s` (e.g., every 15–30 min within the production window).
  The required activity `c_{p,s} = x_p * exp(λ(τ_p − s))` then becomes a
  precomputed constant per (patient, slot). Rounding `P_k` *down* to a slot
  is conservative (always feasible, slightly over-produces). Document this
  discretization explicitly as a known approximation — it is expected to be
  one of the deficiencies exposed by the MILP phase and addressed later (see
  Phase 4). (Revised 2026-09-24: slots were previously on arrival time;
  they are now on batch finish / dispatch time — TIMELINE.md D13.)

## 3. Fleet & Routing Structure

- Single depot (one manufacturing/production site).
- A single truck carries only one isotope/drug (no mixed loads); multiple
  trucks may carry the same drug.
- Homogeneous vehicles for now (same speed across all trucks) —
  flagged as a simplification that may be revisited later based on
  real-world input. **Truck capacity is set per isotope** (revised
  2026-09-24, TIMELINE.md D12): shielding needs differ sharply — Y-90 is a
  pure beta emitter, while Pb-212's decay chain emits a 2.6 MeV gamma — so
  a truck carrying Pb-212 holds far fewer packages than one carrying Y-90.
  Capacity is a **count of unit-dose vials per truck per isotope**
  (TIMELINE.md D15). A radiation-based (transport index) capacity is a
  possible later realism upgrade.
- Deliveries happen daily, scheduled **2 days in advance** for a given
  delivery day.
- Manufacturing has a **per-drug capacity limit** (simple upper bound on
  total activity, in GBq, producible per day per isotope, summed over that
  drug's batches) — not shared across drugs, kept intentionally lightweight.
  Because batch activity depends on batch timing, a tight cap pushes the
  model toward later batches, and so toward more or shorter routes.

## 4. Demand & Network

- Geographic scope for the synthetic phase: **a single metro area** (pick
  one real city/metro — e.g., Boston — and use realistic-scale
  coordinates/distances for hospitals and depot). This sets up a natural
  transition to real map/routing data later.
- Not all hospitals require all drugs — support a hospital-drug
  eligibility/requirement mapping (a hospital may only be equipped/approved
  to administer some subset of the 3 drugs).
- Demand generation: synthetic patient-level demand per hospital per drug
  per day, with realistic distributions for dose requirements per patient
  and patient counts per hospital.
- Delivery time windows: each vial has a **deadline** of `τ_p − 2h` (§2).
  Each hospital also has an earliest receiving time (hot-lab opening
  hours). (Revised 2026-09-24: slots now apply to batch/dispatch time, not
  arrival — see §2.)

## 5. Objective Function

Multi-objective, with priority order open to revision once results are in.
Start with a weighted combination of:
1. Minimize total manufacturing over-dose (excess activity produced beyond
   the theoretical minimum needed at point of administration) — this is a
   proxy for cost, waste, and radiation-safety exposure.
2. Minimize total transportation distance/time across all routes.
3. Minimize number of active routes/vehicles used.

Leave the exact weighting/priority scheme as an open, tunable parameter —
do not hard-code a single scalarization; make it easy to experiment with
lexicographic vs. weighted-sum approaches.

## 6. Solution Approach — Phased

All of these phases should be build one after the other, only once the user gives the heads up. Don't build consecutive phases without approval from the user, even if Phase n doesn't do anything without Phase n+1. There is always enough stuff that can be done to check a single phase.

**Phase 1 — Synthetic data generator.** Build a configurable generator for:
depot + hospital locations (single metro area), hospital-drug eligibility,
per-hospital daily patient counts and dose requirements, 3 isotopes with
real half-lives and A2-derived activity ceilings, per-drug manufacturing
capacity. Should scale cleanly from small (validation-sized) to larger
instances via config, not code changes.

**Phase 2 — Exact MILP formulation.** Formulate and implement the full
problem (decay-linked dosing + VRP + manufacturing capacity + patient-level
unit doses assigned to per-truck production batches) as a MILP. Use
discretized batch/dispatch time slots per Section 2. Solve on small instances using an
available solver (MILP solver such as Gurobi). Validate correctness on
hand-checkable toy cases before scaling up.

**Phase 3 — Deficiency analysis.** Systematically identify where the MILP
approach breaks down or produces unsatisfying results as instance size
grows or as the time-slot discretization is made coarser/finer — solve time
blow-up, discretization error in the decay coupling, quality of the
weighted-objective tradeoff, etc. Document these clearly; they motivate
Phase 4.

**Phase 4 — Metaheuristic approach.** Design and implement a metaheuristic
(e.g., ALNS, genetic algorithm, or similar — propose and justify a choice. The final choice here will have to be made by the user.)
that specifically targets the deficiencies found in Phase 3, particularly
around scaling and/or a more faithful (less discretized) treatment of the
decay–batch-time relationship (continuous `P_k`, evaluated exactly). Compare against Phase 2 MILP results on
shared instances.

**Phase 5 (later, out of scope for now) — Real-world data.** Swap synthetic
hospital coordinates/distances for real map data for the chosen metro area
(actual road network travel times rather than Euclidean/straight-line
distance). Flagged as a natural extension, not part of the initial build.

**Phase 6 Integrate Routes for drivers thru Maps API** Goal here is to be able to display the route on (maybe) Google Maps, which the manager at the plant could use to track the routes, as well as the provide to the drivers that will be making the delivery that morning.

## 7. Tech Stack

- Python throughout.
- MILP: OR-Tools CP-SAT or PuLP + an available MILP backend (confirm solver
  availability before committing).
- Data generation/handling: numpy, pandas.
- Visualization: matplotlib (or similar) for route maps (end goal is to be in a real, interactive map) and
  decay/dose-over-time plots — useful both for debugging and for
  presenting results.

## 8. Deliverables & Documentation Expectations

- All simplifying assumptions (time-slot discretization, homogeneous
  vehicles, per-drug-only manufacturing capacity, single-depot,
  single-metro-area, etc.) should be clearly documented in code comments
  and a running design-notes file — this project is meant to support a
  substantive technical discussion (including as VRP portfolio material),
  so the reasoning behind each simplification matters as much as the code.
- Keep the formulation modular over index sets (drugs, hospitals, vehicles)
  so scaling to more drugs/hospitals is a config change.
- This is an evolving research effort — expect scope to shift as we learn
  from Phase 2/3 results. Structure the codebase to make that iteration
  cheap (clear separation between data generation, formulation, solving,
  and analysis/visualization).


Make sure your goal is not to just write, implement and dump the code. The goal here is to systematically and methodically formulate the problem mathematically, conclude a method to solve it and then implement the code. The real prize here is the learning, understanding, formulation, and documentation. The code is just something that ultimately needs to be done to solve for the most optimal routes.

At all points, while working, ensure that you're also looking for issues that might pop up in the real world that get swept under the carpet during academic work such as this. The idea here is not to solve and work around all of them, but to understand that if we were to implement this in a production environment, the kind of roadblocks and gotchas that we might run into.