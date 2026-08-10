# 批二「能力矩阵」批内消化 —— 增量重审报告（第二轮）

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r8-closure-worktree`，分支 `fix/r8-closure-20260806`
- **HEAD 核验**：`3ca824e933fead2765e54d1b871817f4f8ba6159`（符合工单 tip=3ca824e），`git status --short` 为空
- **消化区间**：`5924cd5..3ca824e`，四 commit（B2F-G1 `138b707` / B2F-G2 `ee7d4d5` / B2F-G3 `af92a91` / SHA 回填 `3ca824e`），14 文件、+1043/-77
- **复核方**：Opus 5 独立只读复核子代理。仓库零写入，临时件全在 `mktemp -d`，所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`，未读主仓库 main 基线
- **本轮性质**：增量重审。重点不是复述上轮，而是①验证上轮五项 finding + 两项观察是否真闭合；②攻击**修复代码自身**是否引入新洞

---

## 一、总裁决

**BLOCK**（程序性阻断，收口成本极低）。

| 定级 | 数量 | 编号 |
|---|---:|---|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 0 | — |
| P3 | 4 | B2FR-01、B2FR-02、B2FR-03、B2FR-04 |
| 观察（非 finding） | 3 | OB-E、OB-F、OB-G |

**归因分布：新引入 4，半修残留 0，历史漏检 0。**

阻断依据是 PLAN《分层收口》"新引入，任意严重度 → 修复并重审"与最终要求"新引入=0"。四项全为 P3，其中 2 项纯台账（B2FR-03/04）、1 项工作流摩擦不涉安全（B2FR-02）、1 项深度防御层被绕但下游三重独立拦截（B2FR-01）。

**上轮 P2 已闭合，核心不变量比上轮更强**：legacy 通道新增 registry tier 长期语义准入闸，上轮两个反例（robinhood legacy READY、三重不符）现均 rc=2；同时存量旧案不误伤（v1/v2 合法案仍 rc=0）。严格路径 C0–C10 十一变体行为逐条不变，全量 suite 76/76 全绿。

---

## 二、本轮发现清单

### B2FR-01 ｜ P3 ｜ 主视角①字段来源审计 ｜ 归因：**新引入**（`138b707`）

**legacy「在场」判据取自 manifest 自报的 artifacts 清单，把 wrapper 条目摘掉即可绕过新增的深验（伪缺席）**

文件行号：`scripts/report/handoff_manifest.py:328-343`

```python
    art_paths = {item.get("path") for item in manifest.get("artifacts") or []
                 if isinstance(item, dict)}
    # Legacy only waives absent Batch-2 artifacts.  If the wrapper is listed, it
    # is evidence and must pass the same current deep validator and scope bind.
    if not legacy or "reconciliation_report.json" in art_paths:
```

判据是 manifest 清单，不是磁盘实际存在。攻击者把 `reconciliation_report.json` 从 `artifacts` 摘掉、同时从 `gates` 摘掉 `reconciliation_four_checks`，**磁盘文件仍留在案目录且内容已篡改**，深验即被跳过。

**最小复现（实测 rc=0）**：

```
构造：make_case + generate READY → 手改 manifest:
      consumer_min_schema='handoff/v2'
      artifacts 删除 reconciliation_report.json 条目
      gates 删除 reconciliation_four_checks
      磁盘上保留 reconciliation_report.json，并把 target.chain 改为 'robinhood'
命令：verify --case-dir <d> --legacy-read-only
输出：rc = 0
      [verify] ⚠ LEGACY READ-ONLY：handoff/v2 旧格式仅供读取既有冻结结论……
```

对照组 RL8（同样篡改但**保留登记**）：rc=2，`reconciliation_report.json 深验失败: reconciliation bal...` —— 证明"在场即深验"在登记路径上有效，缺口只在自报判据。

**测试盲区实证**：新测试 `scripts/tests/test_batch2_legacy_hardening.py:23-29` 的 `rewrite_legacy(keep_reconciliation=False)` 摘登记的**同时**执行 `(case_dir / "reconciliation_report.json").unlink()`，因此只覆盖"真缺席"，从未构造"伪缺席"。

