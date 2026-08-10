# 批三消化 —— 增量重审报告（批三第二循环）

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r8-closure-worktree`，分支 `fix/r8-closure-20260806`
- **HEAD 核验**：`a0481e2df262e7d87a1a63d23816489a7a06d812`（符合工单 tip=a0481e2），`git status --porcelain` 为空
- **区间**：`3df1234..a0481e2`，四 commit（B3F-G1 `75d112f` / B3F-G2 `7c04b72` / B3F-G3 `a85974d` / 回填 `a0481e2`），9 文件、+216/-25
- **纪律**：仓库零写入，临时件全在 `mktemp -d` 的 realpath 根，所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`，未读 main 基线

---

## 一、总裁决

**BLOCK**（纯台账精度问题；代码侧本轮零发现）。

| 定级 | 数量 | 编号 |
|---|---:|---|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 0 | — |
| P3 | 1 | B3FR-01（台账，零代码风险） |

**归因分布：新引入 1（台账），半修残留 0，历史漏检 0。**

**给裁决方的止损计数建议**：本轮唯一发现是 `diff-finding-map.md` / `batch3-report.md` 的逻辑分组与 commit 边界错位，**不触及任何生产代码或测试正确性**。上轮两项代码 finding（B3R-01 P2、B3R-02 P3）经我独立复测**全部真实闭合**，且修复质量高于我提出的最低要求（双 producer 同族等深、撤回中间态 fail-closed、边界外一步四项全守）。若止损线以"代码新引入"为计数口径，本轮宜视为通过、台账问题并入下一批台账维护；若严格按"任何新引入"计数，则为 BLOCK。我按后者给裁决，同时提供前者所需的事实依据。

---

## 二、上轮 finding 闭合总表

| 上轮编号 | 定级 | 本轮状态 | 依据 |
|---|---|---|---|
| B3R-01 | P2 | **已闭合** | window/anchor 双注入实测，四项终态断言全满足；中间态 fail-closed |
| B3R-02 | P3 | **已闭合** | 2 元组分支 `rg` 零命中；五处 mock 全改 3 元组；timestamps 检查到达目标分支 |
| B3R-03 | P3 | **已闭合** | B3-G3 行的 `test_batch3_evm_vertical_slice.py` 已删除（`grep` 计数 0） |
| B3R-Q1 | P3（批四） | **已登记** | ledger 记入批四双条件守卫，与 B1R-01、OB-B 并列 |
| OB-H | 观察 | **已落地** | report §10.3 如实论证 resume 退化是联合事务的直接代价，不粉饰、留后续 checkpoint 设计 |
| OB-I | 观察 | **已落地** | `transport-injections.json` allowed_reason 已收窄，明示端到端只跑 `time_spotcheck`、逐调用点由批一承担 |
| OB-J | 观察 | **已落地** | report §10.3 记录 `/query` 计数盲区，并明确"扩展到 accounting_gate 前必须先补计数" |

---

## 三、本轮发现

### B3FR-01 ｜ P3 ｜ 主视角⑤双向一致性 ｜ 归因：**新引入**（`a85974d`）

**逻辑分组 B3F-G2 与实际 commit 边界错位：其声称的生产侧 hunk 实际落在 B3F-G1 的 commit 中**

实测逐 commit 文件清单：

```
--- 75d112f (B3F-G1) ---        --- 7c04b72 (B3F-G2) ---
scripts/solana/anchor_sampler.py        scripts/tests/test_r7_findings.py
scripts/solana/window_fetch.py          scripts/tests/test_sixlens_receipts.py
scripts/tests/test_batch3_solana_producers.py
```

而 `diff-finding-map.md` 的 B3F-G2 行登记为：

```
| `B3F-G2:scripts/solana/window_fetch.py; scripts/tests/{test_batch3_solana_producers.py,
   test_sixlens_receipts.py,test_r7_findings.py}` | `INV-09` | owner `B3R-02` | ...
```

`batch3-report.md` §10.4 分组表同样如此登记。而「分组→SHA 对照」表把 B3F-G2 映射到 `7c04b72`。

