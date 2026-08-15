# 【消化轮 2 工单】盲审 Round 2 BR2-01/BR2-02 修复（2 项 P2）

> 施工方：codex。**禁一切 git 写命令**；只改文件。完成后写 `maintenance/repair-20260814-batch3/workorder_digest_round2_done.md`，末行 WORKORDER_DIGEST_ROUND2_COMPLETE。
> 禁触：同 workorder_digest_round1.md 头部清单（evmobs 目录、test_evm_observation.py、archive/**、blind-reviews/**、历史 CHANGELOG、_meaningful_text 本体、两处 schema 探测锚行、baseline_run_all*.log）。版本件（VERSION/CHANGELOG/SKILL.md）本单不动。
> 两条 finding 裁判已独立复现属实：BR2-01 精确路径复现得 same_inode=True、entries=3/active=3、reviews=2、finalize/shared/audit 全绿；BR2-02 组合反例 failures=[]。

## D2-01（对 BR2-01，P2）：ledger 路径身份归一 + 基数对账

改 `scripts/report/adversarial_review_runner.py` 与 `scripts/report/shared_release_receipt.py`：

1. **实物身份判重**：`validate_review_ledger` 构建 active 表后，对 active 各 receipt_path 的实物做 `(st_dev, st_ino)` 检重——两个不同 receipt_path 字符串指向同一物理文件（macOS 大小写别名、Unicode NFC/NFD 别名均落此）→ ValueError（消息含两个路径名）。
2. **基数对账**（防 SHA set 折叠遮蔽）：
   - finalize 侧：`len(active) == len(active_receipt_sha256s) == len(传入 receipts)`，任何不等 → rc2 不落盘；
   - shared 侧：`len(active) == len(active_receipt_sha256s) == len(aggregate.reviews)`，不等 → 硬拒。
3. **receipt_path 保守语法**：ledger 行校验与 append 入口均要求 basename 匹配 `^[A-Za-z0-9._-]+$`（现役真实用名全部在此集内）；超出（空格、控制字符、非 ASCII）→ ValueError。`_parse_review_ledger_bytes` 与 `append_review_ledger_entry` 两侧同判。
4. 文档补一句（protocol ledger 机制段）：ledger 拒绝多个路径字符串指向同一实物文件，receipt 文件名限受控字符集。

### 测试（先红后绿，进 test_repair_batch3_f01.py F 族追加）

- **BR2-01 本尊**：同 entrypoint/artifact、receipt 参数仅大小写变体跑两次 critic，finalize 传 claim+小写 receipt → 修后 rc2 拒（先红：HEAD 上全绿 entries=3/active=3/reviews=2，裁判复现脚本同构造）。测试须先运行时探测案目录文件系统是否大小写不敏感（写 probe 文件后 samefile 判定）：不敏感 → 断言 alias 拒；敏感 → 断言两 receipt 为独立实物时基数闸生效（active=3 ≠ 传入 2 → rc2，同样是红转绿点）。
- 基数独立反例：手工构造 ledger 与传入集 SHA set 相等但条数不等的场景 → 拒。
- receipt_path 语法负例：含空格文件名 append → 拒。
- 绿例：正常两路全传仍全绿；同精确路径重跑覆盖语义仍绿（消化轮 1 既有测试不回退）。
- 消费侧：alias 场景手抄 aggregate 后 shared/audit 双拒（若 finalize 已拒则构造 shared 侧独立输入验证）。

## D2-02（对 BR2-02，P2）：台账解析器格式收严

改 `scripts/tests/test_repair_batch3_gates.py` 的 `r10_ledger_failures`：

1. **列数精确校验**：每个 R10 条目行必须以 `|` 开头结尾；按所在 section 校验 split 后 cell 数精确等于该节表头列数（先读真台账确认各节列数，硬编码进 section 表）；不匹配 → FAIL"列数与所在节表结构不符"。多插竖线把状态推入新列的输入自然被列数闸抓住。
2. **cell 内竖线**：转义 `\|` 出现在任何 cell → FAIL（本守卫不支持单元格内竖线）。
3. **结构空白限 ASCII**：`R10_ROW_RE` 等结构正则的 `\s` 全部收紧为 `[ \t]`；全角空格 U+3000 出现在结构位（ID cell、分隔位）→ 因不匹配而 FAIL（fail-closed 路径，不得静默跳行）。
4. **statusish 全列扫描**：所有列扫描宽松状态样式变体——`【\s*(CLOSED|FIXED_PENDING_REVIEW)[^】]*】`（\s 含全角空格，用显式字符类 `[ \t　]`）以及裸词变体；命中且不属于该行合法状态列的严格枚举 → FAIL。状态列内非严格枚举形态（如标记内全角空格）继续走既有"不属于枚举"拒绝路径。
5. 表头/分隔行（`|---|` 类）不参与条目解析但参与列数基准提取。

### 测试（先红后绿，进 gates F07 小节追加）

- **BR2-02 本尊组合**：竖线推列+全角空格状态+同步现役数 → FAIL（先红：HEAD 返回 []，裁判复现脚本同构造）。
- `\|` 转义注入 → FAIL。
- 结构位全角空格（`|　R10-1　|`）→ FAIL。
- 正文格插原始 `|`（改变列数）→ FAIL。
- 真台账 27 条全节零误伤 → 绿（回归既有三反例不回退）。

## 验收标准（裁判执行）

- 裁判两个复现脚本（BR2-01 精确路径 / BR2-02 组合注入）复跑 → 均被拒。
- `test_repair_batch3_f01.py`、`test_repair_batch3_gates.py`、`test_repair_batch2_f02.py`、`test_review_20260804_p105.py`、`test_audit_release_gate.py`、`invariant_scan.py`、`run_all.py` 全量 rc=0。
- done 文件含先红清单、diff→finding 映射、六视角自审、未修事项。
