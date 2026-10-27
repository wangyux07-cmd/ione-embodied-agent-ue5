# 腾讯虚拟人研究项目 Version 2：方案设计与原创角色生产调研

> 日期：2026-10-27  
> 状态：V2 方向文件，等待设计确认后再进入正式制作  
> 项目性质：基于面试讨论与公开资料形成的独立研究原型，不代表腾讯内部方案  

## 0. 这一次最终要交付什么

V2 不再把网页仪表盘或一张 AI 角色图当作项目主体。最终 output 是一个以 Unreal Engine 5 为运行环境、以原创二次元 3D 角色为视觉中心的可玩垂直切片，并附带可复现的研究材料。

最终交付分为五组：

1. **角色身份包**
   - 一页 Character Bible；
   - 背景故事、欲望、缺陷、关系和说话方式；
   - 20 个黑白轮廓缩略图、3 套收敛方案、1 套最终设计；
   - 正面、侧面、背面、3/4 视图；
   - 8 个表情、6 个标志性姿态、服装结构和材质说明；
   - 明确记录被淘汰的方案及原因。

2. **游戏可用角色资产**
   - 可编辑源文件（优先 `.blend`，如使用 Maya/ZBrush 则保留相应源文件）；
   - game-ready Skeletal Mesh、UV、PBR/Toon 混合材质、LOD；
   - 面部表情形态、身体骨骼、头发与少量服装动态；
   - FBX 作为稳定的 Unreal 交换格式；VRM 仅作为可选头像交换格式。

3. **UE5 可玩场景**
   - 一个 3–5 分钟的叙事探索场景，而不是 Dashboard；
   - 玩家可与角色对话、观察她指向世界物体、安慰/拒绝/警告，并在说话和动作中途打断她；
   - C++ Actor/Component 封装，Blueprint 暴露参数与事件；
   - Anim Montage、Control Rig/IK Retargeter、Niagara、Material Custom HLSL 各有一个与角色叙事相关的使用点；
   - Debug UI 只在开发模式出现，不抢角色和游戏空间的视觉主导权。

4. **研究与评测包**
   - Flat Tag、Rhythm、Semantic 三种表演策略；
   - 30 个固定场景、自动指标、人工成对比较表；
   - 至少 5 个真实失败案例与消融说明；
   - Unreal Insights/PIE 中断记录；没有实测的数据不得写成完成。

5. **展示材料**
   - 60–90 秒演示视频；
   - README、架构图、制作过程与限制；
   - 一页项目总结，清楚区分原创设计、AI 辅助、现成工具和未完成项。

现有网页原型与两张 AI 角色图只保留为探索记录，不进入 V2 主展示，也不作为角色质量证据。

---

## 1. V1 为什么失败

### 1.1 角色不是“被设计出来的”，而是“被提示词堆出来的”

上一版同时叠加了未来研究员、宝石、透明布、金属饰品、漂浮界面、月夜宫殿、高跟靴等元素。每个局部都能吸引眼球，但它们没有共同回答“她是谁、为何这样穿、玩家为何会记住她”。这类画面容易出现 AI 生成感：信息密度高、因果关系弱、细节互相竞争。

