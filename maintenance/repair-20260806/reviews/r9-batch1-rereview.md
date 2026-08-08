# R9 批一 · 消化增量重审报告

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree`，分支 `fix/r9-closure-20260807`，HEAD `0bb94ba`
- **增量审查区间**：`144c652..0bb94ba`（3 commit：`fa82b32` 生产修复 / `8477e04` 台账 / `0bb94ba` SHA 回填）；13 文件、36 hunk
- **审查角色**：批一消化增量重审员，只读沙箱，与上一轮审查者无关。全程未对 worktree 做任何 git 写操作或文件增删改
- **审查模型身份（如实登记）**：**Claude Opus 5**，模型 ID `claude-opus-5[1m]`，以 Claude Code / Claude Agent SDK 子代理身份运行。
  PLAN-R9 第二节角色表规定批内对抗审查由「Opus 4.8 子代理」执行，并写明不得静默替代。本次实际调度到的仍是 Opus 5（与上轮审查者同型号、不同线程、无上下文继承）。此处**显式登记不做静默替代**，是否接受该替代由裁判/用户裁决。
- **审查日期**：2026-08-07
- **上轮报告**：`/Users/uravvv/Documents/5.6筹码分析/r9-reviews/b1/report.md`（BLOCK，4 项 finding）

---

## 1. 裁决

### **BLOCK**

一句话理由：**B1R-01 未闭合，且是第二次半修残留**——修复把 producer 校验从「随便哪个仓库文件」收窄成「必须写 `scripts/lib/anchor_plan.py` 这个名字」，但这个名字和它的 sha256 都是公开可算的常量，手写方零成本即可满足；我用一份完全手写、producer 声明为真实 `anchor_plan.py` 的 plan+receipt，在 dry-run 与正式路径双双穿透，并在 loopback fake RPC 上**产出了真正的 `time-spotcheck/v2` PASS receipt**（`verdict=PASS`、`mode=formal`、`points=1`、`mismatch=0`），把 A2 时间抽查的覆盖面自选缩水成 1 个必然对得上的锚点。另外三项（B1R-02 启动隔离、B1R-03 信任根、B1R-04 治理条文）经原反例复跑加各自的边界外一步攻击，确认真实闭合。

**上轮 4 项结论**：CLOSED × 3（B1R-02、B1R-03、B1R-04）；**REOPEN × 1（B1R-01，P1）**。

**新 finding 计数**：2 项，均 P3 —— `B1R2-01`（`solana_attested_session.py` 删末尾空行，无主夹带）、`B1R2-02`（登记 producer 路径成为第三份无对账的事实源）。
**严格三分类**：老问题修复不全 1（B1R-01 REOPEN）；修复中新引入 2（B1R2-01、B1R2-02）；历史漏检 0。

**触发 BLOCK 的条件（三条全中）**：① 任一 REOPEN → B1R-01；② 出现半修残留 → B1R-01 属第二次半修残留；③ 出现新引入 → 2 项 P3。按 `references/maintenance-review-repair.md` 第七节 7.1「新引入、半修残留不分严重度，都要修复后重审」，不能放行。

**夹带扫描**：36 hunk 中 **35 个有主、1 个无主**（自报为 0）。无主的是纯空行删除，零语义；但「有 owner 的 hunk 里夹带目的外语义内容」这种上轮出现过的形态，本轮未复现。

**一句公道话**：本次消化在 B1R-02 上做得扎实——公共原语抽取干净、三处消费者语义一致、「先 receipt 后 plan」的顺序设计在部分隔离场景下真的救了场（E3 实测），且 pool/scan 迁移零回归。B1R-03 的收口也彻底，构造口、位置参数、实例属性三条路全断。问题集中在 B1R-01 一处，而它的病根不是粗心，是**把「红测转绿」当成了「不变量闭合」**：新增的两条测试叫「伪造 **Markdown** producer ……在业务前拒绝」，实现也就正好只挡住 Markdown——测试与实现同构，一起绕开了工单原文要求的那件事。

---

## 2. 上轮 4 项逐项闭合结论

| finding | 上轮 severity | 本轮结论 |
|---|---|---|
| B1R-01 consumer 未绑定 producer 身份 | P1 | **REOPEN** |
| B1R-02 `anchor_plan.py` 无 stale 隔离 | P1 | **CLOSED** |
| B1R-03 Solana 信任锚可由调用者覆盖 | P2 | **CLOSED** |
| B1R-04 治理条文被删（无主改动） | P3 | **CLOSED** |

---

### B1R-01 → **REOPEN**（P1，老问题修复不全：第二次半修残留）

**修复方做了什么**：`scripts/lib/time_spotcheck.py` 新增常量 `EXPECTED_PLAN_PRODUCER = "scripts/lib/anchor_plan.py"`，在 `load_validated_plan` 中把 `receipt.producer.path` 用 `os.path.normpath` 词法归一化后，要求精确等于该常量。

**为什么没闭合**：这道新闸要求的两个值——**登记 producer 的仓库相对路径**和**该文件的 sha256**——都是公开常量，手写方零成本即可满足。`receipt_validate.py:76-85` 对 producer 的全部校验只有「路径是仓库内普通文件」+「sha256 与该文件当前内容一致」，而 `anchor_plan.py` 的摘要任何人用 `shasum -a 256` 就能算出来。修复把「随便声明哪个仓库文件」收窄成「必须声明 anchor_plan.py 这个名字」，但**没有引入任何手写方无法伪造的绑定量**。

上轮工单不变量原文——「正式 EVM plan 必须由**登记 producer** 针对同一 chain/token/final block 和真实输入生成……consumer 只接收**可独立校验的真实 producer receipt**」——依然被击穿。

**最小反例**（脚本 `/private/tmp/r9b1r2/attack_b1r01_v2.py`，C2 用例）：plan、receipt、input manifest 全部手写，`producer` 声明为 `{"path": "scripts/lib/anchor_plan.py", "sha256": <该文件真实摘要>}`，抽查点缩减为 1 个。

```text
真实 producer  : scripts/lib/anchor_plan.py
其公开 sha256  : cdf39a07d62c091e8013f5b6f7cbbc10a0514cc68026942e15b583606e1d9c46
（该摘要任何人可用 shasum -a 256 算出，不是秘密）

