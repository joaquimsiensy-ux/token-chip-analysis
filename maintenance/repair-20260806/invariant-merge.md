# R9 修复闭环：不变量归并表（49 项）

- R8 冻结基线：`main@6e943486a9e4a6f2b673c7cd7a03093f463da233`；R9 当前冻结基线：`main@63cf715cb6d11f6669f4370c77574930da655891`。
- 状态：R8 的 20 个种子、44 项 primary 分配与六同族组已由 Fable 冻结；R9 按 PLAN 第二节追加 5 项，仍使用既有 20 个种子，不拆分/合并。INV-20 继续保留为零 primary 的豁免防回流 secondary 守卫。
- 治理纪律：此后拆分/合并不变量必须经 Fable 批准并同步 ledger 双台账，不得在验收阶段为销账临时改组。
- 计数口径：49 项 finding 每项恰好一个 primary invariant；secondary 只作同族导航，不计 primary 分母。

## 一、PLAN 第三节初始种子（原样照抄）

| ID | 核心不变量 |
|---|---|
| INV-01 | 正式 receipt 必须证明受控 producer 在当前运行真实执行 |
| INV-02 | receipt 必须绑定 target、producer、全部输入、输出与代码身份 |
| INV-03 | verdict、exit code、错误状态与最终进程退出必须一致且 fail-closed |
| INV-04 | partial、stale、失败产物不得留在可被正式消费的位置 |
| INV-05 | data、receipt、error、临时路径必须互异并抗 symlink/alias/TOCTOU |
| INV-06 | 区间、游标、块高、slot、cutoff 必须合法且覆盖闭合 |
| INV-07 | 所有正式 EVM 状态来源必须经过 chain-id attestation |
| INV-08 | accounting、reconciliation、handoff、freeze 必须共享精确 target |
| INV-09 | 网络失败、空响应和不可解析结果不得伪装为“无活动” |
| INV-10 | producer schema 升级必须与 runner、consumer 和存量迁移同步 |
| INV-11 | formal-ready 必须由完整可执行能力闭合导出 |
| INV-12 | READY/A4/A5/release gate 必须是必经路径且不可条件省略 |
| INV-13 | 正式 labels artifact 必须有身份、有效 schema 和有效记录 |
| INV-14 | labels 表、manifest、additions archive 必须属于同一事务 |
| INV-15 | labels 决策字段必须由唯一 canonical parser 解释 |
| INV-16 | 正式使用的数据必须保持正确单位、精度和字段类型 |
| INV-17 | scanner/manifest 的分母必须覆盖实际正式入口和同族调用面 |
| INV-18 | 文档、CLI、schema、registry、测试必须双向一致且单源 |
| INV-19 | runtime、maintenance、archive 路由边界不得互相回流 |
| INV-20 | exploration/nonformal 产物不得重新进入 formal 发布路径 |

## 二、INV → finding 主归并

下表的“primary finding”构成完整且互斥的 49 项分母。`INV-20` 暂无 primary finding，但作为 Robinhood/Multicall 豁免防回流的 secondary 守卫保留；这不构成拆分或合并种子。

| INV | primary finding（按首次出现→后续残留排序） | primary 数 | 主要 secondary 关联 |
|---|---|---:|---|
| INV-01 | `full-F-01` → `six-F-03` → `R7-01` | 3 | `R7-05`、`R8-01`（生产/迁移）；`R7-08`、`R8-06`（必经门禁） |
| INV-02 | `full-F-02` → `R7-03`、`R7-04` | 3 | `R7-13`、`R8-03`、`R8-08`；Robinhood 防回流见 INV-20 |
| INV-03 | `six-F-02`、`six-F-04` → `R7-08` → `R9-03`、`R9-04` | 5 | `six-F-05`～`six-F-08`、`R7-02`、`R8-11` |
| INV-04 | `six-F-05`、`six-F-07`、`six-F-08` | 3 | `R7-06`、`R8-12` |
| INV-05 | `R8-04`、`R8-12` | 2 | `R7-03`、`R7-06` |
| INV-06 | `six-F-06` → `R7-06` → `R8-08` | 3 | `full-F-02`、`R7-03`、`R8-11` |
| INV-07 | `R7-12` → `R8-07`、`R8-09` | 3 | `R8-02`（能力矩阵必须提供 chain id） |
| INV-08 | `six-F-13` → `R7-13` → `R8-03` → `R9-01` | 4 | `R7-03`、`R7-04`、`R8-08`、`R9-02` |
| INV-09 | `R7-02` → `R8-11` | 2 | `six-F-04`、`R8-05` |
| INV-10 | `R7-05` → `R8-01` → `R9-02` | 3 | `full-F-01`、`six-F-03`、`R9-04` |
| INV-11 | `R7-07` → `R8-02` → `R9-05` | 3 | `INV-20`（降级后防回流）；`R9-01` |
| INV-12 | `R8-06` | 1 | `R7-08`、`R7-05`、`full-F-01` |
| INV-13 | `six-F-01` → `R7-09` | 2 | `INV-20`（exploration labels 不得 freeze） |
| INV-14 | `six-F-09` → `R7-10` | 2 | `R7-15`（文档/注册表同步） |
| INV-15 | `six-F-10` → `R7-11`、`R7-14` → `R8-10` | 4 | `R7-15` |
| INV-16 | `full-F-03` | 1 | `full-F-02`、`R8-11` |
| INV-17 | `R8-05` | 1 | 全部正式 producer/transport/entrypoint |
| INV-18 | `full-F-04` → `six-F-11` → `R7-15` | 3 | `R7-05`、`R7-07`、`R8-01`、`R8-02` |
| INV-19 | `six-F-12` | 1 | supplementary `full-C-06`、`full-C-07`、`full-C-08` |
| INV-20 | — | 0 | `full-F-02`、`full-F-03`、`R8-02`；所有 Robinhood/exploration 豁免 |
| **合计** | **49 个互斥 primary finding** | **49** |  |