**事实**：B3R-02 的生产侧改动（删除 2 元组兼容分支、新增 timestamps min/max 检查）与其反例 `B3F-TS-01`，**全部提交在 `75d112f` 里**（我核对 `git diff 3df1234..a0481e2 -- window_fetch.py` 确认三类改动同处一个 diff）；`7c04b72` 只含两个历史测试文件的 mock 三元组化。因此读者按 B3F-G2 行去 `7c04b72` 查找 `window_fetch.py` 与 `test_batch3_solana_producers.py` 的改动会落空。commit message 的描述（`7c04b72` = "删 2 元组兼容分支+timestamps 证据闭环"）同样与其实际内容错位。

**性质界定**：PLAN 允许"一个 hunk 涉及多个不变量时拆行、同一 commit 可有多行"，所以同一文件出现在两行本身合规；问题在于**分组→SHA 的可追溯性断了**——B3F-G2 名下的一部分 hunk 不在 B3F-G2 对应的 SHA 内。

**对未映射 hunk 计数的影响：无。** 9 个文件的全部 hunk 均有 owner 认领（B3R-01 与 B3R-02 各自的改动都被登记），未映射 hunk = 0。

**同族重犯提示**：这是上轮 B3R-03 的同一模式——修复方去掉了旧行（B3-G3）的冗余，但新写的 B3F-G2 行又出现同类错位。与我第二轮抓的 B2FR-04（区间标注在新区间重犯）属同一类流程病：**修了被点名的那一处，新写的同类内容没套用同一规则**。建议在 map 表头加一条硬规则："分组行的文件清单必须与该分组 SHA 的 `git show --stat` 逐一对齐；跨分组的同文件改动按 hunk 拆行并各自注明所在 SHA。"

**修复建议**：二选一——(a) 把 B3F-G2 行的文件清单收敛为其 SHA 实际含有的两个测试文件，并在 B3F-G1 行注明其 `window_fetch.py` hunk 同时承载 B3R-01 与 B3R-02 两个 owner；(b) 若希望保持逻辑分组语义，则在「分组→SHA 对照」表为 B3F-G2 标注"生产侧 hunk 见 `75d112f`"。

---

## 四、注入构造复测（工单重点 1）

用**我自己的** `inject.py` 场景独立复跑（未复用修复方的 `B3F-TXN-01/02`）：monkeypatch `publish_txn` 使其落盘内容 ≠ `data_bytes`，从而让提交后的独立读者自检失败。

### 4.1 四项终态断言

| 组 | exit | 数据在正式位 | receipt.json | error receipt | partial |
|---|---:|---|---|---|---|
| window 基线（无注入） | **0** | 是（正常产物） | 存在，verdict=**PASS** | 无 | 无 |
| **window 注入** | **1** | **否** | **不存在** | **在场，verdict=ERROR** | 在场 |
| anchor 基线（无注入） | **0** | 是（正常产物） | 存在，verdict=**PASS** | 无 | 无 |
| **anchor 注入**（上轮未实测，本轮补） | **1** | **否** | **不存在** | **在场，verdict=ERROR** | 在场 |

window 注入实测输出：

```
[window_fetch] 检测/提交失败（exit 1）: 联合发布后独立读者哈希不一致
  数据在正式位: False
  receipt.json 存在: False
  error receipt 在场: True | verdict=ERROR
  目录: ['config.json','edges.jsonl.gaps.json','edges.jsonl.partial',
         'receipt.error.20260807T104258.284470Z.80673.json']
```

anchor 注入实测输出（补上轮静态判定）：

```
[anchor_sampler] receipt 生成失败（exit 1）: 联合发布后独立读者哈希不一致
  数据在正式位: False
  receipt.json 存在: False
  error receipt 在场: True | verdict=ERROR
  目录: ['anchor.receipt.error.20260807T104258.458196Z.80681.json',
         'anchors.jsonl.partial','config.json']
```

**结论：B3R-01 完全闭合，且两个 producer 同族关到同一深度**——上轮我按④视角静态判定 anchor 为同构缺口，本轮实测证实其修复与 window 等深，未出现"只修主入口"的老病。基线两组仍 exit=0、双产物正常，修复未误伤正常路径。

