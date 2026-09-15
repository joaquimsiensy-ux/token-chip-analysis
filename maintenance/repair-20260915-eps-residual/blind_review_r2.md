<!-- 由 Fable 从 codex 只读盲审任务 task-mu2u6wj9-6zrryq 的最终报告正文原样搬运 -->
# 盲审 R2:FAIL

**发现 1 项 blocker：R2 已按裁决修改，但新裁决的数量不变量仍被实际重放反证，F1 不能关闭。**

审查基线：`main`，HEAD=`2000b6e78f790ee0ed348cc2ecb8eae796d5136e`，工作树版本 `7.0.4`。全程离线、零文件修改，未读取禁止的目录或 tag。审查前后 **1,090 个文件及四份回归账本均无哈希变化**。

## 一、逐项结论

severity 表示对应审查事项的影响等级；下表两处 FAIL 属于同一个 blocker，不重复计数。

| 核对项 | 结果 | severity | 核验结果 | 只读复现 |
|---|---|---|---|---|
| F1：生产文件与 R1 完全相同 | PASS | blocker | SHA-256 精确等于指定的 `e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1` | R0 |
| F1：T4 修改与既有两组样例 | PASS | blocker | 已检查 stock、非 gap/residual raw、新有界差分；旧两组样例保留差 0 断言。本轮内存重放各 **31 项检查通过** | R0 |
| F1：T4-mixed 与 FIFO 解释 | PASS | blocker | 测试存在且接入入口；原样例三策略差值为 **1／0／1**，与 done.md 表格一致；FIFO 的 1 raw 确实留在 A | R1 |
| F1：新数量不变量成立 | **FAIL** | **blocker** | 第二笔改为 **129 raw**，主策略出现 **Δ=−128**，违反非负下界 | R1 |
| F1：文档数量承诺 | **FAIL** | **blocker** | 三处已按裁决改写；但新增的“7.0.4 ≥ 7.0.3”保证被同一反例否定 | R0、R1 |
| F1：APU/PYTHIA 新不变量复核 | PASS | blocker | **224 锚点、666 组三策略比较**全部通过；回归 Markdown、复核 JSON 与账本数字一致 | R2 |
| F2：收据失配范围 | PASS | minor | 已限定为“三策略明细实际变化的锚点”；明确小供应量真实 data_gap 可保持收据匹配 | R0、R4 |
| F3：全套结果 JSON | PASS | nit | `PASS / 147 / 0`、日志路径及 SHA-256 均匹配实际日志，SUITE 顺序一致 | R3 |
| 既有断言一条未删 | PASS | blocker | 原 **69 处 check 表达式全部保留**；现为 84 处。旧日志 105 项均保留，R2 日志共 200 项，其中 mixed 51 项 | R3 |
| 白名单与 git status | PASS | blocker | 相对施工前 1,062 文件，仅七个指定既有文件改变；无删除、无越界新增。当前 7 个 tracked 改动、84 个 untracked 均在允许范围 | R3 |
| `_r2` 日志与 done.md 退出码 | PASS | minor | 七项退出码均为 0；调度日志、结果 JSON、原始输出及被测文件哈希一致 | R3 |

## 二、唯一 blocker：新裁决的非负下界仍不成立

位置：

- [scan-schemas.md:329](/Users/uravvv/.claude/skills/token-chip-analysis/references/scan-schemas.md:329)
- [CHANGELOG.md:92](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:92)
- [done.md:3](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260915-eps-residual/done.md:3)
- [test_entity_source_trace.py:217](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_entity_source_trace.py:217)

令 `H=2^60`，供应量仍为 `10×2^90`，同日精确顺序：

```text
X → A  H
X → A  129
A → D  H
```

完整 `trace_entity()` 在内存 DuckDB 中重放，D 的 current、peak 均得到：

| 主策略字段 | 7.0.3 | 7.0.4 |
|---|---:|---:|
| stock_raw | 1152921504606846976 | 1152921504606846976 |
| data_gap raw | 1152921504606846976 | 1152921504606846720 |
| fp_residual raw | 0 | 128 |
| 构成 Σraw | 1152921504606846976 | 1152921504606846848 |
| closure pct | 100.0 | 100.0 |

因此：

```text
Δ = gap704 + residual704 − gap703
  = −128

0 ≤ Δ ≤ residual704
⇒ 0 ≤ −128 ≤ 128     FAIL
```

直接对这两份内存账本调用 **当前 R2 的 `eps_compare_quantities()`**，出现 **4 条失败**：current、peak 各自的主构成检查和 pro_rata 策略检查。

