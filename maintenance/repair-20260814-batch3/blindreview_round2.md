# repair-20260814-batch3 质量回归盲审（Round 2）

## 总判定：CONDITIONAL

审查对象冻结为 `1da3f225fc38dedf481a2555c6d26329e78f92d7..f912c18483252b8901364b8c1db6b7607579e6e6`，逐 hunk 覆盖 15 个 changed files。Round 1 的四个最小反例均已闭合：省略不利 receipt、伪 `HOME`、正文伪状态/裸状态/重复现役声明均被拒；`83394ab` 新基线也与 97 项 suite 对应。另发现 2 项 P2：macOS 大小写别名会使 ledger 的 active 计数与物理 receipt/reviews 数量失真但三侧仍 PASS；R10 解析器仍可把“单元格内竖线＋全角空格状态”静默解释为 OPEN。无 P1，故不作 BLOCK；两项 P2 修复并补回归前不能判 PASS。

## Findings

### BR2-01 — P2 — 大小写别名可让同一物理 receipt 被计成两个 active，集合对账因 SHA 去重仍全绿

- **所在文件行**：`scripts/report/adversarial_review_runner.py:115-118,136-155,640-648`；`scripts/report/shared_release_receipt.py:750-765`；文档声明见 `references/independent-audit-protocol.md:131,170-172`。
- **归因**：BR1-01 修复新增的路径身份边界缺口；未重新打开“省略一份仍在盘的不利 receipt”的 P1 本尊。
- **问题陈述**：active 表以未经文件系统身份归一的 `receipt_path` 字符串为键，而 finalize/shared 又只比较 receipt SHA 的 `set`。默认大小写不敏感的 macOS 文件系统中，`Critic_execution.json` 与 `critic_execution.json` 是同一 inode，但 ledger 把它们当两个 active；两行 receipt 字节相同时，SHA set 又把它们折叠成一个。实测 aggregate 为 `entries=3, active=3`、`reviews=2`，finalize rc0，shared 空错误，audit `[]`。这违反工单“active=当前有效 receipt 集大小”和“精确集合对账”的声明，也使 aggregate 自报的 active 数不再代表实物数量。
- **最小复现**：在大小写不敏感的 `/tmp` 案目录先跑一份 claim；对同一 `critic.py`、同一 `critic.json`、相同 critic 内容依次运行 runner，仅把 receipt 参数从 `Critic_execution.json` 改为 `critic_execution.json`；`stat` 两路径 inode 相同。随后 finalize 只传 claim receipt 与小写 critic receipt。本次实测：三次 run-role rc 均 0、`same_inode=true`、finalize rc0、`review_ledger={entries:3,active:3,...}`、`len(reviews)=2`、shared/audit 全绿。
- **边界补充**：若大小写变体重跑的 artifact 内容不同，旧行 receipt/artifact 绑定会撕裂并拒绝，因此本反例不是未保留的不利物理文件被省略；同路径覆盖不利结果仍属于工单已明示接受的边界。路径 containment 能拒绝 `../escape.json` 与 `nested/receipt.json`，但空格和换行文件名会被当作普通 basename 接受；本次未构成另一条绕过。
- **建议**：ledger 校验时拒绝两个不同字符串路径指向同一当前实物（`os.path.samefile`/`st_dev+st_ino`），并同时要求 `len(active)==len(active_receipt_sha256s)==len(finalize receipts/reviews)`，不得只比 SHA set。为 `receipt_path` 增加无控制字符的保守 basename 语法。补 macOS 大小写别名与 Unicode 规范化别名回归，finalize/shared/audit 三侧都应拒绝。

### BR2-02 — P2 — R10 守卫未校验 Markdown 列形态，竖线与全角空格组合仍可把可见 CLOSED 静默算成 OPEN

