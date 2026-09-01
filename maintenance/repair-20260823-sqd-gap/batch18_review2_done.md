# 批 18 第二轮盲审消化工单 b18r2 — done

日期：2026-08-31
状态：**RED、F1、F2、定向回归与 6.54.2 版本同步全部完成；未 commit；全量 146 项按工单留给验收方本机 nohup。**

## 1. 基线、锚点与边界

- 工单指定代码基线为 `main@8ae0f637e9dcbaba5646416f9cea73d0c020dfeb`（v6.54.1）。开工时 `HEAD=156a78c6b37c4a335d1206bdfdb69fa48fc6b4fa`，其父提交就是指定基线，唯一树差异为新增 `batch18_review2_workorder.md`；验收方已明确批准按等价工作基线处理。
- `DeepReconciliationWitness`、`_reconciliation_bound_files`、签发/消费点及 1179–1330 深验解引用锚均与 8ae0f63 吻合。
- 施工只涉及工单白名单：生产文件 1、既有测试文件 1、版本/CHANGELOG 4、RED/done 2。`handoff_manifest.py`、`audit_release_gate.py`、`scripts/lib`、既有测试断言、ARC 案根和 API key 均未修改。

## 2. 先红证据

原始证据位于 `maintenance/repair-20260823-sqd-gap/batch18_review2_red_evidence.txt`，SHA256：`cc08b53bcd87e5d86cf738b4b1561401200caffbc12cabcc605c51e7b8cfbe18`。该文件在任何生产改动之前生成。

- **F1 target 原地篡改**：真实签发 witness 后执行 `target["as_of_block"] += 1`，基线 `validate_bundle_errors=[]`。
- **F1 receipts 原地篡改**：真实签发 witness 后改 `receipts["supply"]["supply_raw"]`，基线 `validate_bundle_errors=[]`。
- **F2 深层 output 漏绑**：Solana supply observation bundle 本体在旧闭包中，但其顶层 `output` 所指 `supply_snapshot.json` 不在闭包；只改该实物后基线仍为 `validate_bundle_errors=[]`。
- RED 汇总脚本故意以 rc=1 结束，并输出 `BASELINE_VULNERABILITIES_CONFIRMED=true`。

## 3. F1：payload 摘要冻结

- `DeepReconciliationWitness` 新增 `payload_sha256`；为保持既有反伪造直构测试的调用形状兼容，公开直构默认值为空，但空值不能通过正式签发对象的新鲜度检查。
- 签发时把 `(target, receipts)` 按 `sort_keys=True`、`ensure_ascii=False`、`separators=(",", ":")` 序列化为 canonical JSON，再计算 SHA256。
- Solana provider 消费时在对象身份、案根/wrapper、文件闭包检查中一并重算 payload 摘要；任何原地漂移继续统一返回 `reconciliation witness 无效/过期`。
- wrapper 缺失的纯函数夹具仍使用空闭包哨兵，但合法签发流程同样生成 payload 摘要，原行为不变。

## 4. F2：形状驱动递归文件闭包

- `_reconciliation_bound_files` 从 `reconciliation_report.json` 出发做 JSON 文件 BFS。每份 JSON 内递归遍历 dict/list，凡 dict 含字符串 `path` 即分别按案根、当前 JSON 文件父目录尝试解析。
- 候选必须在案根内、词法路径各段无 symlink、resolve 后仍在案根且为当前普通文件；两个基准命中不同文件时全部登记当前 SHA256。
- 新登记的 `.json` 文件继续入队；按绝对路径防环。最多绑定 128 个文件，嵌套最多 64 层，超过即拒签而非截断；JSON 解析失败时保留该文件字节绑定，仅跳过继续递归。
- 取舍：删除 6.54.1 的 `RECON_CHECK_KEYS`＋`inputs/holder_outputs` 手工定向枚举，由 wrapper 出发的通用扫描覆盖；动态 Solana 冻结 bundle 仍显式必收。闭包宁多勿漏，多绑的代价只是 witness 提前过期并在下次 run 重签。

## 5. 测试与版本

`test_batch18_review_digest.py` 只追加两个新测试函数及 main 列表中的两个函数名，既有三组函数和断言未改；`run_all.py` 未改，SUITE 分母保持 146。

| 测试 | 结果 |
|---|---:|
| `test_batch18_review_digest.py` | PASS，5/5（既有 3＋新增 F1/F2） |
| `test_batch18_shared_bundle_witness.py` | PASS，6/6；N11 文案逐字不变 |
| `test_batch15_three_ledgers_frozen.py` | PASS，12/12；N9 `calls==1`、N10 `calls==2` |
| `test_batch18_manifest_stage2_loop.py` | PASS，7/7 |
| `test_handoff_manifest.py` | PASS，68 项 |
| `test_r9_batch3_release_guards.py` | PASS，6/6 |
| `test_reconcile_v4_receipt.py` | PASS，rc=0 |
| `test_repair_batch1.py` | PASS，rc=0 |
| `changelog_lint.py` | PASS，活跃 66＋归档 139 |
| `docs_lint.py --all` | PASS，59 文档 |
| `test_version_consistency.py` | PASS，6.54.2 |

版本五处已同步：`VERSION=6.54.2`、`pyproject.toml=6.54.2`、`SKILL.md:23=6.54.2`、CHANGELOG 索引 6.54.2、CHANGELOG 6.54.2 六栏详情。详情来源明确为批 18 第二轮盲审 P1×2。

## 6. 收尾声明

- `git diff --check`：PASS。
- 白名单外改动：0。
- 既有测试断言改动：0。
- `audit_release_gate.py` / `handoff_manifest.py` / `scripts/lib` 改动：0。
- API key / secret 读取或改动：0。
- commit：未执行。
- 全量 `python3 scripts/tests/run_all.py`：未执行，按工单交由验收方本机 nohup 跑 146/146。
