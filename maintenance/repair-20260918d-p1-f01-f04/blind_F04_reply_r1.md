# 盲审 F04：PASS

审对象：`7a0b083c66f54017b640486bac2d88483eedf273`；基线：`a4a0f2ccb5cb`。a/b/c 通过；d 无真实测试失败，六项因临时目录不可写记为 `SANDBOX-BLOCKED`，需调度方本机补验。报告全文已打印到 stdout。

**a）终点反例与基线 RED：独立复现通过。**

自行构造同日两笔 v1csv：block 100 mint 100→A，block 101 A→B 40；spec 为 `{"大庄":[A],"散户":[B]}`。仅复用 `write_csv_channel_receipt` 收据构造器，没有依赖新增测试断言。

因物理临时目录不可写，夹具和输出保存在内存文件对象中，DuckDB 通过匿名管道读取原始 CSV；通道校验和重放逻辑保持原样。每例使用全新内存输出目录，另以独立 Python 进程确认实际退出码。

| 对照 | 引擎路径 | 退出码 | `camp_series.json` | 结果 |
|---|---|---:|---|---|
| HEAD | `replay_pass1 → replay_pass2` | pass1=0，pass2=2 | 不存在，未曾打开写入 | stderr 含 `[camp-spec]`、`残差桶` |
| HEAD | `replay_duck --camps --no-merged` | 2 | 不存在，未曾打开写入 | stderr 含 `[camp-spec]`、`残差桶` |
| 基线校验模块 | `replay_pass1 → replay_pass2` | 0 | 存在 | dates=1；散户=`[40.0, 0]` |
| 基线校验模块 | `replay_duck --camps --no-merged` | 0 | 存在 | dates=1；散户=`[40.0, 0]` |

基线通过 `git show a4a0f2ccb5cb:scripts/lib/camp_spec.py` 读取并仅在内存加载，确实接受该 spec；两引擎均产出 `len(散户)=2×len(dates)`。两引擎及 pass1 源码与基线逐字节一致。

HEAD 拒绝路径为 [replay_pass2.py:57](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/replay_pass2.py:57) 或 [replay_duck.py:467](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/replay_duck.py:467) → [camp_spec.py:63](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/camp_spec.py:63) → `_fail` 第 31 行打印、第 32 行退出 2。实际 stderr：

```text
[camp-spec] /__f04_memory__/HEAD_pass1_pass2_process/camps.json 阵营「散户」是 EVM 引擎的残差桶（100−已知阵营），不得在 spec 里配置——显式配置会让 replay_pass2/replay_duck 同日写两个元素；把这些地址归入其他阵营或删掉
```

兼容性实测：

- Solana `validate_camp_spec({"散户":[SA]}, chain_family="solana")` 仍接受。
- `load_addr_camp_json` 使用默认链族，输入 `{SA:"散户"}` 仍接受。
- 合法 EVM spec `{"项目方":[A],"大庄":[B]}` 在两引擎均成功；HEAD 与基线的 `camp_series.json`（315 B）和 `entity_series.json`（50 B）分别逐字节一致。
- 另核五组合法 spec，规范化返回字节一致。

独立验证以 `python3 -B -c` 执行审方内存脚本，成功尾行：

```text
PASS independent F04 reproduction: HEAD reject x2; baseline RED x2; Solana accept x2; legal outputs byte-identical x2
```

**b）修法与工单 v2 精确一致。**

`camp_spec.py` 仅修改第 22 行 docstring，并在第 62–64 行增加 `chain_family == "evm" and camp == "散户"` 拒收，走既有 `_fail`。将基线文本按工单两处替换后，与 HEAD 全文比较相等。

函数签名、返回形状与顺序不变；四入口文件与基线逐字节一致，调用点未动。

**c）白名单及字节数通过。**

实跑命令与输出：

```text
git diff --stat a4a0f2ccb5cb HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
 scripts/lib/camp_spec.py             |  5 ++++-
 scripts/tests/test_repair_batch_c.py | 15 +++++++++++++++
 2 files changed, 19 insertions(+), 1 deletion(-)
```

仅用元数据核得：

| 范围 | 实测字节数 |
|---|---:|
| `SKILL.md` | 8021 |
| `references/**/*.md` | 930076 |
| `commands-staging/*.md` | 8798 |

`git diff --quiet HEAD -- scripts` 返回 0，审阅和执行的脚本对应当前 HEAD。

**d）七条命令均已原样执行。**

| 实跑命令 | 退出码 | 结果／错误尾部 |
|---|---:|---|
| `python3 -B scripts/tests/test_repair_batch_c.py` | 1 | SANDBOX-BLOCKED；E1 |
| `python3 -B scripts/tests/test_repair_batch_d.py` | 1 | SANDBOX-BLOCKED；E2 |
| `python3 -B scripts/tests/test_engine_equivalence.py` | 1 | SANDBOX-BLOCKED；E3 |
| `python3 -B scripts/tests/test_fault_injection.py` | 1 | SANDBOX-BLOCKED；E3 |
| `python3 -B scripts/tests/test_batch4_invariant_guards.py` | 1 | SANDBOX-BLOCKED；E3 |
| `python3 -B scripts/tests/test_exemption_guards.py` | 1 | SANDBOX-BLOCKED；E3，阻塞前 3 项 EX-01 检查 PASS |
| `python3 -B scripts/tests/invariant_scan.py` | 0 | PASS，尾行如下 |

错误原文：

```text
E1 PermissionError: [Errno 1] Operation not permitted: '/private/tmp/c-blind-fix1-rgcsoxw9'
E2 PermissionError: [Errno 1] Operation not permitted: '/private/tmp/d-f07-green-8q1878qc'
E3 FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

C/D 显式指定 `/private/tmp`，同一临时目录写入限制表现为 `PermissionError`；按沙箱受阻归类，未计为实现失败，也未记成测试 PASS。`python3 -c "import tempfile;print(tempfile.gettempdir())"` 自检同样报 E3。等价测试在 E3 后附 Hypothesis `Falsifying example`，根因仍是临时目录创建失败。

`invariant_scan.py` 尾行：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

全程离线、只读，未修改文件、未 commit。未读取 `~/.codex/`、memories、两份施工方自述或其他禁读内容；未主动打开历史 maintenance 文件。maintenance 仅阅读指定工单与裁决作为验收依据，未审其改动。
