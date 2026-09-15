<!-- 由 Fable 从 codex 只读盲审任务 task-mu2t5ozc-ls8ici 的最终报告正文原样搬运;codex 沙箱只读无法自行落盘 -->
# 盲审 R1：FAIL

**发现：1 blocker、1 minor、1 nit。**

审查基线：`2000b6e78f790ee0ed348cc2ecb8eae796d5136e`。审查前后冻结的 62 个文件无哈希变化。全程离线，未读取 `/Users/uravvv/Documents`，未修改文件。

**会话文件系统强制只读，未能生成 `maintenance/repair-20260915-eps-residual/blind_review_r1.md`。以下为报告正文。**

## Findings

### F1 — blocker：拆分浮点桶改变数量，D1 核心不变量不成立

位置：[entity_source_trace.py:477](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/entity_source_trace.py:477)、[plan_v2_approved.md:34](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260915-eps-residual/plan_v2_approved.md:34)。

以下三笔使用同日精确顺序，供应量为 `10 × 2^90`，X 初始为空：

```text
X → A  2^60
X → A  1
A → D  2^60
```

实际重放结果：

| 策略 | HEAD 构成 Σraw | 工作树构成 Σraw |
|---|---:|---:|
| pro_rata | 1152921504606846976 | 1152921504606846977 |
| fifo | 1152921504606846976 | 1152921504606846976 |
| lifo | 1152921504606846976 | 1152921504606846977 |

旧版将两笔缺口合并进同一个浮点桶；新版分别进入 `data_gap` 和 `fp_residual`，改变了浮点合并结果。

进一步通过实际 `trace_entity()` 在内存数据库重放确认：

- current、peak 的 `stock_raw` 两版均为 `2^60`。
- 新版主策略两锚点的构成合计均增加 **1 raw**。
- 两版闭合百分比仍显示 `100.0`，现有闭合检查不能发现该差异。

分支代码照审批片段实现，但审批中的“数量一个单位都不变”已被反证。现有 T4 指定样例没有覆盖两类缺口共存的情况；[done.md:3](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260915-eps-residual/done.md:3) 的 `COMPLETE` 因此不能成立。

**复现命令：下方 R1，查看 `mixed` 输出。**

### F2 — minor：把“含 data_gap”写成翻转收据必然失配，范围过大

位置：[CHANGELOG.md:93](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:93)、[done.md:122](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260915-eps-residual/done.md:122)。

小供应量下 `gap_eps == EPS`，真实 `data_gap` 可以完全保留。以下输入在两版均产生真实三策略翻转，但 `policy_details` 完全一致：

```text
供应量 10^6
Z → M 100    # mint
X → M 100    # X 空账户，真实 data_gap
M → D 100
```

pro_rata/fifo 的第一大来源为 mint，lifo 为 data_gap；库存 100 不属于尘埃豁免。两版明细相同，所以依据 [handoff_manifest.py:858](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/handoff_manifest.py:858)，翻转指纹也相同。

应将“必失配”限定为**三策略明细实际变化的锚点**。旧账本的算法哈希校验拒收已有独立依据。

**复现命令：下方 R1，查看 `small_flip` 的 `policy_details_equal = True`。**

### F3 — nit：全套结果 JSON 仍保留早期未提供状态

位置：[run_all_fable_result.json:2](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260915-eps-residual/run_all_fable_result.json:2)。

该文件仍记录 `NOT_PROVIDED`、计数为 null，并称日志不存在；最终 `done.md` 已引用到位日志。建议更新，或明确标为历史记录。

本轮已独立确认原始日志包含与当前 SUITE 顺序完全一致的 **147 PASS、0 FAIL**。

复现：

```sh
python3 -B -c 'import json,re; from pathlib import Path; d=Path("maintenance/repair-20260915-eps-residual"); print(json.loads((d/"run_all_fable_result.json").read_text())["status"]); print("PASS records:",len(re.findall(r"^\s+PASS\s+\S+\.py",(d/"run_all_fable.log").read_text(),re.M)))'
```