- **所在文件行**：`scripts/tests/test_repair_batch3_gates.py:23-32,305-347`。
- **归因**：BR1-03 修复不全（格式 fail-closed 边界未闭合）。
- **问题陈述**：解析器用普通 `line.split("|")`，没有按 section 校验精确列数，也不识别转义竖线；`R10_ROW_RE` 的 `\s*` 还接受全角空格。状态列之外只扫描严格合法的 `R10_STATUS_RE`，不会扫描 `R10_STATUSISH_RE`。因此把状态用额外竖线推入正文列，再把 ASCII 空格改成 U+3000，可使人眼可见的 `【CLOSED　6.41.0】` 被机器当 OPEN，调整现役数后整个守卫返回 `[]`。
- **最小复现**：在真实台账副本中把 R10-1 的 `...静默漏画【CLOSED 6.41.0】` 改成 `...静默漏画 | 【CLOSED　6.41.0】`，并把 `当前现役 ... **19**` 改成 `**20**`，调用 `r10_ledger_failures()`；本次实测返回 `[]`。单独在 R10-1 后置正文格插入原始 `|` 或 `\|` 也返回 `[]`，把 `| R10-1 |` 改成 `|　R10-1　|` 同样返回 `[]`。对照项：状态标记内部单独换成全角空格会拒，合法状态标记出现在两列也会拒，section V 在状态前插原始竖线会拒；行为取决于插入位置而非统一 fail-closed。
- **建议**：按 section 定义精确列数和状态列，使用能区分未转义分隔符与 `\|` 的 Markdown 行解析；若本守卫不准备支持单元格内竖线，就显式拒绝所有 raw/escaped cell pipe。结构空白改用 ASCII `[ \t]`，并在全行所有非状态列扫描 statusish/bare 变体。补“pipe＋全角状态＋同步现役数”的组合反例，而不只补单点反例。

## 四项 finding 闭合复核

### BR1-01：原反例已闭合，新增 P2 见 BR2-01

- 原三路反例重放：claim、clean critic、bad critic 均 rc0，不利 artifact/receipt 在盘；finalize 只传前两路时 rc2，错误为 `review ledger active receipt set differs from finalize receipts`，且 `adversarial_review.json` 不落盘。
- 32 个独立进程同时 append 32 个不同 receipt：全部子进程 rc0，链校验得到 `entries=32, active=32`，seq/prev/tip 一致；`flock` 覆盖读旧链、计算新行和单次 `O_APPEND` 写入的完整临界区。
- finalize 与 shared 使用同一 `validate_review_ledger` 重算链和 active；两侧分别把 active SHA set 与传入 receipts / aggregate reviews SHA set 比较，audit 在 `audit_release_gate.py:846-847` 委托 shared。除 BR2-01 的路径别名/基数缺口外，逻辑等价。
- `review_ledger` aggregate 键严格要求恰好 `entries/active/tip_sha`；`entries`/`active` 使用 `type(...) is int`，bool、float、额外键均拒；tip 大写或改一位因与实物 binding 不等而拒。四类变体均由 shared 与 audit 双拒。
- 案内残留 `.critic_execution.json.tmp.99999` 不在 ledger/传入集合中时 finalize/shared/audit 继续绿；这是“不扫描目录临时残留”的预期语义。若把未登记的正式 receipt 传给 finalize，则集合不等 rc2。
- 同一精确 `receipt_path` 的 bad→clean 受控重跑得到 `entries=3, active=2`，finalize/shared/audit 全绿；与三份文档“旧行保留、同路径末行有效、允许覆盖重跑”的窄口径一致。

### BR1-02：闭合

- `ACCOUNT_HOME` 与默认 canonical 根均来自 `pwd.getpwuid(os.getuid()).pw_dir`；本机 UID 502 映射 `/Users/uravvv`。`HOME` 设为随机目录、空字符串、完全 unset 三种场景均不再触发 SKIP，部署三文件实测 PASS。
- `is_canonical_checkout` 的显式 `home` 参数仍可做纯函数注入，`resolve()` 覆盖 symlink/`..` 规范化；默认路径不读进程环境。若 POSIX 账户数据库不存在当前 UID，导入会抛错而不是返回假 PASS；Windows 不在工单支持面。
- 新回归不是只会跑绿：在 `/tmp` 副本把 `ACCOUNT_HOME` 定向变异回 `Path.home()` 后，`test_repair_batch3_gates.py` rc1，准确失败于 `F04 真实 canonical checkout 不受伪 HOME 改写`，子进程输出 `SKIP_NON_CANONICAL_CHECKOUT`。

