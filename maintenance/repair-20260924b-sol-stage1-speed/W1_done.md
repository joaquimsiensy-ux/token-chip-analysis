# W1 完成：已实现共享地图驳回继承、来源绑定和独立拒收校验，指定离线回归通过

按 W1 v4 及用户后续 F-03 夹具裁定施工。版本登记与 producer 登记留给对应工单；本单未修改登记文件，未 commit、push。

**开工门禁与固定基线**

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

```text
W1_BASE=6b36dcdd043d0b2b51c03de9ab0bb555b25f436a

$ git status --short
（无输出，工作区干净）

$ git rev-parse --short HEAD
4a1db37

$ git merge-base --is-ancestor "$W1_BASE" HEAD
（无输出，exit 0）

$ git diff --quiet "$W1_BASE" HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets
（无输出，exit 0）
```

首次修改前，工单所列生产与文档目标锚使用 `grep -n -F -x` 核验，均唯一命中且原行号吻合；未触发基线、锚点或新增探针消费者停工条件。

**施工结果与实际 diff 行号**

下表为最终文件的新行号；`+/-` 是 `git diff --numstat "$W1_BASE" -- <文件>` 的新增/删除行数。

| 文件 | + / - | 实际修改位置与职责 |
|---|---:|---|
| `scripts/solana/sqd_coverage_probe.py` | 130 / 7 | 29、36、38–41：复用 helper；355–356、363–364、617、624：recheck 响应见证及结果；698、706、790–812：原始字节绑定与逐项继承；865–934、963–969：修复来源编排、链式转换、剔除及证据重编号；1117、1129–1130：副本发布清单；1422–1434：副本落盘与分类传参；1545–1547：互斥 CLI |
| `scripts/lib/solana_exact_validate.py` | 352 / 5 | 22、224、247–248、278–281：时效与分类；463–668：完整证据映射、专用 recheck、来源副本及实际复用区间校验；887–891：失败清空继承后重算；1078–1081、1099–1101：资产约束；1281–1406：当前 formal 修复来源绑定；1554：β 状态兼容 |
| `scripts/solana/sqd_gap_repair.py` | 1 / 1 | 585：仅在原状态一致性函数的零 nonce 分支加入新状态，α 拒绝条件保留 |
| `scripts/tests/test_sqd_coverage_probe.py` | 505 / 1 | 12–13、744–1240、1255–1260：动态夹具、六组 W1 回归及 main 登记 |
| `scripts/tests/test_f03_sharedmap_reuse.py` | 25 / 10 | 25–26、52–94、598、764–765、784：按用户裁定修正非法 refuted 夹具及对应数据边界 |
| `scripts/tests/test_sqd_gap_repair.py` | 114 / 0 | 1210–1320、1322–1324：新增自包含 β/base/repaired 回归并登记 |
| `references/scan-schemas.md` | 12 / 2 | 667、669、698–705、715–716：仅 §14.1 相关字段及不变量 |
| `assets/sqd-solana-coverage-map/README.md` | 35 / 0 | 44–45、55–87：证据示例、来源、时效、副本、resume 与残余风险 |

探针新增 130 行、总变动 137 行，未超过原 140 行指标。校验器超过原 120 行指标：新增职责主要为证据形态/完整成员计数、摘要绑定响应的独立解码、来源副本与复用账本交叉校验，以及 CURRENT/bundle/resolution/census 修复来源绑定。复用了 `_integer`、`canonical_json`、`_range_pair`、`merge_ranges`、`_check_file_ref`、`_safe_case_path`、`_repair_ref`、`validate_repair_pointer`、`_repair_state_matches`；普通 counts 覆盖仍走原 `_success_ranges`，没有放宽其规则。未为压行数省略校验。

**继承证明、发布协议与限制**

- 资产副本以 `RawBytes` 经 `publish_exclusive` 在 probe_id 计算前落盘；generation-relative `source_ref` 核大小和摘要，摘要与 shared_map 全等。副本加入幂等比较及 pending 清理清单；文件 fsync、施工目录 fsync、rename 后父目录 fsync、CURRENT 后指针父目录 fsync 沿用原发布路径。未增加 pointer.inputs 或 coverage_map.states。
- recheck 账本保存解码响应 `recheck_response` 和 `recheck_outcome`。独立校验器重算标准查询摘要、响应 canonical JSON 的大小与 SHA-256，再从响应重算块头和 nonce 计数；核完整返回及逐 slot 值。不是仅检查 response_sha256 的格式。跨案边界且 counts_coverage=false 的成功行可证明交集内继承，不扩大 counts 覆盖；实际复用区间另与 map-reuse 账本及本案 counts 摘要绑定。
- 副本证明来源资产声明的成员关系及证据对应，不包含源二进制计数。源 counts=2 由探针加载三件套时核验；跨机校验独立核本案 counts、重查响应及复用区间，仍依赖可信来源。部分继承保留副本完整 evidence；新导出才按最终成员重编号和计数。
- 原始 origin_generated_at 不随链式导出刷新；校验按发布记录的 verified_at 判断 30 天时效。`--no-repair` 仍验证当前修复来源并剔除 confirmed 冲突。refuted-only 无修复发布代时，自有驳回不导出。
- `--resume` 保持原限制：shared_map 为 None，继承丢失，恢复后保守重算为普通候选。已用中断后真实 resume 路径验证。

