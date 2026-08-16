# AI-1 Pack 1 fix 阶段施工报告

日期：2026-08-15
范围：F-02、F-11、F-12 生产修复
结论：五项应转绿测试均为 rc=0；真实装机目录未部署，`test_commands_deploy_sync.py` 按计划保持 rc=1，且注入部署夹具的 `test_repair_batch3_gates.py` 为 rc=0。指定防退化与 A4/A5 无关回归全部为 rc=0。

施工期间未执行任何 git 操作，未修改 `scripts/tests/` 下的测试源文件，也未改 `/Users/uravvv/.claude/commands/` 部署副本。

## 文件改动

- `scripts/report/audit_release_gate.py:1171-1172`：`run()` 在 profile 为 `independent-audit` 且 `report is None` 时追加 fail-closed 错误；argparse 的 `--report` 保持可选，未误伤 `new-analysis` 自有分支。
- `references/independent-audit-protocol.md:197`：在发布命令后明文规定独立复核缺 `--report` 即拒，并点明必须重验报告实物与 `claim_registry.report_sha256` 的哈希绑定。
- `commands-staging/token-analyze-2.md:17`：仅把 `A5 seal v2` 替换为带反引号的 `` `a5-report-seal/v3` ``。与未部署副本执行 `diff -u` 只出现该行一个 hunk；未触碰部署副本。
- `scripts/labels/risk_flags.py:5,30-38`：引入正则；保留两端 Unicode 空白/不可见字符裁剪、空段丢弃、去重排序语义；裁剪后非空 token 必须 fullmatch `[a-z0-9-]+`，否则抛出含违规 token `repr` 的 `ValueError`。
- `scripts/labels/validate_labels.py:28,93-103`：逐行捕获 parser 的 `ValueError` 并转为带行号的 `risk_flags 脏字符` 错误；parse 成功后用 `'|'.join(flags)` 复算 canonical，避免第二次进入 parser；脏行置空本行 flags 后继续扫描其余字段和后续行。
- `scripts/labels/labels_resolver.py:138,174`：主表、privacy 子表、EVM fallback 及生成的手工标签 CSV 在装载时 eager 调用 `parse_risk_flags`；任一脏 token 使 `LabelResolver` 构造立即抛 `ValueError`。
- `scripts/labels/label_lookup.py:216-221`：CLI 最外层捕获 `ValueError`，向 stderr 输出稳定的 `BLOCK: risk_flags 脏数据: ...`，并以 rc=2 退出，不暴露 traceback。
- `scripts/evm/analyze_holdings.py`：未修改。resolver 的 eager 校验已使脏库在首个产物落盘前失败，管线负测已证明无部分产物。

## 验证实况

| 命令 | rc | 实况 |
|---|---:|---|
| `python3 scripts/tests/test_repair_g1_audit_report.py` | 0 | F-02 白盒、真实 CLI rc=2、报告哈希不符、防误伤四件套全部 PASS。 |
| `python3 scripts/tests/docs_lint.py` | 0 | PASS：45 个文档，引用无断链、粗体配对完整；authority file 既有 required needles 未破坏。 |
| `python3 scripts/tests/test_batch2_p3_hardening.py` | 0 | PASS：内嵌不可见字符、大写、非 ASCII 等非法 risk_flags 全部 fail-closed。 |
| `python3 scripts/tests/test_batch1_risk_flags.py` | 0 | PASS：canonical parser、四消费面及现库一致；测试内 `checked > 300_000` 全量遍历断言通过。 |
| `python3 scripts/tests/test_repair_g1_risk_flags_pipeline.py` | 0 | PASS：lint 行级报错且继续扫描、resolver eager 拒绝、analyze_holdings 非零且无新产物。 |
| `python3 scripts/tests/test_commands_deploy_sync.py` | 1（预期） | staging SHA 与未部署副本不同；deployed 缺 `a5-report-seal/v3` 且仍含 `A5 seal v2`。这是融合方部署前的指定预期红。 |
| `python3 scripts/tests/test_repair_batch3_gates.py` | 0 | PASS：注入夹具证明双侧同旧文本即使 SHA 相等也被语义层拒绝，deployed banned 与 SHA 双层门禁有效。 |
| `python3 scripts/tests/test_audit_release_gate.py` | 0 | PASS：既有独立复核发布闸全套回归通过。 |
| `python3 scripts/tests/test_contract_routes.py` | 0 | PASS：注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合。 |
| `python3 scripts/tests/test_distribution_gate.py` | 0 | PASS：distribution gate 全套 red-green contract 通过。 |
| `python3 scripts/tests/test_a4_gate.py` | 0 | PASS：A4 gate 契约测试全部通过。 |
| `diff -u /Users/uravvv/.claude/commands/token-analyze-2.md commands-staging/token-analyze-2.md` | 1（有差异） | `diff` 的 rc=1 表示存在差异；输出仅有第 17 行 `A5 seal v2` → `` `a5-report-seal/v3` `` 一个 hunk。 |

