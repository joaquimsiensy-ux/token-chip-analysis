# 批二「能力矩阵」独立复核报告

- **审查对象**：`/Users/uravvv/Documents/5.6筹码分析/r8-closure-worktree`，分支 `fix/r8-closure-20260806`
- **HEAD 核验**：`5924cd58b2c270bd0b2389c8e7fc8f3c83d10929`（以 `5924cd5` 开头，符合工单），工作区 `git status --short` 为空
- **批二区间**：`553806b..5924cd5`，六 commit 齐备（B2-G0 `8f3600c` / B2-G1 `f6844bf` / B2-G2 `2a9d5ed` / B2-G3 `5ef3186` / B2-G4 `07fab90` / SHA 回填 `5924cd5`）
- **复核方**：Opus 5 独立只读复核子代理。仓库零写入，全部临时件在 `mktemp -d`，所有 Python 调用带 `PYTHONDONTWRITEBYTECODE=1`
- **纪律声明**：全部发现在读取修复方自报材料（`batch2-report.md` / `diff-finding-map.md` / `robinhood-impact.md` / `ledger.md`）**之前**独立冻结，自报材料仅用于归因比对，未作为"已修复"证据

### 过程更正（如实记录）

本次复核前期我曾输出过一段 `chain_registry.py` 的"ChainRecord / tuple 结构"描述，该内容**在任何分支上都不存在**，是凭印象补全而非磁盘读取所得，已全部作废。此后每条论断均以本次重读的磁盘文件为准，行号以重读为准。真实结构为 `CHAIN_REGISTRY = MappingProxyType({...})`（`scripts/lib/chain_registry.py:75`）。

---

## 一、总裁决

**BLOCK**（程序性阻断，非设计失败）。

核心不变量——"formal-ready 必须由真实能力闭合导出，不得有任何同义手工/测试开关让链在无批三纵切片证据时表现为 ready"——**经我最强攻击未被击穿**。阻断理由是 PLAN《分层收口》表的硬性纪律：新引入与半修残留**任意严重度**均须"修复并重审"，而本批存在 1 项半修残留（P2）与 3 项新引入（P3）。四项均为边缘面、可快速修复，不涉及能力矩阵主干重做。

| 定级 | 数量 | 编号 |
|---|---:|---|
| P0 | 0 | — |
| P1 | 0 | — |
| P2 | 1 | B2R-01 |
| P3 | 4 | B2R-02、B2R-03、B2R-04、B2R-05 |
| 范围外观察 | 4 | OB-A ～ OB-D |

**核心不变量正面证据**：`formal_ready_chains()` 返回空集，全 16 条链 `formal_ready()` 均为 False，`eth` 的唯一缺口是 `vertical_slice_verified`；生产代码对 `formal_ready_test_harness` 零 import；无第二处手工 formal 开关；`MappingProxyType` 三层（顶层/record/capabilities）常规赋值全部 `TypeError`。

---

## 二、六视角逐条结论

### ① 字段来源审计——关键字段来自原始数据还是自报

检查文件：`scripts/lib/chain_registry.py`（全文 281 行）、`scripts/report/shared_release_receipt.py`（全文 296 行）、`scripts/report/handoff_manifest.py`（全文 1032 行）、`scripts/report/audit_release_gate.py`（全文 830 行）。

**守住的主干**：reconciliation 深验验的是**当前仓库脚本真实哈希**，不是调用方自报。`shared_release_receipt.py:68-78`：

```python
def repo_ref_ok(ref, allowed, label):
    if not isinstance(ref, dict):
        raise ValueError(f"{label} producer/runner ref missing")
    rel = str(ref.get("path", ""))
    if rel not in allowed:
        raise ValueError(f"{label} producer/runner path is not whitelisted: {rel}")
    path = (REPO / rel).resolve()
    path.relative_to(REPO)
    if not path.is_file() or ref.get("sha256") != sha(path):
        raise ValueError(f"{label} producer/runner is not current repository script")
```

`REPO` 来自 `HERE.parent.parent`（`:13`），白名单为模块常量 `RECON_PRODUCERS` / `RECON_RUNNERS`（`:21-40`）。wrapper 自报的 `status`/`exit_code` 仅作为与 receipt 的**比对项**，真值取自 receipt 文件本身（`:109-113`，注释明写 "wrapper fields are comparisons, not truth"）。

**缺陷**：见 B2R-02（`_record_from` 接受调用方自报 Mapping）。

### ② 失败分支审计——fail-closed 还是 warning 后装成功

检查文件：同上，另加 `scripts/tests/run_all.py`。

`handoff_manifest.py:338-339` 的 reconciliation 深验用 `except Exception as exc: fails.append(...)` 包裹，异常即失败，无 fail-open；`audit_release_gate.py:757-761` 对 `validate_bundle` 同样 except 即 append error。`verify_case` 全程收集 `fails` 并在非空时 `return 2`。

