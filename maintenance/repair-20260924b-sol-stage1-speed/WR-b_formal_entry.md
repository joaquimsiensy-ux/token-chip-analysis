# WR-b验收：PASS

①②③④ 全部通过。验收 HEAD：`8ba3de969dd9d7a0bcce4a36fdc9d25635785ef5`。

目标脚本：`scripts/solana/sqd_coverage_probe.py`；源码 commit：`f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6`。
目标 SHA-256：`d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8`。

**① 真实登记查询：通过**

直接调用原始 `producer_history.historical_producer_hashes(script, protocol)`，未替换函数、未 patch 注册表。

| 协议 | 返回哈希数 | 目标 SHA 在结果中 |
|---|---:|---|
| `sqd-solana-coverage/v1` | 5 | `True` |
| `sqd-solana-coverage-pointer/v1` | 5 | `True` |

两个协议返回的完整集合相同，排序后均为：

```text
bccf1802b6a5c9d9bbbdb12e19354ad761416c631e3cdfde2449f7fe1794f176
be415db3552588532ff195126ddd53aefe9d3c14785da64c2be4cf23804f7bea
c4980c984b08d27f5a7e46db50f97c9c16e47ea491f37a459b3773f939218769
d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8
e41370b185aef9bd16fea8ce1abc519a138ee4ce8923bdbc8058d64cdd0619bf
```

**② 差异、历史条目与注册表测试：通过**

独立审查 `git diff fcf81f062daa004a37862a92cfe1c488a98da2b0 HEAD -- scripts`，仅 `scripts/lib/producer_history.py` 变化，`+16/-0`，追加两条目标协议的 ACTIVE 登记，字段与登记单一致。

AST 解析得到原有 38 条、现有 40 条；前 38 条逐项 AST 值及源码片段均相同。进一步从 HEAD 文件字节中移除新增两条所在行，所得整个文件与基线逐字节相同。工作树注册表也与 HEAD 文件一致。

独立执行：

```sh
git show 'f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6:scripts/solana/sqd_coverage_probe.py' | shasum -a 256
```

输出：

```text
d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8  -
```

与登记值及工作树源码哈希相等。亲跑 `test_producer_registry_current.py`：通过 `runpy.run_path(..., run_name="__main__")` 执行原始测试入口，捕获退出码 `0`，共 `53` 条 `ok`，没有失败项。两协议当前哈希检查及两条新增登记的 Git 复现检查均为 `ok`；完整输出保存在临时目录 `registry.log`。尾行：

```text
producer registry: 0 FAIL
```

**③ 真实 coverage 兼容性：通过**

复用 `scripts/tests/test_sqd_coverage_probe.py` 的 `_w1_run` 动态夹具，调用真实探针发布产物。夹具、case 和产物全在 tempfile 中；目录存续期间直接调用真实校验器，未替换校验器或生产者查询函数。

```text
from=0, to=9999
probe_id=fcf2a9df9c459ba9
ok=True
reasons=[]
```

产物 producer SHA 等于目标 SHA。`scripts/lib/solana_exact_validate.py:712-722` 对 coverage 和 pointer 均采用“等于当前源码 SHA，或属于历史登记集合”的条件，因此本步只证明兼容；登记有效性由①及④证明。

**④ 仅内存移除登记的对照：通过**

仅在 `unittest.mock.patch.object(producer_history, "PRODUCER_HISTORY", filtered)` 作用域内移除本次两条登记，条目数从 40 变为 38，查询函数始终是原函数。

| 协议 | 返回哈希数 | 目标 SHA 在结果中 |
|---|---:|---|
| `sqd-solana-coverage/v1` | 4 | `False` |
| `sqd-solana-coverage-pointer/v1` | 4 | `False` |

两个完整结果均严格等于①所列集合减去目标 SHA，其余四个哈希不变。退出 patch 后原元组对象恢复，两协议再次查询均包含目标 SHA。

**运行器关键代码**

以下为实际运行器核心节选；`SCRIPT`、`SHA`、`PROTOCOLS` 为上文脚本、目标哈希和两个协议，`old/new` 为基线与 HEAD 注册表源码字节。

