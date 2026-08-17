# 单元1 独立攻击型盲审报告（anchor-plan v2→v3 机器字段 + producer 历史登记）

- 审计对象：`git diff 0ec6d1e..a2294e2`（提交 a2294e2，v6.46.0）
- 审计员立场：独立攻击者，只读仓库；全部攻击 fixture 建在 `/tmp/blindreview-u1/`（脚本保留：`atk.py` 公共夹具 + `g1`…`g9` 九组攻击脚本）
- 纪律遵守：仓库未做任何写入（本报告除外），未 commit / 未 push；所有实跑均带 `PYTHONDONTWRITEBYTECODE=1`，未在仓库留下 `__pycache__`
- 范式：不重复工单 §3 已覆盖的 12 组正面用例，一律打其**边界外一圈**；每个向量都构造真实输入实跑真实代码取证

## 0. 终局统计

| 判定 | 数量 | 编号 |
|---|---:|---|
| **BREACH** | **2** | V-01、V-31 |
| WEAK | 16 | V-03、V-04、V-06、V-07、V-11、V-12、V-17、V-18、V-20、V-23、V-24、V-28、V-32、V-33、V-34、V-36 |
| DEFENDED | 20 | V-02、V-05、V-08、V-09、V-10、V-13、V-14、V-15、V-16、V-19、V-21、V-22、V-25、V-26、V-27、V-29、V-30、V-35、V-37、V-38 |
| 合计 | 38 | — |

先说结论：**U1 的核心目标（kind 文案退出语义、balance/tx 严格 XOR、v2 存量不误拒）在我能想到的所有形态攻击下都站住了**，其中"投影前先断言再剥字段"这条纪律的实现质量最高（V-27 三路攻击全部大声失败）。两个 BREACH 都不在"点形态契约"本身，而在**契约两侧的信任边界**：一个是 producer 历史登记表的 `protocol` 列在消费端根本没被使用（V-01），一个是 plan 字节的规范性从来没人验、导致新引入的机器字段可以被"重复键"手法视觉伪装（V-31）。

---

## 1. 攻击面 A：producer 历史登记与"当前 ∪ 历史"并集边界

### V-01 协议错配：v3 计划挂 v2 时代 producer 签名 —— **BREACH**

**攻击描述**：`producer_history` 的两条登记都写死 `protocol: "anchor-plan/v2"`，但两个消费端（`time_spotcheck.load_validated_plan:82-83`、`shared_release_receipt._validated_time_plan_authority:964-965`）查询时把协议**硬编码成字面量 `"anchor-plan/v2"`，与正在校验的 plan 实际 schema 无关**。于是造一份 **v3** plan，receipt 的 `producer.sha256` 填历史 v2 producer 哈希 `e5168a…`（该哈希对应的脚本 `PLAN_SCHEMA = "anchor-plan/v2"`，物理上不可能产出 v3 计划），看两侧是否识破这份"provenance 自相矛盾"的件。

**实跑命令**：
```bash
PYTHONDONTWRITEBYTECODE=1 python3 /tmp/blindreview-u1/g1_producer.py
```

**输出摘要**：
```text
V01 executor  (load_validated_plan, v3 plan + v2-protocol historical hash):
  time_spotcheck: ACCEPTED -> anchor-plan/v3
V01 gate      (_validated_time_plan_authority):
  shared: ACCEPTED -> anchor-plan/v3
V02 v3 plan + 1a4611 (v6.45.1 pre-v3 producer, protocol v2):
  time_spotcheck: ACCEPTED -> anchor-plan/v3
  shared: ACCEPTED -> anchor-plan/v3
```

**判定：BREACH**。两条登记哈希（`e5168a…` 与 `1a4611…`）都能给 v3 计划背书，执行侧与发布闸**双双放行**。登记表专门设了 `protocol` 列来绑定"哈希↔协议"，消费端却一次也没用它——这正是 U1 要修的那类"schema 与 producer 版本脱钩"缺陷，只是换了个方向复发。

**诚实的严重性标注**：能改案目录文件的攻击者同样可以直接抄"当前脚本哈希"来伪造 receipt，所以本向量并没有新增"越权"能力；它的实质危害是**契约完整性**——系统接受了一份逻辑上不可能存在的签发声明，等于宣告 `protocol` 列是装饰品。按本仓库既有威胁模型（`maintenance/repair-20260815-g2/blindreview_g2_round1.md:398` 明确把"手写收据"列入威胁模型，并据此要求消费侧独立复验全部绑定），这一项**必修**。

**建议修法**：把协议参数改为按被验 plan 的 schema 动态传入（v3 计划只认 protocol=v3 的登记条目；v2 计划才查 v2），或在并集处加一道"登记条目 protocol 必须等于 plan.schema"的断言。注意 `e5168a…` 只对 v2 有效这一点，正是登记表 `reason` 字段已经写明的事实。

### V-02 未登记哈希（对照）—— DEFENDED
同脚本，`producer.sha256 = "f"*64`：执行侧 `plan receipt invalid: producer hash mismatch`，发布闸 `plan receipt envelope invalid: ['producer hash mismatch']`。并集没有被放开成"任意哈希"。

