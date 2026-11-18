# Research basis for the age-tier design

This project's four age-tier experiences aren't guesses — each one is built
around a specific, citable finding from published UX/fintech research.
This document lists what was found and exactly which design decision it
drove, so the reasoning is checkable rather than asserted.

## Kid & teen tiers — gamified financial literacy

**Sources:**
- Ruiz-Carhuamaca et al., *"Design of a Mobile Learning App for Financial
  Literacy in Young People Using Gamification,"* International Journal of
  Advanced Computer Science and Applications, 2024.
  ([DOI](http://dx.doi.org/10.14569/IJACSA.2024.0151210))
- Nansen, Bliss & Sandberg, *"Making finance fun: Playful affordances and
  gamified interface designs in children's FinTech apps,"* 2026.
  ([DOI](https://doi.org/10.1177/09075682261437591)) — identifies five
  recurring design functions across real child-finance apps: chore/task
  management, child savings, spending systems, parental oversight, and
  banking basics, delivered through points/tokens/rewards.
- NetBramha Studios fintech case study — notes the common failure mode of
  "a single, holistic financial literacy platform that caters to all age
  groups" and the need for content "scientifically-backed" and tailored
  per age band rather than one generic UI.

**What this drove in the app:**
- The **savings-goal + reward-token pattern** these papers describe maps
  directly to the Piggy Bank + badge system in Playground mode.
- The "playful affordances" and points/token framing maps to the XP/Level
  system and Coiny the money buddy, whose expression is tied to real
  progress (not decorative animation) — matching the papers' emphasis on
  linking rewards to genuine behavior rather than arbitrary flourishes.
- The Teen Quest Chain reflects the "challenge-based" structure the 2024
  IJACSA paper proposes for reinforcing financial concepts through
  interactive tasks rather than static reading.

## Senior/Comfort tier — accessible interface design for older adults

**Sources:**
- *"Design Guidelines of Mobile Apps for Older Adults: Systematic Review
  and Thematic Analysis,"* JMIR mHealth and uHealth, 2023.
  ([mhealth.jmir.org/2023/1/e43186](https://mhealth.jmir.org/2023/1/e43186))
- WCAG 2.2 — minimum 4.5:1 contrast ratio for body text, 3:1 for large
  text and interactive elements.
- Multiple UX-for-seniors sources consistently recommending: larger base
  font sizes (16px minimum, with some studies favoring considerably
  larger), sans-serif typefaces, reduced reliance on blue tones (which
  appear faded to aging eyes), minimal clutter/single-column layouts, and
  clear, unambiguous distinction between touchable and non-touchable
  elements.

**What this drove in the app:**
- The Comfort theme sets the **entire app's base font size to 21px** via
  one CSS rule (`html[data-theme="senior"] { font-size: 21px; }`), so
  every page scales up automatically rather than requiring per-component
  overrides — directly implementing the "large font size" recommendation
  app-wide instead of on a single screen.
- Comfort theme's color palette deliberately avoids blue as a primary
  accent (uses teal/green, amber, and deep red instead), and its text
  colors were chosen for high contrast against a warm cream/white
  background, in line with the WCAG 4.5:1 guidance.
- Every Comfort-mode page (Dashboard, Insights, Interventions, Goals,
  Report) uses a **single-column layout** and replaces dense grids/tables
  with plain-language paragraphs and larger tap targets, matching the
  "minimize clutter" and "clear touchable elements" guidance.

## Honesty about scope

This is a design-research grounding, not a machine-learning model trained
on a dataset — there's no user-behavior dataset bundled with this project,
and the platform doesn't learn generalized age-based UX preferences from
external data. What's real: the *design choices themselves* (font sizes,
contrast, gamification mechanics, layout structure) are traceable to
published findings rather than invented from scratch, and are named above
so you can verify them yourself or swap in different sources if you
disagree with any of them.