### 4.2 撤回逻辑自身的边界外一步（工单重点 2）

**中间态：receipt 已删、数据移位失败。** 运行期 monkeypatch 制造撤回步骤失败（window 拦 `os.replace` 到 `.partial`；anchor 拦 `publish_overwrite` 写 `.partial`）：

| 组 | exit | 数据仍在正式位 | receipt.json | error receipt | 错误文本含"撤回失败" |
|---|---:|---|---|---|---|
| window midfail | 1 | 是（撤回失败） | **不存在** | 在场，ERROR | **是** |
| anchor midfail | 1 | 是（撤回失败） | **不存在** | 在场，ERROR | **是** |

实测错误文本：`联合发布后独立读者哈希不一致; 撤回失败: data: simulated: cannot move data out`

**终态评估：仍 fail-closed，设计正确。** 关键在于**先删 receipt、再移数据**的顺序——即使数据撤回失败，canonical PASS 声明已被消灭，落盘终态是"数据残留但无回执"。按本仓库纪律无回执即不可消费，且 error receipt 如实记录了撤回失败原因，运维可据此人工处置。这是"尽力撤回 + 绝不留 PASS + 如实上报"的正确组合；若顺序颠倒（先移数据后删 receipt），中间态就会出现"数据已移走但 PASS receipt 仍在"的更坏形态。

**`_publish_error` / `_error_receipt` 在 receipt.json 已被 unlink 后的旁写行为**：正常。两者写的是 `<receipt_stem>.error.<ts>.<pid>.json` 独立文件，不依赖 canonical receipt 是否存在；四组注入实测均成功落盘且 `verdict=ERROR`。

**anchor 用 `publish_overwrite(partial, RawBytes(out.read_bytes()))` 再 `out.unlink()` 的窗口风险（如实评估）**：该写法先把正式位内容**复制**到 `.partial`，成功后才删除正式位，存在一个"两处都有该数据"的短暂窗口。与 window 的 `os.replace`（原子移动、无双份窗口）相比确实弱一档。但收益评估为**可接受**：①窗口内正式位的 receipt 已被删除，数据无回执不可消费；②若在窗口内崩溃，终态是"正式位有数据、partial 有副本、无 canonical receipt"，仍不构成可消费的正式产物；③anchor 无法直接用 `os.replace`，因为它此前用 `publish_txn` 发布、`.partial` 路径需经 kernel 的安全目标检查才能写入。故不判为缺陷。

**附带正面发现**：本轮把 `partial` 纳入 `assert_distinct_paths(out, args.receipt, partial)`（anchor 新增）。我最初用"预先把 `.partial` 建成非空目录"来制造撤回失败时，两个 producer 都在**入口**即 `exit 2` 并报 `output destination is not a regular file`，根本没进入被测路径——这是该新增检查在真实文件系统上生效的旁证（也是我不得不改用运行期注入的原因）。

---

## 五、timestamps 闭环的边界（工单重点 3）

### 5.1 并发完整性

`window_fetch.py:182-194`：

```python
    def work(seg):
        e, ok, timestamps = scan_seg(seg[0], seg[1], args.endpoint)
        with lock:
            ...
            segment_timestamps.append({"from_slot": seg[0], "to_slot": seg[1],
                                       "min": min(timestamps) if timestamps else None,
                                       "max": max(timestamps) if timestamps else None})
```

`append` 在 `with lock:` 内，与 `outf.write` / `gaps.append` 共用同一把锁——**并发安全**。

数量核对的时机（`:197-203`）在 `list(ex.map(work, segs))` **之后**，所有工作线程已 join，`segment_timestamps` 已收敛：

```python
        with ThreadPoolExecutor(args.conc) as ex:
            list(ex.map(work, segs))
        outf.flush(); os.fsync(outf.fileno()); outf.close()
        if not gaps and (len(segment_timestamps) != len(segs) or any(
                item["min"] is None or item["max"] is None
                for item in segment_timestamps)):
            raise RuntimeError("complete segment 缺少 timestamp min/max 证据")
```

**时机正确**，不存在"边跑边判"的竞态。

