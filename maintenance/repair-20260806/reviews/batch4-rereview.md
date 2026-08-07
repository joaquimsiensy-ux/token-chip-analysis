# 批四消化 —— 聚焦重审报告

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r8-closure-worktree`，分支 `fix/r8-closure-20260806`
- **HEAD 核验**：`0f53b68e4596c84539b2370a8c8e73a84412317a`（符合工单 tip=0f53b68），`git status --porcelain` 为空
- **区间**：`6b7ab8d..0f53b68`，两 commit（B4F-G1 `13d76c0` / 回填 `0f53b68`），5 文件、+154/-14
- **纪律**：仓库零写入（注入全在 `mktemp -d` realpath 根的仓库副本内），所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`，未读 main 基线

---

## 一、总裁决

**PASS**。

| 定级 | 数量 |
|---|---:|
| P0 | 0 |
| P1 | 0 |
| P2 | 0 |
| P3 | 0 |

**新引入 0，半修残留 0，历史漏检 0。**

两项 P3 与两项观察全部闭合，且修复深度均超出我提出的最低要求：labels 第八面收编后双向对表（多链/漏链都红）、派生源诊断覆盖到我未要求的第四类（整键删除）、方法论补条的措辞精确复述了我踩坑的形态。全量 suite 80/80 `EXIT=0`，仓库零污染。

---

## 二、上轮 finding 闭合总表

| 上轮编号 | 定级 | 本轮状态 | 依据 |
|---|---|---|---|
| B4R-01 | P3 | **已闭合** | 第八面 `accumulate_offenders.py` 收编，注入未注册链与漏链**双向**均红；原七面绿例不误伤 |
| B4R-02 | P3 | **已闭合** | 三类派生源不同步全部产出明确诊断、零 Traceback；另测第四类（整键删除）同样守住 |
| OB-K | 观察 | **已落地** | `batch4-report` 裸池措辞收窄，明示 `import ... as` 别名与 `getattr` 不在可见范围、威胁模型为防误用 |
| OB-L | 观察 | **已落地** | 方法论第七节 +1 行"注入须自证到达目标分支"，措辞与我踩的坑一致 |

---

## 三、复测与边界核验明细

### 3.1 labels 第八面对照注入（工单重点 1）

全部在仓库副本内、每组独立副本。

| # | 构造 | rc | 实测命中 | 判定 |
|---|---|---:|---|---|
| 0 | 基线未改动 | 0 | — | **不误报** |
| 1 | 第八面注入 `polygon`（**上轮漏检点**） | 1 | `FAIL labels surface scripts/labels/accumulate_offenders.py:membership:chain:1 has unregistered chains ['polygon']` | **守住** |
| 2 | 第八面摘 `robinhood` | 1 | `... missing labels_table chains ['robinhood']` | **守住**（双向对表） |
| 3 | 原七面之一（`build_goldset.py`）注入 `polygon` | 1 | `... build_goldset.py:membership:chain:2 has unregistered chains ['polygon']` | **不误伤** |

实现侧确认：`_surface_values` 的 locator 判据由硬编码 `== "membership:chain:2"` 泛化为 `startswith("membership:chain:")`，期望条数从 locator 末尾解析（`int(locator.rsplit(":", 1)[1])`）。泛化正确——第八面按 `:1` 只要求一处 membership，`build_goldset` 按 `:2` 仍要求两处，任一数量不符即报 `expected N list(s), got M`。

### 3.2 "无第九面"自报独立核验（工单重点 2）

用我首轮同一字面复列法重跑 `rg` 后，全库 `scripts/labels/*.py` 的**链清单声明面**恰为 8 个，与守卫登记逐一对应：

| # | 面 | 守卫登记 |
|---:|---|:--:|
| 1 | `labels_resolver.py:44` `KNOWN_CHAINS` | ✓ known |
| 2 | `gen_manual_from_addressbook.py:21` `CHAINS` | ✓ known |
| 3 | `build_labels.py:26` `BUILD_CHAINS` | ✓ table |
| 4 | `benchmark_labels.py:24` `EXPECTED_CHAINS` | ✓ table |
| 5 | `roundtrip_check.py:25` `CHAINS` | ✓ table |
| 6 | `goplus_check.py:60` argparse `--chain` | ✓ table |
| 7 | `build_goldset.py:87,187` membership×2 | ✓ table（`:2`） |
| 8 | `accumulate_offenders.py:249` membership×1 | ✓ table（`:1`，本轮新增） |

其余 `rg` 命中经逐条判读均**不是**链支持声明面，故不构成第九面：
- **别名映射表**（外部名→内部 canonical）：`build_goldset.py:31`、`accumulate_offenders.py:165` 的 `CHAIN_MAP`，`build_labels.py:24` `CHAIN_BY_ID`、`:487` `DUNE_CHAIN`，`goplus_check.py:26` `CHAIN_ID`；
- **外部服务能力表**：`sourcify_check.py:31` `CHAIN_IDS`（Sourcify 支持的链含 polygon，与本仓库链清单无关）；
- **业务子集字面量**：`build_labels.py:190/248/349/359/377/481`（特定数据源只覆盖部分链）。

这与施工方在 `fix_v635_stage2` 中"保留字面并登记"的排除体例一致。**"无第九面"自报核验通过。**

### 3.3 派生源诊断质量（工单重点 3）