### V-03 跨脚本冒用：历史哈希对别的 producer 也成立 —— WEAK
`validate_receipt(..., allowed_producer_hashes=…)` 收到的是一个**光秃秃的哈希集合**，与 `script` 列彻底解耦。实跑：receipt 的 `producer.path` 改成 `scripts/lib/anchor_selection.py`、sha256 填 anchor_plan 的历史哈希 `e5168a…`：
```text
V04 validate_receipt with producer.path=scripts/lib/anchor_selection.py + OLD hash:
  validate_receipt errors: NONE (admitted)
```
两个真实调用点各自在下游补了路径闸（`load_validated_plan:97` 的 `EXPECTED_PLAN_PRODUCER` 比对；`repo_ref_ok` 的 `{"scripts/lib/anchor_plan.py"}` 白名单），**今天打不穿**，故判 WEAK 而非 BREACH。风险在于：这是 API 层的 fail-open，下一个忘记补路径闸的调用方会直接继承这个洞。

### V-04 REVOKED 撤不掉"当前哈希" —— WEAK
`validate_receipt:109` 无条件把当前脚本哈希塞进 `allowed_hashes`，并集在登记表之外发生。实跑：往登记表插一条 `status=REVOKED` 且 `sha256 == 当前 anchor_plan.py 哈希` 的条目：
```text
V05 REVOKED entry whose sha256 == current anchor_plan.py hash:
  historical() for v3 returns: empty set
  validate_receipt(current-but-REVOKED hash) errors: NONE (admitted)
```
`producer_history.py` docstring 与工单 §2.6 都宣称 REVOKED 是 **hash-wide 否决**；实测它的作用域只到"历史集合"，管不了当前脚本。属注释/工单与实现不符。

### V-05 REVOKED 直取（同 script+protocol）—— DEFENDED
```text
W1 REVOKED on the same script+protocol:
   OLD still admitted: False | set size: 1
     NES legacy case under revocation: REJECTED(ValueError: plan receipt invalid: producer hash mismatch)
```
撤销杠杆是真的：一旦把 `e5168a…` 标 REVOKED，真实 NES 存量件立刻被拒。证明该表不是摆设。（命令：`python3 /tmp/blindreview-u1/g9_final.py`）

### V-06 status 拼写走样 → 撤销静默失效 —— WEAK
插一条 `status: "Revoked"`（大小写走样）的同哈希条目：
```text
V06 status typo 'Revoked' fails to veto an ACTIVE duplicate:
  OLD still admitted: True
```
`historical_producer_hashes` 对未知 status 的处理是"既不 ACTIVE 也不 REVOKED"——对"是否放行"是 fail-close，但对"撤销意图"是 **fail-open**。唯一防线是 `test_anchor_plan_v3.py:363` 的结构断言（模块外），模块本身不做归一化也不校验。

### V-07 `allowed_producer_hashes` 类型混淆 —— WEAK
参数没有类型校验，`set.update(<str>)` 会把字符串**按字符打散**：
```text
V07 allowed_producer_hashes passed as a bare string:
  single-char sha256 'e' vs string-splatted allow-set -> NONE (admitted)
```
即：若将来有人误传单个哈希字符串而不是集合，所有 1 字符的 sha256 都会被当作合法 producer 哈希。顺带暴露 `validate_receipt` 对 `producer.sha256` **完全不做格式校验**（长度/字符集都不查）。今天两个调用点都传集合，故 WEAK。

### V-08 默认路径与其他 producer 未被放宽 —— DEFENDED
```text
V08 default path (no allowed_producer_hashes) still rejects historical hash:
  errors: ['producer hash mismatch']
V79 other repo_ref_ok call sites keep the default (no historical hashes):
    recon runner with historical anchor hash: REJECTED(... is not current repository script)
    time-spotcheck receipt via default validate_receipt: errors ['producer hash mismatch']
```
放宽面严格局限在 anchor plan 一条线，符合工单 §2.6"默认路径语义零变化"。

### V-09 producer 脚本缺失时的边界 —— DEFENDED
```text
W2 producer script absent from the repo tree (historical hash registered):
   errors: ["producer invalid: [Errno 2] No such file or directory: .../scripts/lib/anchor_plan.py"]
```
即使历史哈希已登记，当前脚本不在场也一律拒（`_regular_file` 先炸）。fail-closed，正确。

### V-10 登记表是不是真的承重 —— DEFENDED
把 `PRODUCER_HISTORY` 清空后重跑真实 NES 存量件：
```text
V76 legacy NES case with the registry emptied:
    registry empty: REJECTED(ValueError: plan receipt invalid: producer hash mismatch)
    registry restored: ACCEPTED -> anchor-plan/v2
```
存量件恰恰是靠这张表过的，不是靠别的巧合。修复的因果链闭合。