F-12 移除未使用的 `canonical_risk_flags` import 后，`test_batch2_p3_hardening.py`、`test_batch1_risk_flags.py`、`test_repair_g1_risk_flags_pipeline.py` 又各复跑一次，最终 rc 均为 0。

## Hunk 映射

| 文件/hunk | invariant | finding | 目的 | test owner |
|---|---|---|---|---|
| `audit_release_gate.py:1171-1172` | independent-audit 没有报告实物不得 PASS | F-02 | 在共享 `run()` 入口按 profile fail-closed，同时保留 argparse 与 new-analysis 合法路径 | `test_repair_g1_audit_report.py` |
| `independent-audit-protocol.md:197` | 操作文档必须明确缺报告即拒 | F-02 | 让权威协议与机器闸一致，消除可选参数被误解为可省略 | `docs_lint.py` |
| `token-analyze-2.md:17` | command A5 schema 必须与现役 producer/validator 的 v3 一致 | F-11 | 清除 staging 现役旧版本串，不越权部署家目录副本 | `docs_lint.py`、`test_commands_deploy_sync.py`、`test_repair_batch3_gates.py` |
| `risk_flags.py:30-38` | 每个非空 token 必须 fullmatch `[a-z0-9-]+` | F-12 | 在唯一 parser 单点拒绝内嵌不可见字符、大小写和非 ASCII 变体，保留边界裁剪兼容性 | `test_batch2_p3_hardening.py`、`test_batch1_risk_flags.py` |
| `validate_labels.py:93-103` | 一条脏记录不得终止全库 lint，也不得二次调用 parser 裸抛 | F-12 | 把 ValueError 转为本行稳定错误并继续扫描 | `test_repair_g1_risk_flags_pipeline.py` |
| `labels_resolver.py:138` | 主库、privacy 与 fallback 的脏 risk_flags 必须在消费前暴露 | F-12 | CSV 装载期 eager 校验，禁止脏 flag 降级为 unknown | `test_batch1_risk_flags.py`、`test_repair_g1_risk_flags_pipeline.py` |
| `labels_resolver.py:174` | 手工生成标签层同属全库 risk_flags 校验范围 | F-12 | 封闭手工 CSV 绕过 eager parser 的同族入口 | `test_batch1_risk_flags.py` |
| `label_lookup.py:216-221` | CLI 对脏库必须稳定 BLOCK、非零退出且无裸 traceback | F-12 | 把 resolver 的 ValueError 转成稳定命令行失败接口 | F-12 CLI 消费面 |

未映射 hunk：0。

## 问题与决策

- 没有发现冻结测试断言错误，因此未触发“报告后停手待裁决”分支。
- `test_commands_deploy_sync.py` 的 rc=1 不是施工失败：真实部署副本按要求冻结未改。逻辑正确性由 `test_repair_batch3_gates.py` 的注入夹具 rc=0 证明，部署留给融合方统一执行。
- resolver eager 校验落在 CSV loader，而不是首次 `risk_partition()`。这样即使脏行从未被地址查询命中，也会在构造阶段拒绝；同时覆盖 privacy、EVM fallback 和生成的手工标签层。
- `validate_labels.py` 在脏行上继续执行其余规则，可能同时报告“tier=risk 无 risk_flags”等次级错误；首要脏字符错误保留违规 token 的 `repr`，且不会妨碍后续行扫描。
- `analyze_holdings.py` 无需最小补丁：真实管线负测已实证 resolver 构造阶段非零退出，四个目标产物均未生成。
