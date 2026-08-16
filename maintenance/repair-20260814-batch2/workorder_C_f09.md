# 工单 C（F-09）：solana-reconcile 身份键（v2→v3）＋Solana 端到端两层

> 批 2 第三单（最重），工单 B 验收合格后开工。总计划见 plan.md「二、F-09」节（含 @CX 四硬坑与分层 window 设计）。
> 施工纪律同前：禁 git 写命令；完成后写 `workorder_C_done.md`。本单产物较多，边做边落盘。

## 0. 背景一句话

`solana-reconcile/v2` 收据零身份键（无 chain/mint/窗口/producer/输入绑定），跨案复制可用；且 Solana 的 state→figures→A4→A5 同案连续链（夹具级）与真实案数据验证（R10-11）均未兑现。

## 1. 不变量

正式序列链上的收据必须携带并被消费侧独立验证链上身份（chain/mint/slot 窗口），跨案复制必拒；消费侧预期身份来自案 target 不来自收据自报；边数据完整性实测（逻辑摘要）不靠声称。

## 2. 同族清单

```
rg -n "solana-reconcile|reconcile_receipt" --glob '!maintenance/**' --glob '!archive/**' --glob '!blind-reviews/**'
```
已知命中：producer `scripts/solana/replay_edges.py:166`（cmd_reconcile）；consumer `scripts/lib/camp_series_provenance.py`（RECONCILE_SCHEMA :380、registry_anchor_check :383 起 sol-rows 分支、endpoint_reconcile sol 分支）；调用点 `scripts/report/state_from_facts.py:156` 与 `scripts/report/audit_release_gate.py:1055`（两处都要接预期身份）；登记 `scripts/tests/invariant_manifest.json:256,300`；测试 `scripts/tests/test_repair_batch_c.py`；文档 `references/scan-schemas.md`。

## 3. 修改内容——第一部分：schema v3 与消费侧

1. producer `cmd_reconcile` 收据升 `solana-reconcile/v3`，新增：
   - `chain:"solana"`；`mint`：base58 **原文原样**（严禁复用 EVM 侧 `.lower()` canonicalization——大小写敏感）；
   - `collection_window:{from_slot,to_slot}`（取自 soltx meta 的采集上界等字段）；`edge_extrema:{first:{slot,ts},last:{slot,ts}}`（重放遍历时顺手取）；
   - `edge_digest`＋`edge_count`：重放同一次遍历中对每条边规范化串（如 `ts|slot|src|dst|amt` 按行）滚动 sha256——零额外 IO；
   - `producer:{path,sha256}`（仿 EVM replay_provenance 模式）；
   - `inputs`：soltx meta.json＋holders_owners.json＋holders_snapshot_meta.json 各 `{path,size,sha256}`。
2. 消费侧 `registry_anchor_check`（camp_series_provenance.py:383）签名扩展：新增预期身份参数（expected_chain/expected_mint，可选 expected_window 上界）；sol-rows 分支验收据 schema=v3＋身份与预期全等＋`gate_pass`；**窗口关系校验**：`edge_extrema ⊆ collection_window`，且 collection_window.to_slot ≤ 快照/target cutoff（**不得要求末边 slot == cutoff**——窗口尾部可以无转账）；slot 是主身份，ts 只作辅助一致性。
3. 两个调用点都接线：`state_from_facts.py:156`（编译时，从其持有的案 target/config 取 chain+mint 传入）；`audit_release_gate.py:1055`（发布时，从发布 target 独立取值传入）——两点各自独立，不得一处传了另一处放空。
4. `endpoint_reconcile` 的净供给交叉（net_supply_raw vs 终态快照合计）保持不动。
5. 存量：v2 收据 fail-closed 拒，错误信息含"重跑 replay_edges reconcile 重新生成 v3 收据"指引。
6. 登记同步：invariant_manifest.json:256,300 两处 v2 串升 v3；contract_ids 快照如有涉及一并；scan-schemas.md 对应段更新。

## 4. 修改内容——第二部分：Solana 端到端两层

### 层 a・夹具级同案连续链（final_acceptance NOTE-1 欠账）

在 test_repair_batch_c.py 的 Solana 链（现止于 compile_state 读 analysis-state.json）基础上延链：同一夹具案继续走 `figures→A4 finalize→A5 seal`，对照件＝`test_repair_batch_d.py::t_fd3_e2e_single_case_evm`（EVM 同案四段贯通的既有实现，照抄结构）。**铁律：同一案目录一条链走到底，禁两案拼接**（上轮终验抓过一次，plan 明令否决的手法）。

