# 批 A 完工报告｜split-run 三段化

## 基线与边界

- 工作目录：`/Users/uravvv/.claude/worktrees/tca-splitrun3`
- 分支：`fix/splitrun3-20260818`
- HEAD：`e1be99ab25c0a6f60091d7a7b635ab6097e532c8`
- 未执行 `git commit`，未改部署目录，未运行工单声明预期红的 `test_commands_deploy_sync.py`。
- 施工改动限于工单白名单的 8 个编号条目（实际 9 个物理文件）及工单明确要求的本 done 报告。

## 同族清单（施工前）

- `A4–A5|A4-A5`：4 处，位于 `references/split-run.md` 2 处、`SKILL.md` 1 处、`commands-staging/token-analyze-2.md` 1 处；均按定稿拆分口径处理。
- `四入口`：1 处，仅 `SKILL.md`；未见测试锚定。
- `大户报警深挖`：恰 2 处，位于 `references/split-run.md` 与 `commands-staging/token-analyze-1.md`；已同步拆分为归属定性深挖与观察事实采集。
- `token-analyze-1|token-analyze-2` 测试硬编码：命中 `test_commands_deploy_sync.py` 与 `test_repair_batch3_gates.py`；已按 T8 扩容 `token-analyze-3.md`。

## T1～T8 改动清单

- T1：新建 `commands-staging/token-analyze-3.md`；全文与工单 T1 定稿代码块逐字比对一致。
- T2：`references/split-run.md` 增加 −3 路由、停止线拆分、ET-1 optional 证据包、A5 装配工单、−2 新收口点和 §3b；§3b 与工单 T2.11 定稿代码块逐字比对一致。
- T3：`commands-staging/token-analyze-2.md` 收口前移至报告正文＋装配工单，A5 装配路由到 −3；required/banned 四契约保持成立。
- T4：`commands-staging/token-analyze-1.md` 将报警地址观察事实采集与归属定性深挖分开。
- T5：`SKILL.md` 改为五入口并补 −3；最终 7961 bytes，未超过 8192 bytes。
- T6：`contract_manifest.json` 新增 `CT-SEMANTIC-61`、`CT-SEMANTIC-62`、`CT-BANNED-16`，每条严格五字段。
- T7：`contract_ids_snapshot.json` 按既有字典序同步三个 ID；双向集合由 route 测试验证。
- T8：部署同步期望集合和 batch3 fixture 扩容到 −3；新增缺文件、SHA 不一致、required 缺失、banned 注入四类实际负例。

## 三件套先红后绿实证

### 先红

先只落 T6/T7 三条新契约，保持 `commands-staging/token-analyze-3.md` 不存在，执行：

```text
$ python3 scripts/tests/docs_lint.py --all
FAIL: 权威文件不存在 CT-SEMANTIC-61: commands-staging/token-analyze-3.md
FAIL: 权威文件不存在 CT-SEMANTIC-62: commands-staging/token-analyze-3.md
FAIL: 权威文件不存在 CT-BANNED-16: commands-staging/token-analyze-3.md
exit 1
```

### 后绿

T1 定稿文件落盘后复跑同一命令：

```text
PASS: 59 个文档，引用无断链、粗体配对完整（--all 全量模式）
exit 0
```

### 同族变体与失败分支

`python3 scripts/tests/test_repair_batch3_gates.py` 实际执行并断言以下四个 −3 负例：

```text
ok    F04 −3 deployed 缺 token-analyze-3.md FAIL
ok    F04 −3 SHA 不一致 FAIL
ok    F04 −3 staging required needle 缺失 FAIL
ok    F04 −3 banned needle 注入 FAIL
PASS: 批3 deploy-sync/env-check/R10-ledger gates 回归全部通过
exit 0
```

## 验收输出摘要

- `python3 scripts/tests/docs_lint.py --all`：exit 0；59 个文档全量 PASS。
- `python3 scripts/tests/test_repair_batch3_gates.py`：exit 0；−3 四类负例和原 F04/F05/F07 全部 `ok`，总判定 PASS。
- `python3 scripts/tests/test_contract_routes.py`：exit 0；`R-01/R-02 注册表、ID 快照、五组锚与 SKILL 原子阶段双向闭合`。
- `wc -c SKILL.md`：7961 bytes，满足 ≤8192。
- `references/split-run.md` needle 计数（按验收命令顺序）：`wave_scan_report.json=3`、`flow_anomaly_report.json=3`、`EF-3A/EF-3B=1`、`EF-3C=1`、`provenance_ledger.json=1`、`distribution_scan.json=3`、`handoff/v3=1`、`holder_distribution_current.png=2`、`a4-seal/v4=1`；整组 exit 0。
- `a5-report-seal/v3`：`token-analyze-2.md=1`、`token-analyze-3.md=2`；exit 0。
- `G11`：`token-analyze-3.md=3`；exit 0。
- `三问一异常`：`token-analyze-2.md=1`；exit 0。
- banned 扫描：`banned clean`；exit 0。
- `git diff --check`：exit 0，无输出。
- 定稿机械比对：T1 全文与 T2.11 §3b 均逐字一致。

## 新建内容六视角①②自查

- `token-analyze-3.md`：工单缺失即停；A5 前置件缺失或漂移即停下报用户并退回 −2；渲染/路径/receipt 红灯进入机械自修；涉及数字、实体名或结论措辞则停工退回 −2。模型自检后的继续是工单定稿明确允许的唯一非硬停分支。
- `split-run.md` §3b：bindings 漂移即停问用户；三类修错分别落到自修、带 amendments 的最小机械修正、停工退回 −2；未发现静默继续分支。

## 发现的问题

- 工单“白名单共 8 个”按编号条目计数，但第 8 项含两个测试文件，因此白名单实际为 9 个物理文件；本报告按列出的明确路径执行，未扩展范围。
- “施工任务按序执行”与“三件套要求 T1 文件尚未创建时先落 T6/T7 跑红”存在顺序张力；按更具体、可验证的三件套要求先做 T6/T7 红灯，再回到 T1～T8 施工。
- 未发现剩余实现缺陷或验收阻断。
