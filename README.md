# Aster Performance Lab

> **Current development direction (2026-10-27):** This repository is being expanded into **Ione: an interruptible, world-grounded UE5 NPC Agent**. The existing Aster web stage and 30-scene performance planner remain an earlier baseline, not evidence that the new LLM Agent or Ione character is complete. See [Version 3 execution and CV evidence plan](Docs/Version3_Agent项目执行与简历交付.md).

The first offline Agent contract is in `Tools/ione_agent.py`. It demonstrates world-state lookup, a consent-gated door tool, an explicit commit boundary, and cancellation of stale turns. It uses a deterministic proposal fixture, not a live LLM. Run `python -m unittest discover -s Tests -v` to verify the contract.

**An Unreal Engine 5-first research prototype for authorable, interruptible game-NPC performance.**

The prototype asks a narrow systems question: can semantic gesture retrieval, designer-authored constraints and a deterministic cancellation boundary improve NPC performance over flat LLM tags and rhythm-only motion—without training a large motion model?

![Aster concept art](Content/Character/Concept/Aster_KeyArt_v2.png)

## Why this is an Unreal project, not a chatbot demo

The generative layer is not allowed to play animation or change the world directly. It proposes dialogue and semantic anchors. An Unreal runtime plugin validates those anchors, retrieves authored montage definitions from a Data Asset, filters them with Gameplay Tags, schedules animation/VFX, and owns interruption recovery.

- `AAsterNPCActor` packages skeletal mesh, voice, Niagara and the performance component.
- `UAsterSemanticPerformanceComponent` exposes A/B/C planning, Blueprint delegates and deterministic timer cancellation.
- `UAsterGestureLibrary` is the narrative/animation designer's control surface.
- `AsterScanDissolve.ush` is a derivative-aware Custom Node include for scan, edge and dissolve masks.
- Niagara is driven through one reusable component with semantic/intensity/interrupt user parameters.
- Gameplay actions stay behind Blueprint events and project-side authority checks.

See [architecture](Docs/architecture.md), [Material/Niagara notes](Docs/material-and-niagara.md), and the [Unreal setup checklist](Docs/unreal-setup.md).

## Run now

The browser version is a **visualization surrogate**, useful for comparing planner behavior before UE assets exist.

```powershell
.\run_demo.ps1
```

Open `http://localhost:4173/Demo/`. Choose any of 30 fixed cases, switch A/B/C, run the plan, and interrupt Aster while events are pending.

Run deterministic evaluations:

```powershell
python .\Tools\run_evals.py --write-report
python -m unittest discover -s .\Tests -v
```

## Strategies

| Strategy | Planning behavior | Expected weakness |
|---|---|---|
| A · Flat Tag | One coarse semantic label and one early gesture | no timing, low coverage, no explicit cancel policy |
| B · Rhythm | Generic beats plus one coarse semantic tag | motion cadence without reliable meaning |
| C · Semantic | Multi-anchor retrieval, style/state filtering, per-gesture interrupt policy | more authoring; still limited by library quality |

## Repository map

```text
Plugins/AsterPerformanceRuntime/  UE runtime plugin and shader include
Source/                           UE game module
Config/                           Gameplay Tags and project metadata
Content/Character/Concept/        original Aster key art (source concept only)
Data/                             18 gestures and 30 fixed scenarios
Demo/                             interactive browser surrogate
Tools/                            deterministic evaluation runner
Tests/                            planner invariants
Reports/                          results, failures and limitations
.codex/skills/ue5-virtual-human/  reusable UE5 development workflow
```

## Implementation status

| Item | Status | Evidence |
|---|---|---|
| Original anime-styled Aster concept | Complete | project key art |
| A/B/C deterministic planner | Complete | browser implementation, Python evaluator, UE C++ source |
| 30 fixed evaluation cases | Complete | `Data/scenarios.json` |
| Interruption transaction design | Implemented in source; UE verification pending | timer cancellation, montage policy, voice/VFX handoff |
| Material Custom HLSL | Source complete; compile pending | shader include and node recipe |
| Niagara integration | C++ parameters and module specification complete; `.uasset` pending | component code and authoring notes |
| Unreal project compile / PIE | **Not yet verified** | no Unreal installation on this machine |
| Rigged 3D character / facial animation | **Not implemented** | key art only |
| Human pairwise study | **Not run** | questionnaire design remains future work |

## Honest next milestone

On a UE 5.8 workstation: compile the plugin, author the gesture Data Asset and three representative Montages (`warn`, `reassure`, `indicate`), create the semantic Niagara system, and record one interrupt test in PIE. Only after that should this be described as an Unreal-integrated prototype.

## Research boundaries

This is an independent prototype inspired by public research and interview discussion. It does not represent Tencent's internal architecture and uses no Tencent assets or non-public information. See [failure analysis](Reports/failure_analysis.md) and [limitations](Reports/limitations.md).

## Visual asset disclosure

`Aster_KeyArt_v2.png` was generated with the built-in OpenAI image generation tool from an original prompt in this project direction. Final prompt intent: premium anime-styled 3D adult field researcher, midnight-indigo / jade / amber palette, expressive eyes, production-feasible layered costume, no existing IP or logos.