**缺陷**：见 B2R-01（`--legacy-read-only` 分支静默跳过三重绑定检查后 `return 0`）。

### ③ 新格式的存量迁移——旧数据怎么办、新产物谁生成

检查文件：`scripts/tests/formal_ready_test_harness.py`、`scripts/tests/test_handoff_manifest.py`（`make_case` 第 66-155 行）、`scripts/report/handoff_manifest.py:42-47`。

批二把 `reconciliation_report.json` 升为 READY 必备件（`handoff_manifest.py:80-81`），存量迁移路径由 `make_case` 生成含四份哈希自洽 receipt 的 fixture 承接；旧 `handoff/v1`、`handoff/v2` 走 `LEGACY_SCHEMAS` 只读降级。修复方自报材料 `batch2-report.md:171` 亦承认"旧 handoff 正例是手写三 gate，改为内容/哈希完整的四回执 fixture"。

**缺陷**：legacy 降级路径正是 B2R-01 的载体——新必备件的存量分支未覆盖。

### ④ 修复点的同族调用面

检查方式：`rg` 全库。

- `record_is_formal_ready` / `missing_formal_capabilities` 全部调用点：生产侧仅 `audit_release_gate.py:68` 一处，传入链名字符串；其余全在 `scripts/tests/`。
- `formal_chain_error` 消费者（必经之路验证）：`a4_gate.py:87`、`a4_gate.py:146`、`audit_release_gate.py:95`（被 `run()` 第 754 行**无条件**调用，不挂可选参数）、`build_html.py:298`。A5 经 `a5_report_seal.py:114-115` → `a4_gate.validate_revision_chain` 间接接入同一错误源。
- 10 个 CLI choices 单源派生已逐一确认（见第四节 E5）。

**缺陷**：见 B2R-04（`PYTHONDONTWRITEBYTECODE` 注入的同族先例未跟进）。

### ⑤ 双向一致性——文档/schema/CLI/测试的 N 份副本

检查文件：B2-G3 全部 8 份文档 diff、`scripts/tests/test_chain_registry.py`、`maintenance/repair-20260806/*.md`。

`test_chain_registry.py:71` 有一道好守卫，防 handoff 侧快照漂移：

```python
assert handoff.READY_CHAINS == formal_ready_chains() == set()
```

`test_chain_registry.py:89-96` 的 `forbidden` 正则对 4 个发布侧文件禁止 `FORMAL_CHAINS|KNOWN_CHAINS|EVM_CHAINS|CHAIN_ALIASES` 赋值与 `formal = True/False`。

文档侧数字改动 14→16 件**属实**：`find scripts/robinhood -maxdepth 1 -type f | wc -l` = 16，其中 `.py` 15 个 + `config.example.json`。

**缺陷**：见 B2R-03（自报材料"只在独立测试进程中"与代码不符）、OB-B（labels 侧硬编码链清单副本）。

### ⑥ 每道闸的可绕性——是否必经之路

检查文件：`audit_release_gate.py:741-795`（`run()`）、`handoff_manifest.py:387-465`（`verify_case`）、`shared_release_receipt.py:173-199`。

`audit_release_gate.run()` 第 754 行 `check_formal_case_chain(data, errors)` 位于主流程、无条件执行；两个 profile（`new-analysis` / `independent-audit`）共用（`:45-48`）。空 claims、缺文件等退化输入均落入 `len(unique) != 1` 分支报错，不存在"静默放行"。

**缺陷**：见 B2R-01（`--legacy-read-only` 是可条件省略的旁路）。

---

## 三、发现清单

### B2R-01 ｜ P2 ｜ 主视角⑥闸可绕性（次②失败分支）｜ 归因：**半修残留**

**handoff verify 的 `--legacy-read-only` 通道跳过 READY 链准入、reconciliation 深验与 target/token 绑定三重检查**

文件行号：
- `scripts/report/handoff_manifest.py:327-328` —— 新增深验位于 legacy 早返回之后
- `scripts/report/handoff_manifest.py:413` —— READY 链准入检查被 legacy 短路
- `scripts/report/handoff_manifest.py:428` —— READY 必备件独立重算被 legacy 短路

真实代码摘录（`:327-339`，legacy 早返回紧邻批二新增的深验段）：

```python
    if legacy:
        return
    try:
        from shared_release_receipt import validate_reconciliation_report
        target = validate_reconciliation_report(case_dir)
        scope = manifest.get("scope") or {}
        chains = {resolve_alias(chain) for chain in scope.get("chains") or []}
        if len(chains) != 1 or resolve_alias(target.get("chain")) not in chains:
            fails.append("reconciliation target.chain 未与唯一 READY scope 链绑定")
        if str(target.get("token") or "").lower() != str(scope.get("contract") or "").lower():
            fails.append("reconciliation target.token 未与 READY scope.contract 绑定")
```

