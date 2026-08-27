# 批 12 工单：分布扫描器供应交叉检查的冻结态容差（方案 A 同族第四现形）

- 裁决依据：延续用户 2026-08-26 方案 A。批 10 关 runner target 层、批 11 关发布深验
  文件绑定层后，ARC A3 实跑暴露同族矛盾第四个消费点：
  `scripts/report/holder_distribution_scan.py`。
- 背景（大白话）：扫描器读 supply_truth.json 时有一条硬拒（`_read_supply_truth`
  约 :241）：`net > onchain` 即判"供给真值 onchain/net 非法"。潜台词是静态时点假设
  ——重放净额（net=replay_net，账本冻结点口径）不可能高于链上现值（onchain，
  观测时点口径）。方案 A 之后两者是**不同时点**：冻结点后链上发生一笔微量销毁,
  onchain(现在) 就会**低于** net(冻结点)——ARC 实测 diff=26,135 raw
  （diff_bps=0.0，supply_truth 闸自己按 10bps 容差判了 PASS），扫描器却在门口把
  这份 PASS 收据拒了 → A3 第 8 项 BLOCKED（案根 anomalies
  ARC-A3-DISTRIBUTION-BLOCKED-14）。
- 修正哲学：与批 10/11 同一句话——supply_truth 闸已经用容差接受了时点差，
  下游消费者不得用静态等式把它再拒一遍。扫描器应**尊重 PASS 收据自带的容差语义**。

## 现状事实（ARC supply_truth.json 实物字段，可作夹具参照）

```
replay_net=999982737531582  onchain_total_supply=999982737505447
diff=26135  diff_bps=0.0  tolerance_bps=10  verdict=PASS  exit_code=0
supply_observation_semantics="bundle getTokenSupply cross-check observed at
  observed_context_slot; canonical freeze remains target.as_of_block from GPA context"
```

## 改动面

### 1. holder_distribution_scan.py `_read_supply_truth`（约 :226-244）

`net > onchain` 的硬拒改为**两态**：
- **静态态/常规向**（net ≤ onchain）：行为逐字不变。
- **冻结态漂移向**（net > onchain）：仅当同一收据满足全部条件才放行——
  a) verdict=="PASS" 且 exit_code==0（现有读取路径已保证是 PASS 收据，复核即可）；
  b) 收据自带 diff 与 tolerance_bps 字段，且 `net - onchain == diff` 逐位复算相等；
  c) 漂移在收据自己的容差内：`(net-onchain) * 10000 <= tolerance_bps * onchain`
     （整数运算，禁浮点）；
  d) 任一条件不满足仍原样硬拒，拒绝文案保留原句并附一句大白话说明冻结态例外的边界。
- 放行时在返回/记录面留痕（如 receipt/JSON 里记 supply_drift_raw），供 −2 阅读；
  具体字段名与落点由你按 distribution-scan/v2 schema 兼容性判断，不得破坏现有
  validator 与消费者。
- **分母语义梳理**：net 仍作分布百分比分母、onchain 仍作快照闭合锚（Solana
  sum(快照)==onchain 精确等式不动）。若你分析后认为漂移向下的分母该用 onchain
  而非 net（活快照对冻结净额的 0.0000026% 偏斜），在 done 报告里给论证，但
  **默认不改分母取向**——改动面最小原则。

### 2. 波及面核查（关到同一深度）

- rg 全库找还有没有其他消费者对 supply_truth 的 net/onchain 做静态等式或方向性
  假设（validator、发布闸、handoff、−3 装配段消费面）；逐处给结论（有=修，
  无=行号证明），写进 done 报告。已知无需改：批 10/11 已关的 runner/深验/绑定层。
- 发布闸 new-analysis 对 distribution 快照的 sha 等值比对（对 observation bundle
  holder_outputs.owners）：本批 distribution 仍消费活观测快照、来源未变，预期
  零影响——给行号确认即可。

### 3. 文档与契约

- scan-schemas.md 的 distribution 段（若有 net/onchain 表述）补冻结态漂移一句；
  analyze-workflow §5/A3 相应处如有静态表述同步。
- 新拒绝/放行路径若需契约锚点，沿用 CT-SQDGAP 系列下一号登记。

### 4. 测试（先红后绿）

- R1 红：构造 ARC 同形夹具（PASS 收据、net>onchain、diff 一致、容差内）→
  现行 `_read_supply_truth` 拒（留红证据）。
- G1 绿：同夹具改后放行，扫描器可产合法 distribution_scan.json。
- N1：net>onchain 且 diff 字段与 net-onchain 不等 → 拒。
- N2：net>onchain 且超收据 tolerance_bps → 拒。
- N3：收据非 PASS/exit 非 0 → 拒（既有行为回归）。
- N4：静态态（net ≤ onchain）全部现有夹具零变化（EVM 与 Solana 各回归）。
- run_all 全套（真实失败清零；沙箱 loopback 环境失败如实标注）。

## 边界与禁改面

- supply_truth 生产者、五查 runner、发布深验、replay_edges 一律不动。
- 不触碰密钥文件；ARC 案根一个字不动（重跑第 8 项由验收方执行）。
- 纯改文件不 commit、不动版本登记面；完成写 batch12_done.md（改动行号、红绿
  证据路径、波及面核查逐处结论、run_all 结果、边界自查），Fable 验收后代 commit。