残余风险已写入文档：驳回继承复用源案的整块签名比对结论，本次只重新验证块头存在且 AdvanceNonce 计数仍为零；该条件不能识别 SQD 在同 slot 增删非 nonce 交易且计数保持零的变化，canary/历史锚/finalized-head 检查也不能消除此风险。本方案依赖来源可信及 SQD 已驳回 slot 的交易集合未发生不可见退化；INHERITED_REFUTED 不代表本案重新证明了完整性。

**§0.7 指定测试：全部 PASS，退出码均为 0**

使用 `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/tests/<文件>`；以下保留各脚本实际尾行。

| 文件 | 尾行 |
|---|---|
| `test_sqd_coverage_probe.py` | `PASS SQD coverage probe: 18/18 offline groups` |
| `test_f03_sharedmap_reuse.py` | `PASS F-03 shared-map reuse: 15/15 groups` |
| `test_batch3_solana_producers.py` | `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards` |
| `test_reconcile_v4_receipt.py` | `GREEN 32 verdict/exit_code/gate_pass 三元互洽` |
| `invariant_scan.py` | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| `test_batch4_invariant_guards.py` | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `test_exemption_guards.py` | `PASS: exemption guards (EX-01 full-F-03)` |

探针 scanner 的消费者集合仍仅为 `{'sqd-solana-shared-coverage-map/v1'}`；无新增消费者，未修改 manifest。`git diff --check` 通过。

**修复相关用例：按函数选择执行，未运行整套入口**

| 文件 / 用例 | 结果 |
|---|---|
| `test_sqd_gap_repair.py::batch3b_mechanism_gate` | PASS；尾行 `PASS test_sqd_gap_repair.batch3b_mechanism_gate` |
| `test_sqd_gap_repair.py::semantic_order_probe` | PASS；尾行 `PASS test_sqd_gap_repair.semantic_order_probe` |
| `test_sqd_gap_repair.py::consumer_repaired_order_regression` | PASS；尾行 `PASS test_sqd_gap_repair.consumer_repaired_order_regression` |
| `test_sqd_gap_repair.py::test_w1_inherited_beta_and_reconcile_paths` | PASS；尾行 `PASS W1 self-contained inherited alpha/beta, base gate, beta formal repair, and repaired gate` |
| `test_sqd_gap_repair.py::functional_repair_regressions` | 未运行，调度方本机补验；读取 `.staging_b3` |
| `test_sqd_gap_repair.py::blocks_cache_end_to_end` | 未运行，调度方本机补验；读取 `.staging_b3` |
| `test_sqd_gap_repair.py::live_mock_transport_regression` | 未运行，调度方本机补验；调用 staged_missing_transactions |
| `test_sqd_gap_repair.py::batch3b_semantic_regressions` | 未运行，调度方本机补验；调用 staged_missing_transactions；其内 adoption_regressions 联动亦未运行 |
| `test_batch8_repair_scale.py::test_key_neutral_identity` | PASS；尾行 `PASS test_batch8_repair_scale.test_key_neutral_identity` |
| `test_batch8_repair_scale.py::test_key_file_precedence` | PASS；尾行 `PASS test_batch8_repair_scale.test_key_file_precedence` |
| `test_batch8_repair_scale.py::test_streaming_structure` | PASS；尾行 `PASS test_batch8_repair_scale.test_streaming_structure` |
| `test_batch8_repair_scale.py::test_sqd_retry_schedule` | PASS；尾行 `PASS test_batch8_repair_scale.test_sqd_retry_schedule` |
| `test_batch8_repair_scale.py::test_concurrent_order_and_hot_failover` | 未运行，调度方本机补验；入口供给的 transactions 来自 `.staging_b3` |
| `test_batch8_repair_scale.py::test_all_quota_receipt_and_cross_key_resume` | 未运行，调度方本机补验；同上 |

两个修复脚本的完整 main 未运行，以免触及上述禁读夹具。`run_all.py`、`docs_lint.py`、`changelog_lint.py` 未运行，**待调度方验收**。

新 β 用例完全使用 tempfile 动态数据，真实执行 formal β 修复及深验，确认 census.coverage_state 为 INHERITED_REFUTED、α 计划为空、β 计划包含该 slot，随后走 repaired 组合判定。因 producer 登记另单，repaired consumer 测试沿用现有测试惯例，仅在测试进程的注册查询处允许当前修复脚本的精确哈希；未跳过 bundle/census 深验，未修改生产登记。此结果不表示正式 producer 登记已完成。

