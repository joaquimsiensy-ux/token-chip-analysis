# 批 10 工单：五查 exact_reconcile 活链协议修正（方案 A）

- 裁决依据：用户 2026-08-26 拍板方案 A（决策页：ARC 案根 DECISION_five_check_liveness_20260826.md）。
- 背景（大白话）：五查 runner 目前强制第五查（exact_reconcile，逐持有人全量对账）
  消费"观测到的链上当前 slot"；而生产者 replay_edges.py 的硬闸又要求对账 slot
  必须精确等于**账本缓存冻结点**（meta 的 finalized_upper_slot）。活链上"当前"
  永远不等于"冻结点"，两条规则互斥——第五查在任何真实活跃币上结构性跑不通
  （ARC 案首次实战暴露；此前只有静态测试夹具跑过）。
- 修正哲学：第五查改为**对冻结点对账**（严格性不降：仍是冻结点上的全量逐 owner
  相等）；观测点与冻结点之间的现值差，继续由第三查 supply_truth 的 10bps 容差兜底
  （它本来就是干这个的）。协议内部从"一查允许时点差、一查禁止时点差"的自相矛盾
  恢复自洽。

## 改动面（三层必须关到同一深度）

### 1. runner：scripts/report/reconciliation_report.py

a) `_validate_spec` 的动态 solana 分支（现 :195-201）：
   - balance / supply_truth / time 三查**维持不变**：必须消费 `{observed_as_of_block}` 占位符。
   - exact_reconcile 改为**禁止**出现该占位符；它的 argv 必须携带字面量 slot
     （由 job 作者钉死为账本冻结点）。谁保证这个字面量没写错？——生产者
     replay_edges.py 的硬闸（--as-of-slot 必须 == cache finalized_upper_slot，
     现 :393-396 附近）**保持原样不动**，它就是权威；runner 不重复造闸。
   - 拒绝消息要说清新语义（大白话），方便下个人理解为什么第五查特殊。

b) `run_job` 的 receipt target 一致性检查（现 :267-268）：
   - 动态 solana 下 exact_reconcile 单独放宽：receipt.target 的 chain/token 必须
     与 wrapper target 全等；as_of_block 必须是非 bool 的 int、0 ≤ N ≤ 观测 slot
     （冻结点不可能在观测点之后——未来时点收据一律拒）。
   - 其余所有 check（含 EVM 全家族）维持全等断言，一个字不松。

### 2. 发布深验：scripts/report/shared_release_receipt.py

`validate_reconciliation_check` 的公共 canonical_target 全等断言（现 :1187-1188）
会同样拦下冻结点收据，需同步：
   - solana + exact_reconcile 走与 runner 1b 相同的放宽（chain/token 全等 +
     as_of_block 为 int 且 ≤ wrapper target 的 as_of_block）；
   - 其余 key / EVM 家族维持全等，零变化。
   - **正向绑定必须存在**：放宽全等后，防"拿旧时点收据蒙混"的闸变成
     "receipt 的 as_of_block == 其绑定账本缓存 meta 的 finalized_upper_slot"。
     先查 `scripts/lib/solana_exact_validate.py` 的 `validate_reconcile_receipt_deep`
     是否已含此绑定（它会深验收据与缓存/edge 绑定）；已含则在 done 报告里给出
     行号证明即可，不重复造；**若无则必须补上**——没有这道正向闸，放宽就是漏洞。

### 3. 生产者：scripts/solana/replay_edges.py

硬闸**不改**。若其报错文案提到"必须 == cache finalized_upper_slot"之外的过时
表述可顺手校对，但语义零变化。

### 4. 文档与模板

- 查 runtime_docs_manifest.json 找到管五查 job spec 的运行时文档，把
  "第五查消费占位符"的旧说法改为新语义（exact_reconcile 钉冻结点字面量，
  其余三查消费占位符），附一段大白话解释为什么。
- 若仓库里有五查 job spec 示例/模板文件，同步。
- 契约注册表（scripts/tests 下契约套件）：本次改动触及的错误消息/行为若被
  契约条目引用，同步更新；新增拒绝路径按现行规则登记。

### 5. 测试（先红后绿，全部进守护套件）

红证据（改代码前先跑、留输出）：
- R1：构造"exact_reconcile 不带占位符、带字面 slot"的合法新语义 spec →
  现行 runner 在 _validate_spec 即拒（证明改前行为）。

绿 + 负向守卫（改后）：
- G1：R1 同一 spec 通过 _validate_spec（可用 stub producer 或最小夹具走通全链）。
- N1：exact_reconcile 带占位符 → 拒。
- N2：balance / supply_truth / time 任一缺占位符 → 仍拒（回归）。
- N3：exact receipt 的 chain 或 token 与 wrapper 不一致 → 拒（runner 与深验两层各测）。
- N4：exact receipt 的 as_of_block > 观测 slot → 拒（两层各测）。
- N5：exact receipt 的 as_of_block ≠ 缓存 finalized_upper_slot → 深验拒
  （正向绑定闸的先红后绿；若绑定已存在，给现有测试或补测）。
- N6：EVM 家族四查路径行为逐字不变（回归，跑现有 EVM 契约即可）。
- run_all 全套全绿。

## 边界与禁改面

- 不得触碰任何密钥文件（~/.config/helius/*、api-keys 相关），不得在代码/测试/
  文档中写入任何真实 key。
- 不得改 replay_edges.py 硬闸语义、不得动 EVM 分支语义、不得动 supply 观测逻辑。
- 只改 skill 仓库；ARC 案根（~/Documents/5.6筹码分析/ARC分析/）一个字不动
  （job spec 由验收方改）。
- 纯改文件不 commit：完成后写 batch10_done.md（含红绿证据路径、行号索引、
  validate_reconcile_receipt_deep 绑定考据结论），由 Fable 验收后代 commit。
- 版本：验收通过后由 Fable 升 6.52.9 并登记 CHANGELOG（codex 不动版本登记面）。