`:413` 与 `:428`：

```python
    if not legacy_mode and status == "READY":
        ...
        unknown = sorted(chains - READY_CHAINS)
        if unknown:
            fails.append(f"READY scope 含非正式链 {unknown}")
```

**最小复现（实测输出）**：以合法 bsc 案 generate READY 后，手改 manifest 三处再 verify。

```
[严格 verify]        rc = 2 | ✗ schema handoff/v2 是旧版…… | ✗ READY scope 含非正式链 ['robinhood']
[--legacy-read-only] rc = 0 | [verify] ⚠ LEGACY READ-ONLY：handoff/v2 旧格式仅供读取既有冻结结论……
```

变体 L4（同时注入三重不符：`scope.chains=['robinhood']`、`scope.contract='0xWRONGTOKEN'`、wrapper `target` 仍为 bsc/`0x0`）：`rc = 0`，全部静默放行。

**危害边界（已实测缓解）**：
- `freeze` 用严格模式（`handoff_manifest.py:843` `verify_case(case_dir, legacy_read_only=False)`）→ 实测 `rc = 2`，报"schema handoff/v2 是旧版"+"READY scope 含非正式链 ['robinhood']"
- `audit_release_gate` 不读 handoff manifest，独立经 `formal_ready()` 判链 → RH 恒拒

故**不能直达 formal 发布**，定 P2 而非 P0/P1。但 `verify` 的语义是"−2 开工 fail-closed 校验"，一个声称 READY + 非正式链 + 错 token 的 manifest 拿到 exit 0，直接违反 INV-12"必经路径且**不可条件省略**"的字面要求——`--legacy-read-only` 就是那个"条件"。

**归因论证**：从严判半修残留。批二 B2-G2 新增 reconciliation 深验（INV-12 主修点）时，把新代码加在历史 legacy 早返回**之后**，同族分支未同步覆盖；`:478-479` 注释承诺的"正式报告入口按本 receipt 统一拒绝"亦无实现点（见 OB-A）。替代解释"纯历史漏检"不成立：legacy 短路 READY 链准入是历史设计，但**新必备件在该分支的缺口是本批引入的**。

**修复建议**：二选一——(a) legacy 模式下仍校验 `scope.chains ⊆ READY_CHAINS` 与 wrapper target 绑定，只豁免两扫描器的新 schema 检查；(b) 更彻底：legacy 模式直接拒绝 `status=READY`（只读旧案应读既有冻结结论，不该接受 READY 语义），并为 `legacy_readonly_receipt.json` 补上真实消费点。

---

### B2R-02 ｜ P3 ｜ 主视角①字段来源审计 ｜ 归因：**新引入**（`f6844bf`）

**`record_is_formal_ready` / `missing_formal_capabilities` 接受调用方自报 Mapping，可被伪造 record 骗过**

文件行号：`scripts/lib/chain_registry.py:180-183`

```python
def _record_from(value):
    if isinstance(value, Mapping):
        return value
    return get_chain_config(value)
```

**最小复现（实测输出）**：

```
record_is_formal_ready(伪造完整dict) = True
missing(伪造) = ()
record_is_formal_ready(最小伪造,无canonical/无evm_chain_id) = True
formal_ready('polygon') 仍 = False
```

最小伪造仅需 `{"release_tier": "formal", "capabilities": {12 项全 True}}`——连 `canonical` 与 `evm_chain_id` 都不需要（缺 `capture_evm_family` 即跳过 `:198-199` 的 chain-id 检查）。`missing_formal_capabilities` 对 record 完整性零校验，不像 `_validate_registry`（`:142-160`）那样比对必需字段集。

**生产可达性（实测不可达）**：`rg` 全库确认，生产侧 `record_is_formal_ready` 零调用；`missing_formal_capabilities` 唯一生产调用点 `audit_release_gate.py:68` 传入的是链名字符串，经 `get_chain_config` 查注册表。该后门当前仅服务测试（`test_batch2_capability_matrix.py:45`、`test_chain_registry.py:82` 依赖它传 dict）。

**为何仍记为 finding**：这是①视角的教科书形态——公开 API 接受自报事实。今后任何人从 JSON/配置读入 record 传进来即刻失守，而它与安全的 `formal_ready()` 仅一字之差，极易误用。

**修复建议**：把自报入口私有化并改名（如 `_record_is_formal_ready_for_fixture`），或在 `_record_from` 中加身份校验——要求传入 record 与 `CHAIN_REGISTRY[record["canonical"]]` 同一。

---

### B2R-03 ｜ P3 ｜ 主视角⑤双向一致性（次③存量迁移）｜ 归因：**新引入**（`2a9d5ed`）

