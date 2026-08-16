# AI-3「采集通道与复核契约组」修复计划（F-05 / F-06 / F-08 / F-13）— @CX 融合版

## Context（背景）

codex 对 token-chip-analysis main v6.44.0（冻结 SHA `ddba187`）六视角全量 review 判 BLOCK，14 findings。三 AI 并行分工中本组（AI-3）领 4 条：F-05、F-06、F-08（P1×3）+ F-13（P3）。用户裁决：**F-05 不加闸**。本计划已经 @CX codex 只读复核并融合其意见（融合记录见文末）。

四条问题的大白话版：
- **F-08**：权威工作流文档给的 A0 记账检查命令，在新 EVM 案上必然报错退出（缺必填参数），且文档没写正式件的正确生成顺序——新案第一步就卡死。
- **F-06**：备用采集通道（SQD/Alchemy）遇到数据源空响应/残缺响应时，会把"什么都没拉到"签成"完整拉完了"，漏掉全部转账还全绿；且收据里的"完成游标"字段是自造值冒充数据源证据。
- **F-05**：文档说对抗复核要 N 路怀疑者+外部异构路，机器闸只验"角色在场"，一路也能过（用户裁决：不装机器强制，改为文档说清边界，状态记用户裁决豁免）。
- **F-13**：文档说受控 runner 会替复核产物"补入"两个字段，实际 runner 只传环境变量、要求 entrypoint 自己写——照文档写的新 entrypoint 会被拒。

## 基线与施工环境

- 仓库：`~/.claude/skills/token-chip-analysis`，基线 `ddba187`（v6.44.0）
- 分支：`repair-20260815-g3`，git worktree 隔离施工
- ⚠️ worktree **不建在 `~/.claude/skills/` 下**（g1/g2 的 worktree 已被 skill 扫描器误识别为重复 skill）——建到仓库外路径（如 `~/Documents/5.6筹码分析/worktrees/repair-g3`）
- 工程档案目录：`maintenance/repair-20260815-g3/`（plan + done 报告 + 实测记录）

## F-08（P1）：A0 命令断裂 —— 修文档 + 分文件两阶段（零代码行为变更）

**现状**（已实读代码确认）：analyze-workflow.md A0 段命令缺 `--bundle`/`--exploration` → `accounting_gate.py:412` exit 2；bundle 要到 A2 才由 observe_supply.py 产出；formal 消费面（shared_release_receipt.py:843-848）EVM 案只认 `--bundle` 产的 accounting-gate/v2。

**修法**（采纳 codex"分文件不同名覆盖"设计）：
1. A0 段命令改为：`accounting_gate.py --token 0x… --chain <链> --exploration --out accounting_mode.exploration.json`，注明"A0 是模型预检（探索档，产 v1）；exit 2＝BLOCK 硬停不采集，语义不变"
2. A2 第 3 查段改为三步顺序：`observe_supply.py` 产 bundle → **`accounting_gate.py --bundle evm_observation_bundle.json --as-of-block <冻结块> --out accounting_mode.json` 产正式 v2 件** → `supply_truth_gate.py`。并加一句："A2 formal 结果为唯一 canonical；与 A0 预检不同时以 formal 为准并停止后续阶段"
3. **分文件理由**：探索件若同名占据 `accounting_mode.json`，提前误跑 A4 时 `adversarial_review_runner.py:568` 会浅取探索 target 绑进 aggregate，正式件覆盖后整套 A4 重做——分文件消除该操作风险（codex 意见，采纳）
4. Solana 命令不动
5. 守卫测试：文档 needle **按 A0/A2 标题分段检查**（A0 段命令含 `--exploration`+exploration 输出名；A2 段含 `--bundle` 重跑指引；避免全文件 needle 假绿——codex 意见）。argparse exit 2 冒烟不再新增（test_repair_batch_a.py:321 已有覆盖，去重）