| # | 注入 | rc | 诊断文本 | Traceback |
|---|---|---:|---|:--:|
| 4 | `ACCOUNTING_PRODUCERS = {}` | 1 | `formal entrypoint derived source ACCOUNTING_PRODUCERS missing families ['evm', 'solana']; registry and shared_release_receipt are out of sync` | 无 |
| 5 | family 缺失（删 `solana` 条目） | 1 | `... missing families ['solana']; ... out of sync` | 无 |
| 6 | `RECON_RUNNERS = set()` | 1 | `... RECON_RUNNERS is empty; ... out of sync` | 无 |
| 7 | **整键删除** `ADVERSARIAL_RUNNERS`（我加测的第四类） | 1 | `... missing keys ['ADVERSARIAL_RUNNERS']; ... out of sync` | 无 |

四类全部产出带"两侧不同步"的明确诊断，**无裸 Traceback**。机制上，`registered_formal_entrypoints` 抛 `FormalEntrypointSourceError`，由 `scan_actual` 捕获转入 `actual["_scanner_errors"]`，再由 `validate_manifest` 并入 errors 列表——与其余守卫的错误形态统一。

**正常路径不变**：`registered_formal_entrypoints()` 仍返回 **16 项**，与批四首轮一致。

### 3.4 新反例真实性

- `B4F-LABEL-03`：真改临时副本的第八面加 `polygon`，断言同时含 `accumulate_offenders.py`、`unregistered`、`polygon` 三个文本 ✓
- `B4F-FORMAL-01`：通过新增的 `shared_path=` 参数注入临时 `shared_release_receipt.py`（不动仓库），先断言 `actual["_scanner_errors"]` 命中，再断言 `validate_manifest` 的 errors 同时含 `ACCOUNTING_PRODUCERS`、`registry`、`shared_release_receipt` —— **断言的是诊断文本而非仅非零退出**，正是方法论本轮新补那一条的自我践行 ✓

### 3.5 方法论新条目与措辞修正（工单重点 4）

- 方法论：`numstat` = **1 行新增、0 行删除**，内容为
  > **注入须自证到达目标分支。** 破坏性注入若被路径防护等前置闸拦下，看似"守住"实为未测到目标；注入脚本必须先证明真的走到被测分支再谈结论。
  
  与我 OB-L 的建议一致，且"被路径防护等前置闸拦下"精确对应我批三两次踩坑（`/var/folders` symlink、预建 `.partial` 目录）的真实形态，**无美化、无夸大**。
- `batch4-report`：原"任一……**裸池**……都会追加 scanner error"中的"裸池"已从绝对列表移除，另起一句限定为"只抓 AST 中以 `RpcPool` 名或 `.RpcPool` 属性出现的直接构造；`import ... as` 别名和 `getattr` 动态取用不在可见范围，威胁模型是防误用、不是防恶意规避"。**与实现完全一致**，OB-K 闭合。

### 3.6 未映射 hunk 复算（工单重点 5）

| 分组 / SHA | map 登记 | 实际 `--stat` | 一致 |
|---|---:|---:|:--:|
| B4F-G1 `13d76c0` | 5（`invariant_scan.py`、`test_batch4_invariant_guards.py`、`batch4-report.md`、`diff-finding-map.md`、`maintenance-review-repair.md`） | 5（逐一吻合） | ✓ |
| 回填 `0f53b68` | 自指式 | 1（map 自身） | ✓ |

**未映射 hunk = 0，清单与 commit 边界逐文件吻合。** 批四主区间已按通例定格为 `f2a6e41..6b7ab8d`，消化区间沿用自指写法。

### 3.7 全量回归（工单重点 6）

`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` → `全部通过`，`EXIT=0`，PASS 计数 **80**。

---

## 四、执行命令清单

```bash
git -C <worktree> rev-parse HEAD                      # 0f53b68e4596...
git -C <worktree> diff --stat 6b7ab8d..0f53b68        # 5 files, +154/-14
git -C <worktree> diff --numstat 6b7ab8d..0f53b68 -- references/maintenance-review-repair.md   # 1 0
git -C <worktree> show --stat --format="" 13d76c0 0f53b68   # 映射复算

# 独立复列（"无第九面"核验，与首轮同一方法）
rg -n "'eth'.*'bsc'|\"eth\".*\"bsc\"|'eth'.*'base'|'sol'.*'robinhood'" --glob 'scripts/labels/*.py' .

# 破坏性注入（仓库副本，realpath 根，全部 PYTHONDONTWRITEBYTECODE=1）
python3 $RT/v.py <copy>   # 基线 + labels×3 + 派生源×4 共 8 组

# 机器判据
python3 -c "... LABEL_CHAIN_SURFACES 八面枚举 + registered_formal_entrypoints() 计数 ..."

# 全量回归与收尾
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py   # 全部通过 EXIT=0（80）
git -C <worktree> status --porcelain                         # 空
```

---

## 五、复核方自我声明

- 仓库全程零写入：所有注入在 `shutil.copytree` 副本内进行；起止 `git status --porcelain` 均为空。
- 临时件位于 `mktemp -d` 的 realpath 解析根，所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`。
- 未与施工线程通信；未读 main 基线、`~/.codex/`、MEMORY 或历史案例目录。
- 每条论断均先 Read 磁盘真实文件后作出；本轮无未实测项。
- 本轮为聚焦重审，非全库扫描——"PASS"仅意味着在工单指定的六项范围内未照出问题。