**harness 同进程激活无 teardown，两处测试在模块顶层调用；自报材料描述与代码不符**

文件行号：
- `scripts/tests/formal_ready_test_harness.py:20-32`（`activate_test_vertical_slices`，直接改模块全局，无恢复）
- `scripts/tests/test_audit_release_gate.py:18-19`、`scripts/tests/test_round4_a5_seal.py:5-7`（模块顶层同进程调用）

```python
    chain_registry.CHAIN_REGISTRY = patched
    return chain_registry
```

`patched` 的 record 与 capabilities 均为**普通 dict**（`:26-27` `dict(record)` / `dict(record["capabilities"])`），故 patch 后连不可变性也一并丢失。

**最小复现（实测输出）**：

```
调用前 formal_ready_chains(): set()
调用后 formal_ready_chains(): ['base', 'bsc', 'eth', 'sol']
patched record 可原地改? YES 可写 —— patch 后不可变性丢失
```

跨文件污染实测（模拟 pytest 字母序收集，`test_audit_release_gate` 先于 `test_batch2_capability_matrix`）：

```
import test_audit_release_gate 后: ['base', 'bsc', 'eth', 'sol']
>>> batch2 能力矩阵断言: FAILED(被污染)
```

即 `test_batch2_capability_matrix.py:60` 的 `assert formal_ready_chains() == set()` 会因前序文件的顶层 patch 而失败。

**缓解（实测）**：`run_all.py:74` 对每个测试文件起独立子进程（`subprocess.run([sys.executable, os.path.join(HERE, args[0])] + args[1:])`），进程边界隔离了污染；且污染方向是"变红"而非"假绿"，不产生虚假通过。本机 `pytest` 未安装，故当前无人踩中。

**双向一致性缺陷**：`maintenance/repair-20260806/batch2-report.md:71` 称"只在独立测试进程中复制矩阵"。这与上述两个模块顶层同进程调用点不符——只有 `run_formal_script`（`:35-52`）才是独立子进程。

**修复建议**：改为 contextmanager 带 `finally` 恢复原 `MappingProxyType`，或提供显式 `deactivate()`；并修正 batch2-report 表述。

---

### B2R-04 ｜ P3 ｜ 主视角④同族调用面 ｜ 归因：**新引入**（`2a9d5ed`）

**`run_formal_script` 未注入 `PYTHONDONTWRITEBYTECODE`，子进程会在仓库写字节码**

文件行号：`scripts/tests/formal_ready_test_harness.py:46-48`

```python
    child_env = os.environ.copy()
    if env:
        child_env.update(env)
```

同族先例（本仓库已有正确做法）：`scripts/report/handoff_manifest.py:745-746`

```python
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
```

**实证**：修复方 `batch2-report.md:207` 自承"结束前已清理 4 个误生的 `.pyc` 及两个空 `__pycache__` 目录"——即该缺口在本批施工中已真实触发。我本次全程显式带 `PYTHONDONTWRITEBYTECODE=1`，子进程继承，故未复现（复核结束时 `find` 确认仓库无 `.pyc` / `__pycache__` 残留）。

**修复建议**：`child_env.setdefault("PYTHONDONTWRITEBYTECODE", "1")`。

---

### B2R-05 ｜ P3 ｜ 主视角⑤双向一致性 ｜ 归因：**新引入**（`8f3600c`）

**`build_labels.py` 的 tier 语义注释改写归入 B2-G0，但该 commit 主题是批一 P3 收尾，map 行未列该 hunk 目的**

`8f3600c` 实际 diff：

```
-# 全量构建必须能产出每条正式链的目标链主表；探索链不得混入正式能力声明。
+# 这是标签资产构建面，不是 release-tier 或 formal-ready 链清单。
 BUILD_CHAINS = {'eth', 'bsc', 'base', 'sol', 'robinhood'}
```

该改动属 RH 降级/tier 语义（INV-11/INV-20，即 B2-G3 的 owner），而 `diff-finding-map.md:22` 的 B2-G0 行"修改目的"仅写"拒绝 producer 中间 symlink；规范零宽/不可见边界空白，拒绝非字符串，OB-2 复用 canonical merge"，未涵盖此 hunk。

**定性**：**非夹带**——它与批二整体主题强相关、纯注释不改行为、且同 commit 的 `merge_risk_flags` 复用（OB-2）有明确归属。属归组偏差 + 映射描述不完整。按 PLAN"所有…文档和元数据 hunk 必须有 owner"从严记为 P3。

**修复建议**：在 `diff-finding-map.md` 的 B2-G0 行补一句该注释 hunk 的 owner，或注明其 secondary invariant 为 INV-11。

---

## 四、边界外一步核验记录表（含"守住"项）

### A. 能力矩阵与 formal_ready