### 5.2 有 gaps 的 FAIL 路径不受误伤

实测（`scan_seg` 返回 `ok=False`）：

```
FAIL 1 segs (1 gaps) -> edges.jsonl.partial
  exit=2 | 数据在正式位: False | receipt.json 存在: True verdict=FAIL | partial 在场
```

新检查以 `if not gaps and (...)` 为前置，FAIL 路径整体跳过，**未误伤**；FAIL receipt 仍正常落 canonical 位置（这是既有语义，数据留 `.partial` 不进正式位）。

### 5.3 B3F-TS-01 是否真到达目标分支

我用自己的构造（`scan_seg` 返回 `([], True, [])`，即 complete 但零时间戳）实测：

```
[window_fetch] 检测/提交失败（exit 1）: complete segment 缺少 timestamp min/max 证据
  exit=1 | 数据在正式位: False | receipt.json 存在: False | error receipt: ERROR
```

错误文本与新检查的 `RuntimeError` 字面一致，**确认到达目标分支**。且因该检查位于 `publish_txn` **之前**（`committed=False`），数据从未进入正式位、canonical receipt 从未生成——比事后撤回更干净的位置选择。

---

## 六、既有测试不回退（工单重点 4）

| 项 | 核验 | 结论 |
|---|---|---|
| 2 元组兼容分支残留 | `rg "len\(result\) == 2\|legacy test adapter"` → **零命中** | 已删净 |
| 五处历史 mock 三元组化 | `test_sixlens_receipts.py:232/244/251/258` + `test_r7_findings.py:199` 全部改为 `(edges, ok, timestamps)` | 全改 |
| `test_sixlens_receipts` disk-full 分支（`:251-262`） | mock 对象仍是 `publish_overwrite`（发生在 `committed=True` 之前，不触发事后撤回）；两条核心断言**原样保留**：`assert not out.exists(), "receipt 写失败前已发布正式 window 文件"` 与 `assert out.read_bytes() == before, "刷新失败未恢复旧 window 正式文件"` | 强度不变 |
| `test_r7_findings` stale 分支（`:196-202`） | 仅 mock 返回值补第三元素，`rc != 2 or old.exists() or not stale` 断言不变 | 强度不变 |
| 全量 suite | `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` → `全部通过`，`EXIT=0`，PASS 计数 **79** | 通过 |

新增三个反例（`B3F-TXN-01/02`、`B3F-TS-01`）挂在既有 `test_batch3_solana_producers.py` 内部，故 SUITE 项数仍为 79（不是 79+3），与 report §10.5 自报一致。

**未发现任何断言被放松或删除。**

---

## 七、未映射 hunk 独立复算（工单重点 5）

| 分组 / SHA | map 登记 | 实际 `--stat` | 差异 |
|---|---:|---:|---|
| B3F-G1 `75d112f` | 3 | 3 | 一致 |
| B3F-G2 `7c04b72` | **4** | **2** | **分组与 SHA 边界错位** → B3FR-01 |
| B3F-G3 `a85974d` | 4 | 4 | 一致 |
| 回填 `a0481e2` | 自指式 | 1（map 自身） | 一致 |

区间合计 9 文件（3+2+4+1=10，`diff-finding-map.md` 在 `a85974d` 与 `a0481e2` 各改一次，去重后 9，与 `git diff --stat` 吻合）。

**复算结果：未映射 hunk = 0**（所有 hunk 均有 owner 认领）。唯一偏差是分组→SHA 可追溯性，已记 B3FR-01。

批三主区间已按工单定格为 `62efbf9..3df1234`，消化区间沿用自指写法，与第三轮确立的通例一致 ✓。

---

## 八、台账一致性比对（工单重点 6）