### V-11 git 可复现守卫在无 `.git` 部署里自动失效 —— WEAK
`test_anchor_plan_v3.py:396` 的 `git show <commit>:<script>` 复现断言包在 `if (ROOT / ".git").exists():` 里。实跑：把 `scripts/` 整树复制到无 `.git` 的目录，并把第二条登记**篡改成伪造哈希 + 不存在的 commit `deadbee`**，再跑同一份测试：
```bash
PYTHONDONTWRITEBYTECODE=1 python3 /tmp/blindreview-u1/g7_registry.py
```
```text
V77 producer_history git guard in a deployed copy without .git:
   fabricated hash+commit, no .git -> ['PASS test_12_producer_history_and_default_boundary']
```
模块 docstring 写着"脏工作树产物不得入表""每条必须 git show 可复现"，但**运行时从不校验登记表**，唯一校验者是这条会自我禁用的测试断言。多设备同步/打包部署（如 codex 副本、`git archive` 交付）正是无 `.git` 的典型场景。

### V-12 登记表 commit 形态不一致 —— WEAK
```text
V78 registry commit-id form:
   e5168a455d... commit=3b76db80130987e0faf68d73094b08cddd161c9b len=40
   1a461169f0... commit=0ec6d1e len=7
   git rev-parse 0ec6d1e -> 0ec6d1e2365c339d200fc26d17344f962fbdb7a9
```
一条 40 位全长、一条 7 位缩写，测试正则 `[0-9a-f]{7,40}` 两者都收。缩写随仓库增长可能歧义（届时 `git show` 报错，属大声失败，不至于误放行），但同一张表两种形态本身就是维护面漂移。建议统一 40 位。

---

## 2. 攻击面 B：版本分派与 receipt 配对矩阵

命令：`PYTHONDONTWRITEBYTECODE=1 python3 /tmp/blindreview-u1/g2_pairing.py`

### V-13 配对矩阵四象限（含第四象限）—— DEFENDED
```text
V10 plan=v3 x receipt.plan_schema=anchor-plan/v2 -> 两侧均 REJECTED(plan_schema mismatch)
V10 plan=v3 x receipt.plan_schema=anchor-plan/v3 -> 两侧均 ACCEPTED
V10 plan=v2 x receipt.plan_schema=anchor-plan/v2 -> 两侧均 ACCEPTED
V10 plan=v2 x receipt.plan_schema=anchor-plan/v3 -> 两侧均 REJECTED(plan_schema mismatch)
```
两个交叉象限在执行侧与发布闸**同拒同放，等深**。工单 §2.3 的"其余组合全拒"成立。

### V-14 未知版本 v4（两侧自洽）—— DEFENDED
`plan.schema = receipt.plan_schema = "anchor-plan/v4"`：执行侧 `plan schema must be one of ['anchor-plan/v2','anchor-plan/v3']`，发布闸 `plan schema must be anchor-plan/v2 or anchor-plan/v3`。

### V-15 `"anchor-plan/v3 "`（尾空格）—— DEFENDED
两侧集合成员判定，均拒。无 strip/归一化的宽容面。

### V-16 v3 标签但机器字段被整体剥掉 —— DEFENDED（附注）
`load_validated_plan` 与 `_validated_time_plan_authority` **都放行**（这两层根本不看点形态），但下游立刻拦住：
```text
V56 v3_missing_source:
    gate deep-verify: REJECTED(ValueError: anchor-plan/v3 balance_block_source invalid: None)
  executor dry-run: exit=2 :: 语义重放 matrix_points differs (missing=4, extra=4)
```
判 DEFENDED，但要留一句：**权威链层是点契约盲区**，v3 形态闸完全靠 `classify`/`_plan_point` 兜底，任何绕过这两个函数直接消费 plan 的新代码都会裸奔。

### V-17 未知 schema 静默退化为 v2 语义 —— WEAK
`classify:236`、`balance_query_block:262`、`shared._plan_point:880` 三处的分派都是 `if schema == v3: … else: <v2 传统语义>`，**默认分支是最弱语义而不是抛错**：
```text
V70 unsupported schema reaches replay helper directly --
  _replayed_points_for_schema('anchor-plan/v9'): REJECTED(unsupported replay plan schema)
  classify with schema anchor-plan/v9 (fallback branch): ACCEPTED -> (10, 3, 0)
  balance_query_block with schema anchor-plan/v9: ACCEPTED -> 300
  gate _plan_point with schema anchor-plan/v9: ACCEPTED -> ('balance', …, 123, '100')
```
对比：同一文件里的 `validate_semantic_replay` / `_replayed_points_for_schema` 是 fail-closed（显式 `unsupported replay plan schema`）。**同一次施工里两套纪律并存**。今天靠入口白名单兜住，故 WEAK。

### V-18 发布闸裸字面量漂移 = 静默退化，且"恰好答对" —— WEAK
`shared_release_receipt.py:880` 用裸字符串 `"anchor-plan/v3"` 分派。假设该字面量将来被改坏（拼写/版本号漏改），v3 计划会掉进 v2 传统分支。实测该分支对边缘点给出**逐字节相同的元组**：
```text
V81 drift of the gate's bare 'anchor-plan/v3' literal (silent v2 fallback?):
   v3 branch tuple : ('balance', '门槛±10% 边缘地址', '0x…13', 300, '100')
   fallback tuple  : ('balance', '门槛±10% 边缘地址', '0x…13', 300, '100')
   identical -> True
    fallback with a renamed kind: REJECTED(time plan balance point missing day_end_block)
```
即：**漂移不会被任何行为测试发现，因为回退路径靠 kind 文案又猜对了同一个答案**——而"不再依赖 kind 文案"正是本单元的立项理由。这条一致性只在文案没改时成立（最后一行实证）。典型"防御依赖偶然性"。

