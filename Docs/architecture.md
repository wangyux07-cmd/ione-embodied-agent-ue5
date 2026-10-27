# Architecture

## UE5-first vertical slice

```text
Player input / interrupt
        |
        v
Dialogue + semantic anchors (JSON contract)
        |
        v
UAsterSemanticPerformanceComponent
  |       |              |
  |       |              +-- state/style constraint filter
  |       +----------------- gesture DataAsset retrieval
  +------------------------- A/B/C planner
        |
        v
Deterministic scheduler (FTimerManager)
        |
        +-- UAnimMontage: body gesture + blend-out policy
        +-- UAudioComponent: voice ownership / fade-out
        +-- UNiagaraComponent: semantic accent state
        +-- Blueprint events: face, UI, world action
```

The LLM is deliberately outside the animation executor. It may propose dialogue and semantic anchors, but it cannot directly play a montage, spawn gameplay effects, or mutate world state. The runtime validates the JSON contract, retrieves authored gestures, filters blocked states, and schedules deterministic engine actions.

## Engine-facing responsibilities

| UE layer | Responsibility | Author control |
|---|---|---|
| `AAsterNPCActor` | Composes mesh, voice, VFX and performance component | Blueprint subclass and Details panel |
| `UAsterSemanticPerformanceComponent` | Builds A/B/C plans and owns cancellation | Blueprint-callable API and delegates |
| `UAsterGestureLibrary` | Maps semantic functions to montages and policies | Data Asset |
| Animation Montage | Gesture clip, slot, blend profile, notifies | Animation editor |
| Niagara | Visualizes anchor and interruption state | User parameters |
| Material Custom node | Scan/dissolve/semantic highlight | Material Instance parameters |
| Blueprint events | Face curves, UI, actual world actions | Project-specific implementation |

## Interruption transaction boundary

An interrupt is not just `StopAllMontages`. It transfers conversational ownership:

1. Cancel every not-yet-fired timer.
2. Fade voice in 80 ms.
3. Apply the current gesture's policy: immediate stop, short blend-out, or finish-phrase.
4. Deactivate semantic VFX and set `User.InterruptStrength` for authored recovery feedback.
5. Enter `Listening`; only a new validated plan may return to `Speaking`.

Gameplay actions are exposed as Blueprint events rather than executed implicitly. The game decides which actions are reversible and where the commit point lies.

## A/B/C strategies

- **FlatTag:** one coarse label, one early gesture. Fast but loses temporal meaning.
- **Rhythm:** generic beats from dialogue length. Better motion cadence, weak semantics.
- **Semantic:** confidence-gated anchors, authored retrieval, GameplayTag constraints and rhythm fallback.

The three strategies share the same executor, assets and scene. Only planning changes, which makes comparison interpretable.
