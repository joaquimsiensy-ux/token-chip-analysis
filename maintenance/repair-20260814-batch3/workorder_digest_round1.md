# 【消化轮 1 工单】盲审 BR1-01/02/03 修复（BR1-04 证据重建由裁判亲自做，不在本单）

> 施工方：codex。**禁一切 git 写命令**（只读 diff/show/log 允许）；只改文件。完成后写 `maintenance/repair-20260814-batch3/workorder_digest_round1_done.md`，末行 WORKORDER_DIGEST_ROUND1_COMPLETE。
> 禁触：`maintenance/repair-20260814-evmobs/`、未跟踪文件 `scripts/tests/test_evm_observation.py`、`archive/**`、`blind-reviews/**`、历史 CHANGELOG 条目、两份 `_meaningful_text` 本体、`shared_release_receipt.py` 约 490 行与 `audit_release_gate.py` 约 839 行的 `schema = receipt.get("schema")` 探测锚行、`maintenance/repair-20260814-batch3/baseline_run_all*.log`（证据文件裁判管）。
> 盲审四条 finding 裁判已逐条独立复验属实（复验输出：BR1-01 三路 rc0/不利产物在盘/finalize 只传两路→PASS 全链绿；BR1-02 假 HOME→SKIP rc0；BR1-03 两伪造副本 failures=[]；BR1-04 baseline log 98 项含 evmobs+尾空格 2 处+invariant 现值 57/76/62/51/58）。

## D1-01（对 BR1-01，P1）：execution ledger 哈希链关死"事后省略 receipt"

### 设计（裁判定案，按此实现，不重开方案讨论）

采 **append-only ledger 哈希链**（复用本仓库 rounds 哈希链已有模式），不采盲审建议的 plan 预冻结（plan 防不了"多跑挑好"且新增受控 producer 面更大；两方案防伪档位相同=防呆+提高伪造成本）。

- **ledger 文件**：case 目录下 `adversarial_review_ledger.jsonl`。每行 JSON：
  `{"schema":"review-ledger/v1","seq":<1 起连续>,"prev_line_sha":<前一行原始字节 sha256，首行 "GENESIS">,"receipt_path":<receipt 文件名>,"receipt_sha":<receipt 文件字节 sha256>,"role":<角色>,"artifact_sha":<artifact 文件字节 sha256>}`
- **写入方**：受控 runner 的 run-role 路径，在 execution receipt 成功落盘后立即 append 一行（O_APPEND 单次 write 原子行）。finalize 不写 ledger。
- **有效集语义**：按 `receipt_path` 取该路径**最后一行**为现行有效（合法重跑覆盖同名 receipt 时 ledger 累积两行，末行有效）。
- **finalize 对账**（在现有 blocker 联动校验之后）：
  1. ledger 缺失或空 → ValueError rc2 不落盘；
  2. 链校验：seq 从 1 连续、每行 prev_line_sha 等于前一行原始字节 sha256 → 断链 rc2；
  3. 集合对账：`{有效集各行 receipt_sha}` 必须与 `{传入 receipts 文件字节 sha256}` **精确相等**——ledger 有而未传（省略不利 receipt，BR1-01 本尊）拒；传了而 ledger 无（未登记 receipt）拒；
  4. 每有效行的 receipt_sha 还须与该行 receipt_path 当前磁盘字节一致（防落账后偷换文件）。
- **aggregate 绑定**：AGGREGATE_SCHEMA 保持 `adversarial-review/v4`（v4 本批新定义、尚无发布存量，同批内修订字段合法），新增必填键 `review_ledger`：`{"entries":<总行数>,"active":<有效集大小>,"tip_sha":<末行原始字节 sha256>}`。
- **消费侧**（shared_release_receipt 与 audit_release_gate 委托的同一 validator）独立重验：ledger 实物存在、链合、entries/active/tip_sha 与 aggregate 绑定一致、有效集 receipt_sha 集合与 aggregate.reviews 所列 receipt 的磁盘字节 sha 集合精确相等。任何一步破 → 硬拒。
- **防伪边界如实写**（文档+done 文件，口径同 R10-17 窄口径纪律）：本修复关死"跑了多路、finalize 时悄悄少传"的**事后省略**面；"同 receipt_path 重跑覆盖不利结果"与"整册 ledger 连同 receipt 全套重造"仍属蓄意伪造面，纯本地文件无外锚不可防（定性同 R10-8 formal_ready 已接受边界）。禁夸大为"完整性证明"。

### 连锁面

