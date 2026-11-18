# Novelty notes

This document is an honest engineering summary of what's distinctive about
SpendSense-XAI's design — written to help you (or a patent attorney, if you
pursue that) evaluate it, not a legal claim of patentability.

## What's genuinely uncommon in consumer expense trackers

Most expense trackers (Mint-style apps, Walnut, spend-category apps bundled
into banking apps) do one or more of:
- categorize transactions,
- show category totals / pie charts,
- compare you to *other users* in aggregate ("people like you spend X"),
- send generic budget-limit alerts ("you're over budget in Food").

What's less common — and is the core of this project — is the **specific
pipeline** combining:

1. **Context fingerprinting** — every expense is tagged with a reproducible
   vector (time bucket, day type, payment method, recent screen time) rather
   than just a category and amount.
2. **Recency-decayed conditional-probability mining** over that context
   vector to surface *context → category* associations, each with a
   confidence score computed from the user's own data (not a population
   model).
3. **Evidence-first explanation** — the system never states a pattern
   without attaching the specific counted evidence used to find it (N of M
   transactions, dates, week count), and templated "why it matters" reasoning
   tied to category + context.
4. **A/B-tested intervention assignment** — competing nudge archetypes
   (Habit / Delay / Limit / Friction) are deliberately alternated per user
   per category, rather than a single fixed suggestion.
5. **Closed-loop outcome measurement** — the system automatically re-checks
   real spend in the affected category after the nudge and computes an
   effectiveness percentage, which feeds a keep/stop decision.
6. **Human-feedback override** — a single thumbs-down immediately retires an
   intervention, which is folded back into future suggestions.
7. **Self-only comparison** — the entire measurement surface (baseline,
   "what changed," goal conflict) is scoped to the individual's own history;
   there's no benchmarking against other users' data, which also sidesteps a
   whole category of privacy/data-sharing concerns.
8. **Pattern expiration** — triggers that stop recurring automatically
   decay out of the active set rather than persisting indefinitely.
9. **Counterfactual simulation grounded in personal transaction size** — "if
   you cut X by N times/week" uses the user's own trailing 90-day average
   transaction amount for that category, not a generic assumption.

## What would matter for an actual patent search

If you want to pursue formal IP protection, the things a patent attorney
would look at are:
- **Novelty**: has this exact combination (steps 1–9, wired together as one
  closed loop) been described in a prior patent or publication?
- **Non-obviousness**: would a skilled engineer combining known techniques
  (behavioral nudging literature, A/B testing, time-decayed association
  mining) arrive at this same pipeline without inventive step?
- **Subject-matter eligibility**: expense-tracking software claims often face
  scrutiny under "abstract idea" doctrines (e.g., in the US, post-*Alice*
  case law) unless tied to a specific technical improvement, which is why
  how you *claim* the invention (e.g., emphasizing the decay-weighted
  mining algorithm and the closed-loop measurement architecture, not just
  "an app that tracks expenses") matters a lot.
- **Prior art**: there are patents in adjacent spaces (behavioral nudging in
  fintech, spend categorization, financial goal tracking) worth a proper
  search before investing in a filing.

None of that can be resolved here — this section exists so you have a clear,
honest starting point rather than an inflated claim.
