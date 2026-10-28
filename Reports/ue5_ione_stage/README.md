# Ione UE 5.8.4 test stage: local acceptance record

Date: 2026-10-28. Platform: Windows 11, Intel Iris Xe, 16 GB RAM. Engine: UE 5.8.4 launcher build. Rendering test: D3D11, Development, 1280 × 720.

## Verified

- `AsterPerformanceLabEditor Win64 Development` built successfully with the runtime plugin.
- Four PNG poses imported as UE `Texture2D` assets; `BP_IoneNPC` binds all four.
- `L_IoneStage` loads in game mode. Ione faces the player camera and stands on a round test disc.
- Test-only keys `1`–`4` select Listening, Speaking, Interrupted and Warning. All four were captured from the UE game renderer:

| Pose | Screenshot |
|---|---|
| Listening | [listening.png](listening.png) |
| Speaking | [speaking.png](speaking.png) |
| Interrupted | [interrupted.png](interrupted.png) |
| Warning | [warning.png](warning.png) |

## Reproduce

Open `AsterPerformanceLab.uproject` in UE 5.8.4, press Play in `L_IoneStage`, then press `1`–`4`. On a low-memory Intel Iris Xe machine, use D3D11 and low scalability settings. The map uses the stock Unreal default sky and floor as a **technical test backdrop**; it is not the intended wasteland art direction.

## Still pending

- A game-facing dialogue box and live dialogue/Agent event wiring.
- `PlayerInterrupt` end-to-end verification, including voice, semantic timers and Niagara cancellation.
- Authored skeletal gestures, a final wasteland set and performance measurements.

The four pose screenshots demonstrate renderer integration and visible switching, not full animation rigging or LLM behavior.