## F-06（P1）：备用采集器假完整 —— fetcher 接受面 + receipt 完成语义分型（本组主工程）

**现状**（已实读代码确认）：
- fetch_sqd_evm.py:87 空正文零迭代也推进/完成；:119-122 receipt 的 `provider_next_block` 填 `a.to_block+1` 自造
- fetch_alchemy.py:88 接受任意 dict result（缺 `transfers` 键=零转账、缺 `pageKey`=完成）；:126-130 同样自造游标
- **codex 补充确认**：Alchemy 协议本身没有块级游标（只有分页 pageKey），v2 schema 却把 `completion.next_block`/`segments[].provider_next_block` 定义为块游标，data-pipeline-evm-channels.md:36 还声称是"严格前进且到达目标的 cursor"——即使修好接受面，Alchemy 填该字段仍是语义不实

### 第一刀：SQD 协议实测定案（施工首步，三场景——codex 扩展）
对 SQD 公共端点实测并落档 `maintenance/repair-20260815-g3/sqd_probe_notes.md`：
1. 零匹配区间：是否返回哨兵行（header-only 末块行）
2. 稀疏区间（最后一笔事件远早于请求上界）：末行 header 代表"最后事件块"还是"扫描前沿"
3. 大响应截断：截断点语义、续拉是否重叠
判据：**SQD 能否提供 provider 侧扫描前沿证据**。能 → SQD 保留正式 receipt 资格（游标=扫描前沿）；不能 → SQD 正式资格与 Alchemy 同刀处置（见第二刀选型）。

### 第二刀：receipt 完成语义修法 —— **选型 B 已拍板（用户 08-15）：除名 Alchemy，schema 不动**
1. `csv_collector_receipt.py:7` SUPPORTED 集合去掉 `fetch_alchemy.py`，旁加一行注释说明除名原因（Alchemy 协议无 provider 侧块进度证据，v2 的块游标语义对它不成立）——防将来被"好心"加回
2. `channels_preflight.py` allowed 三支名单去掉 alchemy → 存量/新造 alchemy receipt 一律被拒
3. `fetch_alchemy.py`：`--receipt` 参数保留但直接 `ap.error` 拒绝并给出指引（"Alchemy 通道无 provider 侧完成证据，不支持正式 receipt，仅探索采集"）；文件加 `FORMAL_CHANNEL_ELIGIBLE = False` 标记，与 fetch_bigquery 等 nonformal 通道同款
4. `test_round4_csv_adapters.py` 同步：native-receipted 名单去掉 alchemy、nonformal 断言名单加入 alchemy（改既有测试属修复一部分，done 报告写明）
5. `data-pipeline-evm-channels.md` 同步改口：Alchemy 降级说明+除名原因；:36 的 cursor 句修正
6. **SQD 依第一刀实测定夺**：有 provider 侧扫描前沿证据 → 保留正式资格（v2 块游标语义对它成立，receipt 游标改传 provider 派生值）；无 → 与 Alchemy 同刀除名（SUPPORTED 暂为空集，机制文件保留）
7. 将来候选（done 报告留账）：若上游 API 提供进度信息或决定升 v3 分型收据，Alchemy 可恢复正式资格

### 第三刀：两 fetcher 接受面（选型无关，必做）
**fetch_sqd_evm.py**：
1. 响应解析抽纯函数：空正文/无有效行返回 None；区间推进只用 provider 返回的行块号（依实测哨兵语义），废除"空响应也 +1 推进"
2. 连续 N 次（拟 5 次）空响应硬退 exit 非零、不写 receipt
3. receipt 游标只传 provider 派生值；从未拿到任何 provider 行则不可签
**fetch_alchemy.py**（虽已除名正式资格，探索数据同样不容静默漏拉——接受面照修，codex 补全字段清单，统一严格）：
4. 响应校验抽纯函数：result 必含 `transfers` 键且为 list（缺键=协议错误入重试，重试尽硬退）；每条 transfer 必含 `blockNum`（且落在请求区间内）/`hash`/`from`/`to`/`uniqueId`（非空正确类型）；`rawContract.value` 必须为合法 hex（**删除 float value×1e18 回退**）；`pageKey` 存在须非空 str 且**不得重复出现**（seen 集合防循环）；**整页先验证完再写任何一行**
5. 纯参数/文件前置检查移到任何网络调用（含 RPC attestation）之前