[C2 producer 声明为真实 anchor_plan.py，plan 仍全手写]
  dry-run rc=0  stdout={"dry_run": true, "balance_points": 1, "tx_points": 0, "total": 1, "need_final_block": 0}
  正式路径 rc=1  末行: [time_spotcheck] ERROR → .../out_formal.error.20260808T022646...json
  >>> 穿透：dry-run exit 0；正式路径亦越过 plan/receipt 闸进入业务(RPC)阶段
```

**影响面终局验证**（脚本 `/private/tmp/r9b1r2/attack_b1r01_pass.py`）：不止「越闸」，而是能产出**真正的正式 PASS receipt**。起一个 loopback fake RPC（`eth_chainId=0x1`，任意 `balanceOf` 恒返回 1000），喂同一份伪造 plan：

```text
consumer rc = 0
stdout: [time_spotcheck] PASS  1/1 一致（balance 1 + tx 0；mismatch 0，rpc_err 0）
RPC 方法序列: ['eth_chainId', 'eth_call']
>>> 正式 receipt verdict = PASS  exit_code = 0
    target = {'chain': 'eth', 'token': '0xdeadbeef', 'as_of_block': 300}
    mismatch = 0   points = 1   mode = formal
```

即：A2 时间抽查的覆盖面（时间三段 × 余额档 + 强制覆盖点）可由调用方自选缩水成 1 个必然对得上的锚点，而 `time-spotcheck/v2` 关卡照打 PASS、exit 0。

**归一化旁路的变形攻击结果**（9 个用例，同一脚本）：

| 用例 | producer 声明 | 结果 |
|---|---|---|
| C1 | `references/maintenance-review-repair.md`（上轮原反例） | 已拦截（`must name registered anchor producer`） |
| **C2** | `scripts/lib/anchor_plan.py` + 真实 sha | **穿透** |
| **C3** | `./scripts/lib/anchor_plan.py` | **穿透**（normpath 抹掉 `./`） |
| C4 | `scripts/lib/../lib/anchor_plan.py` | 已拦截（`receipt_validate` 的 traversal 闸先命中） |
| C5 | 绝对路径 | 已拦截（`repository path must be relative`） |
| C6 | `scripts/lib/Anchor_Plan.py`（macOS 大小写不敏感） | 已拦截（常量比较大小写敏感） |
| C7 | plan=md / receipt=真 | 已拦截（`plan producer differs from receipt producer`） |
| C8 | plan=真 / receipt=md | 已拦截 |
| C9 | 真路径 + 错 sha | 已拦截（`producer hash mismatch`，证明 sha 闸确在工作） |

C3 穿透本身无害（它指向的确实是真 producer 文件），但与 C2 一并说明：这道闸拦的是**字符串写法**，不是**生成事实**。

**修复方为何没发现**：新增的两条测试（`test_time_spotcheck.py` 第 179-192 行）叫「伪造 **Markdown** producer 的 dry-run/正式路径在业务前拒绝」，断言 `"registered anchor producer" in p.stderr`——测试与实现同构，都只针对上轮反例的**字面形态**（producer 是个 .md 文档）。`b1_progress.md` B1F-G1 节自述的红测场景也是「把两份 `producer` 同步伪造为仓库内 `references/maintenance-review-repair.md`」。这是「照着反例修，而不是照着不变量修」的教科书形态，正对应方法论第六节「同族要关到同一深度」与「验收攻击站到对方反例边界外一步」。

**归因（严格三分类）**：**老问题修复不全**。

- 替代解释①「**修复中新引入**」——`EXPECTED_PLAN_PRODUCER` 闸是本次消化全新代码，缺口长在新代码上。**不采纳**：`references/maintenance-review-repair.md` 第二节规则 1 规定「只要无法排除旧不变量仍在原入口/同族正式入口被击穿，按老问题修复不全，不得用『这段是新写的』降格」。本反例落在**原入口** `time_spotcheck.py`、击穿**同一条**工单不变量，规则 1 优先。
- 替代解释②「B1R-01 已闭合，C2 属于**新的、更强的**攻击，应作为新 finding 编号」。**不采纳**：上轮 finding 的不变量表述是「consumer 只接收可独立校验的真实 producer receipt」，不是「consumer 拒绝声明为 Markdown 的 producer」。C2 击穿的正是原不变量的原文，属同一 finding 未闭合。若按新 finding 记账，等于允许用「反例被字面关闭」宣告不变量闭合。
- 替代解释③「**历史漏检**」。**不采纳**：规则 3 要求同时排除前两类，此处前两类均不能排除。

**给修复方的方向**（不代替其设计）：`b1_progress.md` 自述「anchor 特例只绑在 consumer 侧」并刻意未改 `receipt_validate.py`——问题正在于此。需要一个手写方造不出的绑定量：当前 `input_identity` 与 `input_manifest` 全由 producer 自报，consumer 完全不核对它们是否对应本次真实数据（这也是 B1R-02 攻击里「输入哈希是上一轮的、无人核对」的同一条缝）。或按上轮建议从 `invariant_manifest.json` 的 `receipt_producers` 派生登记集合，同时解决下述硬编码双源问题（见 B1R2-02）。

---

### B1R-02 → **CLOSED**（P1）

**修复方做了什么**：新建公共原语 `scripts/lib/artifact_quarantine.py`（`quarantine_run_id()` + `quarantine_current(path, run_id=None)`），pool / scan / anchor 三处共用；`anchor_plan.py` 第 209-223 行在 `main()` 读取解析输入**之前**先隔离 receipt（commit marker）、再隔离 plan，任一失败 `return 1`。

**原反例已闭合**（脚本 `/private/tmp/r9b1r2/attack_b1r02_v2.py`，E1）：

```text
run1 rc=0  plan input sha=3e4b82a6abaf48a5
run2 rc=2  [fatal] anchor plan probe boundary invalid: matrix_points[0].day_end_block=999 outside final_block=300
失败后正式位置: plan=False receipt=False
stale 隔离件: ['anchor_plan.json.stale.1786156130862222000.81711',
              'anchor_plan.receipt.json.stale.1786156130862222000.81711']
