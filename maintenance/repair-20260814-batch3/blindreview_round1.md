# repair-20260814-batch3 对抗性盲审（Round 1）

## 总判定：BLOCK

审查对象冻结为 `83394ab47ebd6e71ae54d83e485cd6e42f3b9349..1da3f225fc38dedf481a2555c6d26329e78f92d7`，逐 hunk 覆盖 30 个 changed files。发现 1 项 P1、3 项 P2。P1 仍允许选择性丢弃不利复核产物后形成 runner/shared/audit 三面 PASS，F-01 的核心不变量未闭合；因此本轮不能把 R10-16 转为 CLOSED，也不能接受 6.43.0 的整体修复结论。

## Findings

### BR1-01 — P1 — F-01 仍可通过省略不利 receipt 绕过 blocker 语义联动

- **所在文件行**：`scripts/report/adversarial_review_runner.py:458-509`；`scripts/report/shared_release_receipt.py:697-747`；`references/analyze-workflow.md:162`；`references/research-workflows.md:113-116`。
- **归因**：老问题修复不全（半修残留）。
- **问题陈述**：`finalize_review` 的 required refs 只从调用者传入的 `receipts` 构建；shared/audit 又只重验 aggregate 自报的 `reviews`。库内没有预先冻结的 review plan/job manifest 来证明应有的全部路次，也不对案内已经成功生成但未被列入 aggregate 的 execution receipt/artifact 做完整性对账。因此可同时跑出 clean critic 与含 finding 的 critic，finalize 时只传 clean critic；不利 artifact 与 receipt 明明在案内，最终仍得到 `release_decision=PASS`，shared 不拒，audit `errors=[]`。这也与文档要求“N 路怀疑者＋完整性批评＋外部异构路全部同批发出，missing 必补跑”的语义断链。现有“两份 artifact 缺一账”测试只覆盖“两份 receipt 都传给 finalize 后少 blocker”，没有覆盖“整份不利 receipt 从输入清单省略”。
- **最小反例 / 验证命令**：

  ```bash
  python3 - <<'PY'
  import json, sys, tempfile
  from pathlib import Path
  sys.path.insert(0, "scripts/tests")
  from test_repair_batch3_f01 import (make_case, claim_artifact, result,
      critic_artifact, run_role, finalize, consume)
  with tempfile.TemporaryDirectory() as td:
      root = Path(td); sha = make_case(root, ("C1",))
      p1, _, r1 = run_role(root, "entity_attribution_skeptic",
          claim_artifact(sha, [result("C1", evidence=["abcdefghij"])]), stem="claim")
      p2, _, r2 = run_role(root, "completeness_critic", critic_artifact(sha), stem="clean")
      bad = critic_artifact(sha); bad["findings"] = ["UNFAVORABLE FINDING"]
      p3, a3, r3 = run_role(root, "completeness_critic", bad, stem="bad")
      pf = finalize(root, [r1, r2])  # 故意不传 r3
      data = json.loads((root / "adversarial_review.json").read_text())
      shared_msg, audit_errors = consume(root)
      print(p1.returncode, p2.returncode, p3.returncode, a3.exists(), r3.exists(),
            pf.returncode, data["release_decision"], shared_msg, audit_errors)
  PY
  ```

  本次实测输出的关键值为：三路 rc 均 0、不利 artifact/receipt 均存在、finalize rc=0、decision=`PASS`、shared 空错误、audit `[]`。
- **建议**：在 fan-out 前由受控 producer 原子生成并冻结 `adversarial-review-plan`（至少绑定当前 registry、预期 role/路数、entrypoint、artifact 与 execution receipt 路径）；finalize 必须按该 plan 做 expected receipts 与实际 receipts 的精确集合对账，aggregate 绑定 plan ref；shared/audit 从 plan 实物独立重建同一 expected 集。不要用“扫描目录里所有 `*_execution.json`”替代，因为旧残留和改名文件会产生新的歧义。补“成功生成一份不利 receipt 后省略该 receipt”在 finalize 与两个消费侧的回归。

### BR1-02 — P2 — F-04 canonical 判定仍可被 `HOME` 改写为 rc0 SKIP

