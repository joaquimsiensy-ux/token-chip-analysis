# 工单 C（F-09）完工摘要

## 1. 基线与施工边界

- 分支：`repair-20260814-batch2`
- 冻结 HEAD：`5150d9c9f80d05f4c3bdb935cf7b103fd0788c8b`
- 未执行任何 git 写命令；未执行 `git add/commit/switch/checkout/reset`。
- 开工先将 `maintenance/repair-20260814-batch2/staging-pythia/` 加入 `.gitignore`；
  `git status --short --ignored` 实测该目录为 `!!`。
- PYTHIA 历史案根仅作输入；真实端到端全部在仓库内
  `maintenance/repair-20260814-batch2/staging-pythia/case/` 执行。

## 2. 改动清单

| 文件 | 改动 |
|---|---|
| `.gitignore` | 忽略整棵 `staging-pythia/`，阻断 6.3G 级案数据入 git |
| `scripts/solana/replay_edges.py` | `solana-reconcile/v2→v3`；新增大小写敏感 mint、chain、slot window、edge extrema、同次重放逻辑摘要/行数、producer 指纹、三输入绑定；cache meta 回填实测摘要/行数；JSON 原子发布 |
| `scripts/lib/camp_series_provenance.py` | sol-rows 消费侧只认 v3；独立验证案 target、producer、三输入、snapshot→owners 绑定、window/extrema、edge digest/count；v2 fail-closed 并给重跑指引 |
| `scripts/report/state_from_facts.py` | 编译调用点从 `source.token` 独立传 `chain/mint/data_cutoff_slot` |
| `scripts/report/audit_release_gate.py` | 发布调用点从 `reconciliation_report.target` 独立传 `chain/token/as_of_block` |
| `scripts/tests/test_repair_batch_c.py` | F-09 原反例、同族变体、两调用点、importer 三失败分支；Solana 同一夹具案延链至 figures→A4→A5 |
| `scripts/tests/test_review_resume_integrity.py` | 现有 reconcile 夹具升级为真实 v3 输入形态 |
| `scripts/tests/invariant_manifest.json` | producer/consumer schema 与新增原子写入口登记同步 |
| `references/scan-schemas.md` | v3 字段、独立身份信任根、窗口关系、v2 存量策略同步 |
| `maintenance/repair-20260814-batch2/import_pythia_legacy.py` | 工单内 legacy importer；manifest/边/GPA/camps 全验证后才发布 staging；边文件只建 hard link，拒 symlink |
| `maintenance/repair-20260814-batch2/workorder_C_done.md` | 本完工摘要、测试/端到端/只读证据与六视角自审 |

`contract_ids_snapshot.json` 未含 `solana-reconcile`，无需修改；`test_contract_routes.py` 已通过。

## 3. 同族调用面复核

施工后 `rg` 结果：

- producer：`scripts/solana/replay_edges.py::cmd_reconcile` 唯一；正式 schema 为 `solana-reconcile/v3`。
- consumer：`scripts/lib/camp_series_provenance.py::registry_anchor_check` 唯一。
- 调用点：仅 `state_from_facts.py` 与 `audit_release_gate.py` 两处，均显式传入各自持有的案 target。
- `cmd_reconcile` 直接调用测试两处均已升级；正式代码无遗留旧签名。
- 活跃代码中的 v2 字符串仅作为 `LEGACY_RECONCILE_SCHEMA` 拒绝分支和回归反例；历史 maintenance 台账原文保持不改写。

## 4. 红→绿双跑

### 红证据（修前真实放行）

在 staging 放入另一案可复制的最小 v2 收据，直接调用旧 `registry_anchor_check`：

```text
RED_BYPASS_ACCEPTED maintenance/repair-20260814-batch2/staging-pythia/red-cross-case-reconcile-receipt.json
```

命令 rc=0，证明旧实现只看 `schema=v2 + gate_pass=true`，没有案身份锚。

### 绿证据