consumer rc=2  [fatal] ... No such file or directory: .../anchor_plan.json
>>> 旧件已退位，consumer 拿不到可消费对
```

**边界外一步攻击（5 项，全部 fail-closed）**：

| 用例 | 注入 | rc | 正式位置状态 |
|---|---|---:|---|
| E2 隔离失败 | 旧 receipt 是**目录** | 1 | `old canonical is not a regular file`；plan 未被隔离（先 receipt 顺序生效），consumer rc=2 拿不到对 |
| E3 部分隔离 | 旧 plan 是**目录**、receipt 正常 | 1 | receipt 已先行退位、plan 隔离失败 → 无可消费对 |
| E4 权限拒绝 | out-dir `chmod 555` | 1 | `[Errno 13] Permission denied`，旧件原地保留但进程非零 |
| E5 半状态 | 只有 receipt 残留、plan 已丢失 | 2 | 旧 receipt 已退位 |
| E6 成功重跑 | 连续两次成功 | 0 | 旧件同样被隔离，新件发布 |

E3 是关键：它验证了「receipt 先、plan 后」这个顺序设计确实有意义——部分隔离时先走的一定是 commit marker，剩下的孤儿 plan 配不上任何 receipt。

**三处消费者行为一致性**（`rg -e quarantine_current -e quarantine_run_id scripts/`）：

- pool `fetch_pool_swaps.py:72`：`quarantine_current(out_path)` 单件，`run_id=None` 内部生成；调用点已自行 `abspath/expanduser`，与原语内的归一化幂等。
- scan `scan_token_accounts.py:172-173`：共享 `run_id`，先 receipt 后 data。
- anchor `anchor_plan.py:216-217`：共享 `run_id`，先 receipt 后 plan。

三者语义一致。原语内的错误文案由中文改为英文（`old canonical is not a regular file`），但 pool 调用点自己的中文包装 `[fatal] 旧 canonical 无法退出本次正式位置` 保留，对外可观测行为未变。

**pool/scan 无迁移回归**：`test_r9_batch1_boundaries.py` → `3/3`（anchor/pool/scan）；`test_fetch_failclosed.py` PASS；`test_batch3_solana_producers.py` PASS。

**census 同步**：`invariant_manifest.json` 的 `atomic_writes` 由 39 改为 38（pool、scan 两份 locator 删除，`artifact_quarantine.py` 加入一份）。我实跑 `invariant_scan.py` → `PASS ... atomic_writes=38 ... exceptions=0`，`--self-test` 的 delete/add 两类注入均 `RED (rc=1)`。分母下降是三份实现合一的机械结果，且由双向对账扫描得出，不是人为压低；census 一向按定义点计数、不含调用点，故合并未使覆盖面实质缩水。

---

### B1R-03 → **CLOSED**（P2）

**修复方做了什么**：删除 `__init__` 的 `expected_genesis` 关键字参数与 `_expected_genesis` 实例状态，`_attest` 直接与模块常量 `SOLANA_MAINNET_GENESIS_HASH` 比较；docstring 改为「Attest the active endpoint **as Solana mainnet**」。

**构造口确已消失**（脚本 `/private/tmp/r9b1r2/attack_b1r03_v2.py`）：

```text
A3-a  传 expected_genesis → TypeError: __init__() got an unexpected keyword argument 'expected_genesis'
A3-b  位置参数走私 SolanaAttestedSession(endpoint, FORK)
      → TypeError: takes 2 positional arguments but 3 were given
