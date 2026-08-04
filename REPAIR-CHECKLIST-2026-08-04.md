# token-chip-analysis 6.14.0 修复验收清单

基线：`f7cf198`（6.13.0）  
修复分支：`main`（只 commit，未 push）  
最终版本：6.14.0  
最终全套：`python3 scripts/tests/run_all.py` → **46/46 PASS**（基线 35/35，新增 11 项）

> 执行环境的可写根不包含 `/Users/uravvv/.claude/skills/token-chip-analysis`，因此提交实际落在同基线修复克隆 `/Users/uravvv/Desktop/老公用/fable筹码分析/token-chip-analysis-repair-20260804`。原目标仓库未写入、未 push。根目录旁另有可由目标仓库直接 fetch 的 git bundle。

## 10 项代码问题

| 问题 | 修改文件 | 新增回归测试 | 红证据（6.13.0） | 绿证据 | commit |
|---|---|---|---|---|---|
| P0-01 | `scripts/evm/channels_preflight.py`、`fetch_hypersync.py`、`make_channel_receipt.py`，相关 fixtures/tests | `test_review_20260804_p0.py::collector provenance` | 错 token、单行 block=5 的自报 CSV receipt 仍输出 PASS | collector-native receipt 绑定代码哈希、token/query/bounds/provider/completion/output hash；错 token/旧 receipt BLOCK | `ec04fb6` |
| P0-02 | `scripts/report/reproduce_receipt.py`、`audit_release_gate.py` | `test_review_20260804_p0.py::reproduce freshness` | no-op 复算脚本复用陈旧输出仍 `[PASS] reproduce receipt` | nonce staging、controller 预建 inode、禁止 unlink/replace/symlink/no-op；仅 v2 新鲜 receipt 放行 | `ec04fb6` |
| P1-01 | `fetch_hypersync_v2.py`、`channels_preflight.py` | `test_review_20260804_p101.py` | 同 outdir 中不同 token 的旧 done 因 capture_from 不同被跳过 | `capture_identity.json` 不可变绑定 token/url/query/network/collector hash；合法不重叠续跑保留 | `8a7c670` |
| P1-02 | `scripts/filecoin/fetch_data.py` | `test_review_20260804_p102.py` | 4,999 笔结果无 truncated 语义；实现固定 50 页 | 按 totalCount 翻页，4999/5000/5001/6000 与分页漂移去重均验证；硬 cap 写 truncated/complete=false 后 BLOCK | `91e6f8a` |
| P1-03 | `scripts/filecoin/fetch_data.py` | `test_review_20260804_p103.py` | `--smoke 1` 仍生成正式 `collection_manifest.json` | smoke 仅写 `smoke_receipt.json`、formal=false；正式 top200 必须绑定全部子阶段 PASS receipt | `4f17259` |
| P1-04 | `scripts/report/audit_release_gate.py` | `test_review_20260804_p104.py` | `current_owner_threshold_pct="NaN"` 未产生错误，float/raw 可被截断 | finite Decimal 与精确整数 parser；NaN/Inf/指数/float/bool/负值均 fail-closed | `c62d308` |
| P1-05 | `a4_gate.py`、`audit_release_gate.py`、`build_html.py` | `test_review_20260804_p105.py` | gate 无 profile，调用 `profile=` 直接 TypeError；全新分析被净室资产卡死 | `new-analysis` 与 `independent-audit` 两条必经且不可互换的 seal/build/release profile | `e2d76a0` |
| P1-06 | `a4_gate.py`、`build_html.py` | `test_review_20260804_p106.py` | audit claim 缺一项仍可 finalize PASS | 净室 finalize 逐项对账 id、规范化文本、verdict、证据集合、报告位置并双封口 | `06e47cf` |
| P2-01 | `entity_identity_gate.py`、`labels_resolver.py` | `test_review_20260804_p201.py` | snapshot A=50/B=50，A 为实体成员时 A.share=null；无 total supply/receipt 参数 | identity v3 绑定 owner 全集 receipt 与 total supply，所有 target 回填占比，遗漏 ≥1% owner BLOCK；Arbitrum 可过 G8 | `59a3c7f` |
| P2-02 | `audit_release_gate.py` | `test_review_20260804_p202.py` | 删除 `audit_input_manifest.json` 触发未捕获 `FileNotFoundError`、exit 1、无 JSON | 逐删 11 项 REQUIRED 均 exit 2＋结构化 JSON BLOCK，无 traceback；所有 hash 前验 containment/regular/non-symlink | `8be6d06` |

