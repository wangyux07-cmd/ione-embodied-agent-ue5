# Aster Performance Lab

> **Current development direction (2026-10-28):** This repository contains **Ione: a world-grounded UE5 NPC Agent prototype**. The earlier Aster web stage and 30-scene performance planner remain as baselines. In UE 5.8.4, the player can type free text into a game-facing dialogue panel; a loopback Agent bridge checks game tools and returns dialogue plus one of four camera-facing 2D poses. See the [live UE evidence](Reports/ue5_ione_live/README.md), [scene design](Docs/Ione_场景视觉设计_v2.md), and [Version 3 plan](Docs/Version3_Agent项目执行与简历交付.md).

The Agent contract is in `Tools/ione_agent.py`; `Tools/ione_fast_agent.py` uses a **local Ollama model** for unfamiliar intent phrasing and direct policy routing for clear domain commands. The tool gate owns route/record lookup, consent-gated door actions and stale-turn rejection. `Tools/serve_ione_agent.py` exposes this pipeline to Unreal on `127.0.0.1`. A 30-case [Agent A/B/C offline evaluation](Reports/agent_eval_summary.md) has per-task traces and a [plan gap audit](Reports/agent_plan_gap_audit.md).

The [paper-feedback experiment and audited findings](Reports/paper_feedback_findings.md) compare blind, raw game-tool feedback and fact-anchored replies from local Gemma 3 4B. On a fresh eight-case verification set, target-fact compliance was 3/8 for raw feedback and 8/8 when the model was given a tool-authored fact sentence; a strict publisher rejected six unapproved embellishments. These are offline, author-written cases, with about 10 seconds P50 extra model time and no live Unreal dialogue link.

The follow-up [tiered Agent evaluation](Reports/fast_agent_findings.md) replaces the slow second factual generation with a small-model intent router, authoritative game tools and authored responses. On a new ten-case offline set, complete task success was 8/10 for the old two-pass flow and 10/10 for the tiered flow; wall-clock P50 was 17.21 s vs 0.62 s, with five tiered cases taking a zero-model rule path. Earlier development/diagnostic failures are retained in the report. The [live UE bridge check](Reports/ue5_ione_live/README.md) is a separate five-case integration smoke test, not a second performance benchmark.

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

On a UE 5.8.4 Windows machine with Python and Ollama installed, first start the local bridge:

```powershell
python .\Tools\serve_ione_agent.py
```

Open `AsterPerformanceLab.uproject` and Play `L_IoneStage`, or launch the project with `UnrealEditor.exe AsterPerformanceLab.uproject -game -d3d11`. Click the ornate input line, type a question, and press Enter. Try `东桥还能走吗？`, `红账本是谁的？`, and `打开档案室的门`. The first two query game tools; the door stays locked without its owner's consent. Clear commands use a zero-model path, while unfamiliar phrasing may invoke local Ollama and take longer on modest hardware. Keys `1`–`4` remain only as a test Blueprint pose preview. See [actual UE screenshots](Reports/ue5_ione_live/README.md).

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
| Ione game-facing scene | **Verified in UE 5.8.4 game mode**; hand-drawn backdrop, contact shadow and UMG dialogue panel | `Reports/ue5_ione_live/start.png` |
| Natural-language dialogue → game tool → UE pose | **Verified in UE game mode** for route and record requests; consent denial verified in bridge and game window | `Reports/ue5_ione_live/`, `Tools/serve_ione_agent.py` |
| Local LLM Agent and 30-case offline A/B/C | **Verified in Python harness**; structured model proposal and tool-gated world state | `Tools/eval_ione_abc.py`, `Reports/agent_eval_abc_30.json` |
| Rigged 3D character / continuous facial animation | **Not implemented** | 2D pose switching only |
| Human pairwise study | **Not run** | questionnaire design remains future work |

## Honest next milestone

Next: author and verify a continuous skeletal or layered 2D animation rig, implement Blueprint reactions for validated world-action events, and run a captured UE-window overlap/interruption scenario. The local bridge already passed a concurrent stale-turn check (`409` old turn, `200` new turn). The current live game demonstrates four authored 2D poses, movement accents and tool-grounded dialogue. It does not establish lip sync, a 3D rig, visible door animation, or a human preference result.

## Research boundaries

This is an independent prototype inspired by public research and interview discussion. It does not represent Tencent's internal architecture and uses no Tencent assets or non-public information. See [failure analysis](Reports/failure_analysis.md) and [limitations](Reports/limitations.md).

## Visual asset disclosure

`Aster_KeyArt_v2.png` was generated with the built-in OpenAI image generation tool from an original prompt in this project direction. Final prompt intent: premium anime-styled 3D adult field researcher, midnight-indigo / jade / amber palette, expressive eyes, production-feasible layered costume, no existing IP or logos.
