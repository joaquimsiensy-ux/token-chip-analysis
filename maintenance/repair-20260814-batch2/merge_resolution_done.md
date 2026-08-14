# 批 2 合并冲突解决完工记录：6.42.0

施工分支：`repair-20260814-batch2`。批 2 原 HEAD：`bacfdf4`；合入基线：
`origin/main` 的批 1 merge commit `4a172a0`。两批共同祖先为 `c41ed07`。
本次只编辑文件内容；未执行 `git add/commit/merge/checkout/reset/restore/stash`
或任何其他 git 写命令。

## 一、6 个冲突文件、8 个冲突块的融合决策

### 1. `CHANGELOG.md`（2 块）

- 索引块保留批 1 的 `6.41.0` 原条目；批 2 让号为 `6.42.0` 并置于其上。
- 详情块完整保留两批各自正文，批 2 标题与冻结基线标注改为 `6.42.0`，批 1
  `6.41.0` 正文不改写。
- 批 2 独立分支的 96 项终验被明确记为“6.42.0 前身冻结基线”；合并后的最终分母
  另以本记录的 97 项实跑为准，避免把旧分母冒充最终融合树。

### 2. `references/analyze-workflow.md`（1 块）

- 保留批 2 的 F-10 三段容差政策、四值最大值定区、严格数值解析、
  `over-cap-approval/v1`、30 天有效期、实义文本与用户批复要求。
- 同时嵌入批 1 的 RV-07 真 FAIL 语义：同 target/schema 家族旧 PASS 先以同目录
  hard-link 归档为 `.superseded-<UTC微秒>.<PID>`，再原子替换 canonical，FAIL 仍为
  exit 2；政策拒绝的旧收据改名归档与 exit 1/2 分层继续保留。
- 两段不是二选一：前者定义放行凭据，后者定义失败发布与旧 PASS 处置顺序。

### 3. `references/scan-schemas.md`（1 块）

- 保留批 1 的 fig1 迁移边界：旧案重绘只允许 `CAMP_ORDER` legacy 键，fig1 入口仍由
  `select_fig1_series()` 白名单硬拒白名单外键，禁止静默漏图。
- 保留批 2 的 Solana 迁移边界：重编译必须补
  `source.json.token.data_cutoff_slot`，且与 reconcile window、snapshot cutoff 同源；
  来源不一致时停止，不得任选值补填。

### 4. `scripts/lib/supply_truth_gate.py`（1 块）

- 同时保留批 2 的 `OVER_CAP_APPROVAL_SCHEMA = "over-cap-approval/v1"` 与批 1 的
  `SCHEMA_FAMILY = "supply-truth-receipt/"`。
- 两个常量职责独立：前者约束超顶批准件，后者约束 supersede 的 receipt 家族；未削弱
  `_meaningful_text` 正向白名单、非有限数拒绝、evidence 内容身份或四值闸。

### 5. `scripts/report/audit_release_gate.py`（2 块）

- 函数块保留批 1 的 `check_figure1_legend_receipt()` 全部语义重算，同时保留批 2
  `check_series_binding(..., expected_target=None)` 的严格签名与发布期 Solana
  reconcile/v3 target、输入和物理 edge SHA 复算。
- 调用块只读取一次 `analysis-state.json`：先以 reconciliation target 调批 2 series
  binding，再以同一 state 调批 1 legend receipt 重算；缺 state 但有 legend receipt
  继续 fail-closed。
- 两层信任根并列生效，没有用任一检查替代另一检查。

### 6. `scripts/tests/run_all.py`（1 块）

- `test_repair_batch1.py` 与 `test_repair_batch2_f02.py` 均保留且去重。
- 顺序按发布先后排列：批 1 `6.41.0` 在前，批 2 `6.42.0` 在后。
- 合并后 `SUITE_COUNT=97`，其中 `test_*.py` 入口 89 个、lint/manifest/env 守卫 8 个。

## 二、跨批夹具接线闭合

首次融合树全量实跑除两项 loopback 环境失败外，发现两处真实正例夹具仍停在另一批
落地前的旧契约；两处都以真实 producer 升级，未删除测试、未手写放行件、未放宽守卫。

1. `scripts/tests/test_repair_batch_c.py`
   - 批 2 的 Solana 同案链原先只生成 figure2；批 1 A5 v3 已把
     `fig1_legend_receipt.json` 设为 new-analysis 必经件。
   - 现改为真实运行 `figures_from_facts.py fig1` 生成
     `charts/final/fig1.png` 与 legend receipt，并把 PNG 纳入报告后再封 A5。
   - 定向结果由 226 增为 **227 checks PASS**。