**危害边界（实测已限）**：scope 链仍受新 tier 闸约束（robinhood 在 `scope.chains` 位置会被拒，见 RL1）；legacy 案落 marker 后 `audit_release_gate` 拒编正式 analysis；`freeze` 严格 verify 拒 legacy。绕过所得与合法"真缺席"路径完全等价，非权限提升，故定 P3 而非 P2。

**修复建议（一行）**：判据改为磁盘在场或清单登记二者取或——

```python
    wrapper_present = ("reconciliation_report.json" in art_paths
                       or os.path.isfile(os.path.join(case_dir, "reconciliation_report.json")))
    if not legacy or wrapper_present:
```

并在 `test_batch2_legacy_hardening.py` 补一条"伪缺席"负例（摘登记但不删文件）。

---

### B2FR-02 ｜ P3 ｜ 主视角⑤双向一致性（次④同族调用面）｜ 归因：**新引入**（`138b707`）

**`generate` 与 `verify` 对 `scope.chains` 的判据口径不一致，generate 产出的 manifest 过不了自己的 verify**

文件行号：
- `scripts/report/handoff_manifest.py:174-176`（generate 侧，集合去重语义，未随本轮改动）
- `scripts/report/handoff_manifest.py:419-424`（verify 侧，本轮改为列表长度语义）

generate 侧判重复用 `set()`：

```python
        if len(set(chains)) != 1:
            print("[generate] READY 当前只接受单链 scope；reconciliation target 必须唯一", file=sys.stderr)
            return 2
```

verify 侧本轮收严为列表恰一元素：

```python
        raw_chains = scope.get("chains")
        if not isinstance(raw_chains, list) or len(raw_chains) != 1 \
                or not isinstance(raw_chains[0], str) or not raw_chains[0].strip():
```

`--chain bsc,bsc` 经 `:169` 展开为 `['bsc','bsc']`，`set()` 长度为 1 故 generate 放行，但写入 manifest 的是二元素列表，verify 必拒。

**最小复现（实测）**：

```
命令：generate --case-dir <d> --status READY --chain bsc,bsc --contract 0x0 ...
输出：generate rc = 0，manifest scope.chains = ['bsc', 'bsc']
命令：verify --case-dir <d>
输出：rc = 2 | ✗ READY scope.chains 必须恰有一个非空字符串链名
```

方向为"更严"不是放行，无安全危害；属 −1 交付方以为 READY、−2 开工才发现的工作流摩擦与口径漂移。新测试 `test_batch2_legacy_hardening.py:56-57` 的 scope 变体用的是 `["bsc","eth"]`（两个不同链），未覆盖同链重复这一路径。

**修复建议**：`cmd_generate` 写入前去重规范化，`chains = sorted({resolve_alias(c) for c in ...})`，使 manifest 恒存单元素列表；两侧口径统一。

---

### B2FR-03 ｜ P3 ｜ 主视角⑤双向一致性 ｜ 归因：**新引入**（`af92a91`）

**台账主表与分组表漏列 `reviews/batch2-review.md`，且报告 §8.5 称「`reviews/` 零改动」与该 commit 新增 484 行文件并存**

事实核验：
- `git show --stat af92a91` 实际 4 文件，含 `maintenance/repair-20260806/reviews/batch2-review.md`（+484）
- `git log --diff-filter=A` 确认 `af92a91` 即该文件的新增 commit
- `diff-finding-map.md` 主表 B2F-G3 行文件清单只列 `run_all.py`、`diff-finding-map.md`、`batch2-report.md` 三项
- `batch2-report.md` §8.4 分组表同样只列三项；§8.5 明写"`reviews/` 零改动"

部分登记情况（从宽记录）：map 的「分组→SHA 对照」表第 45 行写有"+opus 批二审查报告入库"，commit message 亦写明。

