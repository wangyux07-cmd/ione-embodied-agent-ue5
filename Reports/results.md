# Deterministic evaluation results

> These are planner-simulation results, not Unreal frame-time or user-study results. Timing measures local Python planning only.

| Strategy | Semantic accuracy | Forbidden violations | Repetition | Stale / interrupt | Planner P95 |
|---|---:|---:|---:|---:|---:|
| Flat Tag | 48.4% | 0.0% | 0.0% | 0.00 | 0.0036 ms |
| Rhythm | 48.4% | 0.0% | 58.6% | 2.33 | 0.0077 ms |
| Semantic | 98.4% | 0.0% | 11.3% | 0.00 | 0.0117 ms |

## Interpretation

The semantic planner covers more authored functions because it schedules multiple anchors, not because an LLM judge awarded it a score. Constraint filtering removes known forbidden/state-blocked clips. Its zero stale-action value is an architectural expectation from cancelling pending timers; it must still be verified in PIE with real Montages and frame captures.

## Pre-registered hypotheses

- H1 is supported in this deterministic set: C has higher semantic function coverage.
- H2 is supported by construction: C is the only planner that filters forbidden/state-blocked gestures.
- H3 needs human pairwise ratings; this script cannot measure perceived rhythm naturalness.
- H4 needs UE Insights and real model/API timings.
- H5 is represented by A/B stale scheduled events, but needs PIE validation.