### V-19 `V3_SCHEMA` 漂移是大声的（对照）—— DEFENDED
```text
V80: classify after V3_SCHEMA drift: REJECTED(machine point contract requires anchor-plan/v3)
```
`anchor_point_contract.V3_SCHEMA` 一旦与 plan 不符，全部点立刻炸。四处 schema 字面量里，只有 V-18 那处的失败模式是静默的。

### V-20 producer 路径拼写：执行侧收、发布闸拒 —— WEAK
```text
V09 producer path './scripts/lib/anchor_plan.py' (dot-prefixed spelling):
    executor: ACCEPTED -> anchor-plan/v3
    gate    : REJECTED(time anchor plan producer/runner path is not whitelisted: ./scripts/lib/anchor_plan.py)
```
`load_validated_plan:95` 用 `os.path.normpath` 归一化后比对，`repo_ref_ok:104` 用**原样字符串**比白名单。一处拒一处放确实存在，但方向是"发布闸更严"，不构成伪造件放行；实际后果是 A2 能跑通、发布时才炸的返工面。属工艺 WEAK。（严格来说是 U1 之前就有的旧账，本次未动。）

---

## 3. 攻击面 C：v3 点契约边界外一圈

命令：`PYTHONDONTWRITEBYTECODE=1 python3 /tmp/blindreview-u1/g3_contract.py`
四个执行点并排取证：`sign`=`anchor_plan._validate_probe_blocks`、`classify`=执行侧分型、`bqb`=`balance_query_block`、`gate`=`shared._plan_point`。

### V-21 33 组形态矩阵 —— DEFENDED（聚合）
逐行结果（节选，全量见脚本输出）：
```text
V18 day_end_block=-1            -> sign=REJ classify=REJ bqb=REJ gate=REJ
V19 day_end_block=True (bool)   -> sign=REJ classify=REJ bqb=REJ gate=REJ
V20 day_end_block=100.0 (float) -> sign=REJ classify=REJ bqb=REJ gate=REJ
V21 day_end_block='100' (str)   -> sign=REJ classify=REJ bqb=REJ gate=REJ
V27 final source, day != date_range[-1] -> 四处全 REJ
V28 final source in matrix_points       -> 四处全 REJ
V33 source='day_end_block​'(零宽空格) -> 四处全 REJ
V34 source='Day_End_Block'(大小写)         -> 四处全 REJ
V35 balance addr=''(falsy)                 -> 四处全 REJ
V39 tx + 'addr': None                      -> 四处全 REJ
V40 tx + day_end_block=5                   -> 四处全 REJ
V42 tx + balance_block_source='final_block'-> 四处全 REJ
V45 mixed balance+tx / V46 neither         -> 四处全 REJ
V47 point 是 list / V48 point 是 None      -> 四处全 REJ
```
枚举、类型（含 bool 陷阱）、位置（final 源只许 forced_points）、日期自洽、XOR 互斥、Unicode 变体、容器类型——**没有一个漏过**。`day_end_block=0` 与 `expected_balance_raw=0` 这两个"falsy 但合法"的边界被正确放行，没有误杀。

### V-22 禁用键按"键在场"判定（含 null 值）—— DEFENDED
```text
V22 balance + 'block': None            -> 四处全 REJ
V23 balance + 'tx': None               -> 四处全 REJ
V24 balance + 'expected_value_raw':None-> 四处全 REJ
V41 tx + expected_balance_raw=None     -> 四处全 REJ
```
与 docstring"a forbidden key with a null value is still forbidden"完全一致，注释与实现相符。

### V-23 不可哈希枚举值抛 TypeError 而非 ValueError —— WEAK
```text
V32 source=['day_end_block'] -> sign=REJ(TypeError) classify=REJ(TypeError) bqb=REJ(TypeError) gate=REJ(TypeError)
```
`source not in BALANCE_BLOCK_SOURCES` 对 list 抛 `TypeError: unhashable type`。四处调用方全部只 `except ValueError`（`anchor_plan.py:188`、`time_spotcheck.py:345/361`），异常会穿透。终态仍是非零退出（fail-closed），但错误类型契约破了，且施工方自己的 `_expect_reject` 只捕 ValueError——同型输入会让**测试本身报错**而不是记 PASS。建议在枚举判定前先 `isinstance(source, str)`。

### V-24 "正向白名单"名不副实：未知键一律放行 —— WEAK
```text
V25 balance + junk key 'final_block': 7 -> sign=OK classify=OK bqb=OK gate=OK
```
工单 §2.1 与施工报告都称 v3 是"正向白名单"，实现其实是"必填项 + 禁用键黑名单"，任意新增键（哪怕语义上会误导人，如点级 `final_block`）都能过。真正的关闭者是语义重放（V-31/V-33 会说明重放并非处处在场）。措辞应改为"必填+禁用键"，或补一条闭合键集。

### V-25 family 解析与 identity 语义 —— DEFENDED
```text
V50 family=None/''/'MATRIX_POINTS'/'points' -> 全 REJECTED(point family invalid)
V51 orphan point (不在 plan 内) -> REJECTED(point family invalid: None)
V52 同内容点同时出现在两个家族:
      forced member: ACCEPTED -> 300
      matrix member: REJECTED(final_block source is allowed only in forced_points)
```
`balance_query_block` 的 `is` 身份检索没被"同内容不同对象"骗到，family 白名单也是闭集。

