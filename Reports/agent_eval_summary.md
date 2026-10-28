# Ione Agent 离线评测（2026-10-28）

## 测量范围

主实验是 Windows 本机的 **30 道固定英文任务、每题一次模型生成**，覆盖路线与状态变化、地图工具故障、档案门授权、档案所有权/旧记忆冲突、否定指令和生成期间打断。每题创建独立 `World` 和 Agent 会话；模型提出结构化意图、目标、台词、表情，`ToolGate` 再检查目标、授权、轮次并决定是否执行。三组 A/B/C **复用同一题模型输出**，仅改变执行策略。逐题原始响应、工具事件和最终世界状态见 [30 题 JSON](agent_eval_abc_30.json)。

这不是 UE 端到端对话、真实用户研究或生产环境测量。评分只覆盖意图/目标/工具结果/最终状态与是否产出姿态事件，**不评价台词自然度、表情审美或动画质量**。30 题由项目作者编写，不构成独立盲测；通过率只适用于这套受控题集。

## 30 题同输出消融

| 组别 | 能力 | 完整通过 | 过期工具调用（8 个打断题） | 世界状态正确 | 未授权开门 | 姿态事件 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| A | 仅展示 LLM 对话，不执行工具 | 12/30 | 0/8 | 27/30 | 0 | 0/30 |
| B | 结构化 LLM + 世界/授权工具门禁，无生成期打断版本检查 | 22/30 | 8/8 | 28/30 | 0 | 0/30 |
| C | B + 生成期版本检查 + 确定性四姿态事件 | 30/30 | 0/8 | 30/30 | 0 | 30/30 |

任务成功要求意图、目标、工具结果和最终状态均满足预先写定的断言。A 在 8 个打断题上因始终不执行工具而通过，但它不能完成路线、开门、记忆查询目标。B 的 8 次过期调用包含 6 次只读/被门禁拒绝的调用，以及 **2 次在用户打断后打开档案门**（`i01`、`i02`）。C 的版本检查挡住迟到模型输出；C 的姿态数只表示离线事件规划，不代表 UE 动画播放成功。

模型在这 30 道自编题上意图/目标识别为 30/30；B/C 对两道旧记忆冲突题和两道地图故障题均 2/2 正确处理。Ollama `gemma3:4b` 本机完整生成耗时 P50 **9.41 s**、最近秩 P95 **15.50 s**；30 次调用合计输入 **7,718 tokens**、输出 **1,189 tokens**，本地 API 费用为 0。它不是首 token 延迟，也不能推断线上成本或实时体验。

**复现条件：**`ione-agent-abc-30-v1`，题集 SHA-256 `2fdccd8f82305645726f7209bed335c8ad1198aad2ff570e9de6d49d23e62ac7`，Ollama 0.40.12，`gemma3:4b`，JSON Schema，temperature 0。模型输出在 [缓存](agent_eval_abc_30_cache.json) 中逐题保存；结果可不调用模型直接从缓存复算。单次 trial，未测 `pass^k`。

```powershell
ollama pull gemma3:4b
python Tools/eval_ione_abc.py
```

## 先期 12 题模型容量对照

下表是使用当前输出合同（含 `lookup_record`）重跑的 12 题模型容量对照。它与 30 题主实验使用同一结构化合同，但题集与运行次数不同，不能将分子分母相加。

| 方法 | 完整通过 | 未授权开门 | 模型响应中位耗时 |
| --- | ---: | ---: | ---: |
| 关键词规则 `IoneHarness` | 7/12 | 0 | 不适用 |
| Ollama `granite4:350m` + `ToolGate` | 3/12 | 0 | 1.53 s |
| Ollama `gemma3:4b` + `ToolGate` | 12/12 | 0 | 9.58 s |

350M 模型主要把档案门请求识别为正确意图却给出 `none` 目标，因而被门禁拒绝；它还漏掉/误判西侧通道和普通对话。4B 模型在该固定题集上正确识别了全部意图和目标，未授权的两次开门请求都被门禁挡下。两者都没有证明开放式游戏对话质量。耗时含本机模型加载/生成，受缓存和机器负载影响，不能直接当线上延迟。

## 12 题复现

```powershell
ollama pull granite4:350m
ollama pull gemma3:4b
python Tools/eval_ione_llm.py --baseline-only --output Reports/agent_eval_keyword_baseline.json
python Tools/eval_ione_llm.py --model granite4:350m --output Reports/agent_eval_granite4_350m.json
python Tools/eval_ione_llm.py --model gemma3:4b --output Reports/agent_eval_gemma3_4b.json
python -m unittest discover -s Tests -v
```

运行器使用 Ollama 本机 `/api/generate`，JSON Schema 约束输出，temperature 0；评分不采用模型自评。原始记录分别见 [关键词](agent_eval_keyword_baseline.json)、[350M](agent_eval_granite4_350m.json)、[4B](agent_eval_gemma3_4b.json)。

## 与原计划相比仍需真实场景验证

- 目前打断在离线 harness 中模拟；UE 中的语音、动画、Niagara 同步取消以及真实恢复延迟尚未测量。
- `num_predict` 固定且仅 30 次单轮模型调用；多轮上下文、坏 JSON、超时、模型热/冷启动和重复试验仍需追加。
- 没有真人盲法成对评价，不能声称角色可信度或表演自然度提升。