## 三、六个已确认跨轮同族组

| 同族组 | 沿革（首次出现 → 修复承诺 → 当前残留） | primary INV 解释 |
|---|---|---|
| receipt 真实性 | `full-F-01` / `six-F-03` → `R7-01`（runner 内容绑定）→ `R7-05` / `R8-01`（producer 迁移不闭合）、`R7-08` / `R8-06`（READY 可省） | 执行真实性归 INV-01；生产迁移归 INV-10；必经路径归 INV-12。三者保持可分别验收，不把“有 producer”“有 gate”冒充“真实执行”。 |
| fail-closed | `six-F-02`～`six-F-08` → R7 fail-closed 修复承诺 → `R7-02` / `R7-06` / `R8-11` → `R9-03` pool 进程+stale、`R9-04` supply producer 进程+marker | 退出一致 INV-03、失败产物 INV-04、范围 INV-06、传输语义 INV-09 分账；同属 `FAM-FAIL-CLOSED`。 |
| target 身份 | `full-F-02` → `R7-03` / `R7-04` / `R7-13` → `R8-03` / `R8-08` / `R8-12` → `R9-01` observed slot、`R9-02` plan final block | receipt 绑定 INV-02、共享 target INV-08、cutoff INV-06、路径身份 INV-05、producer/consumer 迁移 INV-10；同属 `FAM-TARGET`。 |
| 链能力 | `R7-07` → 注册表单源修复 → `R8-02` Robinhood formal 但强制 CLI 全拒 → `R9-05` Solana cluster capability 无可执行 attestation | 同一 primary `INV-11`；降级后的 formal 防回流由 INV-20 secondary 接管。 |
| RPC 链身份 | `R7-12`（verify_recon）→ `R8-07`（time_spotcheck sibling）、`R8-09`（totalSupply sibling） | 三项统一 primary `INV-07`，正式 EVM 状态读取必须共用 attested session。 |
| labels 语义 | `six-F-10` → `R7-11` / `R7-14` → `R8-10` | 四项统一 primary `INV-15`，canonical parser 必须覆盖 add/validate/roundtrip/resolver 全同族。 |

## 四、finding → primary INV 反查索引

| 报告 | finding → primary INV |
|---|---|
| full review | `full-F-01→INV-01`; `full-F-02→INV-02`; `full-F-03→INV-16`; `full-F-04→INV-18` |
| six-lens | `six-F-01→INV-13`; `six-F-02→INV-03`; `six-F-03→INV-01`; `six-F-04→INV-03`; `six-F-05→INV-04`; `six-F-06→INV-06`; `six-F-07→INV-04`; `six-F-08→INV-04`; `six-F-09→INV-14`; `six-F-10→INV-15`; `six-F-11→INV-18`; `six-F-12→INV-19`; `six-F-13→INV-08` |
| Round 7 | `R7-01→INV-01`; `R7-02→INV-09`; `R7-03→INV-02`; `R7-04→INV-02`; `R7-05→INV-10`; `R7-06→INV-06`; `R7-07→INV-11`; `R7-08→INV-03`; `R7-09→INV-13`; `R7-10→INV-14`; `R7-11→INV-15`; `R7-12→INV-07`; `R7-13→INV-08`; `R7-14→INV-15`; `R7-15→INV-18` |
| Round 8 | `R8-01→INV-10`; `R8-02→INV-11`; `R8-03→INV-08`; `R8-04→INV-05`; `R8-05→INV-17`; `R8-06→INV-12`; `R8-07→INV-07`; `R8-08→INV-06`; `R8-09→INV-07`; `R8-10→INV-15`; `R8-11→INV-09`; `R8-12→INV-05` |
| Round 9 | `R9-01→INV-08`; `R9-02→INV-10`; `R9-03→INV-03`; `R9-04→INV-03`; `R9-05→INV-11` |

## 五、变更提案

**提案数：0。** 当前 20 个种子足以表达 49 项 primary finding；R9 不拆分或合并。`INV-20` 虽暂为 0 个 primary finding，但它是 Robinhood 降级和所有第四类豁免的自动失效/防回流守卫，不能删除。
