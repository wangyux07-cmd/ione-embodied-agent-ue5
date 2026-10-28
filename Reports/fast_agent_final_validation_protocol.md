# 快速分层 Agent：最终新验证题

2026-10-28，在 V01–V12 的任何模型调用前冻结。先前 20 题和 H01–H12 均已被用于修订输出合同、字段一致性与档案进入动作入口，因此均视为开发/诊断题。这批 V 题采用新的间接说法、否定与权限组合；本轮结束后不再据此调整同题分数。

| ID | 玩家新表述 | 权威世界与目标 |
| --- | --- | --- |
| V01 | shattered eastern viaduct / western walkway | 东坍塌、西开放；回答两者 |
| V02 | west wing corridor survived | 西开放；核验西侧 |
| V03 | map dead / east approach works | 地图服务故障；不得声称东侧安全 |
| V04 | unseal the records | 已授权；真正打开门 |
| V05 | go inside the archive | 未授权；门保持锁定 |
| V06 | don't let me into the archive | 已授权但否定命令；不得开门 |
| V07 | ledger after transfer / old tag Hazel | 当前所有者 Nia；不得重复 Hazel |
| V08 | archive's design | 闲聊；不得调用工具 |
| V09 | enter the record room / already open | 门已开；不得声称新打开 |
| V10 | east or west / both broken | 双路线坍塌；不得建议通行 |
| V11 | unlock only if owner approved | 权威授权为 false；拒绝开门 |
| V12 | not asking to open; check west route | 查西侧路线，不打开门 |

同题运行 B0（Gemma 3 4B 双阶段）和 B5（明确否定/受限房间动作走规则入口，其他输入由 Qwen3 1.7B 解析，再经工具与作者台词）。每题独立世界快照，各模式只跑一次。任务成功要求意图、工具、最终门状态、目标事实全部正确。记录模型调用路径/次数、异常、热模型墙钟 P50/P95、逐题原文。零模型的明确规则入口单列，不把它算模型推理。该任务集由作者编写、规模小，不能据此推断玩家体验或统计显著性。
