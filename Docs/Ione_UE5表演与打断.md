# Ione：UE5 对话表演与打断

## 当前交付边界

这是一套 **UE5 原生 C++ 2D 立绘表演实现**，不是骨骼绑定角色。2026-10-28 已在 Windows 的 UE 5.8.4 中编译 `AsterPerformanceLabEditor`，导入四张纹理，创建 `BP_IoneNPC` 和 `L_IoneStage`，并在游戏运行窗口验证四个姿态的按键预览。普通姿态以 0.18 秒交叠过渡；打断姿态立即切换。按键预览仅验证视觉状态，不代表对话 Agent 已接入，也不代表 `PlayerInterrupt` 的语义链路已完成 PIE 验收。

## 四个镜头对视状态

| 状态 | 触发 | 表情 | 大动作 |
|---|---|---|---|
| Listening | 初始或打断恢复 | 直视玩家，微笑，闭口 | 触碰磁带耳机；轻微呼吸起伏 |
| Speaking | 开始说话、解释路线 | 直视玩家，张口 | 前倾、双手打开，外套随重心摆动 |
| Interrupted | 玩家抢话 | 直视玩家，略睁大眼，立刻闭口 | 从耳机撤手，另一手抬掌让出话轮；0.85 秒后转 Listening |
| Warning | `warn`、`refus`、`consent`、`boundary` 语义动作 | 直视玩家，眉头收紧 | 手掌前伸，阻止未经允许的行动 |

所有状态保持镜头目光接触。演员的语言生成和场景动作授权仍由原有 Agent / Gameplay 层负责；语义事件只选择经过作者制作的表演姿态。

## 在 UE 编辑器里接通

1. 用 UE 5.8.4 打开 `AsterPerformanceLab.uproject`；`EngineAssociation` 为空时需选择本机引擎。C++ 编译已在本机通过。
2. 仓库已包含四张导入的 `.uasset`；若需重建，依次运行 `Tools/import_ione_2d_ue.py`、`Tools/create_ione_blueprint_ue.py`、`Tools/create_ione_stage_ue.py`。后两者会保存 Blueprint 和测试关卡。
3. `BP_IoneNPC` 已绑定 `ListeningPortrait`、`SpeakingPortrait`、`InterruptedPortrait`、`WarningPortrait`，并在 `L_IoneStage` 中站在左侧圆盘上。`PortraitWidget` 是世界空间组件，运行时朝向玩家相机。
4. 测试关卡里的 Blueprint 启用了仅供开发验收的 `1`–`4` 键姿态预览。对话 UI 应改用 `Perform` / `PlayerInterrupt` 驱动，发布前关闭调试键。
5. 调用 `Perform(Request)` 开始说话；在玩家开始新话轮的同一帧调用 `PlayerInterrupt(NewUtterance)`。`OnGestureStarted` 会按语义切换 Speaking / Warning；`PlayerInterrupt` 切到 Interrupted 并随后回 Listening。

## PIE 验收场景

- 站在关卡镜头里观察四个状态：瞳孔始终落在玩家方向，人物尺寸和台座协调。
- 说话过程中插入打断：语音开始淡出，尚未触发的语义动作计时器取消，角色当帧闭口并抬掌。
- 测试同一句话在打断前后：旧计划不能再次触发警告或手势；新话轮才能重新开始。
- 测试 `warn` / `consent`：拒绝动作与普通解释动作明显不同，且不会绕过世界状态授权。

连续的面部表情、口型同步和真实的局部肢体动画仍需拆分图层或建立 3D 骨骼。当前方案是四姿态切换加引擎内轻微起伏、10 厘米动作位移、约 5 度倾斜脉冲和中断状态，适合先验证语义与打断时序。位移与倾斜可在 `BP_IoneNPC` 的 Details 中调节。