**§1.1 兼容与新增场景证据**

- `test_w1_compatibility_determinism_resume_and_copy_protocol`：直接加载 W1_BASE 分类器，对无继承输入逐项全等比较；验证空继承无新键、基线 producer 哈希产物通过、无 evidence 的空 refuted 旧格式资产通过；冻结时点后两次发布的 probe_id 与 coverage 字节全等；副本相同幂等重发，缺副本或不同副本拒冲突；resume 丢失继承后候选恢复。
- `test_validate_coverage_historical_producer_matrix`：原 F-03 历史 producer 接受/拒绝矩阵继续通过。
- `test_w1_inheritance_and_partial_retry_fallback`：完整继承、部分继承且 evidence.refuted_count 保持来源全量、跨案边界 recheck、失败重试成功、局部未验证剔除、mismatch/canary 整图回退。
- `test_w1_inherited_tamper_rejection`：26 类外层引用同步重绑的负例；含非成员、越界/bool/重复、索引、缺副本、证据不全等、来源过期、fallback、短返回、缺重查，以及修改响应后连同响应摘要重算仍因实测值不符被拒。拒绝理由含 inherited refuted。
- `test_w1_repair_export_binding_and_conflicts`：当前 formal 修复来源、指针路径/大小/摘要/身份、map/schema/producer/census/state/count 负例；互斥 CLI；两种导出选项均剔除 confirmed；no-repair 不旁路损坏来源。
- `test_w1_chain_origin_ttl_and_reindex`、`test_w1_origin_membership_and_export_index_compaction`：两次链式转换、部分成员、原始时效保留、origin_asset_sha256 首次填入后保留，以及剔除后的索引压缩与计数重算。

**§2.6(f) 例外**

用户明确批准修正 `test_f03_sharedmap_reuse.py::_write_asset`，保护回归语义而非非法旧数据。原 `refuted_slots=[171,180]` 的 counts 均为 3，candidate_slots 仅 `[170]`，且没有来源证据；违反新协议的 counts=2、raw 候选成员和来源证据约束。

新夹具保留 refuted slot 身份 `[171,180]`，counts 改为 2，candidate_slots 改为 `[170,171,180]`，补 `refuted_origin=[0,0]` 及 refuted_count=2 的合法 repair-census 证据。为使零 nonce 点通过原 ERA 判据，资产尾部补 9,901 个正常块头，形成 10,000 个同 ERA 块头；案范围仍为 100–199。对应资产上界为 10,100，fixture OLD_HEAD/NEW_HEAD 从 1,000/1,010 调整为 20,000/20,010，以保持资产不越 finalized head 及 head 前进场景。

原三段重查范围、重试次数、局部失败补扫、canary 与 mismatch 回退、跨案边界、历史 producer、main 登记全部保留，未删用例或放宽断言。仅把目标 refuted 点的精确基值断言由 3 改为 2；UNSCANNED 注入改取完整资产二进制，越界注入改用新资产上界+1，确保原拒绝场景不变。最终 15/15 组通过。

**文档字节数与范围核验**

| 文件 | 修改前 | 修改后 | 净增加 |
|---|---:|---:|---:|
| `references/scan-schemas.md` | 106,700 B | 108,815 B | 2,115 B |
| `assets/sqd-solana-coverage-map/README.md` | 2,761 B | 6,436 B | 3,675 B |

文档净增加合计 5,790 B，超过原 1,200 B 指标；用于完整字段示例、逐项原始时效、来源限制、JSON 副本证明边界、响应绑定和用户要求的残余风险原文。

`git diff --stat "$W1_BASE" -- . ':!maintenance'`：

```text
 assets/sqd-solana-coverage-map/README.md  |  35 +++
 references/scan-schemas.md                |  14 +-
 scripts/lib/solana_exact_validate.py      | 357 ++++++++++++++++++++-
 scripts/solana/sqd_coverage_probe.py      | 137 +++++++-
 scripts/solana/sqd_gap_repair.py          |   2 +-
 scripts/tests/test_f03_sharedmap_reuse.py |  35 ++-
 scripts/tests/test_sqd_coverage_probe.py  | 506 +++++++++++++++++++++++++++++-
 scripts/tests/test_sqd_gap_repair.py      | 114 +++++++
 8 files changed, 1174 insertions(+), 26 deletions(-)
```

以上全部属于工单白名单；W3 已提交差异未计入。除此之外仅新增本完成报告。生产修复文件仅改指定函数；未改版本文件、producer_history、manifest、其他生产文件或资产二进制。

**禁读披露**

未读取 `~/.codex/` 或 memories；未读取 archive/、blind-reviews/、`.staging_*`、`.hypothesis/`、references/attic.md、其他 maintenance 历史目录、Desktop 或 Documents。未运行触及这些路径的用例。全程离线；临时夹具使用系统 tempfile；未执行 stash/checkout/reset、创建 worktree 或手动批量删除。