### BR1-03：三个原反例闭合，组合格式缺口见 BR2-02

- 真实 `r10_ledger.md` 27 条、R10-1..27 集合、唯一现役声明全绿；section I-IV/IVb 的状态取 cell 2，section V 取 cell 3，真实第四、五节零误伤。
- Round 1 正文合法状态样式、裸 `CLOSED 6.41.0`、第二条当前现役声明分别命中“正文列出现状态样式标记”“状态字样未按枚举格式”“声明必须恰好一条”。
- 定向变异关闭 `if body_markers` 后 gates rc1，正式回归准确转红；但现有测试未覆盖 BR2-02 的组合输入。

### BR1-04：闭合

- `baseline_run_all_83394ab.log:1-5` 的完整 SHA 为 `83394ab47ebd6e71ae54d83e485cd6e42f3b9349`，命令、日期、cwd 齐全；日志含 97 条 PASS、零 `test_evm_observation.py`/evmobs，末行 `# rc=0`。`83394ab` 的 `run_all.py` 静态枚举也恰为 97 项且零禁触项。
- 在排除禁触路径的 `/tmp` exact-commit 副本独立复跑：受限沙箱内 95 项 PASS，仅两条 vertical slice 因 loopback bind EPERM；在允许本机 loopback 的环境按原命令分别复跑，两条均 rc0。因此可独立合成为 97/97 业务通过，与新日志声明一致。
- `br104_evidence_rebuild.md` 如实把旧 `baseline_run_all.log` 定性为 411bf18/evmobs 开工实测的 STALE 名分，修正旧 invariant 数和过宽的 diff-check 宣称，也承认先红时序仅属自报。新日志自身第 48、66 行仍保留 run_all 截断输出的尾空格；`git diff --check` 排除 `*.log` 后代码/文档零错误，故记录中的“证据 log 保真、代码文档无空白错误”口径成立。

## 全局与测试验证

- **diff 授权**：15 个 changed files 均可映射到 Round 1 报告/工单/完工记录、BR1-01 runner/shared/测试/manifest/三文档、BR1-02 deploy-sync 与回归、BR1-03 台账守卫与回归、BR1-04 新基线及修正记录。禁触的 `maintenance/repair-20260814-evmobs/`、`scripts/tests/test_evm_observation.py`、archive、blind-reviews、CHANGELOG、VERSION、SKILL 均无 diff；未发现未授权业务改动。
- **定向测试**：`test_repair_batch3_f01.py`、`test_repair_batch3_gates.py`、`test_repair_batch2_f02.py`、`test_review_20260804_p105.py`、`invariant_scan.py`、`test_audit_release_gate.py` 均 rc0；invariant 为 `58/78/62/51/58, exceptions=0`。
- **变异测试**：①禁用 finalize ledger 集合比较，F01 rc1，省略本尊与未登记 receipt 两项转红；②退回 `Path.home()`，gates rc1；③禁用正文列标记检查，gates rc1。新增测试能命中其声明 owner。BR2-01/02 当前无正式回归，现有 suite 会假绿。
- **全量 suite**：`f912c18` 临时副本共 99 项；受限沙箱 97 PASS、两条 loopback EPERM，允许 loopback 后两条原命令均 PASS，业务口径 99/99。`test_repair_batch2_f02`、`test_review_20260804_p105` 等存量消费链均通过。未执行禁触测试。
- **文档三件**：`independent-audit-protocol.md`、`analyze-workflow.md`、`research-workflows.md` 对 ledger 文件、末行有效、精确 SHA 集、aggregate 三键和“仅防事后省略、不防同路径覆盖/整套重造”的说明与当前主路径一致；BR2-01 是未写明的文件系统别名例外，BR2-02 不涉及这三件。
- **工作树纪律**：所有执行、反例和变异均在 `/tmp/tca-round2.qbGzmg` 与 `/tmp/tca-baseline-83394ab-round2.BcsgMc`；未执行 git 写命令，仓库除本报告外未改文件。

BLINDREVIEW_ROUND2_COMPLETE
