# 变异复核消化轮 D1-D4 施工完成报告

日期：2026-08-15

施工目录：`/Users/uravvv/.claude/skills/tca-repair-g1`

状态：**COMPLETE**

本轮完成裁判编号 D1-D4。D2、D3、D4 均先增加或拆分负向测试，在生产代码修改前取得目标红，再修复转绿。用户指定的 14 项回归最终全部 `rc=0`；`invariant_scan.py` 无漂移，不需要 `--dump-actual` 对齐。本轮未执行任何 git 命令。

## 1. 四项消化明细

### D2 / P1：跨分区 token 等式补 state 侧绑定

`audit_release_gate.py` 的正式案 target 等式现会把 `analysis-state.json.token.address` 与 `analysis-state.json.token.mint` 分别纳入 token claims：

- 字段在场即收；两个字段都缺席时不因缺席报错。
- 两字段并存时分别比较，不用 `or` 折叠；值不同会形成 token 声明矛盾。
- EVM 族沿用小写归一；Solana 沿用原串精确比较。
- state claims 与 accounting、reconciliation、shared receipt、identity snapshot receipt 共用同一唯一性检查和统一错误类 `正式发布跨分区 target 不一致`。

测试侧把原 r8 拆成两条独立变异：r8a 只漂移 state，r8b 只漂移 identity receipt。新增 r9 只把 EVM `state.token.address` 换成另一代币，新增 r10 只让 Solana `state.token.mint` 漂移并与正确的 address 冲突；另加 g4 固化 state token 无 address/mint 的存量形态不误伤。

### D3 / P2：adjudication validator 同族 containment

`adjudication_validator.py` 显式安排 `scripts/lib` 导入并统一使用 `case_paths.safe_case_file`。以下动态案内引用已收口：

- `distribution_candidates()` 的 `scan_rel`。
- distribution template/validate 的 `a.out`、`a.adjudications` 和 `--entity-file`。
- pattern validate 的 `a.resolutions`、`source_scan.path` 与逐条 `evidence_refs`。
- candidate template/validate 的 `a.out`、`a.adjudications` 和 `--entity-file`。

直跑 validator 时，`--entity-file` 绝对路径和 `../` 均以非零拒绝。施工中发现当前实物 `handoff_manifest.py` 与工单描述有一处偏差：freeze 子进程当时传的是拼接后的绝对 `ep`，第一次修后回归因此 rc=2。没有放宽 validator，而是把 candidate/distribution 两个子进程调用改传已经过上游 `safe_case_file` 校验的案内相对 `a.entity_file`；最终 freeze/check-unseal 链和 68 项 handoff 回归均通过。

### D1 / P3：本轮 workorder 文档自清

对本轮 9 份既有 `workorder_*.md` 仅做空白字符清理：移除 18 行行尾空格，并把 `workorder_pack1_fix_done.md` 的两个 EOF 换行收敛为一个。未改文字、表格或结论语义。

加入本报告后，对全部 10 份 `workorder_*.md` 做最终字节检查：行尾空格/行尾 tab 零命中，每个文件恰好一个 EOF 换行，无文件末尾多余空行。因全程禁止 git，未运行 `git diff --check`；上述检查直接对文件字节执行。

### D4 / P3：labels 三写入侧稳定错误

- `add_labels.py` 与 `roundtrip_check.py` 的 CLI 外层捕获 `ValueError`，向 stderr 输出 `BLOCK: risk_flags 脏数据: ...` 并以 rc=2 退出。
- `build_labels.py` 是顶层执行脚本、没有可包裹的既有 `main()`；在入口安装专用 uncaught-`ValueError` hook，输出同一稳定 BLOCK 文案并抑制裸 traceback，其他异常仍交还系统默认 hook。
- 新增写入侧真实 CLI 反例：`add_labels.py --dry` 读取内嵌 U+200B 的 risk flag，要求非零、stderr 同时含 `BLOCK` 与 `risk_flags 脏数据`，且不得含 `Traceback`。

## 2. 先红后绿证据

| 项 | 修前真实结果 | 红因 | 修后真实结果 |
|---|---:|---|---:|
| D2 | `test_repair_g1_cross_target.py` rc=1 | r8a、r9、r10 缺统一跨分区 token 错误；r8b 已由 identity receipt 桥独立命中，证明缺口只在 state 侧 | rc=0；r1-r10、g1-g4 全部 PASS |
| D3 | `test_repair_g1_handoff_containment.py` rc=1 | b7 两例中绝对路径和 `../` 均被 validator 以 rc=0 放行 | 最终 rc=0，16/16 PASS |
| D3 链路回波 | 第一次生产修后 rc=1 | validator 已拒绝绝对路径，但 handoff 实物仍把绝对 `ep` 传给子进程，合法 b5 freeze 被阻断 | caller 改传案内相对参数后 rc=0 |
| D4 | `test_repair_g1_risk_flags_pipeline.py` rc=1 | `add_labels.py` rc=1，stderr 为完整 `ValueError` traceback，无稳定 BLOCK | rc=0；写入侧稳定 BLOCK、无 traceback |
| D1 | 修前字节扫描命中 18 行行尾空格，1 文件有 2 个 EOF 换行 | 本轮新产 workorder 文本卫生未收口 | 最终 10 文件行尾空白零命中、EOF 多空行零命中 |