| 修复方陈述 | 我的独立核验 | 判定 |
|---|---|---|
| B3R-01 红证据：冻结实现下"正式 data 仍在"被断言捕获 | 与我上轮注入实测一致 | **属实** |
| 修复顺序"receipt 撤回尝试始终先于 data 撤回" | 代码与 midfail 实测均确认 | **属实** |
| "任一撤回异常并入 ERROR 信息并保持非零退出" | midfail 实测：错误文本含 `撤回失败: data: ...`，exit=1 | **属实** |
| "window 原 `published_current`/`backup` 恒假死分支已删除" | `rg` 确认两符号已不存在 | **属实** |
| "`receipt_kernel.py` 零改动" | 本区间 `--stat` 无该文件 | **属实** |
| "disk full 分支继续绿；该分支发生在 `committed=True` 之前" | 代码位置与 suite 均确认 | **属实** |
| B3R-02："删除 2 元组兼容分支；五处历史 mock 全部改为三元组" | `rg` 双向确认 | **属实** |
| OB-H/I/J 三项落地 | report §10.3 + transport allowed_reason 逐条对表 | **属实** |
| 批四守卫 B3R-Q1 已登记 ledger | 已见登记，与 B1R-01、OB-B 并列 | **属实** |
| "79/79 PASS，EXIT=0" | 独立复跑一致 | **属实** |
| §10.4 分组表文件清单 | B3F-G2 含两个实归 B3F-G1 commit 的文件 | **不实** → B3FR-01 |

本轮抓到一处台账不实，与前四轮同一标准（前四轮分别为：harness"只在独立测试进程"、"reviews/ 零改动"、B2F-G3 清单漏列、B3-G3 清单冗余）。

---

## 九、执行命令清单

```bash
git -C <worktree> rev-parse HEAD                      # a0481e2df262...
git -C <worktree> diff --stat 3df1234..a0481e2        # 9 files, +216/-25
git -C <worktree> show --stat --format="" <各 SHA>    # 映射复算（逐文件名比对）
git -C <worktree> log --oneline 3df1234..a0481e2 -- <文件>   # 定位实际 commit

# 静态核查
rg -n "len\(result\) == 2|legacy test adapter" scripts/      # 兼容分支残留 → 零命中
rg -n 'scan_seg", return_value=' scripts/tests/              # 五处 mock 三元组化
rg -n "published_current|backup" scripts/solana/window_fetch.py   # 死变量已删

# 动态验证（mktemp -d 的 realpath 根，全部 PYTHONDONTWRITEBYTECODE=1）
python3 $RT/re3.py <root> normal  window     # 基线 exit=0
python3 $RT/re3.py <root> inject  window     # 注入：撤回四项断言
python3 $RT/re3.py <root> normal  anchor     # 基线 exit=0
python3 $RT/re3.py <root> inject  anchor     # 注入：同族等深（补上轮未实测）
python3 $RT/re3.py <root> tsempty window     # B3F-TS-01 目标分支
python3 $RT/re3.py <root> gaps    window     # FAIL 路径不受新检查误伤
python3 $RT/mid.py <root> window|anchor      # 撤回中间态（运行期注入撤回失败）

# 全量回归与收尾
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py   # 全部通过 EXIT=0（79）
git -C <worktree> status --porcelain                         # 空
```

**方法自纠两处**：①首轮批量调用用 `set -- $spec` 传参未生效，导致四组实验全部跑成 `anchor` + 空 mode，输出自相雷同才被发现——改为显式传参重跑。②中间态测试最初用"预建 `.partial` 目录"制造撤回失败，被入口的 `assert_distinct_paths` 拦下（exit 2），未进入被测路径；改用运行期 monkeypatch `os.replace` / `publish_overwrite` 才命中目标分支。两次都是"看似有结论、实则没到达被测代码"的假结果，已在得出结论前自查纠正。

---

## 十、复核方自我声明

- 仓库全程零写入：起止 `git status --porcelain` 均为空，无 `.pyc` / `__pycache__` 残留。
- 临时件全部位于 `mktemp -d` 的 realpath 解析根，所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`。
- 未与施工线程通信；未读 main 基线、`~/.codex/`、MEMORY 或历史案例目录。
- 每条论断均先 Read 磁盘真实文件后作出；本轮**无未实测项**——上轮标注为静态判定的 anchor 同构缺口已补实测。
- 本轮为聚焦增量重审，非全库扫描；"BLOCK" 仅就本区间与工单指定重点而言，且已在第一节说明其性质为纯台账、零代码风险。