**内容完整性已独立验证**：入库版与我上轮提交的 scratchpad 原版 484 行**逐字一致**（`diff` 无输出），未被篡改。

**修复建议**：主表 B2F-G3 行与 §8.4 补列该文件；§8.5 表述改为"`reviews/` 仅新增审查报告入库，既有内容零改动"。

---

### B2FR-04 ｜ P3 ｜ 主视角⑤双向一致性 ｜ 归因：**新引入**（`af92a91`）

**未映射 hunk 区间标注末端又写成中间 commit，上轮 OB-D 的同族问题在新区间重犯**

文件行号：`maintenance/repair-20260806/diff-finding-map.md:52`

```
- 批二批内消化（`5924cd5..af92a91`）：`0` 候选（所有新 hunk 已归属 `B2F-G1`～`B2F-G3`；待增量重审独立复算）。
```

候选 tip 是 `3ca824e`，区间末端却写 `af92a91`。上轮 OB-D 指出的批二区间标注问题**已修正**（第 51 行现为 `553806b..5924cd5`，正确），但新写的消化区间重复同一错误形态——属方法论所称"同族要关到同一深度"未做到。

`3ca824e` 本身只改 `diff-finding-map.md` 自身（SHA 回填），属自指式归属，不含生产/测试 hunk，故实质未映射 hunk 仍为 0。

**修复建议**：区间改为 `5924cd5..3ca824e`，并在表下加一句通例说明"末端恒取候选 tip，自指式 SHA 回填 commit 计入本区间"。

---

## 三、观察（非 finding，不计入裁决）

- **OB-E**：`chain_registry.py:197-200` 的 `_registered_record` 对非 `str` 抛 `TypeError`，`formal_ready(None)` 由原先返回 `False` 变为抛异常。实测生产调用面安全——`audit_release_gate.formal_chain_error` 经 `normalize_chain`/`resolve_alias` 恒转字符串，对 `None`/`''`/`123` 均正常返回拒绝理由。但若未来有人直连传 `None`，将得到 exit 1（脚本自身错误）而非 exit 2（验证不通过）。属可接受的 fail-closed 权衡，建议在 docstring 注明。
- **OB-F**：`scripts/tests/test_batch2_registry_harness_hardening.py:74` 以源码字符串匹配验证字节码防护——`assert 'child_env.setdefault("PYTHONDONTWRITEBYTECODE", "1")' in source`。换等价写法（单引号）会假红，若该行后被覆盖则假绿。属测试质量，非生产缺陷。
- **OB-G**：`audit_release_gate.py:747-749` 的 legacy marker 只查 case 目录根，子目录内同名文件不触发（实测确认）。设计内且绕过无收益——marker 是加法防御，删掉它不获得任何权限，`formal_ready` 与 `validate_bundle` 两道独立闸仍在。

---

## 四、L1/L4 复测与存量不误伤（工单重点 1）

上轮 B2R-01 的两个反例现均被拒；同时新增的 tier 闸未误伤存量旧案。全部为子进程黑盒调 CLI，`rc` 为进程退出码。

| # | 构造 | rc | 拒绝/放行理由（实测尾部） | 期望 | 结论 |
|---|---|---:|---|---|---|
| RL1 | legacy + `scope.chains=['robinhood']`（上轮 L1，原 rc=0） | 2 | `✗ legacy READY scope 链为 exploration` | 拒 | **守住**（已闭合） |
| RL2 | legacy + 链/token/wrapper 三重不符（上轮 L4，原 rc=0） | 2 | `✗ legacy READY scope 链为 exploration` | 拒 | **守住**（已闭合） |
| RL3 | **合法旧案**：bsc（formal tier）+ wrapper 真缺席 + 案内自洽 | 0 | `⚠ LEGACY READ-ONLY：handoff/v2 旧格式仅供读取既有冻结结论……` | 放行 | **守住**（不误伤存量） |
| RL8 | legacy + wrapper 登记在册且 target 跨链篡改为 sol | 2 | `✗ reconciliation_report.json 深验失败: reconciliation bal…` | 拒 | **守住**（在场即深验） |