---

## 4. 攻击面 D：v2 兼容路径与投影纪律

命令：`PYTHONDONTWRITEBYTECODE=1 python3 /tmp/blindreview-u1/g5_replay.py`、`g4_gate_depth.py`

### V-26 合法件不被误拒（含三份真实 NES 存量）—— DEFENDED
构造 v2 fixture 与真实存量两路对照。真实件复跑（只读 dry-run，未覆盖任何案例产物）：
```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/lib/time_spotcheck.py \
  --plan  "$N/bsc/anchors/anchor_plan.json" \
  --plan-receipt "$N/bsc/anchors/anchor_plan.receipt.json" \
  --input "$N/bsc/data/replay/merged.parquet" --dry-run --chain bsc \
  --token 0x3131f6b80c26936ab03f7d9d29eb4ddf36ac3fb5 --final-block 115516517 --out /tmp/...
```
```text
--- anchors ---         {"balance_points":1,  "tx_points":1,  "total":2,  "need_final_block":0} exit=0
--- bsc/anchors ---     {"balance_points":13, "tx_points":11, "total":24, "need_final_block":0} exit=0
--- ethereum/anchors ---{"balance_points":14, "tx_points":3,  "total":17, "need_final_block":1} exit=0
```
三份均 `anchor-plan/v2` + `plan_schema=anchor-plan/v2` + producer `e5168a…`，全绿，数值与施工报告 §5 完全一致。**v2 存量零误拒这条硬线成立。**

### V-27 投影纪律三路攻击：先断言后剥离 —— DEFENDED（本单元质量最高的一处）
分别让生成器（而非被验 plan）产出三种畸形，检验投影是否"静默擦干净"：
```text
V66 生成器多带一个 v3 专有键 -> REJECTED(matrix_points differs from deterministic replay (missing=1, extra=1))
V67 生成器把边缘点放进 matrix_points -> REJECTED(final_block source is allowed only in forced_points)
V68 生成器给 tx 点挂 balance_block_source -> REJECTED(tx point carries forbidden keys: balance_block_source)
```
工单 §2.4 三条纪律（只投影重算结果、先断言后剥、只剥一个键）逐条落实，没有 `pop(..., None)` 式静默兜底。这是全单元最经得起打的一处。

### V-28 v2 件携带"说谎的机器字段" —— WEAK
造一份 v2 计划，某余额点 `day_end_block=123` 却挂 `balance_block_source: "final_block"`（plan.final_block=300）：
```text
V60 v2 plan carrying a CONTRADICTORY machine field --
  load+classify: ACCEPTED -> final_block
  balance_query_block: ACCEPTED -> 123          ← 实际查 123，字段自称 final_block(300)
  gate _plan_point: ACCEPTED -> ('balance', …, 123, '100')
  semantic replay: REJECTED(matrix_points differs from deterministic replay)
```
执行侧分型、块解析、**发布闸深验全部放行**，唯一拦截者是语义重放；而发布闸从不跑重放（见 V-32/V-33）。v2 路径按设计忽略机器字段没错，但"件里带着一条与实际行为矛盾的机器声明还能过闸"是新引入的可读性/审计陷阱。建议：v2 分支显式拒绝携带 `balance_block_source` 的点（v2 生产者绝不会写这个键，拒了不会误伤存量——三份 NES 件实测均无此键）。

### V-29 v2 边缘点改名（v2 仍然吃文案）—— DEFENDED（等深）
```text
V59 v2_renamed_kind:
    gate deep-verify: REJECTED(time plan balance point missing day_end_block)
  executor dry-run: exit=2 :: 语义重放 forced_points differs (missing=5, extra=5)
```
两侧同拒。v2 依旧文案敏感是既定设计（工单 §0 要求 kind 一字不改），未构成新洞。

### V-30 `_point_multiset` 规范化特性 —— DEFENDED
```text
V62 NFD Unicode kind      -> 契约放行(kind 非语义 ✔)，重放 REJECTED
V63 day_end_block 写成浮点 -> REJECTED(requires a non-negative int)
V64 同一点重复一份         -> classify OK，重放 REJECTED(extra=1)
V65 点顺序打乱             -> 重放 ACCEPTED（multiset 语义，设计如此，顺序无义）
V69 matrix_points=None/{}/[[]] -> 全 REJECTED(must be a list of point objects)
V69 两家族清空             -> REJECTED(missing=4)
```
数值形态、重复点、Unicode、容器类型全部按预期。顺序不敏感是 Counter 的既定语义，不算洞。

---

## 5. 攻击面 E：plan 字节规范性（新机器字段的伪装面）

### V-31 重复 JSON 键：人看到 `final_block`，机器用 `day_end_block`，全链绿灯 —— **BREACH**

