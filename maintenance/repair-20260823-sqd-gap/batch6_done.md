# 批 6 完成记录：v6.52.0 文档／判例／契约／producer／版本／SUITE 收口

## 结论

T1–T9、T11、T12 已按白名单落盘；T10 的业务回归与四类强制 lint 已完成，但**不能宣称全量验收绿**：`run_all.py` 为 125/128 PASS。两项是工单预告的 loopback bind `EPERM`；第三项是本批必须修改 staging 命令、同时明令禁止修改部署副本造成的 deploy-sync 哈希差。验收方同步 `~/.claude/commands/token-analyze-1.md` 后须补跑 deploy-sync；允许 loopback 的环境补跑两项纵切片。

## 开工门禁与边界

- 分支：`fix/sqd-gap-v6520`。
- HEAD：`cca4efb7732e9bd9cc918dcef838d23448890b17`，满足 `cca4efb` 前缀。
- 开工 `git status --short`：无输出。
- 未 commit、未切分支、未联网。
- 未改任何 `scripts/solana` 生产代码、`scripts/report`、既有测试脚本、PLAN/errata 或部署副本。
- `SKILL.md`、`pyproject.toml` 只改版本行；`scripts/lib` 只改白名单 `producer_history.py`。

## 逐任务组结果

### T1 capture.md：完成

- 新增 §13e，冻结 durable-nonce 小区段整笔缺失、最短 1 slot、地图外缺陷和 2026-06-13/15/16 的 38＋2 段实证。
- 写明 HEALTHY／NO_HEADER／DEFECT_CANDIDATE／ERA_UNCERTAIN 四态、“SQD 有块头但零 AdvanceNonce”、参考源 `getBlocks` 前提与线性成本。
- 路由 probe/repair 生产者、coverage/resolution/bundle/pointer/CURRENT、`solana-reconcile/v4`、wrapper v3 和 `edge_source_binding` 到 scan-schemas §14。
- 写明“修过账不退回 base、base 重采即代全作废”、共享地图 TTL 30 天＋逐 slot 复核＋canary、Helius 唯一参考源＋无预算上限但配额耗尽干净停工换 key。
- 写明 Solana A2 五查、coverage 为 exact 强制输入、α/β 止损（β≤3 轮、残差不降即停、禁逐账户 BFS）。
- 七处旧口径同步：base 与修复代 transaction-exact 边界、硬 gate 定位、代/bundle 信任前提、NO_HEADER 的 getBlocks 终审、统一 `edge_sort_key`、SQD/参考源编号不可互比、§15 拼接先正规化。

### T2 其余文档：完成

- `data-pipeline-solana.md`：新增 coverage probe／gap repair 两条路由。
- `split-run.md`：A2 改 EVM 四查／Solana 五查；FAIL 先探针再 α/β；wrapper v3；wave v5／flow v3 与 binding；产物表和 `reconciliation_checks` 键名同步。
- `analyze-workflow.md`：新增 Solana 第五查，wave/flow 升 v5/v3 并绑定 exact receipt。
- `scan-schemas.md`：§1/§2 主体升 v5/v3；新增唯一字段差异段和旧版 fail-closed 重跑提示；§14 wrapper referenced-receipt 结构与实现对齐。
- `environment.md`：Helius key 路径与配额停工语义。
- `scripts/solana/README.md`：探针默认入口／`export-shared-map`、repair `plan/repair/verify` 及真实产物路径。
- `maintenance-review-repair.md`：新增开放式诊断／补证四件套。
- `commands-staging/token-analyze-1.md`：Solana A2 五查范围句；部署副本按工单未动。

### T3 判例 S-12：完成

新增 S-12【机制成立】，覆盖残差指纹、禁止推断、探针＋签名＋连续性二分、证据上限和 §13e 指针。正式勘误撤回“13,425／Meteora-Raydium CPI／218 漏-739 伪影”旧分类；80 块 404 笔按签名复核为 404/404 在 SQD。

### T4 契约 needle：完成

- 基线 175 条＝159 required＋16 banned。
- 新增 14 required＋5 banned；终态 194 条＝173 required＋21 banned。
- snapshot 194 个 ID，排序、唯一性、集合全等均 PASS。
- 新 required 登记在本批实际新增/更正的 capture/split/analyze 权威页，避免与 §14 已有 18 条 `(authority_file, needle)` 重复；最终重复对为 0。

### T5 producer_history：完成

| script | protocol 数 | commit | sha256 |
|---|---:|---|---|
| `sqd_coverage_probe.py` | 2 | `c2372635cf567c451892f828dcb229cdd4dc277d` | `e41370b185aef9bd16fea8ce1abc519a138ee4ce8923bdbc8058d64cdd0619bf` |
| `sqd_gap_repair.py` | 4 | `5782f76773fae0f3b9b036222ad85298992ec840` | `c8beb16e998c5019f6d3cfee0cb14ca163b4dcc3b7d3eb9bdd43fdfd6e44d137` |

六条均为 ACTIVE、六字段齐全，`git show <commit>:<script> | shasum -a 256` 与工作树哈希一致。fetch 两条和 window_fetch 未改。

### T6 SUITE 124→128：完成