2. `scripts/tests/test_repair_batch_d.py`
   - B-2 Solana 正例原手写 `solana-reconcile/v2`，被批 2 F-09 的 v3 身份闸正确拒绝。
   - 现使用合法 base58 mint、canonical gzip edges、cache meta、snapshot meta 与 owners，
     真实调用 `replay_edges.cmd_reconcile()` 生成 `solana-reconcile/v3`，再写 sidecar。
   - 换仓负例继续保留；定向结果 **BATCH D 全部通过**。

上述两处表明两批生产守卫可同时成立；不存在必须由裁判二选一的不可兼容语义。

## 三、版本让号清单

以下现役发布标注由批 2 `6.41.0` 让号为 `6.42.0`：

- `VERSION`
- `pyproject.toml` 的 `[project].version`
- `SKILL.md` 的 `skill-version` 注释
- `CHANGELOG.md` 批 2 索引、详情标题与最终融合基线说明
- `maintenance/repair-20260813-sixlens/r10_ledger.md` 的批 2 状态同步标题、
  R10-2/R10-10/R10-11/R10-12 四处 `CLOSED`、批 2 新增登记标题及清账状态

批 1 的 CHANGELOG `6.41.0` 条目与批 1验收档案保持原样。批 2 的 plan/done 历史工单
仍记录其在独立分支上实际完成 `6.41.0` 收口的当时事实，不倒改历史执行记录；当前发布
版本的唯一事实源及现役标注已全部为 `6.42.0`。

## 四、验证证据

### 1. 冲突、语法、版本与静态检查

```text
rg -n '^<<<<<<<|^=======$|^>>>>>>>' .
rc=1，零命中（即冲突标记清零）

python3 -m py_compile scripts/lib/supply_truth_gate.py \
  scripts/report/audit_release_gate.py scripts/tests/run_all.py
rc=0

python3 scripts/tests/test_version_consistency.py
rc=0
PASS: M-03 version metadata consistent at 6.42.0

git diff --check
rc=0，零输出
```

### 2. 用户点名定向测试

```text
python3 scripts/tests/test_repair_batch_a.py
rc=0  PASS batch A F-01/F-02 regressions 44/44

python3 scripts/tests/test_repair_batch2_f02.py
rc=0  PASS workorder B F-02 regressions

python3 scripts/tests/test_repair_batch_c.py
rc=0  PASS: repair batch C (F-05+F-04+fixround1+fixround2) 227 checks

python3 scripts/tests/test_a4_gate.py
rc=0  a4_gate 契约测试全部通过（23 项）
```

补充跨批回归：

```text
python3 scripts/tests/test_repair_batch_d.py
rc=0  BATCH D 全部通过
```

### 3. 全量 suite

受限沙箱首跑在夹具升级前为 94/97 PASS：两项 vertical slice 在首个
`socket.bind(127.0.0.1)` 处 `EPERM`，另一个真实失败是 batch D 的 v2 正例夹具；后者按
第二节升级后定向转绿。

最终在获准 loopback 环境对同一融合树完整重跑：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
rc=0
97/97 PASS
test_batch3_solana_vertical_slice.py PASS B3-SOL-E2E
test_batch3_evm_vertical_slice.py PASS B3-EVM-E2E
test_repair_batch_c.py 227 checks PASS
test_repair_batch_d.py BATCH D 全部通过
test_repair_batch1.py PASS
test_repair_batch2_f02.py PASS
末行：全部通过
```

同轮 `changelog_lint.py`、`docs_lint.py --all`、`invariant_scan.py`、
`test_version_consistency.py` 均 PASS。

## 五、merge 状态说明

`git status --short` 仍把原 6 个冲突路径显示为 `UU`，这是本次严格禁止 `git add` 后
索引尚未由 git 层裁判登记“已解决”的预期状态；六个工作树文件内容已无任何冲突标记，
Python 语法、定向套件、完整 suite 与 `git diff --check` 均已通过。裁判下一步只需按其
权限核对后登记索引并完成 merge，本施工方未越权操作 git 状态。

结论：两批改动已按 union 原则融合，批 2 已让号 `6.42.0`，无守卫削弱、无测试删除、
无未裁决的语义冲突。