原因是浮点合并也会**向上舍入**：这里 `float(H)+129` 得到 `H+256`；分桶后的比例扣减与逐桶截断，使新版合计反而减少。仅凭原来的 `1 raw` 样例，不能推出普遍的单向差分保证。

**应退回 F1 的数量裁决，加入该反例后重新确定承诺范围。**

### 原 T4-mixed 的 FIFO 解释成立

原第二笔为 `1` 时：

| 策略 | D 的 Σraw 差值 | D 的 residual704 | A 的剩余 residual704 |
|---|---:|---:|---:|
| pro_rata | 1 | 1 | 0 |
| fifo | 0 | 0 | 1 |
| lifo | 1 | 1 | 0 |

所以 [done.md:147](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260915-eps-residual/done.md:147) 的解释成立。裁决③的 `H+1` 在施工记录中明确落到主构成，FIFO 单独保留差 0。

### 旧措辞残留

指定三个文档中，旧的绝对数量承诺已替换；`done.md:3` 保留旧句是为了说明被替代的历史承诺。原 plan 保留审批历史。

冻结生产文件的模块说明仍有“数量不变”，与 R1 哈希一致；本轮裁决明确禁止修改生产文件，因此未另计为 R2 新问题。

## 三、真实账本抽查

实际核对覆盖全部 **224 锚点及 666 组策略明细**；以下展示三个锚点。stock 两版相同，非 gap/residual raw 逐项相同。

| 锚点 | Σraw，两版相同 | gap703 → gap704 | residual704 | Δ |
|---|---:|---:|---:|---:|
| APU TE-01 current | 22465321377829007555734388734 | 304489068582 → 0 | 304489068582 | 0 |
| APU TE-03 peak | 12692416205350412102490293521 | 2542235651 → 0 | 2542235651 | 0 |
| PYTHIA e_lp current | 36254349538936 | 6827586 → 6827586 | 0 | 0 |

这些实际样本通过，不能证明新不变量对其他输入普遍成立。

## 四、只读复现命令

均在仓库根目录执行。

### R0：生产哈希、测试与文档位置

```sh
shasum -a 256 scripts/report/entity_source_trace.py
sed -n '198,237p;315,360p;409,415p' scripts/tests/test_entity_source_trace.py
sed -n '89,96p' CHANGELOG.md
sed -n '326,331p' references/scan-schemas.md
sed -n '128,169p' maintenance/repair-20260915-eps-residual/done.md
```

### R1：原 mixed、FIFO 留存及新反例

仅读取已核验的 R1 复现代码中的加载部分，调用原模拟函数；不创建文件。

```sh
python3 -B -c '
from pathlib import Path
s=Path("maintenance/repair-20260915-eps-residual/r1_reproduction_r2.py").read_text()
exec(s[:s.index("\nz = ")])
H=2**60
for small in (1,129):
    edges=[(86400,0,i,0,True,i,f,t,v) for i,(f,t,v) in enumerate([
        ("X","A",H),("X","A",small),("A","D",H)])]
    for pol in ("pro_rata","fifo","lifo"):
        values=[]
        for i,m in enumerate(models):
            kw={"gap_eps":m["gap_eps"](10*2**90)} if i else {}
            run=m["simulate"](edges,{"D"},{"X","A"},{},{},pol,172799,**kw)
            assert run["current"]==run["peak"]
            q={r["terminal"][1]:int(r["raw"])
               for r in m["policy_detail"](run["current"])}
            values.append((q.get("data_gap",0),q.get("fp_residual",0),sum(q.values())))
        delta=values[1][2]-values[0][2]
        print(small,pol,"703/704 (gap,residual,sum) =",values,
              "delta =",delta,"bound =",0<=delta<=values[1][1])
    if small==1:
        m=models[1]
        a=m["simulate"](edges,{"A"},{"X"},{},{},"fifo",172799,
                        gap_eps=m["gap_eps"](10*2**90))
        print("FIFO A remaining:",m["policy_detail"](a["current"]))
'
```

关键输出：`129 pro_rata ... delta = -128 bound = False`。

### R2：从四份账本重新计算新不变量