**攻击描述**：`json.loads` 对重复键取**最后一个**。把 plan 字节里某个余额点的 `"balance_block_source"` 复制一份放在前面、值改成 `final_block`，保留原来的 `day_end_block` 在后。人从上往下读这份**已签发**的计划，看到的是"该点在最终块查"；所有机器消费者拿到的是 `day_end_block`（块 123）。receipt 按新字节重签（size+sha256），其余一字不改。这份字节是**现行 producer 物理上不可能产出的**（`json.dumps` 不会产生重复键）。

**实跑命令**：
```bash
PYTHONDONTWRITEBYTECODE=1 python3 /tmp/blindreview-u1/g6_dupkey_kind.py
```

**输出摘要**：
```text
V71 duplicate-key plan bytes
   file shows FIRST occurrence  : final_block
   json.loads yields            : day_end_block -> probe block 123 (plan.final_block = 300 )
    executor load_validated_plan: ACCEPTED -> anchor-plan/v3
    executor semantic replay: ACCEPTED -> PASS
    gate authority chain: ACCEPTED -> anchor-plan/v3
    gate deep-verify (_validate_time_receipt): ACCEPTED -> PASS
  executor CLI dry-run: exit= 0 :: {"dry_run": true, "balance_points": 10, "tx_points": 3, "total": 13, ...}
```

**判定：BREACH**。语义重放 PASS（因为重放比的是 `json.loads` 之后的对象，与文件呈现无关）、权威链 PASS、**发布闸深验 PASS**、执行器 CLI 退出 0。全链没有任何一环要求 plan 字节是**规范可往返**的（`json.dumps(json.loads(b)) == b`）。

**为什么这次比 v2 时代更值钱**：v2 时代块源靠中文 kind 表达，人机看的是同一个字段；U1 把机器字段抬成唯一事实源之后，**"机器字段"本身成了可被视觉伪装的对象**，而伪装手法不留任何机器痕迹（哈希、size、probe_count、重放、闸，全部照过）。另外，不同语言的 JSON 解析器对重复键取舍不一（有取首个的实现），跨工具复核会得到互相矛盾的结论。

**建议修法**：在 `load_validated_plan` 与 `_validated_time_plan_authority` 读入 plan 时加一道规范性闸——用 `object_pairs_hook` 检测重复键直接拒，或断言 `json.dumps(plan, ensure_ascii=False, indent=2) + "\n" == 原始字节`（producer 就是这么写出去的，等价于"字节必须是本 producer 的规范输出"，顺带把一切非规范格式的手写件挡在外面）。

---

## 6. 攻击面 F：发布深验与执行侧的等深性

命令：`PYTHONDONTWRITEBYTECODE=1 python3 /tmp/blindreview-u1/g4_gate_depth.py`、`g8_producer_side.py`、`g4b_baseline.py`
方法：构造**完整自洽的时间抽查案**（真实签发 plan + receipt + 手造 rows/transcript），直接调 `shared._validate_time_receipt` 与执行器 CLI 对打。

### V-32 探测块越过冻结块：闸放、执行器拒 —— WEAK（旧账，本次未清）
```text
-- v54_block_beyond_final --
    gate deep-verify: ACCEPTED -> PASS         ← day_end_block = 10**9，冻结块 = 300
  executor dry-run: exit=2 :: 语义重放 matrix_points differs (missing=1, extra=1)
```
发布闸**全程没有任何"探测块 ≤ as_of_block"校验**（`grep -n "day_end_block|<= *final" scripts/report/shared_release_receipt.py` 只有取值三处，无边界判定）；执行器有两道（重放 + `time_spotcheck.py:370-373`）。
是否本次引入？用 `git archive 0ec6d1e` 拉基线原样复跑同一攻击：
```text
baseline producer schema: anchor-plan/v2
BASELINE 0ec6d1e gate deep-verify: ACCEPTED (block 10**9 vs cutoff 300)
```
**旧账，U1 未新增**。但本单元恰好重写了 `_plan_point` 并在测试矩阵里以"发布深验形态校验"命名，容易给人"闸已覆盖 v3 语义"的错觉——实际闸只验形状不验语义。

### V-33 同族四连：闸全放、只有重放拦得住 —— WEAK
```text
v55 tx block = -1                  -> gate ACCEPTED / executor exit=2
V85 矩阵点挪进 forced_points        -> gate authority ACCEPTED / 重放 REJECTED(missing=1)
V87 边缘点源翻成 day_end_block=0    -> gate ACCEPTED('balance',…,0,'100') / 重放 REJECTED
W3 expected_balance_raw 由 '100' 改成整数 100 -> gate 两个元组完全相同(str() 归一化) / 重放 REJECTED
V57 v2 标签但携带 v3 机器字段        -> gate ACCEPTED / 重放 REJECTED
```
根因同一个：**发布闸从不重放**（`grep -rn validate_semantic_replay scripts/` 仅 `time_spotcheck.py` 内部两处），它只校验"计划点 ↔ 收据行 ↔ transcript"的三方自洽。凡是"计划本身被改了、收据行跟着改"的攻击，闸一律看不见。这一层的真实防线是执行器留下的 time receipt——即闸信任"这份 time receipt 是执行器产的"。按本仓库 DIGEST1 工程确立的双写纪律（消费侧独立复验生产侧全部绑定），把"探测块边界"和"重放"两项补到闸上，才算真的等深。