## 17 项口径漂移

| 漂移 | 收口内容 | 主要文件 | 测试/守护 | commit |
|---|---|---|---|---|
| D-01～D-04 | 支持范围改为明确链矩阵；Filecoin restricted；全新链门禁未齐不得正式发布；new/audit profile 与双 claim 对账成唯一入口；facts/state 归 A3、A4 封口、A5 只写报告 | `SKILL.md`、`analyze-workflow.md`、`independent-audit-protocol.md` | `docs_lint.py --all` semantic contracts | `9179d33` |
| D-05 | 新增唯一 `state_from_facts.py` 编译器；facts 独占实体主键/成员/raw 数字，state_source 只带非重复输入；删手写 15 行拼 state | `state_from_facts.py`、`report-template.md` | `test_state_from_facts.py` | `9179d33` |
| D-06～D-07 | sealed `appendix.json` 可走正式 analysis-new/audit；未 sealed BLOCK；删除两个任何模式都不可达的 skip CLI、G8 误导文字和死分支 | `build_html.py`、`monitoring-package.md` | `test_a4_gate.py` 23 项（含 sealed/unsealed JSON、help 无 skip） | `3c01418` |
| D-08～D-12 | Filecoin 全部改称 restricted/top-200-windowed；同一 analysis-time/window-days 驱动流水、价格、manifest；f00–f0160；pageSize 100/50 全序列 receipt；官方流水 cap fail-closed | Filecoin pipeline、README、`fetch_data.py`、supply recon | `test_review_20260804_filecoin_drifts.py`＋P1-02/P1-03 | `3ade386`（P1-02/03 另见上表） |
| D-13 | G8 总供应、owner 全集快照与 receipt 语义统一；identity v3；Arbitrum 补入链白名单 | identity gate、analyze workflow | `test_review_20260804_p201.py`＋semantic lint | `59a3c7f`、`9179d33` |
| D-14～D-15 | decode 默认 batch 文档改 8；Helius 免费层权威口径改为不支持 batch、账号级 10 RPS，删除 50 RPS/可调大通用声明 | `decode_txs_v2.py`、Solana capture 分册 | py_compile＋Solana integrity＋semantic lint | `9eff3a7` |
| D-16～D-17 | 框架统一命名“三问一异常”；门禁唯一编号 EF-1/2/3、EF-3A/B/C、EF-3C-P1～P4 与 ET-1/2；队列 `collect_manifest` 和链内 `collection_manifest` 分层 | SKILL、analyze/easy/split/report/tiering | `docs_lint.py --all` semantic contracts | `9179d33` |

## Claude 补充三项

- Arbitrum：`entity_identity_gate.CHAINS` 与 label resolver 已加入；GMX/SQD 不再被 G8 白名单卡死（`59a3c7f`）。
- Filecoin cap：沿用 `MAX_RECENT_PAGES` 的 truncated 先例，官方流水 cap 写 `complete=false/truncated=true/complete_reason` 后抛错（`91e6f8a`）。
- G8 死分支：`--skip-identity-gate`、`--skip-a4-gate-reason`、推荐 skip 的 WARN 文本和不可达分支全部删除（`3c01418`）。

## 提交序列

1. `ec04fb6` P0-01/P0-02
2. `8a7c670` P1-01
3. `91e6f8a` P1-02
4. `4f17259` P1-03
5. `c62d308` P1-04
6. `e2d76a0` P1-05
7. `06e47cf` P1-06
8. `59a3c7f` P2-01
9. `8be6d06` P2-02
10. `3c01418` D-06/D-07
11. `3ade386` D-08～D-12
12. `9eff3a7` D-14/D-15
13. `9179d33` D-01～D-05/D-13/D-16/D-17
14. `d9a3478` 6.14.0 版本四件套

## 最终验收

- `python3 scripts/tests/run_all.py`：46/46 PASS。
- `python3 scripts/tests/changelog_lint.py`：PASS。
- `python3 scripts/tests/docs_lint.py --all`：64 个文档 PASS，含 2026-08-04 semantic contracts。
- `python3 scripts/tests/test_version_consistency.py`：6.14.0 PASS。
- `git diff --check`：PASS。
- 未 push；目标 `/Users/uravvv/.claude/skills/token-chip-analysis` 仍停在 `f7cf198`，待在具备该路径写权限的会话中 fetch bundle/fast-forward 后由 Claude 验收。
