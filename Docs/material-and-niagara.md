# Material and Niagara implementation notes

## Material: semantic scan/dissolve

The plugin maps `/Plugin/AsterPerformance` to its shader directory. In a Material Custom Expression, use:

```hlsl
#include "/Plugin/AsterPerformance/AsterScanDissolve.ush"
return AsterScanDissolve(UV, Time, DissolveAmount, EdgeWidth, ScanDensity, ScanSpeed, Noise);
```

Inputs: `UV float2`, `Time float`, `DissolveAmount float`, `EdgeWidth float`, `ScanDensity float`, `ScanSpeed float`, `Noise float`. Output type is `CMOT Float4`:

- R: visibility mask, suitable for Opacity Mask;
- G: dissolve edge;
- B: scanline;
- A: combined emissive mask.

Expose `DissolveAmount`, edge colors and scan parameters in a Material Instance. Drive only scalar/vector parameters at runtime. Custom HLSL is used here for a compact derivative-aware mask; ordinary arithmetic should remain native Material nodes so Unreal can constant-fold it.

## Niagara: `NS_AsterSemanticAnchor`

Create one system with a reusable module script rather than one effect per semantic act.

User parameters:

| Name | Type | Use |
|---|---|---|
| `User.SemanticIntensity` | float | spawn and emissive strength |
| `User.InterruptStrength` | float | recovery collapse/rewind |
| `User.SemanticColor` | linear color | explain / warn / reassure palette |
| `User.AnchorPosition` | position | world-space semantic target |

Emitter outline:

1. GPU sprites, fixed bounds around the hand or target.
2. Spawn Burst Instantaneous on activation.
3. Scratch Pad `OrbitSemanticAnchor`: rotate particle offsets around `User.AnchorPosition`.
4. Scratch Pad `InterruptCollapse`: lerp position and size toward the anchor using `User.InterruptStrength`.
5. Scale Color from `User.SemanticColor * User.SemanticIntensity`.

Promote both Scratch Pad graphs to Niagara Module Script assets after the look is approved. The C++ actor keeps a single inactive component and updates user parameters, avoiding component churn during dialogue.