**legacy tier 准入四分支边界**（B2F-G1 新代码的核心分支，`handoff_manifest.py:428-436`）：

| 链 | registry 语义 | rc | 实测理由 | 结论 |
|---|---|---:|---|---|
| `arbitrum` | exploration | 2 | `✗ legacy READY scope 链为 exploration，拒绝正式回流` | **守住** |
| `polygon` | unsupported | 2 | `✗ legacy READY scope 链非 formal tier` | **守住** |
| `nosuchchain` | 未登记 | 2 | `✗ legacy READY scope 链未登记: nosuchchain` | **守住** |
| `ETHEREUM` | 别名 → eth，formal tier | 0 | LEGACY READ-ONLY 正常放行 | **守住**（别名解析正确，未误伤） |

设计要点确认：legacy 准入读的是 registry **长期 `release_tier`**，而非批三前恒为空集的 `READY_CHAINS`——若用后者，全部存量旧案将被误杀。该取舍正确，RL3 与 `ETHEREUM` 两例即为其正面证据。

---

## 五、C0–C10 严格路径不回退（工单重点 1）

上轮 11 个变体全部原样重跑（同一构造、同一"先改产物再 generate"手法，以排除哈希漂移闸的干扰）。**逐条与上轮完全一致，零回归**。

| # | 构造 | 上轮 rc | 本轮 rc | 结论 |
|---|---|---:|---:|---|
| C0 | 基线未改动（应放行） | 0 | 0 | 一致（证明非"全拒"假象） |
| C1 | wrapper 只剩三查（删 time） | 2 | 2 | 一致 |
| C2 | balance producer sha 伪造 | 2 | 2 | 一致 |
| C3 | wrapper runner 换非白名单（真实哈希） | 2 | 2 | 一致 |
| C4 | 跨链复用 BSC wrapper → sol READY | 2 | 2 | 一致 |
| C5 | receipt 篡改、登记 sha 不同步 | 2 | 2 | 一致 |
| C6 | receipt FAIL / wrapper PASS（哈希已同步） | 2 | 2 | 一致 |
| C7 | target.token ≠ scope.contract | 2 | 2 | 一致 |
| C8 | sol target 配 evm producer | 2 | 2 | 一致 |
| C9 | balance `checked=0` 空对账 | 2 | 2 | 一致 |
| C10 | supply_truth `mode=exploration` | 2 | 2 | 一致 |

**关于「READY scope.chains 必须恰有一个非空字符串链名」收严对严格路径的影响**（工单重点 3 指定项）：C0 基线正例仍 rc=0，说明 `GEN` 常量产出的单链 manifest 不受影响；严格路径 fixture 未被误伤。唯一暴露的口径缺口是 generate 侧未同步去重（见 B2FR-02），且该缺口只在 `--chain` 传入重复链名时才触发，正常单链调用无感。

**全量 suite**：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` → `全部通过`，`EXIT=0`，**76/76 PASS**（`run_all.py` 本轮新挂 `test_batch2_legacy_hardening.py`、`test_batch2_registry_harness_hardening.py` 两项，74→76）。与修复方 `batch2-report.md` §8.5 自报一致，本次为我独立复跑所得。

**批一边界不回退**：`test_batch1_rpc_attestation.py` 在 suite 内 PASS。本轮未触碰 `net.py`；`chain_registry` 的 API 收严只影响 readiness 三函数的入参类型，`attested_rpc_pool` 走 `evm_chain_id_for`（未改），错链零业务调用契约不受影响。

---

## 六、B2R-02/03/04 修复质量核验（工单重点 2）

### 6.1 B2R-02 —— readiness 公开 API 收口

`chain_registry.py:197-200` 新增守门函数，`_record_from` 已整体删除：

```python
def _registered_record(value):
    if not isinstance(value, str):
        raise TypeError("formal readiness APIs require a registry chain name string")
    return get_chain_config(value)