| # | 构造 | 实际输出 | 结论 |
|---|---|---|---|
| A1 | `formal_ready(k)` 遍历全 16 链 | `formal_ready_chains() = set()`；`any ready? False` | **守住** |
| A2 | `missing_formal_capabilities('eth')` | `('vertical_slice_verified',)` | **守住**（唯一缺口正是批三待补项） |
| A3 | `CHAIN_REGISTRY['zzz'] = {}` | `TypeError` | **守住** |
| A4 | `rec['release_tier'] = 'x'`（record 层） | `TypeError` | **守住** |
| A5 | `rec['capabilities']['vertical_slice_verified'] = True`（内层） | `TypeError` | **守住**（三层均 mappingproxy） |
| A6 | `record_is_formal_ready(伪造完整 dict)` | `True` | **守卫失效** → B2R-02（生产不可达） |
| A7 | `record_is_formal_ready({release_tier + caps 全True})` 最小伪造 | `True` | **守卫失效** → B2R-02 |
| A8 | `gc.get_referents(caps)` 取底层 dict 后原地改 | `formal_ready('eth')` False→True | **可绕** → OB-C（威胁模型外，已还原） |
| A9 | `rg` 手工 formal 开关残留 | 命中全为 `attested_rpc_pool(..., formal=True)`，属 RPC attestation 语义（`net.py:359`），与链 tier 无关 | **守住**（无第二开关） |
| A10 | `release_tier` 与 `formal_ready` 是否解耦 | `formal_tier_chains() = {eth,bsc,base,sol}` 而 `formal_ready_chains() = set()` | **守住**（改 tier ≠ 改 ready） |

### B. 测试后门隔离性

| # | 构造 | 实际输出 | 结论 |
|---|---|---|---|
| B1 | `rg` 生产代码（排除 `scripts/tests/`、`maintenance/`）import harness | 零命中 | **守住** |
| B2 | 同进程调 `activate_test_vertical_slices()` 后查全局 | `set()` → `['base','bsc','eth','sol']`，无 teardown | **泄漏** → B2R-03 |
| B3 | 模拟单进程收集顺序污染 | `test_batch2_capability_matrix` 核心断言 FAILED | **泄漏**（方向为变红，非假绿）→ B2R-03 |
| B4 | 生产 `formal_ready()` 不经 harness 时全链状态 | 全 False | **守住** |
| B5 | `run_formal_script` 是否给生产 CLI 留 bypass | 无环境变量/CLI flag 开关，patch 仅存在于子进程内存 | **守住** |

### C. READY reconciliation 深验（11 变体，先改后 generate 以排除哈希漂移干扰）

| # | 构造 | rc | 拒绝理由（尾部） | 结论 |
|---|---|---:|---|---|
| C0 | 基线未改动 | 0 | `[verify] PASS 15 件产物哈希一致，4 个 gate 重查通过` | **守住**（证明非"全拒"假象） |
| C1 | wrapper 只剩三查（删 time） | 2 | `reconciliation wrapper must contain exactly four checks` | **守住** |
| C2 | balance producer sha 伪造 | 2 | `reconciliation balance producer/runner is not current repository script` | **守住** |
| C3 | wrapper runner 换非白名单（真实哈希） | 2 | `reconciliation wrapper producer/runner path is not whitelisted` | **守住** |
| C4 | 跨链复用：BSC wrapper → sol READY | 2 | `reconciliation target.chain 未与唯一 READY scope 链绑定` | **守住** |
| C5 | receipt 篡改、wrapper 登记 sha 不同步 | 2 | `evidence hash mismatch` | **守住** |
| C6 | receipt verdict=FAIL、wrapper 报 PASS（哈希已同步） | 2 | `reconciliation balance wrapper/receipt verdict mismatch` | **守住** |
| C7 | target.token ≠ scope.contract | 2 | `reconciliation target.token 未与 READY scope.contract 绑定` | **守住** |
| C8 | sol target 配 evm producer | 2 | `reconciliation balance producer/runner path is not whitelisted` | **守住**（family 经 `recon_adapter_for` 导出） |
| C9 | balance `checked=0` 空对账冒充全通过 | 2 | `balance receipt observations incomplete or non-PASS` | **守住** |
| C10 | supply_truth 回执 `mode=exploration` | 2 | `supply_truth receipt must be formal and bind replay_stats input` | **守住** |

补充观察（非缺陷）：C1 在 `generate` 阶段放行、`verify` 阶段才拒——`generate` 的 `REQUIRED_FOR_READY` 只验文件存在性，wrapper 内容完整性归 `verify`。属设计分层，消费侧闸仍是必经之路。

### D. legacy 旁路专项