```python
import producer_history
from unittest.mock import patch

query = producer_history.historical_producer_hashes
positive = {p: sorted(query(SCRIPT, p)) for p in PROTOCOLS}
assert all(SHA in positive[p] for p in PROTOCOLS)

old_nodes, old_values = entries(old)  # ast.parse + ast.literal_eval
new_nodes, new_values = entries(new)
assert len(old_values) == 38 and len(new_values) == 40
assert old_values == new_values[:38]
assert all(
    ast.get_source_segment(old.decode(), a)
    == ast.get_source_segment(new.decode(), b)
    for a, b in zip(old_nodes, new_nodes[:38])
)
lines = new.splitlines(keepends=True)
assert b"".join(
    lines[:new_nodes[38].lineno - 1] + lines[new_nodes[39].end_lineno:]
) == old

runpy.run_path(
    str(REPO / "scripts/tests/test_producer_registry_current.py"),
    run_name="__main__",
)  # 外层捕获 SystemExit，断言 code == 0，并保存完整 stdout

fixture = runpy.run_path(
    str(REPO / "scripts/tests/test_sqd_coverage_probe.py"),
    run_name="wr_b_fixture",
)
case, (_, generation, coverage) = fixture["_w1_run"](TEMP / "publication")
exact = fixture["exact"]
assert exact.historical_producer_hashes is query
checked = exact.validate_coverage(
    case, generation / "coverage_map.json",
    case / "data/sqd_coverage/CURRENT.json", 0, 9999,
)
assert checked["ok"] is True, checked["reasons"]

original = producer_history.PRODUCER_HISTORY
filtered = tuple(row for row in original if row not in new_values[38:])
assert len(filtered) == 38
with patch.object(producer_history, "PRODUCER_HISTORY", filtered):
    assert producer_history.historical_producer_hashes is query
    negative = {p: sorted(query(SCRIPT, p)) for p in PROTOCOLS}
    assert all(SHA not in negative[p] for p in PROTOCOLS)
    assert all(set(negative[p]) == set(positive[p]) - {SHA} for p in PROTOCOLS)
assert producer_history.PRODUCER_HISTORY is original
assert all(SHA in query(SCRIPT, p) for p in PROTOCOLS)
```

**执行环境与范围记录**

- Python：`3.14.6 (v3.14.6:c63aec69bd5, Jun 10 2026, 08:07:54) [Clang 21.0.0 (clang-2100.1.1.101)]`；执行器 `/usr/local/bin/python3`，使用 `-B` 和 `PYTHONDONTWRITEBYTECODE=1`。
- 成功运行的 tempfile：`/private/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/wr-b-acceptance-tt4ucu9r`，由 `tempfile.mkdtemp()` 创建并保留。
- 该目录包含 `runner.py`、`results.json`、`scripts.diff`、`registry.log`、`publication.log`、`validation.json`。coverage 路径为其下 `publication/case/data/sqd_coverage/fcf2a9df9c459ba9/coverage_map.json`，pointer 为 `publication/case/data/sqd_coverage/CURRENT.json`。
- 前两次临时运行器尝试分别位于同一系统临时父目录下的 `wr-b-acceptance-7njdeen5` 和 `wr-b-acceptance-1cezvxso`，均保留。第一次因附加路径检查误判 `dir_fd` 相对文件名而中断；第二次因检查范围过窄，拦截 Python 在系统 tempfile 父目录进行的可写性探测。被拦截写入均未执行。将运行 cwd 和 `TMPDIR` 指向本次 tempfile 后完整重跑通过；未修改仓库源码。
- 禁区读取：**否**；未读取 `~/.codex/` 或 memories，未读取用户列明的其他禁区。离线执行，动态夹具提供传输响应；Python 审计钩子禁止网络调用，成功运行无拦截事件。子进程仅执行本地 `git show` 和 `shasum`。
- 本任务仓库内仅写入 `maintenance/repair-20260924b-sol-stage1-speed/WR-b_formal_entry.md`；未 commit、push、stash、checkout、reset，未建 worktree，未批量删除。
- 初始工作树干净；写报告前发现另有未跟踪文件 `maintenance/repair-20260924b-sol-stage1-speed/review_final_prompt.md`。该文件非本任务创建，未读取或修改。
