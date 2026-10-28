# Aster Performance Lab

> **Current development direction (2026-10-28):** This repository is being expanded into **Ione: an interruptible, world-grounded UE5 NPC Agent**. The existing Aster web stage and 30-scene performance planner remain an earlier baseline. The selected Ione has four camera-facing 2D poses, a compiled UE 5.8.4 C++ actor, imported textures, a Blueprint and a runnable test map. The four poses were previewed in a UE game process; a dialogue-driven interruption flow is still pending. See [Ione UE5 performance and interruption](Docs/Ione_UE5表演与打断.md) and [Version 3 execution and CV evidence plan](Docs/Version3_Agent项目执行与简历交付.md).

The offline Agent contract is in `Tools/ione_agent.py`; `Tools/ione_llm.py` adds a **real local Ollama model** for structured proposals. The tool gate owns route/record lookup, consent-gated door actions and stale-turn rejection. A 30-case [Agent A/B/C offline evaluation](Reports/agent_eval_summary.md) has per-task traces and a [plan gap audit](Reports/agent_plan_gap_audit.md). The model-to-Unreal dialogue and animation loop is not yet connected. Run `python -m unittest discover -s Tests -v` to verify the contract.

The [paper-feedback experiment and audited findings](Reports/paper_feedback_findings.md) compare blind, raw game-tool feedback and fact-anchored replies from local Gemma 3 4B. On a fresh eight-case verification set, target-fact compliance was 3/8 for raw feedback and 8/8 when the model was given a tool-authored fact sentence; a strict publisher rejected six unapproved embellishments. These are offline, author-written cases, with about 10 seconds P50 extra model time and no live Unreal dialogue link.

The `Demo/` page is an older browser visualization with developer controls. The new camera-facing Ione art and performance code target Unreal Engine. The art is AI-assisted original concept exploration, imported as UE textures; it is not a 3D rig.

**An Unreal Engine 5-first research prototype for authorable, interruptible game-NPC performance.**

The prototype asks a narrow systems question: can semantic gesture retrieval, designer-authored constraints and a deterministic cancellation boundary improve NPC performance over flat LLM tags and rhythm-only motion—without training a large motion model?

![Aster concept art](Content/Character/Concept/Aster_KeyArt_v2.png)

## Why this is an Unreal project, not a chatbot demo

The generative layer is not allowed to play animation or change the world directly. It proposes dialogue and semantic anchors. An Unreal runtime plugin validates those anchors, retrieves authored montage definitions from a Data Asset, filters them with Gameplay Tags, schedules animation/VFX, and owns interruption recovery.

- `AAsterNPCActor` packages skeletal mesh, voice, Niagara, a camera-facing 2D portrait and the performance component.
- `UAsterSemanticPerformanceComponent` exposes A/B/C planning, Blueprint delegates and deterministic timer cancellation.
- `UAsterGestureLibrary` is the narrative/animation designer's control surface.
- `AsterScanDissolve.ush` is a derivative-aware Custom Node include for scan, edge and dissolve masks.
- Niagara is driven through one reusable component with semantic/intensity/interrupt user parameters.
- Gameplay actions stay behind Blueprint events and project-side authority checks.

See [architecture](Docs/architecture.md), [Material/Niagara notes](Docs/material-and-niagara.md), and the [Unreal setup checklist](Docs/unreal-setup.md).

## Run now

On a UE 5.8.4 Windows machine, open `AsterPerformanceLab.uproject`. It starts in `L_IoneStage`, a functional test map with the character on a small disc. In Play, keys `1`–`4` preview Listening, Speaking, Interrupted and Warning. These keys are enabled only by the test Blueprint and are not the intended player dialogue UI. See [UE test evidence](Reports/ue5_ione_stage/README.md).

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

Run the local-model Agent evaluation after installing Ollama and pulling `gemma3:4b`:

```powershell
ollama pull gemma3:4b
python .\Tools\eval_ione_abc.py
```

The committed per-task model cache lets the 30-case summary be recomputed without another model call. See [experiment method, metrics and limitations](Reports/agent_eval_summary.md).

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
Content/Character/Concept/        earlier concept exploration
Content/Character/Performance2D/  selected Ione art and four front-facing poses
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
| Unreal project compile / game run | **Verified on UE 5.8.4, Windows, D3D11** | `AsterPerformanceLabEditor` build succeeded; `L_IoneStage` ran in game mode |
| Ione 2D expression/action set | Four imported textures, Blueprint, and runtime key previews verified | `Content/Character/Performance2D/`, `Reports/ue5_ione_stage/` |
| Local LLM Agent and 30-case offline A/B/C | **Verified in Python harness**; C plans pose events, no UE dialogue link | `Tools/eval_ione_abc.py`, `Reports/agent_eval_abc_30.json` |
| Rigged 3D character / continuous facial animation | **Not implemented** | 2D pose switching only |
| Human pairwise study | **Not run** | questionnaire design remains future work |

## Honest next milestone

Next: replace the template test map with an authored wasteland scene and player-facing dialogue UI, connect the dialogue/Agent event stream to `Perform` and `PlayerInterrupt`, then capture an actual semantic interruption test. The current key-driven preview does not validate the full interruption transaction, montage timing, or LLM integration.

## Research boundaries

This is an independent prototype inspired by public research and interview discussion. It does not represent Tencent's internal architecture and uses no Tencent assets or non-public information. See [failure analysis](Reports/failure_analysis.md) and [limitations](Reports/limitations.md).

## Visual asset disclosure

`Aster_KeyArt_v2.png` was generated with the built-in OpenAI image generation tool from an original prompt in this project direction. Final prompt intent: premium anime-styled 3D adult field researcher, midnight-indigo / jade / amber palette, expressive eyes, production-feasible layered costume, no existing IP or logos.