```sh
python3 -B -c '
import json
from pathlib import Path
G=("UNRESOLVED","data_gap",None)
R=("UNRESOLVED","fp_residual",None)
def raw(rows,policy=False):
    out={}
    for r in rows:
        k=tuple(r["terminal"]) if policy else (r["kind"],r["subkind"],r["via"])
        assert k not in out
        out[k]=int(r["raw"])
    return out
def compare(x,y):
    assert 0<=y.get(G,0)+y.get(R,0)-x.get(G,0)<=y.get(R,0)
    assert sum(x.values())==sum(y.values())
    assert {k:v for k,v in x.items() if k not in (G,R)}=={
        k:v for k,v in y.items() if k not in (G,R)}
cases=[
 ("APU",".staging_eps/apu/provenance_ledger.json",
        ".staging_eps/apu/provenance_ledger_704.json"),
 ("PYTHIA",".staging_eps/pythia/t7_compare/ledger_703.json",
           ".staging_eps/pythia/t7_compare/ledger_704.json")]
for name,p0,p1 in cases:
    old,new=[json.loads(Path(p).read_text()) for p in (p0,p1)]
    a,b=[{e["entity_id"]:e for e in l["entities"]} for l in (old,new)]
    assert a.keys()==b.keys()
    anchors=policies=0
    for eid in a:
        for anchor in ("current","peak"):
            x,y=a[eid]["anchors"][anchor],b[eid]["anchors"][anchor]
            assert x["stock_raw"]==y["stock_raw"]
            compare(raw(x["composition"]),raw(y["composition"]))
            u,v=[l["bounds_sensitivity"]["per_entity"][eid]["anchors"]
                 .get(anchor,{}).get("policy_details",{}) for l in (old,new)]
            assert u.keys()==v.keys()
            for p in u:
                compare(raw(u[p],True),raw(v[p],True))
                policies+=1
            anchors+=1
    print(name,"anchors =",anchors,"policies =",policies,"PASS")
'
```

预期：APU `210 / 630`，PYTHIA `14 / 36`，全部 PASS。

### R3：断言保留、范围、F3 与退出码

```sh
git --no-optional-locks status --short
python3 -B -c '
import ast,collections,hashlib,json,os,re
from pathlib import Path
d=Path("maintenance/repair-20260915-eps-residual")
def checks(s):
    return collections.Counter(ast.dump(n) for n in ast.walk(ast.parse(s))
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
        and n.func.id=="check")
old=(d/"test_entity_source_trace_before_r2.txt").read_text()
new=Path("scripts/tests/test_entity_source_trace.py").read_text()
a,b=checks(old),checks(new)
assert not(a-b)
print("check calls:",sum(a.values()),sum(b.values()),"removed:",sum((a-b).values()))
def passed(name):
    return collections.Counter(x[6:] for x in (d/name).read_text().splitlines()
                               if x.startswith("ok    "))
a,b=passed("test_entity_source_trace.log"),passed("test_entity_source_trace_r2.log")
assert not(a-b)
print("executed:",sum(a.values()),sum(b.values()),"missing:",sum((a-b).values()))
before=json.loads((d/"scope_before_r2.json").read_text())
changed=[]; missing=[]
for name,r in before["files"].items():
    p=Path(name)
    if not p.exists() and not p.is_symlink():
        missing.append(name); continue
    blob=os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
    if hashlib.sha256(blob).hexdigest()!=r["sha256"]: changed.append(name)
print("r2 changed files:",sorted(changed),"missing:",missing)
result=json.loads((d/"run_all_fable_result.json").read_text())
blob=(d/result["log"]).read_bytes()
passed_all=re.findall(r"^\s+PASS\s+(\S+\.py)",blob.decode(),re.M)
failed_all=re.findall(r"^\s*FAIL(?:\(rc=[^)]+\))?\s+(\S+\.py)",blob.decode(),re.M)
assert result["status"]=="PASS" and len(passed_all)==result["pass"]==147
assert len(failed_all)==result["fail"]==0
assert hashlib.sha256(blob).hexdigest()==result["log_sha256"]
print("F3:",result["status"],len(passed_all),len(failed_all))
receipt=json.loads((d/"check_results_r2.json").read_text())
assert receipt["results"]==[
    json.loads(x) for x in (d/"run_checks_r2.log").read_text().splitlines()]
for name,h in receipt["files"].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
for r in receipt["results"]:
    assert r["exit_code"]==0
    lines=(d/r["log"]).read_text().splitlines()
    print(r["log"],"exit",r["exit_code"],lines[-1:] or ["empty"])
print("final checks:",json.loads((d/"final_checks_r2.json").read_text()))
'
```

F3 记录的是既有 `run_all_fable.log`；`exit_code=null` 如实反映日志未单列退出码。空的 `run_all_fable_r2.log` 没有被用于 PASS 证明。本轮没有重跑会落盘的完整测试或 CLI。

### R4：F2 小供应量反例

```sh
python3 -B maintenance/repair-20260915-eps-residual/r1_reproduction_r2.py
```

`small_flip` 输出 `policy_details_equal = True`。本轮另外调用实际 `flip_fingerprint()` 确认两版指纹相同，支持“收据仍匹配”的修正文案。

**总结论：FAIL——1 项 blocker；F1 新数量不变量被 −128 raw 的实际反例推翻，其余所列 R2 核对项通过。**