### 第四刀：签发前置与失败件卫生（codex 旧 receipt 残留反例，必做）
6. SQD 正式模式（带 `--receipt`）要求：**输出路径与 receipt 路径运行前均物理不存在**（lexists 语义——零字节文件、symlink 都算存在），且两路径不得相同
7. 两 fetcher 失败退出时输出改名 `.partial`，不打印 `[COMPLETE]`——半成品不可被后续补签/误用

### 测试（先红后绿，双层——codex 意见：纯函数级不够）
- 纯函数层：SQD 空正文/哨兵行/残行；Alchemy 缺键/残 transfer/坏 rawContract/pageKey 循环
- **主路径层（mocked transport，零真实网络）**：monkeypatch 响应注入，证明"残响应 → 进程非零退出 → SQD receipt 不存在且 emitter 未被调用"；以及"已写合法页后再遇残响应，仍不能签发"
- 除名负测：`emit_native_receipt` 对 fetch_alchemy.py collector 必 raise；preflight 对 alchemy receipt 必拒；`fetch_alchemy.py --receipt` 必 exit 2
- 先红：负测先对当前代码复现假完整，修复后转绿，证据留档

### 留账不闭合面（done 报告明示，不声称 F-06 全族闭合）
- SQD receipt 无 chain 字段、dataset 任意名、preflight 不与分析目标链交叉验证（错链空扫描面）——交融合方登记后续工单
- 存量口径：改 fetcher 后脚本 sha 变化，旧 SQD/Alchemy native receipt 的 preflight 重验会拒；备用通道"平时不跑"应零正式存量，若有须重采集或走 audit 迁移口径

## F-05（P1）：A4 N 路机器化 —— 用户裁决不加闸 → 文档精确边界 + ACCEPTED_RISK

**裁决执行**：不新增任何机器强制，`adversarial_review_runner.py` 零改动。

**修法**（采纳 codex"精确清单代替泛称"）：
1. analyze-workflow.md A4 第 5 步末与 research-workflows.md §2 补边界段，**逐项列明**：
   - 已机器化：两 role 在场（≥1 怀疑者+≥1 完整性）、claim 并集覆盖、entrypoint 内容去重、execution ledger 精确对账、evidence 实义门槛、REFUTED/findings 与 blocker 双向联动
   - 未机器化（靠执行纪律与盲审）：N 路数量、每结论分档路数、外部模型异构性、外部异构路成功与否（现行文档明示该路失败不阻塞交付，research-workflows.md:119）
2. **状态定性（codex 意见，采纳）**：F-05 记 `ACCEPTED_RISK`（用户裁决豁免），**不得标 FIXED/CLOSED**，r10 台账保持现役+正文注记裁决——登记行由融合方写，done 报告给出建议文本

## F-13（P3）：runner 注入描述矛盾 —— 改文档一句对齐现实（零代码）

**修法**（采纳 codex 精确措辞）：research-workflows.md:102 改为——"entrypoint 必须从 `CHIP_REVIEW_ROLE` 与 `CHIP_REVIEW_REGISTRY_SHA256` 读取值，逐字写入 `CHIP_REVIEW_OUTPUT` 指定的 artifact；runner 在发布前校验一致，不会静默覆盖或补入"。
不选"runner 覆盖补入"代码方向：受控侧静默覆盖会消掉"entrypoint 写错 role 被拒"的检测面。
测试：文档 needle 并入 F-08 守卫测试文件。

## 施工顺序

