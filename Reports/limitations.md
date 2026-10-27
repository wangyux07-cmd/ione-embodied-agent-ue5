# Limitations

- No Unreal installation was available on the implementation machine; C++ and shader source require UE 5.8 compile/PIE verification.
- The repository contains no binary Animation Montage, Niagara System, Material or Blueprint assets.
- The web surrogate communicates state changes with 2D key art; it is not evidence of real-time facial or body animation.
- The 30 scenarios are synthetic and small. They test deterministic planner behavior, not player preference.
- Planner timing in `results.md` is Python runtime only. It is not model latency, game-thread cost or render cost.
- Interruption metrics model the intended cancellation boundary. Unreal Insights and frame captures are required to validate it.
- The character key art is original AI-assisted concept art. A production character still needs turnaround consistency, modeling, topology, rigging and licensing review for the chosen asset pipeline.
- No Tencent internal data, requirements, assets or implementation details were used.
