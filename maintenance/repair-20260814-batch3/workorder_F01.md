# 【修复工单 F01】bug：A4 对抗复核允许"质检意见与整改清单脱钩"的空壳 PASS（codex review F-01，P1）

> 施工方：codex。**禁一切 git 写命令**（git add/commit/checkout/restore 等一律不跑）；只改文件。完成后写 `maintenance/repair-20260814-batch3/workorder_F01_done.md`。
> 禁触：`maintenance/repair-20260814-evmobs/`、`scripts/tests/test_evm_observation.py`（未跟踪，别人的）、`archive/**`、`blind-reviews/**`、两份 `_meaningful_text` 函数本体、`shared_release_receipt.py` 约 490 行与 `audit_release_gate.py` 约 839 行的 `schema = receipt.get("schema")` 直赋值行。
> 本工单行号基于当前分支 HEAD（生产代码与 83394ab 逐字节一致）；若有漂移以语义锚为准。

## 1. 不变量（本单要建立的）

1. adversarial_review 的 release_decision=PASS ⟺ 完整性批评者（completeness_critic）每条 findings、每条 non_covered，以及所有 claim-review artifact 中每个 verdict=REFUTED 的记录，都有对应 blocker 且全部 resolved（带 ≥10 实义字符 resolution）。
2. evidence 每条 ≥10 个实义白名单字符（复用 _meaningful_text 逐字符计数，不改其本体）。
3. 同一 entrypoint 脚本（按 sha256）在一次 finalize/消费中只能出现一次——跨角色也不行。
4. 以上三条在生产侧（finalize）与消费侧（shared/audit）各自独立成立；手抄绕过 finalize 的自洽聚合会被消费侧从 hash 绑定的 artifact 字节独立重建账本后拒绝。

## 2. 同族清单（rg 结果，施工前自行复核一遍）