```

| 核验项 | 实测 | 结论 |
|---|---|---|
| `missing_formal_capabilities(伪造 Mapping)` | `TypeError: formal readiness APIs require a registry chain name string` | **守住** |
| `record_is_formal_ready(伪造 Mapping)` | 同上 `TypeError` | **守住** |
| `formal_ready(伪造 Mapping)` | 同上 `TypeError` | **守住** |
| `_record_from` 符号残留 | `hasattr(cr,'_record_from') = False` | **已清除** |
| 调用面回归 `formal_chain_error(None/''/123)` | 分别返回 `chain=<missing> 未进入正式支持矩阵` ×2、`chain=123 未进入…`，无异常 | **守住**（经 `resolve_alias` 恒转 str） |
| `formal_chain_error('robinhood'/'polygon'/'bsc'/'arbitrum')` | exploration / 未进入矩阵 / 缺 `vertical_slice_verified` / arbitrum 探索档，四种理由各归其位 | **守住** |

上轮的自报 record 入口已迁为显式测试面 `formal_ready_test_harness.fixture_missing_formal_capabilities`（`:53-56`），命名含 `fixture`、docstring 标注 "test-only"、内部调私有 `_missing_formal_capabilities_from_record`。符合上轮修复建议。

### 6.2 B2R-03 —— harness 可逆化

`formal_ready_test_harness.py:32-50` 改为 `@contextmanager`，`finally` 恢复原对象；`_readonly_registry`（`:22-29`）逐层包 `MappingProxyType`。旧名 `activate_test_vertical_slices` 已删。

| 核验项 | 实测 | 结论 |
|---|---|---|
| 旧名残留 | `hasattr(H,'activate_test_vertical_slices') = False` | **已清除** |
| 激活中 readiness | `['base','bsc','eth','sol']`（fixture 正例可用） | 符合设计 |
| 激活中三层类型 | top/rec/caps 均 `mappingproxy` | **守住** |
| 激活中三层赋值 | top=只读、record=只读、caps=只读（均 `TypeError`） | **守住** |
| 正常退出后 | `CHAIN_REGISTRY is original = True`；`formal_ready_chains() == set()` | **守住**（恢复同一原对象，非等值副本） |
| 异常路径退出后 | 抛 `RuntimeError` 后同样 `is original = True`、`== set()` | **守住** |
| 字母序 import 泄漏（上轮反例） | import `test_audit_release_gate` 后 readiness 仍 `set()`；`test_batch2_capability_matrix` 核心断言**通过** | **守住**（上轮此处 FAILED） |
| 二次叠加 import `test_round4_a5_seal` | readiness 仍 `set()`，断言再次通过 | **守住** |

### 6.3 B2R-04 —— 子进程字节码防护

`formal_ready_test_harness.py:73` 补 `child_env.setdefault("PYTHONDONTWRITEBYTECODE", "1")`。用 `setdefault` 而非 `[...]=` 保留了调用方覆盖能力，方向正确。本轮复核全程结束后 `find` 确认仓库无 `.pyc` / `__pycache__` 残留。

对应测试断言为源码字符串匹配（见 OB-F），属弱断言但不影响生产行为正确性。

### 6.4 上轮 finding 闭合总表

| 上轮编号 | 定级 | 本轮状态 | 依据 |
|---|---|---|---|
| B2R-01 | P2 | **已闭合** | RL1/RL2 转 rc=2；tier 四分支全守；RL3 存量不误伤 |
| B2R-02 | P3 | **已闭合** | 三 API 全拒 Mapping，`_record_from` 删除 |
| B2R-03 | P3 | **已闭合** | contextmanager 可逆、三层只读、字母序零泄漏 |
| B2R-04 | P3 | **已闭合** | `setdefault` 已补 |
| B2R-05 | P3 | **已闭合** | map B2-G0 行已补 `BUILD_CHAINS` 注释的 owner 与 secondary `INV-11` |
| OB-A | 观察 | **已闭合** | `audit_release_gate.py:747-749` 建立真实消费点，四边界实测守住 |
| OB-D | 观察 | **已闭合但同族重犯** | 批二区间已修正为 `553806b..5924cd5`；新消化区间又写 `..af92a91` → B2FR-04 |
| OB-B / OB-C | 观察 | 维持原状（批四 / 威胁模型外） | map B2F-G3 行已登记"记录 `OB-B, OB-C`" |

---

## 七、新代码边界外一步核验（工单重点 3 —— 本轮核心价值）

方法论第 24 行："修 bug 的代码是重灾区，不是安全区。"以下攻击全部针对 B2F 三个 commit **新写的**代码，站在修复方自带反例的边界之外。

### 7.1 legacy tier 准入分支的边界

| 攻击 | 实测 | 结论 |
|---|---|---|
| `resolve_alias` 怪异输入：`ETHEREUM` 大写别名 | 解析为 `eth`（formal tier）→ rc=0 放行 | **守住**（未误伤别名） |
| 未登记链名 `nosuchchain` → `get_chain_config` 返回 None 分支 | `✗ legacy READY scope 链未登记` | **守住**（None 分支有专门处理，未 `AttributeError`） |
| `chains` 集合空路径：`scope.chains = []` | 拒（新测试 `test_batch2_legacy_hardening.py:57` 亦覆盖） | **守住** |
| `chains` 多元素路径：`['bsc','eth']` | 拒 | **守住** |
| `chains` 多元素**同链重复**：`['bsc','bsc']` | verify 拒，但 generate 放行 → 口径不一致 | **缺口** → B2FR-02 |
| `scope.contract` 空串 | 拒 | **守住** |

### 7.2 audit_release_gate legacy marker 的误伤与可绕

`audit_release_gate.py:747-749`，判据 `legacy_marker.exists() or legacy_marker.is_symlink()`：

| 攻击 | marker 错误命中 | 结论 |
|---|:--:|---|
| 正常案（无 marker） | 否 | **守住**（不误伤，正常案本就不该有该文件） |
| marker 为普通文件 | 是 | **守住** |
| marker 为 **broken symlink**（`.exists()` 返 False 的经典绕法） | 是 | **守住**（`or is_symlink()` 正是为此而加） |
| marker 置于子目录 | 否 | 设计内，见 OB-G（绕过无收益） |

### 7.3 handoff verify 非 legacy 路径是否被意外改变

`verify_case` 的 scope 检查由 `if not legacy_mode and status == "READY"` 改为 `if status == "READY"`（对两种模式统一生效）。核验其对严格路径的影响：C0 基线正例仍 rc=0，C1–C10 十条负例 rc 全部不变（见第五节）。**严格路径行为未被意外改变。**

### 7.4 「在场即深验」判据的可操纵性 —— 本轮最有价值的攻击

修复方的设计意图是"缺席可豁免、在场必深验"。我构造了介于二者之间的第三态：**文件在磁盘、登记已摘除**（伪缺席）。

| 对照组 | wrapper 磁盘 | wrapper 登记 | rc | 说明 |
|---|:--:|:--:|---:|---|
| RL3 真缺席（合法旧案） | 无 | 无 | 0 | 设计内放行 |
| RL8 在场且篡改 | 有 | 有 | 2 | 深验生效 |
| **RL7 伪缺席** | **有（已篡改为 robinhood）** | **无** | **0** | **深验被跳过** → B2FR-01 |

新测试之所以没抓到：`test_batch2_legacy_hardening.py:23-29` 的 `rewrite_legacy(keep_reconciliation=False)` 在摘登记的同一分支里执行了 `unlink()`，两个动作被绑死，第三态在测试空间中不可达。

### 7.5 registry API 收严的行为面变化

`formal_ready(None)` 由返回 `False` 变为抛 `TypeError`（见 OB-E）。已实测生产四类调用面（`formal_chain_error`、`check_formal_case_chain`、`handoff` 的 `formal_ready_chains()` 内部遍历、`identity_snapshot_receipt` 的 `identity_chains()`）均传字符串或注册表键，无异常路径。**未发现生产回归。**

---

## 八、未映射 hunk 独立复算（工单重点 4）

区间 `5924cd5..3ca824e`，`git diff --stat` 合计 **14 文件**。逐 commit 与 `diff-finding-map.md` 的 B2F-G1～G3 行比对：

| 分组 / SHA | map 主表登记文件 | `git show --stat` 实际 | 差异 |
|---|---:|---:|---|
| B2F-G1 `138b707` | 3 | 3 | 一致 |
| B2F-G2 `ee7d4d5` | 7 | 7 | 一致 |
| B2F-G3 `af92a91` | 3 | **4** | **漏列 `maintenance/repair-20260806/reviews/batch2-review.md`（+484）** |
| SHA 回填 `3ca824e` | —（自指） | 1（`diff-finding-map.md` 自身） | 自指式归属 |

**复算结果**：生产代码与测试 hunk **未映射 = 0**；文档/元数据 hunk 有 1 份文件在主表漏列（`reviews/batch2-review.md`），已记为 **B2FR-03**。

从宽认定的缓解事实：该文件在 map 第 45 行「分组→SHA 对照」表的 B2F-G3 说明中以"+opus 批二审查报告入库"形式出现，commit message 亦写明，故属"部分登记、主表漏列"而非无主夹带。

**逐 hunk 夹带检查**：三个生产文件（`chain_registry.py` +27/-? 、`handoff_manifest.py` +60/-? 、`audit_release_gate.py` +4）的改动全部落在 B2R-01/02 的修复面内，无顺手整理、无历史文档段改写、无与本轮 owner 无关的改动。测试侧七个文件的改动均为 harness 改名适配（`activate_test_vertical_slices` → `with test_vertical_slices()`）或新增反例，名实相符。

**区间标注问题**：map 第 52 行把消化区间写作 `5924cd5..af92a91`，末端非候选 tip `3ca824e` → **B2FR-04**。因 `3ca824e` 仅含本表自身的 SHA 回填，实质未映射 hunk 仍为 0。

---

## 九、台账一致性比对（工单重点 5）

上轮我抓到一处自报不实（`batch2-report.md:71` 称 harness"只在独立测试进程中"）。本轮以同一标准逐条核对 §8 批内消化章节的红绿证据与 map 修正。

| 修复方陈述 | 出处 | 我的独立核验 | 判定 |
|---|---|---|---|
| §2 表述修正为"独立子进程或同进程受控 `contextmanager` 作用域内…并在 `finally` 恢复原三层只读矩阵" | `batch2-report.md` §2 | 与 `formal_ready_test_harness.py:32-50` 代码一致；R4 实测三层只读 + 正常/异常路径均恢复原对象 | **属实**（上轮不实表述已修正） |
| B2R-01 红证据：旧代码上 LG-01/LG-02/OB-A 三项失败 | §8.2 | 与我上轮实测吻合（L1/L4 原 rc=0；OB-A 原无消费点，rg 确认零消费者） | **属实** |
| "`B2F-LG-03` 对 v1/v2 各回放一个 bsc 案…legacy verify 仍 `rc=0`" | §8.2 | RL3 独立复现 rc=0 | **属实** |
| "审查表 C0–C10 所在严格契约 65 项全绿，行为未回退" | §8.2 | C 表 11 变体独立复测逐条一致 | **属实** |
| B2R-02 绿证据：三公开 API 均抛 `TypeError` | §8.2 | R1 独立复现 | **属实** |
| B2R-03 绿证据：退出后 `formal_ready_chains()==set()` 且恢复原对象、三层赋值均失败、字母序 import 无泄漏 | §8.2 | R4/R5 独立复现（含异常路径） | **属实** |
| B2R-04 绿证据：补 `setdefault` | §8.2 | 代码 `:73` 确认；仓库无字节码残留 | **属实** |
| "76/76 PASS，EXIT=0" | §8.5 | 独立复跑 `run_all.py` → `全部通过`，`EXIT=0`，76 项 | **属实** |
| "legacy 豁免粒度收紧为『新件缺席可豁免』，而非『旧 schema 全面免验』" | §8.1 | 设计意图属实且主路径生效；但"缺席"判据可被自报操纵（B2FR-01），实现未完全兑现该表述 | **部分属实** |
| "`reviews/` 零改动" | §8.5 | 该 commit 新增 `reviews/batch2-review.md`（+484 行）；在"既有内容未改"意义上成立，字面易误读 | **表述有张力** → B2FR-03 |

**审查报告入库完整性**：入库的 `maintenance/repair-20260806/reviews/batch2-review.md` 与我上轮提交的 scratchpad 原版 `diff` **无输出**，484 行逐字一致，**未被篡改或删改**。

**map 的上轮欠账处理**：B2-G0 行已按我 B2R-05 的建议补入 `BUILD_CHAINS` 注释 owner 与 secondary `INV-11`（第 22 行改动属实）；批二区间已按 OB-D 修正为 `553806b..5924cd5`。两项均已兑现。

---

## 十、执行命令清单

```bash
# HEAD 与区间
git -C <worktree> rev-parse HEAD                       # 3ca824e933fe...
git -C <worktree> log --oneline 5924cd5..3ca824e
git -C <worktree> diff --stat 5924cd5..3ca824e         # 14 files, +1043/-77
git -C <worktree> show --stat --format="" <各 SHA>     # 映射复算
git -C <worktree> log --oneline --diff-filter=A -- maintenance/repair-20260806/reviews/batch2-review.md