| 命令/测试 | 结果 |
|---|---|
| Solana F-09 定向同案链 | rc=0，`SOL_LAYER_A_PASS 27` |
| importer 失败分支定向测试 | rc=0，坏 meta／缺 GPA／逻辑哈希不符＋零 receipt 共 4 项 PASS |
| `python3 scripts/tests/test_review_resume_integrity.py` | rc=0 |
| `python3 scripts/tests/test_repair_batch_c.py` | rc=0，`135 checks` |
| `python3 scripts/tests/invariant_scan.py` | rc=0；producers=55 / consumers=73 / transports=62 / atomic=48 / formal=58 / exceptions=0 |
| `python3 scripts/tests/test_batch4_invariant_guards.py` | rc=0 |
| `python3 scripts/tests/test_contract_routes.py` | rc=0 |
| `python3 scripts/tests/test_audit_release_gate.py` | rc=0 |
| `git diff --check` | rc=0 |
| 沙箱内 `python3 scripts/tests/run_all.py` | rc=1；仅两个 vertical slice 因 `socket.bind(127.0.0.1)` 被沙箱拒绝 `EPERM`，其余全 PASS |
| 沙箱外同一 `run_all.py` 复跑 | **rc=0，全部通过**；Solana/EVM vertical slice 均 PASS |

F-09 绿测覆盖：跨案同净供给收据复制、身份键缺失、mint 不符、仅改大小写、
同 mint 不同 cutoff、meta/owners 快照撕裂、producer path/sha 错、edge digest/count/extrema
改写、v2 旧收据、编译/发布两调用点各自命中、importer 三失败分支。

## 5. 夹具级同案连续链（层 a）

`test_repair_batch_c.py::t_f05_f04_solana_chain` 在同一个
`/private/tmp/c-f09-sol-*` 案目录内依次完成：

1. `replay_edges reconcile(v3)` 与 `evolution`；
2. `state_from_facts --series-source`；
3. `figures_from_facts.py check`，生成 PASS `figure2_check_receipt.json`；
4. `a4_gate register→finalize`，同案封口 state/facts/figure receipt；
5. distribution initial/final/record-round；
6. `a5_report_seal.py` 同案收口。

终点断言：`a5_report_seal.json` 在同一案目录生成；没有第二案、没有复制他案 seal 或图表件。

## 6. PYTHIA 真实案端到端（层 b）

### 6.1 importer 实测

`import_pythia_legacy.py` 实测 PASS：

- collect manifest：mint 原文、gaps=[]、cutoff/front=`436376480`；
- 边：`4,857,654` 行，逻辑 SHA-256
  `11d45c2f0aa0663b564debe5fd065982d913f169d11f3c11b427bf016b1807c7`；
- extrema：first slot `309937871`，last slot `436376438`，落在采集窗口内且末边不强等 cutoff；
- GPA 确定性重放：82,257 raw/unique accounts，38,039 非零账户，38,012 owners；
  owner sum=`998158041739995`，与 supply/manifest 精确闭合；
- camps：只取 `analysis-state.json.whale_groups` 八组，按 `type` 机械聚合成 6 个标准阵营，
  共 131 个互斥地址；未读取 `s2_entity_members.json` 拼装。

首次 importer 在沙箱内到 hard-link 步骤被 `EPERM` 拒绝（rc=2）；获批后用同一命令在
沙箱外重跑 rc=0。该失败发生在事实全验之后、业务产物发布之前；未降级为 copy/symlink。

### 6.2 真实链退出码

| 阶段 | 结果 |
|---|---|
| legacy importer | rc=0，`migration_receipt.json verdict=PASS/exit_code=0` |
| `replay_edges.py reconcile --mint <原文>` | rc=0；负余额 0；38,012/38,012 owner 一致；净供给精确相等 |
| `replay_edges.py evolution --camps camps.json` | rc=0；生成 13,944 个小时点 |
| consumer 复算（load sidecar→数值闸→registry v3→endpoint） | rc=0；`PYTHIA_SERIES_BINDING_PASS`，denominator=`998158041739995`，spec_camps=6 |

### 6.3 staging 产物清单