A3-c  分叉链业务 RPC：拒绝，方法序列=[getGenesisHash]，业务调用数=0
A3-d  实例属性事后注入 _expected_genesis / __dict__ 写入 → 无效，业务调用数=0
```

A3-d 是边界外一步：即便按旧字段名事后写实例属性，也不再有任何代码读它。

**其他改写信任根的正式路径口子**：`rg -n "expected_genesis|_expected_genesis"` 全库命中仅 3 类——台账文档、`diff-finding-map.md` 说明行、以及正式测试中的攻击调用；**生产实现零命中**。`rg -n "SOLANA_MAINNET_GENESIS_HASH"` 显示该常量只在 `solana_attested_session.py` 第 10 行定义、第 89/92 行使用，测试文件 import 只作只读比对，**没有任何正式代码 import 后改写它**。模块常量猴补在 Python 语言层始终可达（本次实测确认），但那是语言固有性质、非正式路径口子，且任务已将其列在核验范围之外。

**原 5 条 transport 反例仍全绿**（我独立复跑，未用仓库测试）：

```text
T1 正确 genesis: 业务通过，序列=[getGenesisHash, getAccountInfo, getAccountInfo]，attest 次数=1（只验一次）
T2 错 genesis 单 endpoint: 已拒绝，业务调用数=0
T3 failover: 序列=[(bad,getGenesisHash), (good,getGenesisHash), (good,getAccountInfo)]
             坏 endpoint 上的业务调用数=0（换端点必重验）
T4 非字符串 genesis: 已拒绝，业务调用数=0
T5 error 响应: 已拒绝，业务调用数=0
T6 保留字 getGenesisHash: 已拒绝（reserved for session attestation）
```

仓库自身 `test_r9_solana_attested_session.py` → `PASS 6/6`。docstring 与实现的双向一致性已修复（`request_json` 现在确实是唯一注入边界）。

---

### B1R-04 → **CLOSED**（P3）

**条文已恢复且语境正确**。`invariant-merge.md` 第 5 行新增独立一行：

> 治理纪律：此后拆分/合并不变量必须经 Fable 批准并同步 ledger 双台账，不得在验收阶段为销账临时改组。

位置在「状态」行与「计数口径：**49 项** finding 每项恰好一个 primary invariant」行之间，属页首状态区，语境正确。与 `63cf715` 删除前的原文逐字对照，语义完整（原文把该条嵌在 R8 冻结状态句尾，现拆为独立条目，面向未来的约束力不变；R8 阶段性表述被 R9 状态替代属 G6 声明目的内，上轮亦未就此立 finding）。

**map 的 B1F owner 行与实际 commit 吻合**（逐行核对）：

| map 行 | 声明文件清单 | 实际 commit | 核对 |
|---|---|---|---|
| `B1F-G1` | time_spotcheck.py; test_time_spotcheck.py; b1_progress.md | `fa82b32` | ✓ |
| `B1F-G2` | artifact_quarantine.py, anchor_plan.py; fetch_pool_swaps.py, scan_token_accounts.py; test_r9_batch1_boundaries.py, invariant_manifest.json; b1_progress.md | `fa82b32` | ✓ |
| `B1F-G3` | solana_attested_session.py; test_r9_solana_attested_session.py; b1_progress.md | `fa82b32` | ✓ |
| `B1F-G4` | invariant-merge.md, diff-finding-map.md, b1_progress.md | `8477e04` | ✓ |

SHA 对照表四行已由 `0bb94ba` 回填（G1/G2/G3→`fa82b32`，G4→`8477e04`），与三个 commit 的实际文件边界一一吻合；未映射 hunk 节新增 `144c652..候选 tip` 消化区间行，计数 `0`。owner 表末列（SHA 列）四行留空，与既有 `R9-B1-G5/G6/G7` 行同格式，非遗漏。

`docs_lint.py --all` → `PASS: 58 个文档，引用无断链、粗体配对完整`。

---

## 3. 新 finding 明细

本轮新发现 **2 项，均为 P3**（上轮为 P1×2、P2×1、P3×1）。按方法论第五节「唯一诚实的收敛指标是新发现的严重度逐轮降级」，新引入部分确实降级了；但这不抵消 B1R-01 的 REOPEN。

---

### B1R2-01｜P3｜修复中新引入（夹带／无主改动）｜`solana_attested_session.py` 删除文件末尾空行，不在 B1F-G3 声明目的内

**证据**：区间内第 36 个 hunk。

```text
@@ -120,4 +116,3 @@ class SolanaAttestedSession:
                     self._advance()
             raise SolanaRpcError(
                 f"all Solana endpoints failed for {method}: " + " | ".join(failures))