- **所在文件行**：`scripts/tests/test_commands_deploy_sync.py:11-12,29-33,65-71`；对应工单承诺 `maintenance/repair-20260814-batch3/workorder_F04.md:21-23`。
- **归因**：老问题修复不全（半修残留）。
- **问题陈述**：工单明确要求 canonical 判定“不用环境变量”，实现却以 `Path.home()` 同时构造 `DEPLOYED` 与 canonical 路径；在 POSIX/macOS 上该值受进程 `HOME` 影响。即使脚本实际位于真实规范路径 `/Users/uravvv/.claude/skills/token-chip-analysis`，只要启动时覆盖 `HOME`，就会把真实 canonical checkout 误判为 non-canonical；新的唯一 rc0 SKIP 分支随即成为原缺目录假绿的等价逃逸口。`resolve()` 只规范化结果路径，不能恢复可信 home 来源。
- **最小反例 / 验证命令**：

  ```bash
  tmp_home=$(mktemp -d /tmp/blind-f04-home.XXXXXX)
  HOME="$tmp_home" python3 scripts/tests/test_commands_deploy_sync.py
  echo $?
  ```

  本次在真实 canonical checkout 实测输出 `SKIP_NON_CANONICAL_CHECKOUT: /Users/uravvv/.claude/skills/token-chip-analysis`，退出码 0。
- **建议**：canonical home 使用不受 `HOME` 覆盖影响的系统账户目录（macOS/POSIX 可用 `pwd.getpwuid(os.getuid()).pw_dir`）或受控配置锚；同时将 SKIP 改为需要显式 opt-in 的非发布模式，正式 run_all/pre-commit 路径不得把 SKIP 当 PASS。补“真实 canonical root＋伪 HOME＋缺 deployed”必须 rc1 的回归，并保留 symlink/`..` 路径规范化负测。

### BR1-03 — P2 — F-07 守卫可把正文伪标记当状态，也会把枚举外 CLOSED 当 OPEN

- **所在文件行**：`scripts/tests/test_repair_batch3_gates.py:19-26,285-336`。
- **归因**：修复中新引入。
- **问题陈述**：守卫没有解析 Markdown 表格的状态所在列，而是在整行执行 `R10_STATUS_RE.findall`；任何说明文字、代码示例或引用里的合法形态 `【CLOSED x.y.z】` 都会被计作该条真实状态。反向地，`CLOSED x.y.z`、`FIXED_PENDING_REVIEW ...` 等无全角括号的枚举外状态完全不进入 `R10_ANY_MARKER_RE`，被静默归为 OPEN。现役声明也采用全文件多匹配后 `declared_active[-1]`，可由后置说明行操纵。故“状态枚举 fail-closed＋计数一致”可以在语义错误的台账上假绿。
- **最小反例 / 验证命令**：调用 `test_repair_batch3_gates.r10_ledger_failures()` 对两份 `/tmp` 副本验证：①在 R10-8 条目正文插入“代码示例 `【CLOSED 9.9.9】`，不是状态”，把当前现役 19 改为 18；②把 R10-1 的 `【CLOSED 6.41.0】` 改为无括号 `CLOSED 6.41.0`，把当前现役改为 20。本次两份返回值均为 `[]`。
- **建议**：把状态放入独立、固定列并按 Markdown 单元格精确解析；该单元格必须是 `OPEN|CLOSED x.y.z|FIXED_PENDING_REVIEW x.y.z 批N` 之一，正文其他列出现状态样式应拒绝或忽略但不得计数。第六节当前声明必须限定 section、要求恰好一条，不得 last-match-wins。更稳妥的是把 R10 状态迁到机器可读 JSON/TOML，Markdown 由机器表生成。补上述三类破坏性注入回归。

### BR1-04 — P2 — 基线与完工证据仍绑定 rebase 前的 evmobs 状态，且“diff --check 全绿”可证伪