输出：`NOT_PROVIDED`、`PASS records: 147`。

## D1–D5 核对

| 项目 | 结果 |
|---|---|
| D1 | **FAIL**：分类、计数、`ev_map` 均按要求增加；数量保证被 F1 反证。 |
| D2 | PASS：系数 `1e-13`、EPS 下限及计算公式正确。 |
| D3 | PASS：默认参数为 `EPS`；四处 SQD 直接调用输入的原返回字段完全一致，新增计数为 0；三策略传参及 algorithm 登记正确。 |
| D4 | 登记完整：三处版本均为 7.0.4，7.0.3/7.0.4 详细段及 schema 三处新增齐全；消费面措辞存在 F2。 |
| D5 | 禁改代码保持原样；数量行为存在 F1。 |

受保护点已逐字比较：

- `VectorAccount`、`LayeredAccount` 整个类及 `__slots__` 不变。
- EPS 定义与账户条件位于当前生产文件第 **90、276、279、308、314、319** 行。
- 输出／策略筛选位于第 **573、588、595** 行，均不变。
- 实际账户条件为 **5 处，另有 EPS 定义 1 处**；没有漏掉实际引用。
- 闭合、尘埃标记、`ORDER_MATERIAL_PCT`、`order_raw`、`unresolved_total` 汇总代码均不变。
- `fp_residual` 确实计入 `UNRESOLVED`；其加入模拟桶后的整体数量问题见 F1。

## T1–T9 与 RED

测试定位：[test_entity_source_trace.py:158](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_entity_source_trace.py:158)。

| 项目 | 核对结果 |
|---|---|
| T1 | 存在；主账本所列断言齐全。本轮另独立确认三策略旧 gap=1、新 residual=1。 |
| T2 | 两档真实缺口测试存在，raw、事件及退出码断言符合工单。 |
| T3 | 阈值及 dust 双版本明细对照存在；本轮内存重放一致。既有断言逐字未改。 |
| T4 | 指定两组样例及四项数量断言存在、通过；未覆盖 F1 混合桶场景。 |
| T5 | algorithm 参数和 simulation 新键断言存在。 |
| T6 | APU 105 实体、210 锚点全量独立核对通过。正式与诊断账本的实体及三策略明细一致。 |
| T7 | 按裁决执行同输入双版本；7 实体、102 地址；退出码均为 2，原因一致；14 锚点数量核对通过，fixture 未改。 |
| T8 | 存在完整案根、真实 subprocess freeze；新账本 exit 0、旧算法账本 exit 2，并断言算法哈希拒收。保留日志对应齐全。 |
| T9 | 版本检查本轮通过；现有全套日志与 147 项 SUITE 完全对应，全部 PASS；结果 JSON 有 F3。 |

RED 核验：

- 三段证据均有命令、退出码、测试及生产文件哈希。
- 生产哈希与 HEAD、`3b29e38` 的生产文件一致。
- 测试哈希与当前测试文件一致。
- T1/T2 摘录与保留账本一致；12 条失败记录计数准确。
- 本轮纯内存重放复现了 T1 的旧版缺口及新版分类。
- GREEN 日志确有 **105 条通过记录**。

本轮未执行会生成文件的完整测试、CLI trace 或 freeze；其执行结果按源码、保留日志及账本核验。

## 回归数字独立复算

**APU：**210 锚点全部一致；三策略数量失败 0；data_gap 条目 `105→0`，residual 条目 105；策略变化键 426，非 gap/residual 变化键 0；指纹变化 `118/210`，恰好对应旧三策略含 gap 的 118 个锚点；旧收据失配 `8/10`。两版 `unresolved_total_pct` 均为 `0.0041`。

**PYTHIA：**14 锚点全部一致，回归 Markdown 与 JSON 无数字错配；两版 `unresolved_total_pct` 均为 `75.7347`。`e_lp` 事件数确为 `11145→3+11139`，少 3 次，但已保留锚点的整数 raw 不变量仍通过。