-
```

`od -c` 核对末字节为 `\n - \n`，即删除一个纯空行，无任何非空白字符改动。

`diff-finding-map.md` 的 `B1F-G3` 行声明目的为「删除调用方 `expected_genesis` 覆盖口，信任根只取 mainnet 库常量，docstring 与唯一 transport 注入边界对齐」——**不涵盖文件末尾空白规整**。按 PLAN「`diff→finding` 映射覆盖每个变更块；无主改动一律视为夹带」，此 hunk 无主。

**影响**：零。纯空白，无行为、无语义、`git diff --check` 无告警、`docs_lint` 与全量 suite 不受影响。

**为什么仍然记账**：上轮报告在第 4 节明确把「顺手整理式的格式化夹带」列为扫描对象并报告「未发现」；本轮出现了一处。方法论第七节 7.1 规定「新引入、半修残留**不分严重度**，都要修复后重审——P3 也可能是下一轮旁路的入口」。记账的意义不在这一个空行，而在于「修复 commit 里可以夹带未登记改动」这一习惯本身。

**最强替代解释及不采纳理由**：最强替代解释是「删末尾多余空行属于编辑器/格式化的自动行为，是修改该文件的必然副产物，应视为 B1F-G3 的直接依赖」。**不采纳**：它不是修改该文件的必然副产物——同一 commit 内改动的其余 12 个文件都没有出现类似的空白规整，说明这是该文件独有的一次额外动作；且方法论 7.3 要求「每个 hunk 必须同时有 invariant、finding/豁免、**目的**和测试 owner」，登记成本极低（map 里加半句），不登记没有正当理由。归「修复中新引入」而非「老问题修复不全」：该 hunk 与任何旧不变量无关，纯属本轮 diff 新增。

---

### B1R2-02｜P3｜修复中新引入｜登记 producer 路径成为第三份无对账的事实源

**证据**：`scripts/lib/anchor_plan.py` 这个路径字符串现在同时存在于三处，且**没有任何守卫强制它们一致**：

1. `scripts/tests/invariant_manifest.json` 的 `receipt_producers`：`{"schemas": ["anchor-plan-input/v1", "anchor-plan-receipt/v2", "anchor-plan/v2"], "script": "scripts/lib/anchor_plan.py"}`
2. `scripts/lib/time_spotcheck.py:52`：`EXPECTED_PLAN_PRODUCER = "scripts/lib/anchor_plan.py"`
3. 文件的实际位置

`rg -n "EXPECTED_PLAN_PRODUCER"` 全库仅 3 处命中，全在 `time_spotcheck.py` 自身（定义 + 比较 + 错误文案），**无任何测试或守卫把它与 manifest 的登记条目对账**。

上轮报告的修复方向明确写过「可从 `invariant_manifest.json` 的 `receipt_producers` 派生，避免再造一份事实源」；`b1_progress.md` B1F-G1 节记的是「通用 `receipt_validate.py` 未改，anchor 特例只绑在 consumer 侧」，未说明为何不派生。

**影响**：属视角⑤双向一致性缺口。若 `anchor_plan.py` 被改名或移位（本工程正在做的瘦身/迁档正是这类动作，`archive/` 考古区迁移已有先例），`invariant_scan.py` 会因 manifest 与实际扫描不符而红，但 `time_spotcheck.py` 的硬编码常量不在任何对账范围内——它会静默地拒绝**所有真实 plan**。方向是 fail-closed（不会放行假货），所以定 P3 而非更高；但它把一次改名事故的暴露点从「机器守卫」推迟到了「正式跑 A2 抽查时才发现」。

**最强替代解释及不采纳理由**：最强替代解释是「硬编码单一常量比从 manifest 派生更简单可靠，manifest 是测试件、生产代码不该依赖测试件」。这条**有相当分量**——让 `scripts/lib` 的生产件 import `scripts/tests/invariant_manifest.json` 确实是倒置依赖，工程上可议。**仍记账，但只记 P3 且不指定实现**：不采纳的部分不是「别硬编码」，而是「三份副本零对账」。最低成本的闭合可以只是一条守卫（例如让 `invariant_scan.py` 或某个契约测试断言 `EXPECTED_PLAN_PRODUCER` 出现在 `receipt_producers` 中），不必倒置依赖。归「修复中新引入」：该常量是本轮消化全新代码，此前不存在这份副本，规则 3 的「历史漏检」不成立。

---

### 未列为 finding 的观察（如实登记，供裁判裁决）

1. **`anchor_plan.input.json` 未纳入启动隔离集合**。`anchor_plan.py` 只隔离 receipt 与 plan，input manifest 走 `publish_overwrite`。我验证过这不构成 fail-open：receipt 先行退位后已无可消费对，且成功路径下 input manifest 会被本次内容覆盖。E6 实测确认它从不产生 stale 兄弟件。
2. **argparse 阶段失败时旧件不隔离**。`anchor_plan.py` 的隔离点在 `ap.error("--final-block must be non-negative")` 之后、`_input_identity` 之前，即「参数错 → 旧件保留」。这与 pool/scan 现有语义一致，也与上轮报告第 3 节②登记的同型观察一致——失败发生在任何业务动作之前，语义等同「本次运行没启动」，可辩护。
3. **`.stale.<time_ns>.<pid>` 堆积面扩大**。上轮已把「stale 只生成不清理」作为给下一批的提醒；anchor 加入后，成功路径（E6 实测）也会在正式产物目录留下 `anchor_plan.json.stale.*` 与 `anchor_plan.receipt.json.stale.*`。若下游存在 `anchor_plan*` 形态的 glob，误读面比上轮更大。仍属既有提醒的扩面，不新计 finding。
4. **`anchor_plan.py` 的 `out_dir` 新增 `expanduser()`**（原为 `Path(a.out_dir).resolve()`）。是行为变更（`~` 现在会展开），但属把 out_dir 计算提前到 `main()` 开头的必要配套，且与公共原语内部的 `expanduser` 语义对齐，方向是修正。属 B1F-G2 的直接依赖，不计夹带。
5. **`test_r9_batch1_boundaries.py` 的 `bad_dir` 全新目录场景被替换**。新断言（同 out-dir 先成功后失败 + 双 stale 存在 + consumer 非零）严格强于旧断言，但「全新目录下失败不产出」这个变体不再有显式覆盖。净覆盖面为增，登记备查。

---

## 4. 夹带扫描（36 hunk 逐块归属）

**方法**：`git diff --unified=0 144c652..0bb94ba` 逐 hunk 列头（共 36 个 `@@`，13 文件），不看 map 独立判定归属，再与 `diff-finding-map.md` 的 B1F 四行对账。

| # | 文件 | hunk 头 | 我的独立归属 | 有主 |
|---:|---|---|---|:--:|
| 1 | `maintenance/repair-20260806/b1_progress.md` | `-193,0 +194,66` | B1F-G1～G4 消化节 | ✓ |
| 2-4 | `maintenance/repair-20260806/diff-finding-map.md` | `-58,0 +59,4` / `-91,0 +96,4` / `-105,0 +114` | B1F-G4（owner 四行 / SHA 对照四行 / 消化区间行），含自指回填 | ✓ |
| 5 | `maintenance/repair-20260806/invariant-merge.md` | `-4,0 +5` | **B1R-04** 直接闭合 | ✓ |
| 6-7 | `scripts/evm/fetch_pool_swaps.py` | `-25,0 +26,3` / `-63,14 +65,0` | **B1R-02**（改用公共原语 / 删本地实现） | ✓ |
| 8-11 | `scripts/lib/anchor_plan.py` | `-37,0 +38` / `-207,0 +209,16` / `-213,2 +230,2` / `-372,2 +389,2` | **B1R-02**（import / 启动隔离 / out_dir 提前 / jp,rp 复用） | ✓ |
| 12 | `scripts/lib/artifact_quarantine.py` | `-0,0 +1,27`（新文件） | **B1R-02** 公共原语 | ✓ |
| 13-18 | `scripts/lib/solana_attested_session.py` | `-30 +30` / `-36,2 +36` / `-49,2 +47,0` / `-52 +48,0` / `-93 +89` / `-96 +92` | **B1R-03**（docstring / 签名 / 删校验 / 删实例状态 / 比较改常量 / 错误文案） | ✓ |
| **19** | `scripts/lib/solana_attested_session.py` | `-123 +118,0` | **无主**——删末尾空行，不在 B1F-G3 声明目的内 | ✗ |
| 20-21 | `scripts/lib/time_spotcheck.py` | `-51,0 +52` / `-82,0 +84,7` | **B1R-01**（常量 / producer 校验） | ✓ |
| 22-24 | `scripts/solana/scan_token_accounts.py` | `-24,0 +25` / `-41,14 +41,0` / `-181 +168` | **B1R-02**（import / 删本地实现 / run_id 改公共） | ✓ |
| 25-28 | `scripts/tests/invariant_manifest.json` | `-17 +17` / `-671,5 +670,0` / `-695,0 +691,5` / `-816,5 +815,0` | **B1R-02** census 同步（39→38 / 删 pool locator / 加公共 locator / 删 scan locator） | ✓ |
| 29-31 | `scripts/tests/test_r9_batch1_boundaries.py` | `-172 +171,0` / `-176 +175` / `-178,2 +177,9` | **B1R-02** 红测 | ✓ |
| 32-33 | `scripts/tests/test_r9_solana_attested_session.py` | `-107,0 +108,12` / `-114,0 +127` | **B1R-03** 红测 | ✓ |
| 34-36 | `scripts/tests/test_time_spotcheck.py` | `-64,0 +65,21` / `-157,0 +179,14` / `-162 +197` | **B1R-01** 红测（forge 工具 / 用例 8-9 / 计数 8→10） | ✓ |
| | **合计 36** | | | **35 有主 / 1 无主** |

**结论**：

- 未映射 hunk = **1**（第 19 号），与自报的 `0` 不符。见 B1R2-01。
- 其余 35 个 hunk 全部落在 B1R-01～04 的四组修复目的内，与 map 的 B1F-G1～G4 四行逐行对得上；**没有发现指向第五个目的的改动**，也没有发现「有 owner 的 hunk 里夹带目的外语义内容」（上轮 B1R-04 那种形态本轮未复现）。
- 范围声明抽验：`VERSION` 零 diff（仍 `6.36.0`）；`chain_registry.py`、`accounting_gate_sol.py` 零 diff；`getGenesisHash` 仍只存在于新原语及其测试两个文件，未接正式 callsite。
- 无 `.pyc` / `__pycache__` 进入版本控制；`git diff --check` 通过。

---

## 4bis. 修复方自报验证表

**原则：不信自报，每条用我自己的命令重跑。**

| # | `b1_progress.md` 消化节的声明 | 我的结果 | 属实 |
|---:|---|---|:--:|
| 1 | 全量 `82/82 PASS`，`exit=0`，末行「全部通过」 | 实跑 `run_all.py`：rc=0，82 个 PASS 行，末行「全部通过」 | ✅ |
| 2 | `test_time_spotcheck.py` `10/10` | 实跑：`time_spotcheck 契约测试全部通过（10 项）` | ✅ |
| 3 | `test_r9_batch1_boundaries.py` `3/3` | 实跑：anchor / pool / scan 三项 PASS | ✅ |
| 4 | `test_r9_solana_attested_session.py` `6/6` | 实跑：`PASS R9 SolanaAttestedSession: 6/6` | ✅ |
| 5 | `test_fetch_failclosed.py`、`test_batch3_solana_producers.py` 通过 | 实跑：两项均 PASS | ✅ |
| 6 | `invariant_scan.py` census `atomic_writes=38`、`exceptions=0` | 实跑：`receipt_producers=49, receipt_consumers=53, transport_calls=58, atomic_writes=38, formal_entrypoints=58, exceptions=0` | ✅ |
| 7 | `--self-test` delete/add 两类注入均稳定红 | 实跑：两条均 `RED (rc=1)` | ✅ |
| 8 | `docs_lint.py --all` PASS 58 个文档 | 实跑：`PASS: 58 个文档，引用无断链、粗体配对完整` | ✅ |
| 9 | EVM 纵切片受沙箱 `bind(127.0.0.1)` 限制、需沙箱外运行 | 本审查环境允许 loopback bind，`run_all` 内直接通过 | ✅（环境差异，非缺陷） |
| 10 | 未改 `VERSION`，仍 `6.36.0` | `cat VERSION` + `git diff --stat` 空 | ✅ |
| 11 | 施工期未执行 git 写操作；`git diff --check` 通过 | `git status --short` 空；HEAD=`0bb94ba`；`diff --check` 通过 | ✅ |
| 12 | `rg '^def quarantine_current'` 仅命中公共原语，无三重复制 | 实跑 `rg -e quarantine_current -e quarantine_run_id scripts/`：定义仅 `artifact_quarantine.py`，pool/scan/anchor 三处均为调用 | ✅ |
| 13 | `expected_genesis` 生产实现零命中 | 实跑全库 `rg`：仅台账文档与测试攻击调用命中 | ✅ |
| 14 | 未映射 hunk = `0` | 独立复算 36 hunk | ❌ 实为 `1`（见 B1R2-01） |
| 15 | 「四项红→绿」——`B1R-01` 已转绿 | C2 反例穿透，并产出真 PASS receipt | ❌ 不成立 |
| 16 | 「四项红→绿」——`B1R-02` / `B1R-03` / `B1R-04` 已转绿 | 复跑原反例 + 各自边界外一步攻击，均未攻穿 | ✅ |

**汇总**：16 条中 14 条属实、2 条不成立。不成立的两条都指向同一个模式——**用「红测转绿」代替「不变量闭合」**：第 15 条的红测只覆盖了上轮反例的字面形态，第 14 条的自查只数了「hunk 有没有 owner 行」而没读 hunk 正文。与上轮一样，施工方在「哪些没做」上的陈述是诚实的（未发现把未销账 finding 谎报为已修），失准集中在对自身修复深度的评价。

---

## 5. 实际运行的关键命令清单

全部命令的工作目录为 worktree 或 `/private/tmp/r9b1r2`；**对仓库严格只读**，未执行任何 git 写操作、未增删改 worktree 内任何文件，临时产物一律落系统 tempdir。

**仓库状态与 diff 复算**

```bash
git log --oneline -8
git status --porcelain && git branch --show-current
git diff --stat 144c652..0bb94ba
git diff --unified=0 144c652..0bb94ba | grep -c "^@@"          # → 36
git diff --unified=0 144c652..0bb94ba | grep "^diff --git\|^@@"  # 36 hunk 逐块定位
for f in $(git diff --name-only 144c652..0bb94ba); do \
    git diff --unified=0 144c652..0bb94ba -- "$f" | grep -c "^@@"; done