| # | 构造 | rc | 结论 |
|---|---|---:|---|
| L1 | schema=handoff/v2 + scope.chains=['robinhood'] + `--legacy-read-only` | 0 | **守卫失效** → B2R-01 |
| L2 | reconciliation 换成语义垃圾 + legacy | 2 | **守住**（靠 `AUTO_GATES` 重查 `verdict=None`，非深验） |
| L3 | legacy verify PASS 后继续 freeze | 2 | **守住**（`freeze` 严格 verify 拒 legacy + 非正式链） |
| L4 | legacy + 链/token/wrapper target 三重不符 | 0 | **守卫失效** → B2R-01 |

### E. Robinhood 防回流七面 + choices 派生

| # | 面 | 证据 | 结论 |
|---|---|---|---|
| E1 | registry tier / chain-id | `chain_registry.py:95-99` `release_tier="exploration"`、`evm_chain_id=None` | **守住** |
| E2 | READY handoff | `formal_ready_chains()` 空集；RH 永不入 `READY_CHAINS`（`handoff_manifest.py:86`） | **守住** |
| E3 | audit release 两 profile | `formal_chain_error("robinhood")` → "chain=robinhood 为 exploration，不得编译正式 analysis"；`run()` 第 754 行无条件调用 | **守住** |
| E4 | A4 / A5 / build_html | `a4_gate.py:87,146`、`build_html.py:298` 直连同一错误源；A5 经 `a5_report_seal.py:114-115` → `a4_gate.validate_revision_chain` 间接接入 | **守住** |
| E5 | labels 存在不抬升 tier | `labels-robinhood.csv` 非空但 `labels_table=True` 只是 12 项事实之一；`release_tier` 独立 | **守住** |
| E6 | 旧 RH A4 seal 不能用于 A5 重签 | `test_batch2_robinhood_exploration.py:102-108` 断言 `create_seal` 抛含 "exploration" 的 ValueError | **守住** |
| E7 | 豁免失效哨兵 | `test_batch2_robinhood_exploration.py:29-33` + `:44-53` 哨兵自验（对 `release_tier=formal` 与 `evm_chain_id=4663` 两种失效条件均须转红） | **守住** |
| E8 | RPC 层附加拒绝（我另发现的第八面） | `test_batch1_rpc_attestation.py:139-146`：`attested_rpc_pool("http://fixture","robinhood",formal=True)` 必抛 `RpcAttestationError`；且 `attested_evm_chains()` 不含 RH，RH 不在任何 EVM CLI 的 `--chain choices` 里 | **守住** |
| E9 | choices 单源派生 | 4 mandatory：`accounting_gate.py:381`、`verify_recon.py:47`、`supply_truth_gate.py`（`formal_reconciliation_chains("supply")`）、`time_spotcheck.py:75`；6 attested：`fetch_alchemy.py:36`、`lp_positions.py:91`、`multicall_balances.py:91`、`pierce_stake.py:132`、`scan_bloxroute_seg.py:34`、`rpc_batch.py:58` | **守住**（10/10 派生，无发布侧硬编码副本） |

---

## 五、批一 47 边界回归结论

**不回退，回归通过。**

- `test_batch1_rpc_attestation.py` 在全量 suite 中 PASS。
- 语义辨析：批二改的是各 CLI 的 `argparse --chain choices`（准入名单），未触碰 `net.py:359` `attested_rpc_pool` 的内部 attestation 逻辑；`formal=True` 参数属 RPC attestation 语义（"业务调用前必须验 `eth_chainId`"），与链 release tier 同名不同义，批二未改 `net.py`。
- 反向加固：批二把 RH 的 `evm_chain_id` 设为 `None` 后，`test_batch1_rpc_attestation.py:139-146` 的 `test_registry_factory_rejects_missing_identity` 对 `robinhood`/`opbnb` 的拒绝断言更强而非更弱。

