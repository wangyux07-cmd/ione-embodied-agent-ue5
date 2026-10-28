# Ione：简历与 HR 沟通证据稿

更新：2026-10-28。先完成 [论文方法与实验报告](../Reports/paper_feedback_findings.md)，再写此稿。英文项目条目按现有 CV 的 Background → 两条 Responsibilities → Impact & Results 结构。指标均来自作者编写的离线题和本机 UE 测试，不能解释为玩家体验或生产环境效果。

## 可放入英文 CV 的项目条目

**Ione | Independent Game NPC Research Prototype | Oct 2026**

**Background:** Built an original wasteland archivist and an Unreal Engine 5.8 game-NPC prototype to investigate whether function feedback can keep free-form player dialogue, permissioned actions and character expression aligned with authoritative game state.

**Responsibilities**

- **Grounded Agent & Experimental Design:** Adapted Rao et al.'s function-return feedback into a local Gemma 3 4B JSON-schema agent. Built route/record/consent-gated tools, turn-version cancellation, tool-authored fact cards and a publication gate; evaluated blind, raw-feedback and anchored replies on reset world snapshots with saved traces and a fresh eight-case verification set.
- **Unreal Engine Virtual Human:** Art-directed Ione's chibi wasteland design—worn workwear, black-root blonde hair and a single cassette earpiece—and integrated four full-body 2D poses. Compiled an Unreal Engine 5.8 C++/Blueprint actor with a camera-facing world-space portrait, timed cross-fades and interrupt-pose hooks; verified all four in game mode.

**Impact & Results:** In audited offline response tests, target-fact compliance rose from **1/12 to 12/12** on the development set and **3/8 to 8/8** on a fresh verification set; a strict publisher rejected **6/8** unapproved model embellishments in that verification set. Separately, versioned cancellation reduced stale tool attempts from **8/8 to 0/8** in fixed interruption cases. Measured second-pass generation at **10.05 s P50** on the verification set; UE dialogue-to-performance wiring and human ratings remain future work.

### 中文说明：为什么这两条比旧稿更合适

第一条写清论文方法、实际 Agent 分层、权限/回合并发边界、事实锚点和可复现评测，而非笼统“做了 Agent Architecture”。第二条明确写 **Unreal Engine**、原创人物审美决策、2D 全身姿态、C++/Blueprint 的世界空间组件和表演时序；没有冒充 3D 骨骼、口型同步或已连通的实时 LLM→UE 动画。英文长度接近现有 CV 中 IBM / Agent 项目职责的两行半至三行密度；实际换行取决于模板字号和列宽。

## 给 HR 的英文沟通段落（可作为 Cover Letter 核心）

After our conversation about game NPC agents, I read Rao et al.'s [study of LLM-driven Minecraft NPCs](https://arxiv.org/html/2407.03460v1). One concrete idea caught my attention: return the success or failure of a game function to the NPC before it speaks to the player. I tested that mechanism with a small local model in Ione, my Unreal Engine 5.8 virtual-human prototype. Raw tool feedback rarely produced a clear, state-grounded answer in my fixed offline tasks, so I added tool-authored fact cards, versioned action checks and a conservative response gate. On a fresh eight-case verification set, target-fact compliance improved from 3/8 with raw feedback to 8/8 with fact anchoring; the gate rejected six unapproved embellishments. I also designed Ione's visual identity and verified four camera-facing states in the Unreal game renderer. The next step is to connect live dialogue to those states and evaluate the player experience directly.

## 面试时应主动讲清的证据边界

- **论文联系**：论文研究玩家与 NPC 的协作任务；借鉴的是函数回执返回模型、角色背景和受限游戏 API 这部分。事实锚点、发布门禁、回合版本取消是本项目扩展，不能归功于论文。
- **数字含义**：1/12→12/12 与 3/8→8/8 是目标事实是否在模型回答中说清的规则评分；模型已收到完整事实句，不能说“推理能力提高”。发布后 8/8 属于合同和兜底的结果。8/8→0/8 是离线版本门禁，不是 UE 内流式打断录像。
- **UE 证据**：[四姿态测试截图](../Reports/ue5_ione_stage/README.md)仅证明引擎编译、素材导入、相机正面显示和按键切换。无玩家对话 UI、原创新关卡完工视频或真人主观偏好数据。
- **实际代价**：第二次模型生成在新验证题上约 10 秒 P50；作为游戏实时交互仍需优化或流式设计。

## 证据入口

- [论文方法与逐轮结论](../Reports/paper_feedback_findings.md)、[原始逐题 JSON](../Reports/fact_anchor_eval.json)、[第一轮逐题 JSON](../Reports/paper_feedback_eval.json)。
- [旧 30 题 Agent 离线消融](../Reports/agent_eval_summary.md)、[Version 3 计划缺口审计](../Reports/agent_plan_gap_audit.md)。
- [UE 5.8 游戏窗口四姿态与局限](../Reports/ue5_ione_stage/README.md)、[表演实现说明](Ione_UE5表演与打断.md)。