Valve 的角色美术指南强调，角色需要先在轮廓、明度结构和游戏视角中可读，并用“安静区域”平衡细节；高饱和和高对比应集中在少数焦点，而不是平均铺满全身。[Valve《Dota 2 Character Art Guide》](https://help.steampowered.com/en/faqs/view/0688-7692-4D5A-1935)

### 1.2 漂亮不等于有角色性

通用的大眼、精致脸、长发和华丽服装可以生产“好看的人”，却不能自动产生“只属于这个游戏的人”。专业角色流程通常从 brief、世界观、早期探索和删案开始，再进入正交图、3D 和宣传图；Envar Studio 的公开课程也把 worldbuilding、characterization、参考搜集、草图探索和逐步锁定设计放在建模之前。[ArtStation Learning：Building an Original Character](https://magazine.artstation.com/2023/04/building-original-character/)

### 1.3 技术展示抢走了游戏感

V1 把语义、约束和时间线全摆在界面上，结果更像 AI 控制台。V2 会把研究数据放在可切换的 Debug 模式；正常体验只呈现游戏世界、角色、台词和玩家打断。技术不是消失，而是通过角色真的看向、指向、停下、恢复和改变行动来被看见。

---

## 2. 外部调研：专业与个人开发者怎样制作虚拟角色

### 2.1 调研方法

检索日期为 2026-10-27。优先使用 Epic、Valve、Pixiv/VRoid、VRM Consortium、Blender Foundation、Adobe、Reallusion、Marvelous Designer 的官方资料；用 ArtStation Learning/Gnomon 的资深角色艺术家流程补充生产实践；用 VRM4U GitHub 仓库和 issue 检查 UE5 实际接入风险。

纳入标准：能说明具体流程、输入输出、版本要求或已知限制。排除标准：只有成图没有过程、只给提示词、复制已有 IP、无法确认工具版本、把厂商宣传中的“可用”直接等同于“高质量”。

这不是系统综述。官方产品文档最适合确认能力与接口，但不能独立证明艺术质量；课程资料代表专业实践案例，不代表唯一正确流程。

### 2.2 行业公开流程的共同骨架

公开资料呈现出高度一致的顺序：

```text
故事/Brief
  → 参考板与反参考板
  → 黑白轮廓和比例探索
  → 服装功能、色彩与材质语言
  → 正侧背/表情/姿态设计
  → 3D Blockout 与 paint-over
  → 高模/低模/重拓扑/UV
  → 烘焙与材质
  → 骨骼、蒙皮、表情、头发和衣物
  → Unreal 导入、重定向、材质与性能验证
  → 游戏镜头下回看并迭代
```

Epic 把角色资产的 design、modeling、surfacing、rigging 和 animation 明确放在进入引擎之前，并在 UE 中继续完成 Skeleton、Animation Blueprint 和角色逻辑设置。[Epic：Setting Up a Character](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-a-character-in-unreal-engine)

资深角色艺术家 Kat Unsworth 展示的完整 stylized game-character 流程为：概念和 paint-over、Maya blockout/低模/重拓扑/UV、ZBrush 高模、Marmoset 烘焙、Substance Painter 材质，最后进入 UE5。[Gnomon/ArtStation：Modeling a Stylized Character for Games](https://katunsworth.artstation.com/projects/29lzOg)

Adobe 对 baking 的定义是把网格信息转移到纹理，供 shader、curvature、normal、Smart Material/Mask 使用；这也是“高模细节进入实时低模”的关键环节，而不是让生成图直接变成游戏角色。[Adobe Substance 3D Painter：Baking](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/baking/baking)

### 2.3 独特性来自约束，不来自更多装饰

可迁移到本项目的设计原则如下：

- **轮廓先行**：关闭纹理后仍能分辨角色方向、姿态和身份。
- **有限的形状语言**：为角色选择一组主形和一组对比形，而不是每件衣服都使用不同语法。
- **有限色板**：主色、辅色、极小面积强调色；先用灰度检查焦点。
- **detail/rest 对比**：脸、手或核心道具承担细节，躯干和腿保留安静区域。
- **功能解释服装**：每一个袋、扣、开衩、材质都应与职业、环境或动作有关。
- **动作也是外观**：站姿、注视、说话前的准备动作和被打断时的反应，是角色识别的一部分。

这些原则直接来自 Valve 对 silhouette、value、color、areas of rest、pose 与 gameplay readability 的总结，而不是“少即是多”的泛泛审美口号。[Valve《Dota 2 Character Art Guide》](https://help.steampowered.com/en/faqs/view/0688-7692-4D5A-1935)

### 2.4 AI 在生产中的合理位置

AI 可以用于：参考方向发散、情绪板候选、快速材质草案、色彩组合和失败可能性枚举。它不应直接承担最终角色设定、严格正交图、拓扑、服装结构、面部 rig 或跨视角一致性。

原因不是排斥 AI，而是最终资产需要连续决策：一个正面看起来漂亮的外套，必须在侧面和背面保持结构；头发要能 rig；眼睛要能变形；衣服要在动作和 LOD 下工作。Epic 的 stylized MetaHuman 教程也假设输入角色已经具备 game-ready topology 和 baked textures，并要求理解 joints、skin weights、blendshapes、edge loops 和 PBR；这说明 MetaHuman 是接入和绑定管线，不是概念设计替代品。[Epic：MetaHuman Stylized Character Tutorial](https://dev.epicgames.com/documentation/metahuman/metahuman-stylized-character-tutorial?lang=en-US)

---

## 3. 平台路线比较

| 路线 | 速度 | 独特性上限 | UE5 接入 | 主要问题 | 本项目判断 |
|---|---:|---:|---:|---|---|
| 直接 AI 图 → Image-to-3D | 很快 | 低到中 | 不稳定 | 多视图、拓扑、服装结构和脸部 rig 不可靠 | 只做 blockout 参考，不做最终英雄角色 |
| VRoid → VRM | 很快 | 中 | 中 | 原生容易有“VRoid 模板感”；UE 插件版本风险 | 适合 48 小时原型，不适合不改造就交付 |
| VRoid → Blender 深度改造 → FBX/UE | 中 | 中到高 | 高 | 需要建模、贴图和 rig 清理 | **推荐 MVP 路线** |
| Blender/ZBrush/Maya 全自定义 → FBX/UE | 慢 | 最高 | 高 | 技能和工时要求最大 | **推荐作品集最终路线** |
| Custom Mesh → MetaHuman | 中到慢 | 半写实较高 | 很高 | 极端二次元比例求解不稳定，拓扑会被统一 | 不作为纯二次元默认路线 |
| Character Creator 5 → UE | 快 | 中到高 | 很高 | 商业付费，基础资产仍需强改造避免模板化 | 有预算、重速度时的备选 |

### 3.1 VRoid：最快的二次元起点，但必须“逃离默认脸”

VRoid Studio 免费，允许调整脸、身体、发型、服装和纹理，并可导出 VRM；它尤其适合没有完整角色建模经验的个人开发者快速得到带骨骼和表情的二次元基础。[VRoid Studio 官方页](https://vroid.com/en/studio) [VRoid VRM 导出说明](https://vroid.pixiv.help/hc/en-us/articles/360014383713-How-to-create-a-VRM-file)

VRM 是基于 glTF 的跨平台 humanoid avatar 格式；其优势是头像交换，不等同于 Unreal 原生生产格式。[VRM 官方说明](https://vrm.dev/en/vrm/vrm_about/)

VRM4U 可为 Unreal 导入骨骼、Morph Target、BlendShapeGroup、Spring Bone、碰撞和 MToon 材质，但它是社区维护插件。仓库说明由个人维护，2026 年 UE 5.8 还出现过二进制版本与正式版 ABI 不匹配、需使用更新源码或重新编译的问题。因此它适合技术验证，不应成为唯一不可替代的交付路径。[VRM4U GitHub](https://github.com/ruyo/VRM4U) [UE 5.8 compatibility issue](https://github.com/ruyo/VRM4U/issues/581)

**V2 使用方式**：在 VRoid 内只确定基础身材、面部拓扑、头发草型和初始表情；进入 Blender 后重做脸部比例、眼睛/眉毛纹理、发束轮廓、外套和鞋，删除模板饰品，统一材质与边线。最终导出 FBX 进入 UE；VRM 另存为可选兼容资产。

### 3.2 MetaHuman：强绑定和面部管线，但不应强迫它变成纯二次元

UE 5.8 的 From Custom Mesh 可以接受任意拓扑并输出标准 MetaHuman 拓扑和 rig；官方 stylized 教程还覆盖 Maya round-trip、DNA、面部/身体 rig 修改和自定义材质。[Epic：From Custom Mesh](https://dev.epicgames.com/documentation/metahuman/metahuman-creator-from-custom-mesh-tool-in-unreal-engine) [Epic：Stylized Character Tutorial](https://dev.epicgames.com/documentation/metahuman/metahuman-stylized-character-tutorial?lang=en-US)

但 Epic 同时明确提示：工具最适合接近真实人类形态的 A-pose；大头、小身体、尖锐卡通形体等极端比例可能出现体积损失或肩胯变形。[Epic：From Custom Mesh，Workflow Tips](https://dev.epicgames.com/documentation/metahuman/metahuman-creator-from-custom-mesh-tool-in-unreal-engine)

**V2 判断**：如果最终美术收敛为“高质量日式半写实”，MetaHuman 值得做技术支线；如果坚持 80% 二次元比例，保留自定义骨骼和面部 blendshape 更安全。

### 3.3 Character Creator：减少技术劳动，但不会自动产生审美

Character Creator 5 提供 stylized/realistic 基础、FBX/OBJ/USD/Alembic、PBR/UDIM，并有 UE Auto Setup、Control Rig 和 Live Link；官方 Auto Setup 会处理 UE 骨骼、shader、hair、eye、skin 和部分物理设置。[Character Creator 5](https://www.reallusion.com/character-creator/default.html) [CC UE Auto Setup](https://www.reallusion.com/character-creator/unreal-engine-auto-setup.html)

它适合需要快速得到稳定脸部、身体、LOD 和动画兼容的个人项目，但仍需在 morph、服装、发型、材质和动作上做强定制。否则只是把“AI 模板感”换成“角色生成器模板感”。商业成本与附加插件也需要单独预算。

### 3.4 Blender + 专项工具：最适合把个人审美留在资产里

Blender 免费开源，创作者拥有自己制作的作品；Rigify 提供基于 meta-rig 的自动 rig 起点。[Blender 官方许可](https://www.blender.org/about/license/) [Rigify Manual](https://docs.blender.org/manual/en/5.4/addons/rigging/rigify/index.html)

本项目可把 Blender 作为主 DCC：建模、重拓扑、UV、简单雕刻、shape keys、发型和 Rigify/自定义骨骼都在一个文件中完成；如果追求更高雕刻质量，再加入 ZBrush；材质用 Substance Painter 或 Blender 自身完成。Substance 的价值主要在高低模烘焙、曲率/AO/法线和可控材质层，而不是给服装自动贴一个“科幻材质”。[Adobe Substance 3D Painter：Baking](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/baking/baking)

### 3.5 衣物和头发：只做一处值得记住的动态

UE 5.8 的 Chaos Cloth Dataflow 已是 production-ready，并支持与 CLO/Marvelous Designer 的非破坏 round-trip；但 Outfit/Parametric Clothing 仍有复杂度和体型变形风险。[Epic：UE 5.8 Release Notes—Chaos Cloth](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes) [Epic：Parametric Clothing](https://dev.epicgames.com/documentation/metahuman/getting-started-for-creating-parametric-clothing-in-metahuman?lang=en-US)

V2 不做大面积披风、透明拖尾和多层飘带。只保留一块短后襟或窄带作为二级动态，头发主体由骨骼/受控形变保持轮廓。Epic 的 Hair Art Directability 也强调可以在 simulation 与 art-directed animation 之间混合，避免物理把设计好的发型冲散。[Epic：Hair Art Directability](https://dev.epicgames.com/documentation/metahuman/hair-art-directability)

---

## 4. V2 推荐的实际制作路线

### 路线结论

**角色设计：人工主导的 2D 角色圣经**  
**快速基础：VRoid 仅作为二次元 humanoid 基底**  
**独特性重建：Blender 中重做脸、眼睛、头发轮廓、衣服和材质**  
**稳定交换：FBX 2020.2 兼容导出到 UE5**  
**动画：UE5 IK Rig/Retargeter + 少量定制 Montage + 面部 Shape Keys**  
**可选支线：VRM4U 验证、MetaHuman 半写实对照，不进入关键路径**

Epic 的 FBX pipeline 支持 Skeletal Mesh、animation、Morph Target、多 UV、LOD 和 vertex color，并明确 UE FBX importer 使用 FBX 2020.2；IK Rig 则可在骨骼数量、命名和朝向不同的角色间转移动画。[Epic：FBX Skeletal Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine) [Epic：IK Rig Retargeting](https://dev.epicgames.com/documentation/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine?lang=en-US)

### 为什么这样选

- 比纯 VRoid 多一层人工造型，能摆脱默认脸、默认眼睛、默认发束和默认服装剪裁；
- 比全手工从零更快，个人开发者能把时间集中在真正影响识别度的 20%；
- 比 MetaHuman 更适合明显二次元的头身和眼睛；
- 比只押 VRM4U 更稳，因为 FBX 是 UE 官方路径；
- 最终角色仍然能使用 UE 的 IK Retargeter、Animation Blueprint、Montage、Control Rig 和 Niagara。

### 4.1 个人开发者的三档工具组合

| 预算/目标 | 工具组合 | 适合什么 | 不应该期待什么 |
|---|---|---|---|
| 低预算验证 | VRoid + Blender + Krita + UE5 | 快速做出二次元基础、改脸/发/衣服、完成可玩原型 | 不经过 Blender 深改就获得独特英雄角色 |
| 中等预算作品集 | Blender + Substance Painter + UE5；需要时加 Marvelous Designer | 自定义造型、稳定贴图、较好衣物与引擎表现 | 软件自动替代角色设计、重拓扑和蒙皮判断 |
| 高速商业管线 | Character Creator 5 + iClone/Auto Setup + UE5，再用 Blender/ZBrush 定制 | 快速取得稳定身体、脸、动画与 UE 接口 | 只调 slider 就摆脱生成器模板感 |

Blender 本体免费开源；VRoid 也免费并允许导出自制 VRM，但使用第三方素材时仍需逐项检查许可。[Blender 官方许可](https://www.blender.org/about/license/) [VRoid Studio 官方页](https://vroid.com/en/studio) Character Creator 和 Substance 属于商业工具，价格与捆绑会变化，因此正式采购前应重新查看官方商店，而不是把本报告中的日期当作长期报价。

### 4.2 建议的个人制作排期（工程估算，不是行业统计）

以下排期假设一名开发者已有基础 Blender 和 UE 能力，每天投入 4–6 小时：

| 工作包 | 建议时间 | 必须留下的中间证据 |
|---|---:|---|
| 故事、参考与反参考 | 2–3 天 | Character Bible、参考来源、禁用套路 |
| 轮廓、候选和服装结构 | 3–5 天 | 20 个缩略图、3 个候选、删案理由 |
| Turnaround、表情、pose | 3–5 天 | 可供建模的正侧背和表情表 |
| VRoid 基底与 Blender 重塑 | 5–8 天 | 灰模 turntable、拓扑/变形检查 |
| UV、bake、材质和头发 | 4–7 天 | 目标灯光 lookdev、灰度/材质通道检查 |
| rig、面部、权重和二级动态 | 4–7 天 | 8 表情、6 gesture、极限姿态测试 |
| UE 导入、重定向和性能 | 3–5 天 | PIE 视频、Insights/ProfileGPU、失败记录 |

总计约 24–40 个半天工作单元。若没有角色美术基础，最应该削减的是服装层数和动态部件，而不是省略 turnaround、拓扑或游戏镜头测试。

---

## 5. 原创角色提案：Ione（伊俄涅）

> 暂定名；在角色设计阶段可以更名。V2 先用它建立“故事—视觉—动作”闭环。

### 5.1 游戏背景

游戏暂名 **《The Last Frequency / 最后一段频率》**，是一款第三人称叙事探索游戏。

一座长期受潮汐侵蚀的近未来海港城，把市民的紧急录音、证词和私人留言保存在遍布地下交通网的“公共声档站”中。大停电后，许多录音损坏并互相串扰。玩家进入封闭区域寻找失踪者，而 Ione 是陪同玩家恢复这些声音的现场修复员。

这不是宏大救世故事。核心冲突是：Ione 相信记录必须忠实，却曾为保护一个人而删除过一段关键录音。随着玩家恢复越来越多的档案，她必须决定是坚持职业准则，还是再次修改真相。

### 5.2 她在游戏中的作用

- 她能分辨环境中的异常频率，帮助玩家定位线索；
- 她会解释设备、指路、阻止危险行动，也会拒绝玩家查看不属于自己的私人记录；
- 玩家可以打断她。她不是继续机械播报，而是停下动作、转移注视、确认玩家意图，再决定是否恢复原话题；
- 她对“记录”和“隐私”的矛盾，使拒绝、犹豫、安慰和警告都具有剧情含义，正好支持表演层研究。

### 5.3 性格与行为

- 表面：安静、准确、少说废话；
- 内核：对失真的信息极度敏感，对人的动机没有同样把握；
- 欲望：修复完整档案，证明真相可以被保存；
- 缺陷：把“准确”当成逃避情感判断的方法；
- 标志动作：说话前会用右手两指触碰耳后的校准夹，先听半秒再回答；
- 被打断时：手先停、眼神转向玩家、身体随后回正。这个时间差成为她的表演特征。

### 5.4 视觉语言：只保留三个记忆点

1. **头发轮廓**：下颌长度的深墨蓝短发，右侧耳后收紧，左后方保留一束窄而长的校准带状发束。不是大马尾，也没有大量发饰。
2. **单一功能物**：右耳后的氧化铜“调谐夹”，既是听觉辅助设备，也是她习惯动作的触点。它取代漂浮水晶、全息法阵和多余饰品。
3. **外套负形**：防水短外套在左后方延伸一块窄长后襟，形成不对称但清楚的剪影；其余衣服保持干净。

### 5.5 色彩与材质

- 70% 深墨蓝/海水黑：外套、头发、靴子；
- 20% 温灰白：内层和脸部附近，建立视觉焦点；
- 8% 氧化铜：调谐夹、两个结构扣；
- 2% 暗朱红：只用于设备处于记录状态时的微小指示。

不再使用常见的“青绿色发光 + 金色饰边 + 透明布”组合。材质只包含防水布、针织内层、磨旧铜和哑光橡胶四类，方便 3D 制作并保持游戏可读性。

### 5.6 服装逻辑

- 短外套便于在狭窄车站和维修梯中行动；
- 高领针织层降低潮湿环境中的不适；
- 稳定的平底短靴适合金属栈道，不使用高跟鞋；
- 腰侧只带一个磁带大小的校准器，无武器、无多层皮带、无装饰性罗盘；
- 后襟提供轻微二级动态，但长度不妨碍跑动和坐姿。

### 5.7 眼睛与脸

她的吸引力不依赖“越大越亮的眼睛”。眼型略下压，虹膜是低饱和灰绿，靠瞳孔有一圈很窄的铜色环；默认眼神专注而不是妩媚。眉毛有清楚的内外高差，方便表达怀疑、担忧和克制的拒绝。嘴型保持简洁，重点制作闭唇、轻启、压唇和单侧紧张四类形态。

---

## 6. 如何确保她独一无二

### 6.1 先做“反参考板”

除了搜喜欢的角色，还要搜并标记不允许出现的套路：

- 大马尾 + 透明披风 + 宝石胸针；
- 全身金色描边；
- 不明用途的漂浮晶体；
- 制服、女仆、偶像、机甲紧身衣等强模板；
- 高跟鞋和战术装备同时出现；
- 左右不对称仅用于增加复杂度。

### 6.2 四次强制测试

1. **纯黑剪影测试**：缩到 160 px，能否靠头发和外套负形识别；
2. **灰度测试**：脸和手是否自然成为焦点，衣服是否糊成一块；
3. **三秒记忆测试**：看三秒后，测试者能否画出两个主要特征；
4. **动作测试**：只看骨架和 pose，能否分辨她的“听、拒绝、警告、被打断”。

如果只能靠耳环纹样或衣服上的小字识别，说明设计仍然失败。

### 6.3 角色必须有“删减日志”

每轮设计至少删掉 30% 元素，并记录：元素服务哪个故事/动作；如果没有答案就删除。这样可以避免后期把“舍不得删的细节”合理化成世界观。

---

## 7. 需要的 Skill，而不只是软件

| Skill | 要解决的问题 | 最低可接受证据 |
|---|---|---|
| Art direction | 世界观、形状、色彩、反参考、删案 | 角色圣经与设计决策日志 |
| Concept design | 轮廓、服装结构、正侧背、表情 | 可建模的 turnaround，不是单张美图 |
| Character modeling | 比例、面部、手、服装和鞋 | 3D blockout 与正交图对齐 |
| Retopology / UV | 变形、性能、材质布局 | 动画测试下无明显夹陷 |
| Texturing / lookdev | 有限材质、眼睛、皮肤、布料层级 | UE 目标灯光下的材质球和角色截图 |
| Rigging / facial | 骨骼、蒙皮、Shape Keys、修形 | 8 表情和 6 动作无严重破面 |
| Technical animation | IK 重定向、Montage、打断、二级动态 | PIE 中断录像与日志 |
| UE technical art | Material、Niagara、LOD、性能 | ProfileGPU/Insights 记录 |
| Narrative design | 背景、矛盾、台词和边界 | 同一人格下的 30 个场景 |

Codex/Skill 的作用是把已经验证的规范沉淀下来，例如命名、导出设置、材质函数、Niagara 参数、C++ Actor 封装和验收清单。它不能替代“角色为什么是这样”的审美决策；那部分必须由 Character Bible、参考板、删案和人工评审承担。

---

## 8. 分阶段计划与验收门槛

### 阶段 A：角色设计锁定（先做，不碰最终 3D）

输出：故事一页纸、参考/反参考板、20 个剪影、3 个候选、色彩研究、最终 turnaround、8 表情、6 pose。

验收：

- 3 秒记忆测试至少 3/5 人能复述两个相同特征；
- 纯黑剪影中能区分正面方向；
- 服装的每个主要结构有功能解释；
- 不依赖生成图的随机细节；
- 角色与背景故事互相解释。

### 阶段 B：3D Lookdev 原型

输出：VRoid/Blender base、脸部重塑、头发轮廓、衣服 blockout、UE 灰模导入、三种目标灯光测试。

验收：

- 正侧背不漂移；
- 眼睛、鼻口和发际线不再像默认 VRoid；
- 160 px 游戏镜头仍能识别；
- 不出现自交、严重穿插或动作不可行的衣服。

### 阶段 C：Game-ready 角色

输出：低模、UV、bake、材质、骨骼、Shape Keys、LOD、FBX、UE Skeletal Mesh。

验收：

- FBX/Morph Target 导入无错误；
- IK Rig 可重定向基础 idle/walk/turn；
- 8 表情在游戏灯光下可读；
- 头发和后襟动态不破坏原轮廓；
- ProfileGPU 和 draw call 有记录，不预设漂亮就等于性能合格。

### 阶段 D：UE5 叙事垂直切片

输出：一个声档站场景、Ione Actor、对话与语义表演组件、Montage、Niagara、Material、打断恢复、Debug 模式。

验收：

- 玩家能在至少三个时间点打断；
- Voice、Face、Body、VFX 和游戏动作回到一致状态；
- 普通游戏画面中没有常驻研究仪表盘；
- Debug 模式可看 A/B/C 与计划日志；
- 录制真实 PIE 视频，不用网页替身冒充。

---

## 9. 决策：下一步不应该做什么

- 不再直接生成“最终角色图”；
- 不再把华丽程度当成设计完成度；
- 不先写大量 UE 功能再补角色；
- 不把 MetaHuman、VRoid、CC5 的默认结果当原创成果；
- 不让 Material、Niagara 和 C++ 各自炫技，它们都必须服务同一个场景；
- 不在没有 UE 编译和 PIE 录像时宣称“完成 Unreal 集成”。

下一步只做 **阶段 A**：角色圣经、参考/反参考板、轮廓与服装结构。阶段 A 没通过，3D 和引擎实现暂停。

---

## 10. 证据质量与限制

| 来源类型 | 用途 | 可信边界 |
|---|---|---|
| Epic/Valve/VRoid/Blender/Adobe 官方文档 | 确认工具能力、格式、版本和官方流程 | 不能证明某工具一定产生好看的角色 |
| Reallusion 官方页面 | 确认 CC/UE Auto Setup 与商业产品功能 | 带营销倾向，需在试用版或实际项目中验证 |
| ArtStation Learning/Gnomon 专业课程 | 说明真实角色制作步骤和岗位协作 | 属于实践案例，不是行业统计 |
| VRM4U GitHub 与 issue | 检查社区插件能力和版本风险 | issue 是个案证据，不能代表所有环境 |

本报告没有采访角色艺术家，也没有在当前机器安装 UE5、VRoid、Blender 或 CC5 进行同一角色的横向试做。平台选择属于基于公开证据的工程判断；最终质量仍取决于阶段 A 的人工设计与后续实际验证。

---

## 11. 关键来源

- [Epic Games — MetaHuman Stylized Character Tutorial](https://dev.epicgames.com/documentation/metahuman/metahuman-stylized-character-tutorial?lang=en-US)
- [Epic Games — MetaHuman From Custom Mesh](https://dev.epicgames.com/documentation/metahuman/metahuman-creator-from-custom-mesh-tool-in-unreal-engine)
- [Epic Games — Setting Up a Character](https://dev.epicgames.com/documentation/en-us/unreal-engine/setting-up-a-character-in-unreal-engine)
- [Epic Games — FBX Skeletal Mesh Pipeline](https://dev.epicgames.com/documentation/en-us/unreal-engine/fbx-skeletal-mesh-pipeline-in-unreal-engine)
- [Epic Games — IK Rig Retargeting](https://dev.epicgames.com/documentation/unreal-engine/ik-rig-animation-retargeting-in-unreal-engine?lang=en-US)
- [Epic Games — Hair Art Directability](https://dev.epicgames.com/documentation/metahuman/hair-art-directability)
- [Epic Games — Getting Started with Parametric Clothing](https://dev.epicgames.com/documentation/metahuman/getting-started-for-creating-parametric-clothing-in-metahuman?lang=en-US)
- [Valve — Dota 2 Character Art Guide](https://help.steampowered.com/en/faqs/view/0688-7692-4D5A-1935)
- [ArtStation Learning / Envar — Building an Original Character](https://magazine.artstation.com/2023/04/building-original-character/)
- [Kat Unsworth / Gnomon — Modeling a Stylized Character for Games](https://katunsworth.artstation.com/projects/29lzOg)
- [VRoid Studio](https://vroid.com/en/studio)
- [VRM Consortium — What is VRM?](https://vrm.dev/en/vrm/vrm_about/)
- [VRM4U GitHub](https://github.com/ruyo/VRM4U)
- [Reallusion — Character Creator 5](https://www.reallusion.com/character-creator/default.html)
- [Reallusion — Auto Setup for Unreal Engine](https://www.reallusion.com/character-creator/unreal-engine-auto-setup.html)
- [Blender — License and artwork ownership](https://www.blender.org/about/license/)
- [Adobe Substance 3D Painter — Baking](https://experienceleague.adobe.com/en/docs/substance-3d-painter/using/baking/baking)
- [Marvelous Designer — Official Manual](https://www.marvelousdesigner.com/manuals)

---

## 12. AI 使用披露

本报告使用 AI 辅助完成公开资料检索、来源筛选、路线比较、风险整理和初稿写作。平台能力均链接到公开来源；角色故事和 V2 方案属于项目原创提案。现有 AI 生成角色图被明确降级为失败探索，不作为最终角色设计、可生产性或 UE 集成证据。