### V-34 `final_block` 非整数：闸拒、执行器加载层收 —— WEAK
```text
V82 plan.final_block as a string at the gate:
    gate: REJECTED(target as_of_block/slot must be a non-negative integer)
    executor: ACCEPTED -> anchor-plan/v3     ← load_validated_plan 层
```
执行器 CLI 层还有 `time_spotcheck.py:354-358` 兜底（`isinstance(plan_final, int)`），终态 fail-closed；但 `load_validated_plan` 作为公开 API 不做该校验，与闸不等深。

### V-35 kind 文案免疫（比工单用例更狠的验法）—— DEFENDED（本单元立项目标达成）
工单用例 8 是"stub 掉生成器"来验；我改成**把 `anchor_selection.LEGACY_FINAL_BLOCK_EDGE_KIND` 常量真改掉，用真实生成器重新产计划**，再跑全链：
```text
V72 kind text immunity via the REAL generator (constant monkeypatched)
   renamed edge kind: 彻底改写的展示文案 v3
    sign _validate_probe_blocks: ACCEPTED -> OK
    classify: ACCEPTED -> (10, 3, 0)
    balance_query_block(edge): ACCEPTED -> 300
    gate _plan_point(edge): ACCEPTED -> ('balance','彻底改写的展示文案 v3',…,300,'100')
    semantic replay (same renamed generator): ACCEPTED -> PASS
    v2 projection of the SAME renamed plan: REJECTED(non-edge balance point missing day_end_block)
   constant restored: True | repo value: '门槛±10% 边缘地址'
```
v3 全链对文案完全免疫，v2 路径照旧文案敏感（对照组）。仓库内 `LEGACY_FINAL_BLOCK_EDGE_KIND` 值实测与 HEAD 一致，工单 §0"一字不改"遵守。

---

## 7. 攻击面 G：守卫、台账与整体回归

### V-36 "单源对账"守卫被稀释 —— WEAK
`test_time_spotcheck.py:306-313` 原本是**全局断言**："整张 manifest 里只有一个 producer 声称 anchor-plan 协议，且它是 anchor_plan.py"。U1 改成先按 `script == EXPECTED_PLAN_PRODUCER` 过滤再数，于是"是否存在第二个 anchor-plan producer"这个问题不再被回答。而且现实里**已经有第二个了**：
```text
receipt_producers:
    scripts/lib/anchor_plan.py    ['anchor-plan-input/v1','anchor-plan-receipt/v2','anchor-plan/v3']
    scripts/lib/time_spotcheck.py ['anchor-plan/v3','time-spotcheck/v3']   ← 它并不产 anchor plan
```
实跑（在 `git archive a2294e2` 的干净副本里注入第三个伪 producer）：
```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_time_spotcheck.py   # 注入后
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py
```
```text
injected bogus producer entry: scripts/report/build_html.py -> anchor-plan/v3
=== single-source guard after injection ===
ok    EXPECTED_PLAN_PRODUCER 与 invariant_manifest 单源对账     ← 守卫没看见
=== invariant_scan after injection ===
FAIL receipt_producers: manifest point missing from code: ('scripts/report/build_html.py', ('anchor-plan/v3',))
```
缓解项：`invariant_scan` 能抓"台账有、代码没有"的凭空条目。**未缓解项**：一个真的在代码里写了 `anchor-plan/v3` 的新脚本会被 `--dump-actual` 如实登记、通过 invariant_scan、并悄悄绕过被削窄的单源守卫——这正是该守卫当初存在的理由。建议改回全局语义（按 schema 过滤 + 断言唯一），并把 `time_spotcheck.py` 的 producer 面用 `exceptions` 显式豁免而不是靠改断言迁就。

### V-37 全量 suite 与不变量扫描 —— DEFENDED
```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py      # → 全部通过
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py
# PASS invariant manifest: receipt_producers=63, receipt_consumers=91,
#      transport_calls=63, atomic_writes=54, formal_entrypoints=58, exceptions=0
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_anchor_plan_v3.py   # 12/12 PASS
```
本机允许 loopback bind，**两个 vertical slice 测试也真跑通了**：施工报告 §6 里那 2 项 FAIL 确系 codex 沙箱能力限制，非断言失败——已代调度方核销。
残留扫描（排除 maintenance/tests/blind-reviews/archive）：现役代码里 `anchor-plan/v2` 仅剩 10 处，全部落在 `producer_history` 登记、`time_spotcheck` 兼容集合/历史查询/v2 投影分派、`shared_release_receipt` 配对矩阵与历史查询——逐条属兼容路径，**运行时文档（SKILL.md / references/ / commands/）零命中**，不存在漏改的现役 v2 producer。

### V-38 签发侧硬闸是真的 —— DEFENDED
```text
V83 producer CLI with --final-block below the data's max block (123):
   exit= 2 :: [anchor_plan] ERROR → .../anchor_plan.receipt.error.<ts>.json
   plan file written? False
V84 remove one point after signing:
    executor: REJECTED(plan receipt probe_count mismatch)
    gate:     REJECTED(plan receipt probe_count differs from consumed plan)
V86 executor CLI --final-block 299 against a plan frozen at 300:
   exit=2 :: [fatal] anchor_plan final_block 必须与 CLI --final-block 精确一致
```
越界不签、不落 plan 文件、落错误 receipt；点数绑定两侧等深；CLI 与签发件的冻结块强耦合。

