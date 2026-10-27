# Unreal setup and truthful validation boundary

The repository contains UE source code and authoring recipes, not generated binary `.uasset` files. This machine did not have Unreal Engine installed, so the project has not been compiled in-editor yet. Do not describe it as a completed Unreal integration until the checklist below passes on a UE 5.8 workstation.

## Open and compile

1. Install Unreal Engine 5.8 with a C++ toolchain and enable Niagara.
2. Right-click `AsterPerformanceLab.uproject` and generate project files.
3. Build the `AsterPerformanceLabEditor` target.
4. Open the project and allow the plugin module to load.

## Authoring checklist

1. Create `DA_AsterGestureLibrary` from `UAsterGestureLibrary`.
2. Add 16–24 gesture rows and assign Animation Montages.
3. Create `BP_AsterNPC` from `AAsterNPCActor`; assign mesh, AnimBP, library and semantic Niagara system.
4. Bind `OnDialogueStarted`, `OnPlayerTookTheFloor`, `OnGestureStarted` and `OnInterrupted` in Blueprint.
5. Route actual game actions through `OnGameActionRequested` with project-side authority checks.

## PIE acceptance test

- FlatTag, Rhythm and Semantic produce visibly different plans for the same request.
- A forbidden or state-blocked gesture never starts.
- Interrupting before a scheduled anchor prevents it from firing.
- Soft cancel uses the configured montage blend-out; immediate cancel stops within one frame plus blend.
- Voice fades and the executor ends in `Listening`.
- Niagara user parameters change without spawning a second system.
- Networked projects repeat the test with server authority; replication is intentionally not claimed by this prototype.
