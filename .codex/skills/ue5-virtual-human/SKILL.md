---
name: ue5-virtual-human
description: Build or revise Unreal Engine 5 virtual-human prototypes where dialogue semantics must drive authored animation, Niagara, materials, and interruptible C++/Blueprint gameplay. Use for UE NPC performance work; do not route ordinary web chatbots here.
---

# UE5 Virtual Human

Build engine-native vertical slices whose behavior is inspectable by designers.

## Decide the boundary first

- Keep generative dialogue/planning outside irreversible engine actions.
- Accept structured semantic anchors; validate them before animation or gameplay execution.
- Use Data Assets and Blueprint-exposed properties for authored choices.
- Use C++ Actor Components for reusable runtime behavior and Actors for scene composition.
- Mark uncompiled code, missing `.uasset` content, and simulated visuals explicitly.

## Runtime pattern

1. Parse a versioned request with dialogue, semantic anchors, confidence, state and forbidden actions.
2. Retrieve authored gestures by semantic function.
3. Filter with Gameplay Tags for character style, pose and world state.
4. Schedule montages, face events, audio and Niagara from one deterministic executor.
5. On interruption, cancel future timers first, then apply per-gesture policy: immediate, soft cancel, or finish phrase.
6. Keep gameplay actions behind Blueprint/C++ authority checks and an explicit commit boundary.

## Project conventions

- Prefix assets by type: `BP_`, `DA_`, `AM_`, `NS_`, `NM_`, `M_`, `MI_`.
- Expose tuning through `EditAnywhere`/`BlueprintReadWrite`; expose observations through multicast delegates.
- Prefer one parameterized Niagara system over many nearly identical systems.
- Use Material Custom HLSL only when it adds functionality or clarity; native nodes optimize constant expressions better.
- Never claim a generated `.uasset`, compile result, frame-time result, or platform compatibility without running it in that engine version.

## Verification

Read [references/acceptance.md](references/acceptance.md) before finalizing an Unreal delivery. For this repository's architecture and authoring details, use `Docs/architecture.md`, `Docs/material-and-niagara.md`, and `Docs/unreal-setup.md`.