# 生产改动逐份精读（Read 磁盘真实文件）
scripts/lib/chain_registry.py            # _registered_record / _record_from 删除
scripts/report/handoff_manifest.py       # art_paths 判据、scope 收严、legacy tier 分支
scripts/report/audit_release_gate.py     # LEGACY_READONLY_RECEIPT marker
scripts/tests/formal_ready_test_harness.py            # contextmanager + setdefault
scripts/tests/test_batch2_legacy_hardening.py         # 新反例覆盖面
scripts/tests/test_batch2_registry_harness_hardening.py

# 动态攻击（mktemp -d，全部 PYTHONDONTWRITEBYTECODE=1）
python3 $TD/re_registry.py    # R1-R3 API 收口 + 调用面回归
python3 $TD/re_harness2.py    # R4-R6 可逆性/字母序泄漏/fixture 后门
python3 $TD/re_legacy.py      # RL1-RL9 legacy 复测 + tier 四分支 + 伪缺席 + 口径不一致
python3 $TD/re_strict.py      # C0-C10 不回退 + marker 四边界

# 全量回归与收尾自查
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py    # 全部通过 EXIT=0（76）
git -C <worktree> status --porcelain                          # 空
find <worktree> \( -name "__pycache__" -o -name "*.pyc" \) -not -path "*/.git/*"   # 空
diff <scratchpad 原版> maintenance/repair-20260806/reviews/batch2-review.md        # 无输出
```

**方法自纠记录**：R4 首两次探测 `MappingProxyType` 可写性时误用 `.__setitem__` 与 `.update`，两者在 mappingproxy 上均不存在（抛 `AttributeError` 而非 `TypeError`），导致脚本中断。第三次改用下标赋值语句（需 `def` 而非 `lambda`）后取得正确结论。该失误本身反向印证了只读性——mappingproxy 连变更方法都未暴露。

---

## 十一、复核方自我声明

- 仓库全程零写入：起止 `git status --porcelain` 均为空；收尾 `find` 确认无 `.pyc` / `__pycache__` 残留。
- 未与修复线程通信；未读 `~/.codex/`、MEMORY、rollout、历史案例记忆目录；未读主仓库 main 基线。
- 本轮每条论断均先 Read 磁盘真实文件后作出，行号以本次重读为准；上一轮的幻觉教训（凭印象描述不存在的 `ChainRecord` 结构）在本轮未复发。
- 四项发现均附最小复现构造、实测 rc 与输出尾部；无凭印象补全的代码摘录。