### 层 b・真实案级（R10-11，PYTHIA）

数据源：`/Users/uravvv/Documents/5.6筹码分析/PYTHIA分析/`（只读！历史案根零改动）。
工作区：仓库内 `maintenance/repair-20260814-batch2/staging-pythia/`（先在 `.gitignore` 加该路径——6.3G 级数据严禁进 git）。

已知四硬坑与对策（@CX 实核）：
- ①文件名/meta 版本不匹配：现役 replay_edges 要求 `data/soltx-<sha256(mint)>.jsonl.gz`＋`sqd-solana-cache/v3` meta；PYTHIA 实际是 `soltx-<小写mint>-txaware-repaired.jsonl.gz`＋version:2 meta。写 **legacy importer** 脚本（放本工程目录，不进 scripts/ 正式面）：先验证案内 `collect_manifest.json` 既有事实（repaired 边文件路径／逻辑 SHA／行数 4,857,654／cutoff slot 436376480／gaps 空——逐项实测对得上才继续），再在 staging 落现行命名＋v3 meta，并产 `migration_receipt.json` 明示迁移件身份（绑定源文件 sha 与 collect_manifest sha），不冒充原生采集产物。
- ②holders_snapshot_meta.json 重建必须真重放：用 `snapshot_final/gpa_with_context.json`（原始 GPA 响应在盘）做无网络确定性重放重建，与 holders_owners.json 对账闭合后落 meta；**不得**拿 supply.json＋snapshot_manifest.json 包装了事（验自洽≠验真实）。
- ③隔离输出：reconcile/evolution 硬编码写 `data/` 下五个产物——一切在 staging 案目录内跑（cd staging），staging/data/ 下放输入件。大文件（边 gz）用**硬链接**引入（同盘零空间；闸拒 symlink，禁用软链），小文件实拷。
- ④camps 单源：从 PYTHIA `analysis-state.json` 的 whale_groups（八组）按唯一机械规则转换成 camps.json（转换脚本落工程目录＋绑源文件 sha 进 migration_receipt）；不得与 s2_entity_members.json 拼装。

端到端目标链：staging 内 `reconcile(v3)→evolution 产序列＋sidecar→state_from_facts（或 check_series_binding 消费路径）复算过闸`，全链退出码与产物清单写入 `workorder_C_done.md`。
若 collect_manifest 事实验不过或 GPA 重放闭合不了：**停下**，把实测差异写入完工摘要"端到端受阻"节（这属用户裁决点，不得降级拼接冒充）。

## 5. 三件套测试（先红后绿）

a. 原反例：构造两个夹具案净供给相同，把甲案 reconcile 收据（哈希重绑）喂乙案 sidecar → 当前放行（红证据），修后拒。
b. 同族变体：身份键缺失／mint 与预期不符／mint 仅改大小写／同 mint 不同 cutoff／meta 与 owners 分属两快照（inputs sha 撕裂）／producer path 或 sha 错／edge_digest、edge_count、extrema 被改／v2 旧收据。
c. 两调用点各自直测：state_from_facts 路径与 audit_release_gate 路径分别命中身份校验（不允许只测一处）。
d. importer 失败分支：坏 meta／缺 gpa_with_context.json／逻辑哈希对不上 → 三条 fail-closed。
e. 绿例：v3 全链绿；test_repair_batch_c 存量夹具收据升 v3 防误伤；层 a 同案连续链用例入 run_all SUITE；run_all 全绿。

## 6. 六视角①②自审（完工摘要必填）

①身份字段信任根（预期值是否来自调用方案 target 而非收据自身？edge_digest 是否重放实算？）；②失败分支 fail-closed＋staging 半成品零残留＋历史案根零写入（完工摘要附 PYTHIA 案根 mtime 抽查证据）。

## 7. 归因预判

老问题修复不全（批 C 给 EVM 加了 target 三键，Solana 同族未等深）。本单闭合 R10-10/11。

## 8. 验收口径

裁判独立跑：跨案复制反例复现（修后拒）＋test_repair_batch_c rc=0＋层 a 用例 rc=0＋run_all 全绿＋git diff 审＋PYTHIA 案根零改动核查（find -newer 抽查）。