`run_all.py` 追加四项：coverage probe、gap repair、reconcile v4 receipt、recon fifth check。机械计数为 128，四项单跑均 PASS。

### T7 版本与 CHANGELOG：完成

- 现役 VERSION／pyproject／SKILL 注释与 CHANGELOG 首索引／首详情一致为 6.52.0；`test_version_consistency.py` PASS。
- 新条目含 coverage＋repair 窄门、正式勘误、SUITE 124→128、wave v5／flow v3／wrapper v3／reconcile v4、EVM `--reseal` 迁移。
- 写入前与写入后 `changelog_lint.py` 均 PASS。
- `6.51.0` 仅在 CHANGELOG 历史索引与历史详情保留 2 处；现役元数据和非历史执行面为 0。改写这两处会破坏版本史，未照字面“全库替换”改史。

### T8 批 5 发现项①：完成

`contracts_draft/reconciliation-report_v3.json` 已把五个 v4 值明确为 `checks.exact_reconcile.receipt` 引用实物里的字段；wrapper item 本体写明 `{status,exit_code,process_exit_code,producer,receipt}`。同一措辞同步 scan-schemas §14。JSON parse PASS；PLAN/errata 未改。

### T9 invariant_manifest：核对完成，无需改文件

- 现有 minimum floors：70 producers／92 consumers／65 transport／56 atomic／61 formal。
- 实现扫描：75／112／65／56／61，exceptions=0，全部覆盖且没有缺登。
- 批 1b 的新增面已在 manifest；本批没有新增生产实现或消费实现，因此不为了追平动态扫描总数抬 floor。

### T10 全量验收：部分闭合

- `changelog_lint.py`：PASS。
- `docs_lint.py --all`：PASS（59 文档）。
- `test_contract_routes.py`（contract scan＋snapshot）：PASS。
- `invariant_scan.py`：PASS。
- 四个新增测试：全部 PASS。
- `run_all.py`：125/128 PASS，exit 1。
  - `test_batch3_solana_vertical_slice.py`：loopback bind `PermissionError: [Errno 1] Operation not permitted`。
  - `test_batch3_evm_vertical_slice.py`：同一 loopback bind EPERM。
  - `test_commands_deploy_sync.py`：staging SHA `c27789d…`，部署副本 SHA `4e205b3…`。本工单既要求改 staging，又明令部署副本由验收方同步、执行方不动；当前会话无法合法消除该差异。

### T11 done 报告：本文件

逐任务、红绿、grep、发现项和未闭合验收均已如实记录。

### T12 绿证归档：完成

`batch6_green_evidence.txt` 已保存开工门禁、docs_lint 红绿、契约/版本/invariant 输出、producer 哈希、关键 grep、四项新测试摘要，以及全量 128 项汇总和三项失败完整根因。SHA-256：`06b76242767045e62a307cebc2dca34b4a79f767879017734dcee59c0a1a6041`。

## 红→绿实拍

加入 banned needle 后：

```text
FAIL: 禁用 needle 回捡 CT-BANNED-17: references/data-pipeline-solana-capture.md → 签名需要时可按该位置反查
FAIL: 禁用 needle 回捡 CT-BANNED-20: references/split-run.md → wave-scan/v4
FAIL: 禁用 needle 回捡 CT-BANNED-21: references/split-run.md → flow-anomaly/v2
```

文档修正后：

```text
PASS: 45 个文档，引用无断链、粗体配对完整
```

## 关键 grep 清零

以下命令均无输出（rg exit 1＝零命中）：

- 旧签名反查句：排除其 banned 定义、maintenance 证据和 archive 后，现役全库 0。
- 旧跨源位置映射句：同上，现役全库 0。
- `reconciliation_four_checks`：references／commands-staging／SKILL 0；仅生产代码读入别名和历史测试保留。
- `wave-scan/v4|flow-anomaly/v2`：split-run 0；scan-schemas 版本差异段、CHANGELOG/maintenance 和旧版拒收测试按工单豁免。
- `6.51.0`：CHANGELOG/maintenance/archive 之外 0。

## 发现项

1. **工单内部验收冲突（未扩改）**：T2 要求修改 `commands-staging/token-analyze-1.md`，边界又禁止修改部署副本；全量 suite 的 deploy-sync 必然红。不是实现回归，但使 T10 “除两个 EPERM 外全 PASS”在本执行边界内不可达。处置已由工单指定：验收方同步部署副本后补跑。
2. **版本 grep 字面冲突（保留历史）**：全库仍有 CHANGELOG 历史 6.51.0 两处。把它们改成 6.52.0 会制造历史错标/版本撞号；按 changelog 历史不可改原则保留，现役版本面已全部 6.52.0。
3. **无 invariant 缺登**：扫描数高于 floors 但 invariant PASS、exceptions=0；未为“数值看齐”擅改 `invariant_manifest.json`。

## 未做与验收方动作

- 未同步 `~/.claude/commands/`，未借临时豁免或修改测试绕过 deploy-sync。
- 未在受限沙箱绕过 loopback 权限；两项纵切片需在允许 bind 的验收环境复跑。
- 未 commit。验收方完成部署同步后依次跑：`python3 scripts/tests/test_commands_deploy_sync.py`、两项 vertical slice、最后 `python3 scripts/tests/run_all.py`。