以下为抽样展示；实际核对覆盖全部 224 个锚点：

| 锚点 | Σraw，两版相同 | gap 旧→新 / residual 新 |
|---|---:|---|
| APU TE-01 current | 22465321377829007555734388734 | 304489068582→0 / 304489068582 |
| APU TE-02 current | 0 | 0→0 / 0 |
| APU TE-03 peak | 12692416205350412102490293521 | 2542235651→0 / 2542235651 |
| APU TE-04 current | 4448780812288 | 0→0 / 0 |
| APU TE-05 current | 3003802027185799069564993630 | 478750745388→0 / 478750745388 |
| PYTHIA e_h9 current | 12061341704654 | 0→0 / 0 |
| PYTHIA e_lp current | 36254349538936 | 6827586→6827586 / 0 |

TE-02/TE-04 的两个尘埃标记均保持。输入清单重新计算 SHA-256，分别为 **33/33、1/1、2/2** 通过。

## 范围与只读检查

- 7 个已跟踪改动文件均在白名单内；54 个未跟踪文件均位于本工单目录。
- `handoff_manifest.py`、两个受保护测试、PYTHIA fixture、invariant manifest、`run_all.py` 均与 HEAD 相同。
- 既有测试移除本次新增部分后，与 HEAD 字节一致。
- 本轮实际运行：CHANGELOG lint、docs lint、版本检查、invariant scan、fixtures lint、`git diff --check`，全部通过。
- `done.md` 的回归数字和测试计数有证据支持；`COMPLETE` 受 F1 否定，收据措辞受 F2 影响。

## R1：F1/F2 共用只读复现命令

在仓库根目录执行；仅读取代码并在内存调用原函数：

```sh
python3 -B -c '
import ast, subprocess
from collections import deque
from pathlib import Path
p = "scripts/report/entity_source_trace.py"
names = {"VectorAccount", "LayeredAccount", "make_account",
         "simulate", "gap_eps", "policy_detail"}
def load(s):
    ns = dict(deque=deque, EPS=1e-6, GAP_EPS_REL=1e-13,
              ENTITY_NODE="@ENTITY",
              ORDER_AMBIGUOUS_KEY=("UNRESOLVED","order_ambiguous",None))
    nodes = [n for n in ast.parse(s).body
             if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),p,"exec"),ns)
    return ns
models = [
    load(subprocess.check_output(
        ["git","--no-optional-locks","show","HEAD:"+p],text=True)),
    load(Path(p).read_text())]
z = "0x0000000000000000000000000000000000000000"
cases = [
    ("mixed",
     [("X","A",2**60),("X","A",1),("A","D",2**60)],
     10*2**90, {"X","A"}, {}),
    ("small_flip",
     [(z,"M",100),("X","M",100),("M","D",100)],
     10**6, {"X","M"}, {z:("PROVEN_ORIGIN","mint",z)})]
for name,rows,supply,ancestors,terms in cases:
    detail = []
    for i,m in enumerate(models):
        edges = [(86400,0,j,0,True,j,f,t,a)
                 for j,(f,t,a) in enumerate(rows)]
        kw = {"gap_eps":m["gap_eps"](supply)} if i else {}
        pd = {
            pol:m["policy_detail"](m["simulate"](
                edges,{"D"},ancestors,terms,{},pol,172799,**kw)["current"])
            for pol in ("pro_rata","fifo","lifo")}
        detail.append(pd)
        print(name,("HEAD","WORKTREE")[i],
              {pol:sum(int(r["raw"]) for r in rs) for pol,rs in pd.items()})
    print("policy_details_equal =",detail[0]==detail[1])
    if name=="small_flip":
        print("tops =",{pol:rs[0]["terminal"] for pol,rs in detail[1].items()})
'
```

**最终结论：FAIL。应先解决 F1 的数量保证冲突，并补充混合缺口回归，再进入验收。**