- `adversarial-review/v3` 代码点：runner:24（AGGREGATE_SCHEMA）、:26（V3_RERUN_HINT）、:418 落盘；shared_release_receipt.py:22 import、:671-675 schema 分支；audit_release_gate.py:22 import、:837 手抄中文句（B-08 遗留，顺手单源化）、:840-843 分支、:849 及同文件 "对抗复核 v3" 错误前缀（rg "v3" 全扫两文件的 docstring/错误文案，不只常量点）。
- `adversarial-review-artifact/v1`：runner:22；夹具写入点 test_audit_release_gate.py:107、test_repair_batch_d.py:947、test_repair_batch2_f02.py:66；文档 research-workflows.md:103；invariant_manifest.json runner 相关条目。
- invariant_manifest.json 涉 v3 的**三个数组**：receipt_producers（runner，约 138-141）、receipt_consumers（audit_release_gate，约 372-383）、receipt_consumers（shared_release_receipt，约 433-448）。
- entrypoint 去重两处：runner:400-403、shared:731-734。
- "两角色同字节 entrypoint"夹具全库仅两处：test_audit_release_gate.py:104-115（refresh_adversarial）、test_repair_batch_d.py:944-955。
- 文档：independent-audit-protocol.md:127、:167、:175-177、:182；analyze-workflow.md:162；research-workflows.md:103-107。
- 历史档案（CHANGELOG 6.42.0 条、maintenance/**、blind-reviews/**）**不改**。

## 3. 施工内容

### 3a. blocker 账本（runner）

常量区新增：

```python
BLOCKER_REQUIRED_KEYS = frozenset({"id", "resolved", "source"})
BLOCKER_ALLOWED_KEYS = BLOCKER_REQUIRED_KEYS | {"resolution"}
BLOCKER_SOURCE_KINDS = frozenset({"completeness_finding", "non_covered", "refuted_claim", "manual"})
MIN_MEANINGFUL_CHARS = 10
AGGREGATE_SCHEMA = "adversarial-review/v4"
ARTIFACT_SCHEMA = "adversarial-review-artifact/v2"
V4_RERUN_HINT = "存量 adversarial-review/v2、v3 须按 v4 重跑对抗复核"
```

（V3_RERUN_HINT 删除，全库引用点同步改 V4_RERUN_HINT。）

`validate_blocking_findings` 扩展，**校验顺序必须 id → resolved → 键白名单 → source → resolution**（f02:332-352 断言 "id is invalid" 先触发，顺序是载荷性的）：

- id：_valid_identifier（不变）。
- resolved：严格 bool（不变）。
- 键白名单：`set(item) - BLOCKER_ALLOWED_KEYS` 非空即拒；BLOCKER_REQUIRED_KEYS 缺任一即拒。
- source：必须 dict 且 `set(source) == {"kind", "ref"}`；kind ∈ BLOCKER_SOURCE_KINDS；ref 为 meaningful_text（≥1，不设 10 门槛——refuted_claim 的 ref 含短 claim_id）。
- resolution：resolved=true 必填；resolved=false 可缺省；**只要存在就必须 ≥10 实义字符**。
- id 去重（不变）+ 非 manual 的 (kind, ref) 记账去重（两条 blocker 记同一对象=账本歧义，拒）。

### 3b. 机械定位符与双向对账（runner + shared）

ref 格式（机械定位符，@CX 定案——防"两 critic 同文 finding / 两 reviewer 各 REFUTED 同一 claim"被 set 折叠）：

- completeness_finding → `<artifact相对路径>#/findings/<idx>`
- non_covered → `<artifact相对路径>#/non_covered/<idx>`
- refuted_claim → `<artifact相对路径>#/results/<idx>:<claim_id>`

新纯函数（放 validate_blocking_findings 之后，两侧共用）：

```python
def build_required_refs(review_entries):
    """从每份已验证 artifact 机械生成必须记账的 (kind, ref) 全集。
    review_entries: [(role, artifact_relpath, artifact_data), ...]，全部累积、多份同角色 artifact 逐份展开。"""

def validate_blocker_linkage(blockers, required_refs):
    """双向对账：required−booked 非空=缺账拒；booked−required 非空=幽灵账拒。
    booked 只取非 manual blocker 的 (kind, ref)。报错回显缺失/幽灵项（含 finding 原文时整段附上）。"""
```

挂载：

- finalize_review：循环内接住 validate_review_receipt 返回值的第二项（现 L387 是 `execution, _, reviewed = ...`，把 `_` 接为 artifact_data），逐份收集 (role, artifact 相对路径, artifact_data)；L415 validate_union_coverage 之后调 build_required_refs + validate_blocker_linkage。**联动失败 → ValueError → 走既有 except 兜底 rc=2、不落盘**；账全但有 unresolved → 照旧落盘 BLOCKED（L416-424 不动）。
- shared_release_receipt.validate_adversarial_review：同法（现 L727 的 `_` 接住；L740 validate_blocking_findings 之后加 linkage）。消费侧从 hash 绑定的 artifact 字节独立重建 required 集——这是防"手抄聚合删账"的关键。
- audit_release_gate 零新逻辑（100% 委托 shared，自动继承）。

### 3c. 10 实义字符门槛

新谓词（命名不夸大——它数白名单字符，纯 10 个标点也过，防呆不防伪）：

```python
def _has_min_meaningful_chars(value, minimum=MIN_MEANINGFUL_CHARS, *, meaningful_text=_meaningful_text):
    if not isinstance(value, str):
        return False
    return sum(1 for char in value if meaningful_text(char)) >= minimum
```

- `_string_array` 加 `min_meaningful=None` 参数；evidence 挂载点 runner:174-175 传 `min_meaningful=MIN_MEANINGFUL_CHARS`。
- alternative_explanations、critic findings/non_covered **不加门槛**（防误伤）。
- meaningful_text 注入链贯穿：消费侧调用时注入 shared 自己那份 `_meaningful_text` 副本（既有 kwargs 注入链照抄）。**两份 _meaningful_text 本体零改动**。

### 3d. entrypoint sha 全局唯一

- runner:400-403：`entrypoint_key = (role, ...sha256)` 改为 sha256 单键；错误消息改 "duplicate review entrypoint content"。
- shared:731-734 同步同文。
- 两份夹具 body 插 role 注释行使两角色脚本字节分叉：test_audit_release_gate.py:104-115、test_repair_batch_d.py:944-955（如在 body 首行后插 `# adversarial fixture role: {role}`）。

### 3e. invariant_manifest.json（精确 diff，改完必单跑 invariant_scan.py 验证）

- runner producer：v3→v4；artifact v1→v2（runner 相关条目按扫描器实际输出对齐）。
- audit consumer / shared consumer：保留 v2、v3（拒绝分支字面量），新增 v4；artifact 条目同步。
- minimum_counts 地板不降。

### 3f. 文档四件（同 commit 带机器件）

- independent-audit-protocol.md：
  - :127 "blocking_findings 非空→禁发布"改为"联动不全或存在 unresolved → 禁发布"（原句与 resolved 可 PASS 矛盾）。
  - :167 v3→v4；"非空 evidence"→"每条 evidence 至少 10 个实义白名单字符"。**保留 `"resolved": bool` 精确子串与既有 scope_terms 原词**（f02 t_documentation_contract:918-934 锁定）。
  - :175-177 blocker 结构块改四键形态+source 结构+机械定位符格式+联动语义（多记少记都拒、manual 自由）。
  - :182 迁移句改"存量 v2、v3 须按 v4 重跑"，并写明：改 runner 后存量案先报 "producer is not current runner"，重跑=两角色 runner+finalize 全程。
  - entrypoint 闸定性一句：防误复用/一人分饰两角，**不是**独立复核证明。
- analyze-workflow.md:162：10 门槛句 + v3→v4。
- research-workflows.md:103-107：artifact/v2、evidence ≥10 注释、"越界"清单补联动项。
- SKILL.md 不改。

### 3g. f02 存量适配（scripts/tests/test_repair_batch2_f02.py，六处）

1. :292-294 bad_blockers 补 `"source": {"kind":"manual","ref":"fixture negative"}`（保住原测试理由）。
2. :656 手抄聚合 v3 字面量 → `runner.AGGREGATE_SCHEMA` 引用。
3. :795、:797 V3_RERUN_HINT → V4_RERUN_HINT。
4. :1011-1013 blocker 负例补 manual source（"空 id"行不用补，id 先触发）。
5. :1092-1107 v2 负例断言 "v3"→"v4"。
6. :66 夹具 artifact schema 字符串 → v2（或改引 runner.ARTIFACT_SCHEMA）。

## 4. 三件套测试（新文件 scripts/tests/test_repair_batch3_f01.py，并挂 run_all.py SUITE 末尾）

风格照抄 f02（check/FAILS 收集器、`if __name__ == "__main__"` 守卫、main 固定执行序）；可 `from test_repair_batch2_f02 import make_case, entrypoint, claim_artifact, result, critic_artifact, run_role, run_existing_role, finalize, residue, rejected, rejection_message, build_valid, write_json, sha`。新增本地 helper：`blocker(...)` 造账条目、`rebind_artifact(...)`（改 artifact 后重绑 receipt/aggregate 哈希，仿 f02 rewrite_aggregate_claim_id）。

**A 联动族**：findings 非空+blockers=[] → finalize rc2 且无 aggregate 落盘、零残留（F-01 本尊）；non_covered 版；REFUTED 无账版；绿例=finding+定位符 blocker（resolved+resolution≥10）→ finalize rc0 PASS → shared+audit 双消费绿；账全未决 → 落盘 BLOCKED+双消费拒；幽灵账拒；重复记账拒；**两份 critic artifact 各有不同 finding，缺任一账拒；两份 artifact 同文 finding 仍需按各自定位符分别记账；两个 reviewer 各 REFUTED 同一 claim 需两项处置；多 artifact 累积不被循环末份覆盖**；manual 绿例（不进对账）；键白名单负例（第 5 键 "note" 拒；缺 source 拒）；source 坏 kind/零宽 ref/多余键拒；消费侧独立性（取 PASS 聚合手抄删账/改 manual → shared 拒+audit errors 非空）。

**B 门槛族**：evidence 9/10 实义边界双测（ASCII 一组+汉字一组）；9 实义+20 个零宽 → 拒；10 实义+零宽 → 过；**纯 10 个标点 → 过**（明示形式门槛定位）；`"ab       cd"`（4 实义）拒；resolution 边界双测（resolved=true 9/10；resolved=false 但写了 9 实义 → 拒）；alternative_explanations=["OTC"] 绿例；消费侧独立门槛（rebind 把 PASS 案 evidence 降 9 实义 → shared 拒）。

**C 身份族**：两角色两文件同字节 → finalize rc2；消费侧孪生（手抄聚合绕 finalize）→ 拒；两角色分叉 body → 全链绿。

**D 迁移族**：v3 聚合 → shared 拒且消息含 "v4" 与 "重跑"，audit errors 同（v2 负例在 f02 已有，此处补 v3）。

**E 文档契约**：protocol 含 source、refuted_claim、10 门槛句、v4 重跑句 needle；analyze-workflow 含 10 门槛句。

**先红纪律**：施工前先在当前 HEAD 跑一遍新测试文件，把"错误地绿/不存在校验"的项记入 done 文件（先红清单）；修后全绿。f02 与全量 suite 同时保绿。

## 5. 新建代码自审（六视角①②）

done 文件里逐条写：字段源头（required 集从哪份字节生成、两侧是否独立）、失败分支（linkage 失败是否零残留、不落盘）。

## 6. 归因预判

半修复（v3 结构化修复未闭合语义联动，批 2 工单 B 边界"不判断观点对错"留下的已登记缺口 R10-16/17，用户已裁决收口）。

## 7. 验收标准（裁判执行）

- `python3 scripts/tests/test_repair_batch3_f01.py` rc=0；`python3 scripts/tests/test_repair_batch2_f02.py` rc=0；`python3 scripts/tests/invariant_scan.py` rc=0；`python3 scripts/tests/run_all.py` 全绿。
- codex review F-01 的最小反例（findings=["UNRESOLVED REAL GAP"]+blockers=[]+同 entrypoint 双角色+evidence=["x"]）复跑 → 三个面全部被拒。
- git diff 逐 hunk 有 finding/豁免归属。
