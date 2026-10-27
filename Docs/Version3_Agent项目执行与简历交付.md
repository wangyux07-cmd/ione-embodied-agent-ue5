# Version 3：Ione 具身 Agent 项目执行书

> 2026-10-27。此文件定义目标和验收，不把计划写成已实现功能。现有 Aster Performance Lab 保留为表演层探索与对照基线。

> 角色外观已在后续迭代改为“布丁头＋右耳圆形磁带装置”。下文的“谐振叉”是早期方案；当前表演资产与导入步骤以 [Ione UE5 表演与打断](Ione_UE5表演与打断.md) 为准。

## 目标与最终交付

研究问题：当游戏 NPC 可以访问世界状态、记忆和受约束工具时，怎样在玩家打断后取消过期计划，同时让台词、动作和游戏行为保持一致？

最终作品为一个 UE5 可玩垂直切片：原创角色 Ione 在淹水档案站帮助玩家调查安全路线。玩家可询问、追问和打断；Agent 读取实时世界状态，检索档案，提出工具调用，经游戏规则校验后执行，并将语义状态映射到角色表演。配套交付源码、可复现评测、失败分析、60–90 秒录屏、角色设计过程及简历证据表。

角色唯一强识别元素是右耳后的「谐振叉」：两臂从耳后延至颈侧，氧化铜与小块陶瓷构成；其张合与脉冲分别提示 listening、planning、tool execution 和 interruption。衣服、发饰和灯效让位于这一轮廓。角色的背景、伤痕和标志性动作必须支持这一装置的存在。

## 系统边界

```text
玩家输入 → 世界状态/记忆检索 → LLM Agent 结构化提议
          → schema 与权限/前置条件校验 → 游戏工具提交
          → 台词/语义锚点/表演计划 → UE5 确定性执行器
玩家打断 → 取消流式输出、TTS、未提交工具和未来动画事件 → 新回合
```

LLM 不直接改变关卡。工具须有参数 schema、前置条件、提交点、失败返回和审计记录。中断需区分未提交动作的取消与已提交动作的后续补救，不能宣称可回滚一切世界变化。

## Baseline 与评测

| 组别 | 能力 | 目的 |
|---|---|---|
| A Dialogue | 对话与情绪标签，无世界工具和持久记忆 | 检查空泛回答及世界幻觉 |
| B Tool Agent | 世界状态、检索与受约束工具，简化表演 | 单独衡量 Agent 对任务的贡献 |
| C Embodied Agent | B 加语义表演与统一中断管理 | 衡量具身表达和恢复的增益及成本 |

至少 30 条固定场景应覆盖路线、状态变化、工具失败、隐私边界、记忆冲突与不同中断时刻。A/B/C 使用相同输入与关卡快照。记录任务完成率、非法工具调用率、世界状态一致性、记忆引用准确率、过期动作率、中断恢复延迟、P50/P95 首响应时间、token/费用，以及盲法成对的角色可信度与表演语义评分。所有数字须由实际运行脚本或 PIE 日志生成，不能从原有表演层模拟数据移植。

## 开发里程碑与可见产物

1. **M0 现状基线**：运行现有网页代理演示与 Python 评测，保存真实输出；标注它仅验证表演规划，不验证 LLM/Agent 或 UE 运行。
2. **M1 Agent 核心**：实现版本化输入输出、世界快照、记忆检索、工具 gate、回合取消和确定性假模型；CLI 与单元测试可运行。网页演示增加 Agent 事件轨迹。
3. **M2 模型接入**：提供可配置模型适配器与离线回放，记录真实延迟和成本；密钥只走环境变量，仓库不含凭据。
4. **M3 角色与 UE**：角色设计定稿、可编辑 3D 源文件、UE 导入、Actor/Component、谐振叉材质/Niagara、至少三种 Montage；在 PIE 实测打断。
5. **M4 研究交付**：运行 30 条场景，产出三组 baseline、消融、失败分析和演示视频；README 的状态表随证据更新。

当前电脑若没有 UE 和 3D 工具，M3 保持待验证，不能在简历中写成完成。每个里程碑都在本机展示可运行页面或引擎画面，附截图/录屏路径与测试命令。

## Git 与公开发布

仓库建议名 `ione-embodied-agent-ue5`，公开前检查版权、第三方资产许可证、密钥、个人信息和大型二进制。使用主题明确的提交，例如 `docs: define embodied-agent baselines and deliverables`、`feat(agent): validate tool proposals against world state`、`test(evals): add interruption and stale-action cases`、`feat(unreal): bind resonance-fork state to Niagara`。每个提交描述实际改动；本地测试通过后推送。README 区分已实现、模拟、待 UE 验证。

## CV 项目条目模板（最终按实测替换）

**Background** — Built an independent UE5 game NPC research prototype inspired by an interview discussion on dialogue, performance models and AI agents. Studied how a character can act on world state and recover from player interruptions.

**Responsibilities**

- Designed a grounded LLM agent with structured tool calls, memory retrieval, world-state validation and cancellation boundaries; implemented reproducible A/B/C baselines.
- Built the UE5 character runtime and authored a distinctive visual state system around Ione's resonance fork, connecting dialogue semantics to animation, Niagara and gameplay events.

**Impact & Results** — To be filled only from measured evidence: `N` scenarios, task completion `A→B→C`, invalid action rate, stale-action rate, P95 latency, user preference and a linked demo/repository. If UE PIE or human study is not complete, remove those claims rather than use placeholders in a submitted CV.

## 当前状态

现有仓库拥有表演层 A/B/C、30 条固定情境、Python 评测器、网页代理演示及未编译的 UE C++ 插件。Ione 资产、LLM Agent 工具链、真实模型评测、UE PIE 录屏与 CV 实测结果均尚未完成。
