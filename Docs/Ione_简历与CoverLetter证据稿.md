# Ione：简历与 HR 沟通证据稿

更新：2026-10-28。定位为 **Game NPC Agent / Unreal Engine 5 交互原型**。以下是可放进现有 CV 的英文项目条目；数字只指本机、作者编写的离线题集和集成冒烟检查，不能解释为线上用户效果。角色是四张 2D 全身姿态，不是 3D 骨骼动画。

## CV project entry

**Ione | Independent Unreal Engine 5 Game NPC Agent Prototype | Oct 2026**

**Background:** Built a playable wasteland NPC in Unreal Engine 5.8 to test whether authoritative game-state feedback and tiered intent routing can keep open-ended player requests, permissioned actions and visible character performance aligned.

**Responsibilities**

- **Agent architecture and evaluation:** Designed a local tiered Agent with deterministic routing for clear commands, Qwen3 1.7B structured intent proposals for unfamiliar phrasing, Gemma 3 fallback, consent-gated route/record/door tools, turn-version cancellation and tool-authored factual replies. Built reset-world A/B evaluations with per-turn traces and explicit failure audits.
- **Unreal Engine character and interaction:** Art-directed Ione's black-root blonde hair, worn workwear and cassette earpiece; integrated a hand-drawn archive scene, shadow and ornate UMG dialogue interface in Unreal Engine 5.8 C++/Blueprint. Connected free-text input to the loopback Agent and mapped verified tool outcomes to four full-body 2D poses, movement accents and Blueprint action events.

**Impact & Results:** On a fresh, author-written 10-case offline set, complete task success improved **8/10 → 10/10** and wall-clock P50 fell **17.21 s → 0.62 s** (5/10 optimized requests used a zero-model policy path). The UE game build passed, and a separate **5/5 live bridge smoke test** confirmed grounded route/record answers, consent denial and no-action negation; actual game-viewport screenshots show dialogue-driven pose changes. No human player study or continuous animation was measured.

### 中文解读与岗位匹配

第一条突出 LLM Agent 的结构化意图、工具权限、事实发布边界、低时延分层和可复现评估；第二条突出 Unreal Engine C++/UMG 的游戏内交互、虚拟人物审美与可见表演。两条职责各自有技术决策和可追问细节，避免把人物设计当成项目的全部。简历最终排版行数以你的 CV 模板为准，不能仅凭 Markdown 保证两行半。

## 论文如何成为真实动机

1. [Rao et al., *Collaborative Quest Completion with LLM-driven Non-Player Characters in Minecraft* (2024)](https://www.microsoft.com/en-us/research/publication/collaborative-quest-completion-with-llm-driven-non-player-characters-in-minecraft/) 研究玩家和 LLM NPC 在游戏任务中的协作，指出只靠语言的角色缺乏充分的游戏状态与视觉理解。本项目把“工具结果能否使角色准确解释行动后果”收窄成可测问题：先复现原始工具回执，再加入事实锚定和权限门禁。旧的二次生成虽然在新八题上把目标事实复述从 3/8 提到 8/8，但增加约 10 秒 P50，因此不能当作实时方案。
2. [Chen et al., *TCQA²: A Tiered Conversational Q&A Agent in Gaming* (REALM 2025)](https://aclanthology.org/2025.realm-1.20/) 将游戏问答做分层处理，目标包含准确性、低延迟和低风险。本项目借鉴的是**分层思想**：明确命令直达规则、陌生表达交给小模型、游戏事实和权限由工具决定、回复由验证结果生成。没有复现论文的知识图谱、多检索器、个性化记忆或用户研究，也不能与论文结果直接比较。

## 给腾讯 HR 的简短消息

您好，上次交流后，我对游戏中 LLM Agent 如何可靠地感知状态并驱动虚拟角色更感兴趣。我读了 Rao 等人的 Minecraft NPC 研究和 TCQA² 游戏分层 Agent 论文，随后独立做了一个 Unreal Engine 5.8 原型：玩家可以自然语言询问路线或档案，角色根据真实工具结果回答并切换表情动作。新 10 题离线对比中，任务成功 8/10→10/10、P50 17.21→0.62 秒；仓库有逐题记录和 UE 实机截图。想请您看看这是否贴近团队关心的方向。

## English cover-letter paragraph

After our discussion of game NPC agents, I read [Rao et al.'s Minecraft NPC study](https://www.microsoft.com/en-us/research/publication/collaborative-quest-completion-with-llm-driven-non-player-characters-in-minecraft/) on collaboration and the limits of language-only game-state awareness, followed by [Chen et al.'s tiered gaming Q&A agent](https://aclanthology.org/2025.realm-1.20/). I turned those ideas into Ione, an independent Unreal Engine 5.8 prototype where typed player requests pass through a local intent router and authoritative game tools before the character speaks or changes pose. A fact-anchored second generation improved factual restatement but proved too slow for this scene, so I replaced it with tiered routing and tool-authored replies. On a fresh ten-case offline set, complete task success changed from 8/10 to 10/10 and median wall time from 17.21 to 0.62 seconds; I also verified the route, record and consent paths in a playable UE scene. The repository includes raw traces and actual game screenshots, with the evaluation and 2D animation limits stated explicitly.

## 可核验边界和追问准备

- **指标口径**：[十题分层实验](../Reports/fast_agent_findings.md)是作者编写的本机离线题，包含五题零模型政策路径；不是模型推理能力提升，也不是线上玩家时延。原始逐题记录在 [`fast_agent_postfix_10.json`](../Reports/fast_agent_postfix_10.json)。
- **UE 证据**：[实机截图与五题服务集成](../Reports/ue5_ione_live/README.md)证明自然语言输入、角色对话、工具校验和四张 2D 姿态的连接。并发服务请求已验证旧回合 `409`、新回合 `200`；没有 3D 骨骼、口型、可见的开门场景动画、真人偏好评分，重叠请求尚未完成 UE 窗口实机捕获。
- **模型路径**：明确的中文领域命令走规则；陌生表达可调用本地 Ollama 小模型，但本机一次非规则英文请求耗时 11.26 秒，一次未覆盖中文改写耗时 33.91 秒并误判成闲聊。修复了这句的路由同义词，不能据此声称开放式中文都实时可靠。
- **论文归属**：游戏状态盲点与 NPC 协作问题来自 Rao 等人；分层问答启发来自 Chen 等人。事实锚、发布门禁、取消版本号、UE 场景和本机指标均是项目自己的实现与测试。

## 证据入口

- [十题优化报告](../Reports/fast_agent_findings.md)、[实机集成报告](../Reports/ue5_ione_live/README.md)、[原始五题 JSON](../Reports/ue5_ione_live/bridge_smoke.json)。
- [先前论文方法与失败审计](../Reports/paper_feedback_findings.md)、[旧 30 题 Agent 消融](../Reports/agent_eval_summary.md)。
- [求职主张证据账本](Ione_求职主张证据账本.json)。