**全量 suite 独立复跑**：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` → `全部通过`，`EXIT=0`，74 项全绿（与修复方 `batch2-report.md:201` 自报一致，本次为我独立复跑所得）。

---

## 六、diff → finding 映射复核与未映射 hunk 复算

### 文件级复算

| 分组 | map 登记文件数 | `git show --stat` 实际 | 一致 |
|---|---:|---:|:--:|
| B2-G0 `8f3600c` | 4 | 4 | ✓ |
| B2-G1 `f6844bf` | 15 | 15 | ✓ |
| B2-G2 `2a9d5ed` | 12 | 12 | ✓ |
| B2-G3 `5ef3186` | 10 | 10 | ✓ |
| B2-G4 `07fab90` | 4 | 4 | ✓ |
| 合计 | **45** | 批二 `--stat` = **45 files changed** | ✓ |

### 逐 hunk 夹带检查（重点抽查小改动）

- `test_r7_findings.py`（+3/-1）：`audit.formal_chains()` → registry 的 `formal_ready_chains()`，因 B2-G1 删除了 audit 侧本地副本。**名实相符**。
- `test_adjudication_validator.py`（+3）：加 realpath 判断使调 handoff 的路径走 harness 版 `run`。**名实相符**。
- `test_audit_release_gate.py`（+2）、`test_round4_a5_seal.py`（+2）：仅加 harness 激活两行。**名实相符**。
- `build_labels.py`（8 行）：`merge_risk_flags` 复用（OB-2，有归属）+ BUILD_CHAINS 注释口径改写（**无 owner 描述** → B2R-05）。

### B2-G3 文档改动专项（是否只改现役入口、历史段是否零改写）

结论：**符合"历史段不改写"**。

- `SKILL.md`：仅改 frontmatter description 的现役支持声明；实测 7483 bytes < 8192B 硬限。
- `analyze-workflow.md`：2 处，路由表 RH 行 + G8 身份快照说明，均为现役口径。
- RH 三分册（channels / traps / methods）：各仅在**文件头部**插入一行"准入边界"提示，坑 1–17、方法论条目、修正记录**零改动**。
- `data-pipeline-robinhood.md`：头部加"当前准入状态"段 + 分册索引表一行（14 件→16 件）。历史实测内容（"Robinhood Chain = Arbitrum Orbit L2（chainid 4663）…"）保留未改。数字经我独立验证属实（16 个普通文件 = 15 Python + `config.example.json`），有归属（map B2-G3 行"同步现役入口口径和 16 文件实数"，测试 ID `B2-DOC-RH-COUNT`）。
- `labels/README.md`、`labels/MAINTENANCE.md`：将"标签表完整性"与 release tier 拆开，资产与 benchmark 未删。

### 未映射 hunk 复算值

**0（生产/测试/文档 hunk 全部有 owner）**，与 `diff-finding-map.md:47` 的声称一致。

两点附注：
1. `5924cd5` 是本表自身的 SHA 回填，`diff-finding-map.md:29-41` 的"分组→commit SHA 对照"表已预告该动作，属自指式归属，不计未映射。
2. `diff-finding-map.md:47` 把批二区间标注为 `553806b..07fab90`，而候选 tip 是 `5924cd5`——区间标注应更新（见 OB-D）。实质未映射 hunk 仍为 0。

---

## 七、范围外观察（不与批二 finding 混计）

- **OB-A**：`legacy_readonly_receipt.json` 在生产侧**零消费者**（`rg` 确认仅 `handoff_manifest.py` 产出、`invariant_manifest.json:129` 登记 schema、测试断言其存在）。`handoff_manifest.py:478-479` 注释承诺"正式报告入口按本 receipt 统一拒绝"没有实现点。归因历史漏检（v6.8.1），批二未动该段。与 B2R-01 同源，建议合并修复。
- **OB-B**：`scripts/labels/` 存在多份硬编码链清单副本，与 registry 无双向守卫：`labels_resolver.py:44 KNOWN_CHAINS`、`build_labels.py:26 BUILD_CHAINS`、`benchmark_labels.py:24 EXPECTED_CHAINS`、`roundtrip_check.py:25 CHAINS`、`goplus_check.py:60 choices`、`gen_manual_from_addressbook.py:21 CHAINS`、`build_goldset.py:87,187`。修复方 `batch2-report.md:138` 已自认"批四 scanner 补双向监测"。归因历史漏检。
- **OB-C**：`gc.get_referents()` 可穿透 `MappingProxyType` 拿到底层 dict 并原地改写（实测 `formal_ready('eth')` False→True，测后已还原）。该手法要求攻击者已具备任意代码执行能力，超出本仓库闸的威胁模型（防误用/图省事，非防恶意代码）。informational，不建议为此加防护。
- **OB-D**：`diff-finding-map.md:47` 批二区间标注 `553806b..07fab90` 与候选 tip `5924cd5` 不一致，建议更新标注。

---

## 八、执行命令清单

```bash
# HEAD 与区间核验
git -C <worktree> rev-parse HEAD                      # 5924cd58b2c2...
git -C <worktree> log --oneline 553806b..5924cd5
git -C <worktree> status --short                      # 全程为空

# 静态检查
rg -n "formal_ready_test_harness|activate_test_vertical_slices" --glob '!scripts/tests/**' --glob '!maintenance/**' .
rg -n "record_is_formal_ready|missing_formal_capabilities" .
rg -n "formal\s*=\s*True|\"formal\"\s*:\s*True|vertical_slice_verified\s*=\s*True" --glob '!maintenance/**' .
rg -n "formal_chain_error|validate_formal_case_chain|check_formal_case_chain" --glob '!scripts/tests/**' scripts/
rg -n "legacy_readonly_receipt|LEGACY_RECEIPT_NAME|legacy_read_only" --glob '!maintenance/**' .