1. 建 worktree（仓库外路径）→ 落工程 plan
2. **F-08**（文档+分段 needle 测试，热身）→ **F-13**（一句）→ **F-05**（边界段×2）→ **F-06**（主工程：SQD 三场景实测 → 按选型动 receipt 层 → 两 fetcher 接受面 → 签发前置 → 双层测试先红后绿）
3. 每步跑 `docs_lint --all`（注意逐行粗体配对；升 v3 时文档中 `evm-collector-run/v2` 契约 needle 同步改）与相关既有测试

## 验收标准

- SUITE 既有 101 项全绿（本机跑，含 loopback 两项）；本组新测试单跑全绿
- F-06 先红证据、SQD 实测记录留档工程目录
- done 报告 `workorder_G3_done.md`：改动清单、先红后绿证据、F-06 留账面与存量口径、待融合方注册的 SUITE 行/契约行/invariant 行、F-05 ACCEPTED_RISK 建议文本、决策点记录

## 协调边界（三方并行规则，本组承诺）

- **不碰**：VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、run_all.py（SUITE 注册行留融合方）
- analyze-workflow.md / research-workflows.md / data-pipeline-evm-channels.md 本组独占；fetch_sqd_evm.py / fetch_alchemy.py / csv_collector_receipt.py / channels_preflight.py 本组域
- `adversarial_review_runner.py`、`shared_release_receipt.py`、`audit_release_gate.py` 本组零改动 → 与 AI-1/AI-2 冲突面为零
- 选型 B 落定后不升 schema → **不碰契约注册表**（共享文件冲突风险消除）；`.partial` 改名若触发 invariant manifest 登记则标注交融合方
- `test_round4_csv_adapters.py` 名单更新属本组修复内容（既有测试文件，非中心注册表）
- 措辞纪律：负向测试/变异复核，不用攻击性词汇

## 决策点记录

| 决策 | 定论 | 理由 |
|---|---|---|
| F-05 加不加闸 | 不加（用户 08-15 裁决），状态 ACCEPTED_RISK 非 FIXED | 文档精确边界，台账保持现役 |
| F-06 receipt 修法 | **选型 B（用户 08-15 拍板）：除名 Alchemy，schema 不动** | 最小刀；代价=HyperSync 故障时 ETH 侧无正式备用路径（用户知情接受）；将来可凭升 v3 分型恢复资格（留账） |
| F-06 SQD 正式资格 | 依三场景实测：有扫描前沿证据→保留；无→与 Alchemy 同刀除名 | provider 侧证据是正式资格前提 |
| F-13 代码还是文档 | 文档 | runner 覆盖会放宽检测面 |
| F-08 探索件文件名 | 分文件 `accounting_mode.exploration.json`（codex 设计） | 消除同名过渡态误绑 A4 风险 |

## @CX codex 复核融合记录

codex 总评：反对原样开工；F-08/F-13 方向成立、F-05 只能记用户接受风险、F-06 有两处实质缺口。融合处置：
- **采纳**：F-06"不升版理由不成立"（schema 须诚实表达证据类型，Alchemy 无块游标）→ 改为选型 A/B 待裁决；旧 receipt 残留反例 → 第四刀签发前置；Alchemy parser 字段补全+整页先验后写+前置检查移到联网前；主路径 mocked-transport 测试；SQD 实测扩三场景；F-08 分文件设计+"formal 为准停止后续"句+needle 按标题分段+argparse 冒烟去重；F-05 精确边界清单+ACCEPTED_RISK 定性；F-13 精确措辞。
- **留账**：SQD 链身份绑定（dataset/chain 交叉验证）不在本次范围，done 报告交融合方。
- **保留意见**：无实质分歧项。
- **用户终裁**：F-06 receipt 修法在 codex 给出的两选型中拍板选型 B（除名 Alchemy）；F-05 维持不加闸＋ACCEPTED_RISK 定性。
