# W4盲审：FAIL

审查 HEAD：`fcb374568b3a82edab0ab4bcfd73814aadfe46fb`。

**请求合并实现未发现回归；FAIL 原因是本次要求 e 的正式入口验收尚未成立：三类产物测试调用底层深验，未经过 `validate_repair_bundle(deep=True)`，当前 producer SHA 也尚未登记。** 这是已在完成报告中披露、等待 WR-a 的验收缺口。

**唯一阻断项：三类产物通过底层深验，不等于通过正式入口。**

[test_sqd_gap_repair.py:1576](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_gap_repair.py:1576) 调用的是 `exact.validate_repair_bundle_deep(...)`。该测试调用的生产流程也只调用底层深验。

正式入口在 [sqd_cache_identity.py:143](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_cache_identity.py:143) 先检查 producer 登记；当前 SHA 不在允许集合中。我以真实函数及真实登记表、仅替换 JSON 读取为内存输入执行该关卡，实际得到：

```text
ValueError: formal repair producer is not registered
```

以下命令可只读、离线复现测试入口和登记缺口；在指定工作目录执行：

```bash
python3 -B -S -c '
import ast, hashlib
from pathlib import Path

p = Path("scripts/tests/test_sqd_gap_repair.py")
tree = ast.parse(p.read_text())
test = next(n for n in tree.body
    if isinstance(n, ast.FunctionDef)
    and n.name == "test_w4_evidence_generations")
calls = [
    getattr(n.func, "attr", getattr(n.func, "id", ""))
    for n in ast.walk(test) if isinstance(n, ast.Call)
]
h = {}
exec(Path("scripts/lib/producer_history.py").read_text(), h)
script = "scripts/solana/sqd_gap_repair.py"
sha = hashlib.sha256(Path(script).read_bytes()).hexdigest()
print("direct_deep_calls =", calls.count("validate_repair_bundle_deep"))
print("formal_wrapper_calls =", calls.count("validate_repair_bundle"))
print("registered =", sha in h["historical_producer_hashes"](
    script, "sqd-solana-cache/v4"))
'
```

实际输出：

```text
direct_deep_calls = 1
formal_wrapper_calls = 0
registered = False
```

本次 e 的预期是三类产物通过真实 `validate_repair_bundle(deep=True)`；当前测试与登记状态不能满足。应由 WR-a 完成登记，再补三类产物的正式入口验证及 `resolve_formal_cache` 验收，无需为此修改 W4 禁改的登记文件。

**其余核验结果：**

| 项目 | 独立审查结果 |
|---|---|
| a：白名单、行数 | 范围内仅修改三份白名单代码／测试文件。生产文件 `+19/-33=52` 行；schema、CLI、版本、登记表、manifest 均未改。未发现压行数导致的输入处理删减或可读性问题。 |
| b：合并与状态算法 | 77 组内存响应对照基线 `_state_probe`，present/nonce_count 一致；覆盖非目标块、缺键、null、空数组、重复块及超过 255 的长度。状态校验仍先于 Helius，函数体未改。 |
| c：查询与摘要 | `_census_body` 复用 `sqd_query_body` 的 instruction 字段及选择器，保留原交易选择器与键顺序。新摘要两两相等且满足 hex64；深验没有摘要必须互异的要求。 |
| d：删除与保留 | 允许检索范围内 `_state_probe` 无残留引用。AST 对比仅 `_census_body`、`_fetch_live_slot` 和删除 `_state_probe` 有变化；β 查询及退避函数未改。 |
| e：构造与保留 | 源码确实自包含构造全旧、全新、混合三类证据，使用固定旧模板，并要求存在 confirmed 缺失交易；断言旧 evidence 字节保留、旧 ledger 行内容保留、旧 slot 无请求。正式入口缺口如上。 |
| f：故障与恢复 | 独立执行 SQD 耗尽：4 次 census、退避 2/4/8 秒、Helius 0 次。源码中的故障测试明确断言 rc=2/3、STOPPED、成功前缀及恢复；磁盘流程本轮未执行。 |
| g：测试登记、报告 | 新增用例已接入两份测试的 main。52 行及 SHA 陈述正确；完成报告明确披露正式入口验收待办，没有声称已经通过。 |

实际 SHA：

```text
15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33
```

独立运行真实调度函数、用内存替换持久化：workers=1、4 均验证逐 slot `sqd-census=1`、`sqd-probe=0`、Helius=1，有序提交，恢复前缀不重采。该验证不代表磁盘落盘验收。

**h 的独立拒收验证全部符合预期：**

| 输入（slot=42） | 实际结果 | Helius |
|---|---|---:|
| 两个 `header.number==42` 块 | `SQD census duplicated slot 42` | 0 |
| `MISSING_BLOCK` α 却有目标块头 | `SQD coverage state changed before repair` | 0 |
| `INHERITED_REFUTED` 进入 α，有块头 | `non-candidate coverage state entered alpha` | 0 |
| `INHERITED_REFUTED` β，nonce=1 | `SQD coverage state changed before repair` | 0 |
| `INHERITED_REFUTED` β，无目标块头 | 同上 | 0 |
| `DEFECT_CANDIDATE` α，nonce=1 | 同上 | 0 |

“α 有块头应拒绝”需要带上状态条件：`DEFECT_CANDIDATE` α 有块头且 nonce=0 应通过，独立验证也确实通过。

本轮未执行需要创建文件的完整测试、三类产物磁盘深验、STOPPED 落盘或正式 resolver 验收；未访问在线 SQD。调度方验收报告中的完整运行结果仅作为已有证据，未冒充本轮复跑结果。

全程未读取禁区或 memories，未联网、未修改文件、未 commit；结束时工作树干净。