- `scripts/report/adversarial_review_runner.py`：run-role 落账 + finalize 对账 + aggregate 新键。
- `scripts/report/shared_release_receipt.py`：validator 补 ledger 重验（注意禁触 490 行锚）。
- `scripts/report/audit_release_gate.py`：保持 100% 委托 shared，确认无需独立改动（若有手抄面须单源化）。
- `scripts/tests/test_repair_batch3_f01.py`：辅助函数 run_role 已是唯一 receipt 生产口的话，存量测试天然带 ledger；逐一排查手工构造 receipt 绕过 run_role 的测试点并适配（手工场景补手工 append 合法行，或改走 run_role）。
- `scripts/tests/test_repair_batch2_f02.py` 等消费侧存量测试：夹具产 aggregate 处补 review_ledger 键与 ledger 文件（排查 refresh_adversarial 类夹具）。
- `scripts/tests/invariant_manifest.json`：`review-ledger/v1` 登记 producer（runner）与 consumer（shared validator）；先跑 `invariant_scan.py` 看现拓扑再登记，精确 diff。
- 文档三件：`references/independent-audit-protocol.md`（ledger 机制+边界句）、`analyze-workflow.md`、`research-workflows.md`（产物清单补 ledger 文件与 aggregate 新键）。保住 f02 文档契约 needle（`"resolved": bool` 精确子串与 scope_terms 原词）。

### 测试（先红后绿，进 test_repair_batch3_f01.py 新 F 族小节）

1. **BR1-01 本尊**：跑 3 路（1 claim + 1 clean critic + 1 bad critic），finalize 只传 2 路 → rc2 不落盘（先红：HEAD 上此场景 PASS，用裁判复验脚本同构造）。
2. 手删 ledger 中间一行 → 链断拒。
3. 手改 ledger 单行内容（链重算前）→ prev_sha 失配拒。
4. 传入 receipts 含 ledger 未登记的合法格式 receipt → 拒。
5. 同 receipt_path 重跑覆盖（clean 覆盖 bad）→ 绿（合法重跑语义，明示边界定位）。
6. ledger 缺失 → finalize 拒。
7. 消费侧独立性：finalize 正常落盘后手抄 aggregate 的 review_ledger.tip_sha 改一位 → shared+audit 双拒；手改 ledger 末行（tip 变）→ 双拒。
8. 绿例：全传全登记 → finalize PASS + 消费全绿。

## D1-02（对 BR1-02，P2）：canonical home 摆脱 HOME 环境变量

- `scripts/tests/test_commands_deploy_sync.py`：canonical 基准目录与 DEPLOYED 根均改用 `pwd.getpwuid(os.getuid()).pw_dir`（系统账户目录，不受进程 HOME 覆盖影响；macOS/POSIX 可用，本仓库无 Windows 面）。`Path.home()` 在本文件内清零。
- 测试（进 `test_repair_batch3_gates.py` F04 小节追加）：
  1. **BR1-02 本尊**：子进程 `env={"HOME": <tmp>}` 跑本脚本，真 canonical checkout 下必须仍走 canonical 分支（本机即 canonical，断言输出不含 SKIP_NON_CANONICAL_CHECKOUT 且 rc 按 deployed 实况；先红:HEAD 上输出 SKIP rc0）。
  2. 纯函数注入面回归保持全绿。

## D1-03（对 BR1-03，P2）：台账守卫解析收紧

改 `scripts/tests/test_repair_batch3_gates.py` 的 `r10_ledger_failures`：

- **状态标记只认第 2 列**（条目名列）：按 `|` 切 cell，标记从 cell[2]（条目名格）提取；其余 cell（一句话/修法线索/状态出处列）出现 `【CLOSED ` 或 `【FIXED_PENDING_REVIEW ` 样式 → FAIL"正文列出现状态样式标记"。注意四、五节表格状态写在第 3 列（"状态与出处"列）——先读真台账确认各节列结构，按节适配列号或统一"每行恰一个状态标记、且必须位于该行首个含标记的合法列"规则，绝不许两列同现标记。
- **裸词 fail-closed**：条目行内出现无全角括号的 `CLOSED \d+\.\d+\.\d+` 或 `FIXED_PENDING_REVIEW \d+\.\d+\.\d+` 字样（不在【】内）→ FAIL"状态字样未按枚举格式"（先红：BR1-03 反例②）。正文叙述"待盲审转 CLOSED"（无版本号）不误伤——先对真台账全文跑一遍确认零误伤再定正则。
- **现役声明收严**：只认 `当前现役\s*=.*?=\s*\*\*(\d+)\*\*` 模式，且**全文件恰一条**；0 条或 ≥2 条 → FAIL（删 last-match-wins 与建档行 fallback；建档行"现役保留/接受项合计 23 条"是历史叙述不再参与对账）。
- 三注入回归（先红）：①正文列插`【CLOSED 9.9.9】`→FAIL；②去括号裸 `CLOSED 6.41.0`→FAIL；③追加第二条"当前现役 = **18**"行→FAIL；真台账绿。裁判复验脚本的两个反例必须转红。

## 验收标准（裁判执行）

- 盲审三个最小反例（BR1-01 省略 receipt / BR1-02 假 HOME / BR1-03 两伪造副本）逐一复跑 → 全部被拒。
- `python3 scripts/tests/test_repair_batch3_f01.py`、`test_repair_batch3_gates.py`、`test_repair_batch2_f02.py`、`test_review_20260804_p105.py`、`invariant_scan.py`、`run_all.py` 全量 rc=0。
- done 文件含：先红清单（每项 HEAD 现象→修后现象）、diff→finding 映射、防伪边界如实句、六视角自审、未修事项如实列。
