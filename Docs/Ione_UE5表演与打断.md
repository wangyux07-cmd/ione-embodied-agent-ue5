# Ione：UE5 对话表演与打断

## 当前交付边界

这是一套 **UE5 原生 C++ 2D 立绘表演实现**，而不是已完成的骨骼绑定角色。本机未检测到 Unreal Editor，因此尚未生成 `.uasset`、编译插件或通过 PIE 验收。`Content/Character/Performance2D` 里的 PNG 是透明原画，需导入编辑器后才能显示。普通姿态间以 0.18 秒交叠过渡；被打断时立即换成闭口立绘，保证话轮转移清楚。

## 四个镜头对视状态

| 状态 | 触发 | 表情 | 大动作 |
|---|---|---|---|
| Listening | 初始或打断恢复 | 直视玩家，微笑，闭口 | 触碰磁带耳机；轻微呼吸起伏 |
| Speaking | 开始说话、解释路线 | 直视玩家，张口 | 前倾、双手打开，外套随重心摆动 |
| Interrupted | 玩家抢话 | 直视玩家，略睁大眼，立刻闭口 | 从耳机撤手，另一手抬掌让出话轮；0.85 秒后转 Listening |
| Warning | `warn`、`refus`、`consent`、`boundary` 语义动作 | 直视玩家，眉头收紧 | 手掌前伸，阻止未经允许的行动 |

所有状态保持镜头目光接触。演员的语言生成和场景动作授权仍由原有 Agent / Gameplay 层负责；语义事件只选择经过作者制作的表演姿态。

## 在 UE 编辑器里接通

1. 安装与工程匹配的 UE5，生成工程文件并编译 `AsterPerformanceLabEditor`。目前仓库的 `EngineAssociation` 为空，打开时由本机选择引擎版本。
2. 启用 Editor Scripting Utilities 与 Python Editor Script Plugin，在 UE Python 控制台运行 `Tools/import_ione_2d_ue.py`。它将四张 PNG 导入 `/Game/Character/Performance2D/`。
3. 以 `AAsterNPCActor` 创建 `BP_IoneNPC`。在 Details 中把四张纹理分别填入 `ListeningPortrait`、`SpeakingPortrait`、`InterruptedPortrait`、`WarningPortrait`。检查贴图保留 alpha；如边缘发黑，改用适合 UI 的压缩设置并确认材质透明混合。
4. 把 `BP_IoneNPC` 放到关卡左侧的小台座上。`PortraitWidget` 是世界空间组件，每帧朝向玩家相机；可在 Blueprint 中调整其位置和大小。未配置 Skeletal Mesh 时，这个 Actor 仍可使用 2D 立绘层。
5. 调用 `Perform(Request)` 开始说话；在玩家开始新话轮的同一帧调用 `PlayerInterrupt(NewUtterance)`。`OnGestureStarted` 会按语义切换 Speaking / Warning；`PlayerInterrupt` 切到 Interrupted 并随后回 Listening。

## PIE 验收场景

- 站在关卡镜头里观察四个状态：瞳孔始终落在玩家方向，人物尺寸和台座协调。
- 说话过程中插入打断：语音开始淡出，尚未触发的语义动作计时器取消，角色当帧闭口并抬掌。
- 测试同一句话在打断前后：旧计划不能再次触发警告或手势；新话轮才能重新开始。
- 测试 `warn` / `consent`：拒绝动作与普通解释动作明显不同，且不会绕过世界状态授权。

连续的面部表情、口型同步和真实的局部肢体动画仍需拆分图层或建立 3D 骨骼。当前方案是四姿态切换加引擎内轻微起伏、10 厘米动作位移、约 5 度倾斜脉冲和中断状态，适合先验证语义与打断时序。位移与倾斜可在 `BP_IoneNPC` 的 Details 中调节。
