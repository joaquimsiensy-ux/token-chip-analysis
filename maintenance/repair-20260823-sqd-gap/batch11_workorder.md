# 批 11 工单：五查冻结快照与活观测分家——同文件绑定改冻结 bundle 哈希绑定

- 裁决依据：延续用户 2026-08-26 方案 A（第五查对冻结点对账）。批 10 关了 target
  层，实跑暴露同一矛盾还有最后一层没关：**文件绑定层**。
- 背景（大白话）：发布深验现在要求第五查消费的持有人快照与 supply 观测产出的
  持有人快照是**同一个文件**（shared_release_receipt.py 约 :1430-1441 的
  `exact_path == supply_path`）。方案 A 之后两者天然是两份：supply 观测的是
  "链上现在"（活快照），第五查对的是"冻结点"（封账快照）。同文件要求逼着
  第五查吃活快照 → 活跃币必然对不平（ARC 实跑 966 mismatch）。更糟的是
  supply 观测按 job spec 会把封账快照文件**覆盖掉**（ARC 案今天真实发生，
  靠密封复合快照逐字节还原才救回）。
- 修正哲学：同文件绑定的本意是防伪（"第五查用的快照必须是真观测的那份"）。
  分家后防伪链改为**哈希绑定**：第五查消费的快照必须与案内**密封冻结观测
  bundle** 里记录的指纹逐字节一致。防伪强度不降（sha256 绑定 ≥ 路径同一）。

## 现状事实（ARC 案已就位，可作实物参照，但代码不得写死 ARC 路径）

- 冻结观测 bundle 正式命名：`data/solana_observation_bundle_frozen.json`
  （target.as_of_block == 冻结点 == exact receipt 的 as_of_block；含
  holder_outputs.owners/accounts 的 sha256+size、attestation、inputs 指纹）。
- 冻结快照三件在 `data/holders_owners.json` / `data/holders_accounts.json` /
  `data/holders_snapshot_meta.json`（replay_edges.py reconcile 的固定读取路径，
  本批**不改**该路径）。
- 活观测已分家：job spec 里 supply 的 `--work-dir` 指到 `data/observe_live`，
  活 bundle 仍在 `data/solana_observation_bundle.json`（supply_truth 消费）。

## 改动面

### 1. shared_release_receipt.py 的 solana 同文件绑定（约 :1429-1443）

现行（else 分支，family solana）：
```
exact_path == supply_path  # exact.inputs.holders_owners 与 supply bundle owners 同一文件
```
改为**两态**：
- **静态态**（exact receipt target.as_of_block == wrapper target.as_of_block）：
  维持原同文件绑定，一字不改（存量夹具/静态案零变化）。
- **冻结态**（exact as_of < wrapper as_of，即方案 A 动态活链）：
  a) 案内必须存在 `data/solana_observation_bundle_frozen.json`；
  b) 对它做与活 bundle 同深度的信封/envelope 校验（validate_receipt 案根约束、
     schema、attestation genesis、closed/closure，比照现行 supply bundle 的
     校验路径，能复用就复用不重造）；
  c) 冻结 bundle 的 `target`（canonical）必须与 exact receipt 的 target 全等
     （chain/token/as_of_block 三元组，as_of_block 即冻结点）；
  d) exact.inputs.holders_owners 的 sha256+size 必须与冻结 bundle
     `holder_outputs.owners` 的 sha256+size 全等（哈希绑定替代路径同一）；
  e) 拒绝消息用大白话说清"冻结态第五查快照必须哈希绑定冻结观测 bundle"。

### 2. handoff_manifest.py 消费面核查

它在 READY 深验里要求 exact receipt 及 inputs 进 data_map/artifacts（约 :279-296、
:427-441）。核查冻结态下是否需要把 `data/solana_observation_bundle_frozen.json`
一并纳入必进清单——**应当纳入**（它现在是防伪链一环）；实现向 required_exact
集合加入冻结 bundle 路径（仅冻结态）。

### 3. 文档

- references/scan-schemas.md：批 10 加的那行"exact 检查组合…同一文件并调用独立
  深验"改为两态表述（静态同文件/冻结态哈希绑定冻结 bundle），大白话解释为什么。
- references/analyze-workflow.md §5：补一句冻结态 job spec 的分家要求
  （supply `--work-dir` 独立子目录如 `data/observe_live`，防覆盖封账快照三件；
  冻结 bundle 正式命名 `data/solana_observation_bundle_frozen.json`）。
- 契约：若新增拒绝路径的守卫锚点，按现行规则登记（沿用 CT-SQDGAP 系列下一号）。

### 4. 测试（先红后绿）

- R1 红：构造冻结态夹具（exact as_of < wrapper as_of、快照与冻结 bundle 哈希
  一致但与活 bundle 不同文件）→ 现行 validate_reconciliation_report 在同文件
  绑定处拒（留红证据）。
- G1 绿：同一夹具改后通过。
- N1：冻结态但案内无 `solana_observation_bundle_frozen.json` → 拒。
- N2：冻结 bundle target.as_of_block ≠ exact receipt as_of_block → 拒。
- N3：exact 消费的 holders_owners 哈希 ≠ 冻结 bundle 记录（伪造/换包）→ 拒。
- N4：静态态（as_of 相等）仍走原同文件绑定：原有夹具回归零变化。
- N5：handoff READY 深验冻结态缺冻结 bundle 于 data_map/artifacts → 拒
  （若第 2 点实现为必进清单）。
- run_all 全套全绿。

## 边界与禁改面

- replay_edges.py 硬闸与固定读取路径不动；runner reconciliation_report.py 本批
  不动（批 10 已关 target 层）；EVM 全家族零变化。
- 不触碰密钥文件；不在任何产物写真实 key；ARC 案根一个字不动（案内实物由
  验收方管理）。
- 纯改文件不 commit、不动版本登记面；完成写 batch11_done.md（改动行号、红绿
  证据路径、handoff 核查结论、边界自查），Fable 验收后代 commit。