| 产物 | 字节 | 说明 |
|---|---:|---|
| `migration_receipt.json` | 3,244 | 迁移身份、源/输出指纹、边/GPA/camps 实测 |
| `config.json` / `camps.json` | 120 / 6,944 | 原文 mint 与八组单源转换 |
| `data/soltx-1a4c…0105.jsonl.gz` | 91,315,431 | 与历史边文件同 dev+inode 的 hard link，非 symlink |
| `data/soltx-1a4c…0105.meta.json` | 436 | 当前 `sqd-solana-cache/v3` 迁移 meta |
| `data/holders_owners.json` / `holders_snapshot_meta.json` | 2,155,758 / 771 | GPA 真重放闭合后的 owner 实物与绑定 meta |
| `data/reconcile_receipt.json` | 1,548 | `solana-reconcile/v3`，gate_pass=true |
| `data/replay_final_balances.json` | 2,231,780 | reconcile 末态 |
| `data/camp_share_series.json` / `.provenance.json` | 4,194,178 / 979 | 13,944 小时点与 sidecar |
| `data/effective_balances.json` / `sniper_set.json` | 2,231,780 / 10,782 | evolution 同次重放末态与狙击地址集 |
| `data/source_*` 六件 | 23,992,241 | collect/meta/GPA/snapshot/supply/analysis-state 的隔离实拷；其中 GPA 23,356,478 字节 |

`migration_receipt` 的 importer SHA 与当前脚本 SHA 一致；`reconcile_receipt.producer.sha256`
与当前 `scripts/solana/replay_edges.py` 一致。

## 7. PYTHIA 历史案根零内容改动自证

- 开工 marker 后执行
  `find /Users/uravvv/Documents/5.6筹码分析/PYTHIA分析 -type f -newer <marker> -print`：
  **零输出**。
- 关键 mtime 开工前后相同：案根 `1785598179`、collect manifest `1785567912`、
  analysis-state `1785575006`、GPA/owners `1785509247`、repaired edge `1785566828`、
  legacy meta `1785566835`。
- repaired edge 物理 SHA-256=`cad2c30813cb2d5a3c0a0678915efc9c8cd0001ba34f03b9d97477cb0cfb4360`；
  staging 与源文件 `dev=16777231, inode=33930285, size=91315431, mtime=1785566828` 完全相同。
- 按工单要求创建 hard link 会使该 inode 的 `nlink` 从 1 变 2（ctime/link-count 元数据必然变化），
  但历史目录没有新增/改写文件，源内容、size、mtime 与 SHA 均未变化；没有 symlink。

## 8. 六视角①②自审

### ① 身份字段信任根

- 编译期预期身份来自 `source.token.{chain,mint,data_cutoff_slot}`；发布期独立来自
  `reconciliation_report.target.{chain,token,as_of_block}`；两处都不从 receipt 补空。
- mint 全程按 Solana base58 原文精确比较；生产/消费/F-09 importer 均未调用 `.lower()`。
- `edge_digest/edge_count/extrema` 在 reconcile 同次遍历中实算；摘要/行数回填 cache meta，
  consumer 再对锚，不能只靠 receipt 自报。
- producer path/sha 对当前仓库脚本；soltx meta、owners、snapshot meta 三输入逐件 size/sha
  三验；snapshot 内 `outputs.holders_owners` 再与 receipt 输入全对象相等。
- slot 是窗口主身份；验 `extrema ⊆ collection_window`、`window.to ≤ cutoff`、
  snapshot cutoff 与案 target 相等；没有错误要求 `last_edge.slot == cutoff`。

### ② 失败分支、半成品与只读边界

- v2、缺键、大小写变化、错 mint/cutoff、错 producer、输入撕裂、摘要/行数/extrema 篡改
  全部 fail-closed。
- importer 在任何发布前完成 manifest、边、GPA、camps 四类验证；发布阶段异常时只逐个删除
  明确 staging 路径，不递归删除、不触碰历史案根。
- importer 坏 meta／缺 GPA／逻辑摘要不符三分支均实测拒绝，且无 migration receipt。
- staging 边文件必须 `os.link` 且同 inode；目标在场或 symlink 均拒；没有 copy 降级。
- `.gitignore` 已在开工首项落地，staging 整棵目录被 git 忽略。

## 9. 端到端受阻

无。collect manifest 事实、GPA 重放、reconcile、evolution、消费复算均闭合；没有拼接补件或降级冒充。

## 10. 发现未修

- 本工单范围内无已知未修代码缺口。
- 沙箱内两个 localhost vertical slice 的 `socket.bind EPERM` 属执行环境能力限制；已在获批的
  沙箱外用同一全量命令复跑并全绿，不是业务测试豁免。
- 历史 maintenance 台账中关于 v2 缺身份键的文字是当时审计事实，按历史不改写原则保留；
  活跃代码、登记与 schema 文档已升 v3。
