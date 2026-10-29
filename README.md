# Ione | Unreal Engine 5 NPC Agent

## Project

Ione is an interactive NPC set in a flooded wasteland archive. Players talk to Ione through an Unreal Engine 5 dialogue interface and follow a story about recovering a missing sister's recording.

The project combines a full-body illustrated character, expressive 2D poses, a hand-drawn-style environment and an event-driven Journal. A local Agent routes dialogue into game actions. ToolGate checks world state, quest prerequisites and recording permissions before committing actions. SQLite stores each session's progress, memory and relationship state for the next visit.

The Python tooling supports completion-only LoRA supervised fine-tuning, Direct Preference Optimization, adapter reload checks and controlled Base/SFT/DPO evaluation. The runtime includes an optional Hugging Face dialogue worker for selecting these model variants.

![Ione dialogue and quest objective in the Unreal Engine game window](Media/ione-gameplay.png)

## Run Locally

1. Install **Unreal Engine 5.8.4**, **Python 3.11**, [Ollama](https://ollama.com/) and **Visual Studio 2022 Build Tools** with the C++ desktop workload, Windows SDK and .NET Framework 4.8 SDK.

2. Clone the repository and create a Python environment:

   ```powershell
   git clone https://github.com/wangyux07-cmd/ione-embodied-agent-ue5.git
   cd ione-embodied-agent-ue5
   py -3.11 -m venv .venv
   ```

3. Start Ollama and download the routing models:

   ```powershell
   ollama pull qwen3:1.7b
   ollama pull gemma3:4b
   ```

4. Start the local Agent bridge from the repository root:

   ```powershell
   .\.venv\Scripts\python.exe .\Tools\serve_ione_agent.py
   ```

   The bridge runs at `http://127.0.0.1:8765`. The default dialogue path combines Ollama intent routing with authored tool-result replies.

5. Open `AsterPerformanceLab.uproject` with Unreal Engine 5.8.4, build the C++ modules when prompted, open `Content/Maps/L_IoneStage`, and press **Play**. Click the dialogue input, type a message, and press **Enter**. Press **J** to open the Journal and **Esc** to close it.

   Start with: `Please look up the public dispatch index for my sister's message.` Continue by checking the route, diagnosing the relay, collecting a replacement fuse and repairing it. Follow the Journal to collect public evidence and verify the recording's release card.

   Progress is stored in `Saved/ione_sessions.sqlite3`; the game keeps its session ID in `Saved/IoneClientSession.txt` and restores the session on launch.

Run the Python regression tests with:

```powershell
.\.venv\Scripts\python.exe -m pip install pytest pytest-subtests
.\.venv\Scripts\python.exe -m pytest -q
```

See [Tools/TRAINING.md](Tools/TRAINING.md) for LoRA SFT, DPO and the optional Base/SFT/DPO dialogue worker.