## 3. 指定全回归 rc 表

统一以 `PYTHONDONTWRITEBYTECODE=1` 执行；涉及 Matplotlib 的测试使用可写的 `/private/tmp/mpl-repair-g1` cache。

| 测试 | rc | 结果摘要 |
|---|---:|---|
| `test_repair_g1_cross_target.py` | 0 | r1-r10、g1-g4 PASS；state/identity 独立漂移可区分 |
| `test_repair_g1_handoff_containment.py` | 0 | 16/16 PASS，含 b7 两条 validator 直跑负例 |
| `test_repair_g1_risk_flags_pipeline.py` | 0 | lint、eager consumer、无部分产物、写入 CLI 稳定 BLOCK 全过 |
| `test_audit_release_gate.py` | 0 | 发布闸十一类契约全过 |
| `test_a4_gate.py` | 0 | A4 契约全过 |
| `test_build_html.py` | 0 | 九条 build_html 契约全过 |
| `test_handoff_manifest.py` | 0 | 68 项全过，freeze 子进程相对参数链无回归 |
| `test_repair_batch_d.py` | 0 | `BATCH D 全部通过` |
| `test_review_20260804_p105.py` | 0 | new-analysis / independent-audit profile 边界通过 |
| `test_batch1_risk_flags.py` | 0 | canonical parser、四消费面和 live table 一致 |
| `test_batch2_p3_hardening.py` | 0 | 不可见字符/type、producer symlink、canonical merge 通过 |
| `invariant_scan.py` | 0 | producers=62、consumers=83、transport=63、atomic=52、formal=58、exceptions=0 |
| `docs_lint.py` | 0 | 45 个文档通过 |
| `test_repair_g1_text_hygiene.py` | 0 | 三组变异通过；303 个 active tracked files 零命中 |

本轮指定集合未出现纵切片 loopback `EPERM`；指定集合也不含两条纵切片命令，因此没有把未运行项写成通过。

## 4. Hunk → 裁判项映射

| 文件 / hunk | 裁判项 / 不变量 | 目的 | test owner |
|---|---|---|---|
| `audit_release_gate.py:218-231,281-294` | D2 / state token 在场即比 | 保留 state 双 chain，并把 address/mint 分别加入统一 claims | cross-target r8a/r9/r10/g4 |
| `test_repair_g1_cross_target.py:302-400,451-460` | D2 / 独立归因与防误伤 | 拆 r8a/r8b，新增 r9/r10 与缺席 g4 | D2 先红后绿 |
| `adjudication_validator.py:45-47` | D3 / helper 单源 | 显式导入 `safe_case_file` | handoff containment b7 |
| `adjudication_validator.py:191-268` | D3 / distribution 动态路径 containment | 收口 scan/out/adjudications/entity-file | b7、handoff manifest |
| `adjudication_validator.py:321-369` | D3 / pattern 动态路径 containment | 收口 resolutions/source scan/逐条 evidence refs | handoff containment、既有回归 |
| `adjudication_validator.py:376-420,426-469` | D3 / candidate 动态路径 containment | 收口 template out、adjudications 与 entity-file | b7、freeze 链 |
| `handoff_manifest.py:1263-1277` | D3 / 合法 freeze caller 不误伤 | 两个 validator 子进程传已校验的案内相对 entity-file | handoff 68 项、containment b5 |
| `test_repair_g1_handoff_containment.py:28-42,233-249,325-334` | D3 / 直跑 validator 负例 | 绝对路径与 `../` 必须非零拒绝 | D3 先红后绿 |
| `add_labels.py:230-235` | D4 / 写入 CLI 稳定错误 | 捕获 ValueError，stderr BLOCK，rc=2 | risk flags pipeline |
| `build_labels.py:21-28` | D4 / 顶层构建脚本稳定错误 | uncaught ValueError 转稳定 BLOCK、无裸 traceback | risk flags pipeline + 静态入口复核 |
| `roundtrip_check.py:179-184` | D4 / roundtrip CLI 稳定错误 | 捕获 ValueError，stderr BLOCK，rc=2 | risk flags pipeline + 既有 batch tests |
| `test_repair_g1_risk_flags_pipeline.py:143-169` | D4 / 写入侧真实 CLI 反例 | 锁定非零、BLOCK 文案和无 traceback | D4 先红后绿 |
| `maintenance/repair-20260815-g1/workorder_*.md` 纯空白 hunk | D1 / 本轮文档自清 | 仅移除行尾空白与 EOF 多空行 | 字节扫描 |
| `workorder_digest1_done.md` | 交付 / 可复算施工证据 | 四项明细、红绿证据、回归表、hunk 映射 | 最终空白/EOF 自检 |

未映射施工 hunk：0。

## 5. 最终结论

D1-D4 均已消化，三项生产修复有真实先红后绿证据，D1 有直接字节级零命中证据，指定 14 项回归全部 `rc=0`。没有 manifest 漂移、业务失败或沙箱 EPERM 需要遗留。