git diff 144c652..0bb94ba -- scripts/lib/ scripts/evm/ scripts/solana/
git diff 144c652..0bb94ba -- scripts/tests/
git diff 144c652..0bb94ba -- maintenance/repair-20260806/{b1_progress.md,diff-finding-map.md,invariant-merge.md}
git show 63cf715:maintenance/repair-20260806/invariant-merge.md   # 对照治理条文删除前原文
git diff 144c652..0bb94ba -- scripts/lib/solana_attested_session.py | tail -4 | od -c
git diff --stat 144c652..0bb94ba -- VERSION scripts/lib/chain_registry.py scripts/solana/accounting_gate_sol.py
git diff --check && git rev-parse HEAD && git status --short
```

**自报声明重验**

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py            # 82 PASS / rc=0
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_time_spotcheck.py            # 10/10
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch1_boundaries.py      # 3/3
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_solana_attested_session.py # 6/6
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_fetch_failclosed.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch3_solana_producers.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py                 # atomic_writes=38
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py --self-test      # delete/add 均 RED
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all                # 58 文档 PASS
rg -n -e "quarantine_current" -e "quarantine_run_id" scripts/
rg -n "expected_genesis|_expected_genesis" .     # 生产实现零命中
rg -n "SOLANA_MAINNET_GENESIS_HASH" .            # 无正式代码 import 后改写
rg -n "EXPECTED_PLAN_PRODUCER" .                 # 仅 time_spotcheck 自身 3 处，无守卫对账
rg -l "getGenesisHash" --type py .               # 仍 2 文件，未接正式 callsite
rg -n "旧 canonical" .                            # 确认 pool 中文错误包装保留
python3 -c "<解析 invariant_manifest.json 的 anchor_plan/time_spotcheck 登记条目>"
```

