# Acceptance checks

## C++ and Blueprint

- Editor target compiles without warnings treated as errors.
- Blueprint subclass can tune the library, blend-out and strategy.
- Null assets and empty plans fail safely.
- Delegates expose plan, gesture, state and interrupt telemetry.

## Animation and interruption

- Every semantic montage uses an explicit slot and blend profile.
- Future timers are cancelled before the active montage transitions.
- Immediate, soft-cancel and finish-phrase policies are tested separately.
- Voice, face, body, Niagara and gameplay ownership converge on the same post-interrupt state.

## Materials and Niagara

- Shader include mapping resolves in a packaged Development build, not only in Editor.
- Material instance parameters cover art tuning without HLSL edits.
- Niagara fixed bounds are validated and user parameters update an existing component.
- GPU cost is measured with Unreal Insights/ProfileGPU before making performance claims.

## Evidence

- Capture engine version, platform, test map and build configuration.
- Keep a failure case where the planner selected a legal but semantically weak gesture.
- Label web/mock visuals as surrogates until the same flow runs in PIE.
