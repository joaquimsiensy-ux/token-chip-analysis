# 工单C7复核：退回

发现 **1 项 minor**：显式 `dual_basis: null` 仍被静默省略，未完全落实“若给必为对象”的约定。其余指定锚点、五变体预期及已检查的兼容性均成立。

当前 HEAD：`afed1cad6468541311849506c6080ed8916900b1`。两个目标源码与 `1b317b3` 逐字节相同；本次只复核 C7。

**C7-R01｜minor｜显式 null 绕过 dual_basis 类型校验**

工单位置：[workorder_C.md:534](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_C.md:534)，关联 :539–540 的输出与类型说明、:557–559 的测试列表。

工单 :7 明确要求“dual_basis 若给必为对象”，但 C7 原文为：

```python
dual_basis = fi.get("dual_basis")
if dual_basis is not None and not isinstance(dual_basis, dict):
    raise ValueError("facts_inputs.dual_basis 须为对象")
```

缺键和 JSON `null` 都得到 `None`，后续 `if dual_basis is not None:` 又将该字段省略。对原 C4-d 正常夹具仅增加 `"dual_basis": null`，套用拟稿后的内存实测：

```text
derive_facts：成功
facts 中存在 dual_basis：False
build_main：rc=0
check_facts_vs_ledgers：errors=[]
```

修订建议：保留取值及输出逻辑，只将校验条件改为：

```python
if "dual_basis" in fi and not isinstance(dual_basis, dict):
    raise ValueError("facts_inputs.dual_basis 须为对象")
```

用例 15 增加 `("dual_basis", None, "dual_basis")`。该修订已在内存验证：**15 类、34 个独立用例通过**，缺键仍允许、显式 `{}` 仍保留。未修改文件。

**已实际核过的项**

a）逐条执行 `grep -n -F`，以下 **13 条均恰好命中 1 处，行号一致**：

| 文件 | 已核行号 |
|---|---|
| `scripts/report/facts_gate.py` | 69、357、358、359、360、368、446、447、448 |
| `scripts/tests/test_report_facts.py` | 121、257、283、285 |

b）按工单原文在内存完成替换并解析 AST：

- `symbol/decimals/metrics/dual_basis` 的定义和后续引用一致，无遗留旧取值或未定义变量；受保护的 `Facts/gate_check/load_and_check/build_main/main` AST 未变。
- `metrics` 缺省或显式 `{}`，输出均为 `facts.metrics == {}`；`dual_basis={}` 保留。
- “metrics 为对象且每项为对象”足以消除本次两种非对象输入导致的 `AttributeError`。实际渲染空项、value 项、num_raw 项分别得到 `?`、`7`、`10.00%`。数值内容的合法性仍由既有逻辑处理。

c）五变体实测与工单一致：

| 输入 | 基线 1b317b3 | C7 拟稿 |
|---|---|---|
| `symbol=123` | RED：未拒绝 | GREEN |
| `decimals="18"` | GREEN：已拒绝，回归例 | GREEN |
| `metrics=[{"value":"7"}]` | RED：未拒绝 | GREEN |
| `metrics={"m1":"7"}` | RED：未拒绝 | GREEN |
| `dual_basis="x"` | RED：未拒绝 | GREEN |

基线合计 **29 通过、4 失败**；C7 拟稿 **33/33 通过**，既有七项宏/gate 契约也通过。`edit(root,name,fn)`、`reject(root,text="")`、`run(name,test)` 签名匹配；lambda 默认参数正确捕获每轮值。`results` 是列表、每次 run 追加一项，两条 metrics 同名不会合并；“15 类、33 个独立用例”与计数逻辑一致。

d）对排除禁读路径后的 **1414 个常规文件**执行 `grep -rn -I -F` 筛查：

- 测试及夹具没有依赖旧文案 `缺失或非法` 的断言。
- `facts_inputs` 的测试构造来源为 `test_report_facts.py:72–74` 和共享助手 `test_audit_release_gate.py:217–220`，未发现合法路径传入非字符串 symbol 或非对象 metrics。
- 共享助手的默认 `TT`、调用方 `SOLX/FX` 均为字符串，metrics 为 `{}`；三个值均用真实助手在内存执行并通过。

e）回归与字节约束：

- `invariant_scan.py` 对基线及 C7 内存替换版本均 **exit 0**；计数均为 producers=80、consumers=117、transport=65、atomic=60、formal_entrypoints=61、exceptions=0。
- 未发现 C7 导致现有用例变红的新增依赖。未提交时直接跑全套，仍可能触发现有 `test_stage2_reseal.py:604–611` 的 W3 overlay 白名单拒绝；工单 §4 已规定提交后同步验收 worktree，这一前提仍须遵守。
- §1.1 仅用 stat 核对：`SKILL.md=8021 B`、`commands-staging Markdown=8798 B`、`references Markdown=930065 B`。C7 只涉及脚本及施工证据，不改变这三项。

**执行边界**

本轮动态验证使用内存文件系统和真实生产函数；CLI 测试中的子进程调用替换为直接调用 `build_main`。未执行原始落盘 CLI、完整集成测试或 `run_all.py` 的 151 项全套，因此上述结果不作为全套通过证明。

报告全文已打印到 stdout。全程离线、零文件写入、无 commit。开工及收尾 `git status --porcelain=v1 --untracked-files=all` 均为空，收尾 `git diff --check` 通过、`git diff --stat` 为空。禁读内容未通过工具读取；`references/attic.md` 仅参与获准的 stat 汇总。

Codex session ID: 01a0afd3-f2f7-72c3-993a-946643269b6d
Resume in Codex: codex resume 01a0afd3-f2f7-72c3-993a-946643269b6d
