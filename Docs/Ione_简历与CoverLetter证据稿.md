# Ione 项目：明天简历与 Cover Letter 可用稿

更新：2026-10-28。只写已经有本机运行证据的工作；招聘版本可按岗位描述再压缩。

## 项目定位

**Ione — World-grounded Embodied Agent in Unreal Engine 5.8**
独立原型：末世档案馆 NPC。玩家用自然语言询问路线或请求开门；本地 LLM 生成结构化意图与表演建议，确定性工具门禁核对世界状态、所有者授权和打断轮次。UE 5.8 已编译运行四姿态正面角色与测试舞台；完整的实时 LLM→UE 对话链路仍待接入。

## 可直接放入英文 CV 的项目条目

**Ione | Independent Research Prototype | UE5 Game NPC Agent | Oct 2026**

**Background:** Built a world-grounded, interruptible NPC prototype to test how LLM dialogue proposals can drive game actions and character expression under explicit state and permission rules, informed by research on LLM-driven game NPCs.

**Responsibilities**

- **Agent Architecture:** Integrated local Gemma 3 4B with JSON-schema action proposals, world-state tools, owner-consent checks and versioned turn cancellation; kept model text separate from the Python harness's authoritative state commit boundary.
- **Unreal & Evaluation:** Compiled a UE 5.8 C++/Blueprint character prototype with four in-game portrait poses; designed a resettable 30-scenario A/B/C offline ablation with per-task model output, tool traces and final-state assertions.

**Impact & Results:** On 30 fixed offline scenarios, task completion rose from **12/30 (dialogue only)** to **22/30 (tool-gated)** and **30/30 (tool-gated + cancellation/pose events)**; stale tool calls on eight interrupted cases fell from **8/8 to 0/8**, with **zero unauthorized door openings**. Local Gemma 3 4B full-generation latency was **9.41 s P50 / 15.50 s P95**. Four character poses were verified in UE game mode; the dialogue-to-UE animation loop remains future work.

The A/B/C results are from an author-written offline benchmark, one trial per task. C emits pose events but does not yet play them from live dialogue in Unreal. Keep this qualifier in any interview explanation even if the CV line is shortened.

## Cover Letter 英文段落草稿

Following our discussion about game NPCs, I read [Rao et al.'s ACL 2024 study of LLM-driven Minecraft NPCs](https://arxiv.org/html/2407.03460v1). Their documented failures around missing live game state and unsuccessful tool actions gave me a concrete question to examine in Ione, an independent agent prototype alongside a UE 5.8 character stage. A local LLM proposes structured dialogue and actions, while a deterministic gate checks world state, owner consent and turn validity before committing changes. In a fixed 30-scenario offline comparison, task completion was 12/30 for dialogue only, 22/30 with tool access and 30/30 after adding cancellation; stale tool calls on eight interrupted cases fell from eight to zero. I also compiled the Unreal C++/Blueprint prototype and verified four camera-facing poses in game mode. The live dialogue-to-performance loop is the next integration step.

## 给面试官看的证据

- [实验方法与结果](../Reports/agent_eval_summary.md)，以及同目录的 12 题、30 题逐题 JSON。
- [原计划与现状逐项对照](../Reports/agent_plan_gap_audit.md)。
- [UE 运行截图及限制](../Reports/ue5_ione_stage/README.md)：四姿态、测试场景、引擎版本。
- `Tools/ione_llm.py`、`Tools/ione_agent.py`、`Tools/eval_ione_llm.py`、`Tests/test_ione_llm.py`。

## 还不能写的表述

- “实现了完整的 UE5 实时 LLM 虚拟人对话”——UI、通信和动作调度尚未端到端接通。
- “12/12 证明用户体验/生产可靠性”——没有开放式用户测试或独立盲测。
- “达到真实 3D 角色面部动画效果”——当前是 2D 姿态图切换。