**边界外一步攻击（全部为本轮新写，非复跑上轮或施工方反例）**

```bash
python3 /private/tmp/r9b1r2/attack_b1r01_v2.py    # B1R-01 九用例：C2/C3 穿透，C1/C4-C9 拦截
python3 /private/tmp/r9b1r2/attack_b1r01_pass.py  # B1R-01 影响面：loopback fake RPC → 真 PASS receipt
python3 /private/tmp/r9b1r2/attack_b1r02_v2.py    # B1R-02 六用例：E1 原反例已闭合，E2-E6 全 fail-closed
python3 /private/tmp/r9b1r2/attack_b1r03_v2.py    # B1R-03：构造口/位置参数/实例属性注入 + 原 5 条 transport 反例
```

**攻击脚本留存位置**：`/private/tmp/r9b1r2/`（`attack_b1r01_v2.py`、`attack_b1r01_pass.py`、`attack_b1r02_v2.py`、`attack_b1r03_v2.py`），供裁判独立复现。上轮脚本 `/private/tmp/r9b1/` 保持原状未改动。

---

## 附：给消化方的提醒（不构成 finding）

1. B1R-01 的两次修复都停在「关掉审查者给的那个反例」这一步。第一次是 `plan.producer == receipt.producer` 的自洽比较，第二次是 producer 路径的字面白名单——两次都没有回答工单不变量真正问的那个问题：**consumer 凭什么相信这份 plan 是 producer 跑出来的，而不是有人照着格式写出来的**。下一次修复前建议先写出「一个手写方无论如何造不出的值是什么」，再决定改哪个文件。
2. 与此直接相关：`input_identity` 与 `input_manifest` 目前全部由 producer 自报，consumer 一个字节都不核对。B1R-02 的原攻击（旧 plan 绑定的是上一轮输入哈希、无人察觉）和 B1R-01 的 C2 攻击（输入哈希纯属捏造）其实是同一条缝的两个方向——B1R-02 从时序上关掉了它，B1R-01 从内容上还没有。
3. 未映射 hunk 的自查目前只统计「hunk 有没有 owner 行」。上轮的 B1R-04 与本轮的 B1R2-01 都不是这样抓到的，都要读 hunk 正文才看得见。建议自查口径改为「逐 hunk 正文对照 owner 行声明的目的」。