# 动态攻击（全部在 mktemp -d，均带 PYTHONDONTWRITEBYTECODE=1）
python3 $TD/attack1.py        # A1-A8 能力矩阵/不可变性/gc 穿透
python3 $TD/attack2.py        # B2-B3 harness 同进程泄漏
python3 $TD/attack3.py        # B3 单进程收集顺序污染
python3 $TD/attack_recon.py   # generate 阶段 8 变体（方法自纠：深验在 verify）
python3 $TD/attack_verify.py  # C0-C10 verify 阶段 11 变体
python3 $TD/attack_legacy.py  # L1-L2 legacy 旁路
python3 $TD/attack_l3.py      # L3-L4 freeze 拒 legacy / 三重不符

# 全量回归（独立复跑）
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py    # 全部通过 EXIT=0（74 项）

# 收尾自查
git -C <worktree> status --porcelain                                  # 空
find <worktree> -name "__pycache__" -o -name "*.pyc" -not -path "*/.git/*"   # 空
```

**方法自纠记录**：`attack_recon.py` 首轮攻击 `generate` 阶段，8 例全"放行"，我一度误判为守卫失效。复查后确认 `generate` 只验文件存在性、reconciliation 深验在 `verify` 的 `_verify_light_schema`，遂重写为 `attack_verify.py`，并改为**先改产物再 generate**（否则会被产物哈希漂移闸拦下，掩盖深验是否真生效）。C0 基线放行用于证明 fixture 有效、排除"全拒"假象。

---

## 九、归因汇总

| 编号 | 定级 | 归因 | git 证据 | 替代解释与排除理由 |
|---|---|---|---|---|
| B2R-01 | P2 | 半修残留 | `2a9d5ed` 在 `handoff_manifest.py:327-328` legacy 早返回**之后**新增深验 | 替代解释"纯历史漏检"——排除：legacy 短路 READY 准入确为历史设计，但新必备件在该分支的缺口由本批引入 |
| B2R-02 | P3 | 新引入 | `f6844bf` 引入 `_record_from`（`chain_registry.py:180-183`） | 替代解释"测试便利有意设计"——不改归因：有意与否不改变"公开 API 接受自报事实"的缺陷性质 |
| B2R-03 | P3 | 新引入 | `2a9d5ed` 新建 `formal_ready_test_harness.py` | 替代解释"run_all 子进程已隔离"——属缓解不属排除，且自报描述与代码不符独立成立 |
| B2R-04 | P3 | 新引入 | `2a9d5ed` 新建 `run_formal_script`（`:46-48`） | 无替代解释；`batch2-report.md:207` 自承已触发 |
| B2R-05 | P3 | 新引入 | `8f3600c` 的 `build_labels.py` 注释 hunk | 替代解释"夹带"——排除：与批二主题强相关、纯注释不改行为，定性为归组/映射不完整 |

---

## 十、与修复方自报材料的比对

| 修复方陈述 | 出处 | 我的独立结论 |
|---|---|---|
| "生产代码无环境变量、CLI 参数或可写开关绕过" | `batch2-report.md:71` | **证实**（rg 零命中 + 生产 `formal_ready()` 全链 False） |
| "只在独立测试进程中复制矩阵" | `batch2-report.md:71` | **不成立**：两处模块顶层同进程调用 → B2R-03 |
| "`R8-06` 的'整闸可省'路径已切断" | `batch2-report.md:168` | **部分成立**：严格路径已切断（C1-C10 全守住），legacy 路径仍可省 → B2R-01 |
| "readiness 只由 12 项 capability facts + EVM chain ID 计算" | `batch2-report.md:167` | **主干成立**，但未识别自报 Mapping 入口 → B2R-02 |
| "生产文本中不存在 registry record 的 `formal=True/False` 或同义第二开关" | `batch2-report.md:140` | **证实**（命中全为 RPC attestation 语义的同名参数） |
| "`scripts/robinhood/` 实数 16 个普通文件" | `batch2-report.md:158` | **证实**（独立 `find` 复算） |
| "最终全量 74/74 PASS，exit=0" | `batch2-report.md:201` | **证实**（独立复跑一致） |
| 豁免台账七要素齐备、Fable/盲审栏留空 | `robinhood-impact.md:109-112` | **证实**（`RH-EX-01/02` 七栏齐全，符合待裁决状态） |

---

## 十一、复核方自我声明

- 仓库全程零写入：起止两次 `git status --porcelain` 均为空；收尾 `find` 确认无 `__pycache__` / `*.pyc` 残留。
- 未与修复线程通信；未读取 `~/.codex/`、MEMORY、rollout 或历史案例记忆目录；未读取主仓库 main 基线（避免旧结构污染判断）。
- 所有临时脚本与 fixture 位于 `mktemp -d` 创建的系统临时目录。
- 本报告全部发现在读取修复方自报材料前独立冻结；自报材料仅用于第十节比对与归因参照。
