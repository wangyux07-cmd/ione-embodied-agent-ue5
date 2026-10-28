# Ione game scene: UE 5.8.4 acceptance

Date: 2026-10-28. Windows 11, Intel Iris Xe, D3D11, 1280×720 game viewport.

- `AsterPerformanceLabEditor Win64 Development` compiled successfully after the UMG scene was added.
- The project ran in UE game mode. [Listening / scene](scene.png) shows the new hand-drawn archive backdrop, full-body character on the left, independent contact shadow, and right-side dialogue panel. The former checkerboard pedestal was removed from `L_IoneStage`.
- Key `4` selected [Warning](warning.png) in the same game window. This verifies that the existing actor state changes the visible game-screen portrait. Keys `1`–`4` are test-only.
- The visible dialogue is authored copy. The `ENTER` prompt is a layout placeholder for the next natural-language integration stage; this screenshot does not demonstrate a working LLM conversation.

The scene uses 2D texture poses, UMG layout, a subtle bob and transition displacement. It is not a rigged 3D character or continuous facial animation.