- **所在文件行**：`maintenance/repair-20260814-batch3/plan.md:3`；`maintenance/repair-20260814-batch3/baseline_run_all.log:43,61,99-102`；`maintenance/repair-20260814-batch3/workorder_F01_done.md:59-61,80-90`；`maintenance/repair-20260814-batch3/workorder_closeout_done.md:25-32`。
- **归因**：修复中新引入（rebase 后证据未重绑/收口记录漂移）。
- **问题陈述**：plan 已承认开工误从 evmobs tip `411bf18` 切出后才 rebase 到 `83394ab`，但 `baseline_run_all.log` 没有随基线重建：文件中共有 98 条 suite 行且第 99 行包含禁触并行项 `test_evm_observation.py`，不是 CHANGELOG/closeout 所称的 `main@83394ab` 97 项基线。F01 done 记录的 invariant 计数是 `59/77/63/52` 且声称全量包含 evmobs；最终分支本次实跑为 `57/76/62/51`，证明该段仍是 rebase 前证据。另 `git diff --check 83394ab..HEAD` 实际在 baseline log 第 43、61 行报 trailing whitespace，直接反驳两个 done 文件的“diff --check exit 0/无空白错误”。测试与修复又在同一 commit 落盘，git 历史不能独立证明“测试文件先存在且先红”的时间顺序；旧实现确实具备所述缺口，但记录的执行顺序只能视为自报。
- **最小反例 / 验证命令**：

  ```bash
  rg -c '^\s+PASS  ' maintenance/repair-20260814-batch3/baseline_run_all.log
  rg -n 'test_evm_observation.py' maintenance/repair-20260814-batch3/baseline_run_all.log
  python3 scripts/tests/invariant_scan.py
  git diff --check 83394ab..HEAD
  ```

  本次输出分别证明：98 条、存在 evmobs 项、final invariant 为 `57/76/62/51/58`、两处 trailing whitespace。
- **建议**：在 exact parent `83394ab` 与 exact candidate `1da3f22` 分别重建证据，日志首部写入 commit SHA、完整 SUITE 清单哈希、命令、rc、环境边界；rebase 后使旧日志显式标记 STALE，不得继续作为 main 基线。若要证明先红，保存 test-only patch/hash 或独立 test-only commit/不可变执行记录，再保存绿态；完工记录只能引用与最终分支一致的计数。修正两处尾空格后再宣称 `git diff --check` 通过。

## 已验证但未形成额外 finding 的项目

- **F-01 已覆盖面**：对于已经列入 receipts/reviews 的 artifact，findings、non_covered、REFUTED 的缺账、幽灵账、重复账、多 artifact 同文项均会被 runner 与 shared/audit 拒；把非 manual 项手抄改为 manual 不能绕过。相同 entrypoint 字节跨角色会被两侧拒绝。v2/v3 aggregate 均给出 v4 重跑路径，v1 artifact 不能进入 v4。9 个白名单字符与“9 实义＋零宽”被拒；纯 10 标点按工单明示的“防呆不防伪”边界放行，不另计 finding。
- **F-04 已覆盖面**：旧 `MIGRATION_CHANGED`/`MIGRATION_NEEDLES` 旁路已删除；在未触发 SKIP 的情况下，三份 staging/deployed 文件逐 SHA-256 严格比较，缺文件和一字节漂移均拒。symlink/realpath 解析未发现另一个独立假绿，但 `HOME` 信任问题足以击穿 canonical 分支。
- **F-05**：实查 `env_check.py` 的 pyproject 全直接依赖机械派生、PEP 503 规范化、direct→唯一 lock pin→installed 原文全等、pin 数字下限、非白名单说明符 fail-closed、requires-python；真实环境 21/21 通过。未发现本批承诺内的假绿。平面 lock 无法区分多余传递 pin 与已删直接依赖残留，已在工单如实列为边界。
- **文档与 schema**：`independent-audit-protocol.md`、`analyze-workflow.md`、`research-workflows.md` 的 v4/artifact-v2、10 字符、blocker 四键与迁移文字和当前代码一致；BR1-01 所述“应有路次集合无机器绑定”是主要断契约。`invariant_manifest.json` 与实际扫描相符，`python3 scripts/tests/invariant_scan.py` rc0。
- **diff 映射**：除 BR1-04 的证据失配外，30 个 changed files 的业务/测试/文档/版本 hunk 均可映射到 F-01、F-04、F-05、F-07 或批准的开工/收口动作；未发现额外业务功能混入。
- **测试**：F01、F04/F05/F07、F02、invariant、audit、batch D 定向套件均通过。全量 `run_all.py` 的 99 项中，沙箱内 97 项 PASS；仅两个 loopback vertical slice 因 `socket.bind(127.0.0.1)` 权限失败。随后在允许 loopback 的环境按原命令复跑，Solana 与 EVM vertical slice 均 PASS、rc0。绿测不覆盖 BR1-01/02/03 的新反例。

BLINDREVIEW_ROUND1_COMPLETE