---

## 8. 总评：哪些面最薄

按"最薄 → 最厚"排序：

1. **plan 字节的规范性（最薄，BREACH V-31）**——全链只验哈希不验字节形态。U1 把 `balance_block_source` 抬成机器唯一事实源，却没有同步要求"这份字节必须是本 producer 的规范输出"，于是新字段本身成了可视觉伪装的对象，且伪装不留机器痕迹。**一行 `object_pairs_hook` 或一次 round-trip 断言即可关闭**，性价比最高。
2. **登记表的 `protocol` 列在消费端形同虚设（BREACH V-01）**——查询接口做对了（按 script+protocol 过滤、REVOKED hash-wide 否决），两个调用点却把协议写死成 v2，导致 v3 计划可以挂 v2 时代 producer 签名。修法明确：协议随被验 plan 的 schema 动态传入。
3. **发布闸与执行侧的深度差（WEAK V-32/V-33/V-34，旧账）**——闸只做"计划↔收据↔transcript"三方自洽，不重放、不校验探测块是否越过冻结块。我构造的五种计划篡改（越界块、负块号、块源翻转到块 0、跨家族搬点、数值retype）**全部过闸**，只有执行器的语义重放拦得住。基线 0ec6d1e 复跑证实是旧账，但本单元重写了 `_plan_point` 又没顺手补，且测试矩阵的命名容易让人以为闸已覆盖 v3 语义。
4. **分派默认分支的 fail-open（WEAK V-17/V-18）**——三处 `if v3 … else 传统语义`；更糟的是发布闸那处的失败模式**静默且恰好答对**（回退路径靠 kind 文案猜出同一个块号），等于本单元想根除的"依赖文案"在错误处理路径上活了下来。
5. **登记表自身的完整性纪律（WEAK V-11/V-04/V-06/V-12）**——"git 可复现"只由一条会自我禁用（无 `.git` 即跳过）的测试断言守着；REVOKED 管不到当前哈希；status 拼写走样静默丢失撤销力；commit 形态不统一。运行时对这张表是全盘信任。
6. **守卫迁就实现（WEAK V-36）**——单源对账断言为了容纳一条事实不准的 manifest producer 条目而被削窄，丢掉了它原本回答的那个问题。

**做得好、经得起打的部分（点名表扬，不是客套）**：
- v2 投影"先按 v3 契约断言、再只剥一个键"的三条纪律**实现到位**，三路生成器投毒全部大声失败（V-27）——这是本单元最硬的一块。
- 点形态契约本体（枚举/类型/bool 陷阱/位置/日期自洽/XOR/禁用键按在场判定）33 组边界外攻击**零漏过、零误杀**（V-21/V-22）。
- kind 文案免疫在"真改常量 + 真生成器"的更狠验法下依然成立（V-35），立项目标达成。
- v2 存量零误拒是真的，三份真实 NES 件全绿且数值与施工报告逐项吻合；并且已实证这不是巧合——清空登记表它们立刻被拒（V-10/V-26）。
- 放宽面严格局限：其他 producer、其他 receipt 类型、默认路径语义均未被波及（V-08/V-09）。

**给调度方的最小修复清单（按优先级）**：
1. plan 读入处加字节规范性闸（拒重复键 / round-trip 断言）——关 V-31。
2. `historical_producer_hashes` 的 protocol 参数改为按被验 plan schema 动态传入——关 V-01。
3. 三处 `else` 分派改为白名单显式分派、未知 schema 抛错；发布闸的裸字面量与 `time_spotcheck.PLAN_SCHEMA` 收敛到单一常量——关 V-17/V-18。
4. v2 分支显式拒绝携带 `balance_block_source` 的点（实测三份 NES 存量件均无此键，零误伤）——关 V-28。
5. `balance_block_source_of` 枚举判定前加 `isinstance(source, str)`，把 TypeError 收成 ValueError——关 V-23。
6. 单源对账守卫改回全局语义 + 用 manifest `exceptions` 显式豁免 time_spotcheck 的 producer 面——关 V-36。
7. （旧账，可另立单元）发布闸补"探测块 ≤ as_of_block"与语义重放——关 V-32/V-33。

---

### 附：复现材料
所有攻击脚本与夹具保留在 `/tmp/blindreview-u1/`：
`atk.py`（公共夹具：真实签发 plan、重签 receipt、闸调用封装）、`g1_producer.py`（A 面）、`g2_pairing.py`（B 面）、`g3_contract.py`（C 面）、`g4_gate_depth.py` + `g4b_baseline.py`（F 面含 0ec6d1e 基线对照）、`g5_replay.py`（D/E 面）、`g6_dupkey_kind.py`（V-31/V-35）、`g7_registry.py`（A 面守卫 + 漂移）、`g8_producer_side.py`（G 面签发闸）、`g9_final.py`（REVOKED/缺文件/类型归一化）。
基线副本 `/tmp/blindreview-u1/oldrepo`（`git archive 0ec6d1e`）与干净副本 `/tmp/blindreview-u1/mcopy`（`git archive a2294e2`）均为只读导出，仓库工作树全程 clean。
