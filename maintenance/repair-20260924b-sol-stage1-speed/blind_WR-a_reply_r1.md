# WR-a盲审：FAIL

**A 通过；B/C 未完成，0.7 正式入口验收不能判定通过。** 阻断原因是当前沙箱连系统 `/tmp` 都禁止写入，无法生成所要求的自包含夹具。此 FAIL 表示验收未完成，未发现可复现的生产代码错误。

审查 HEAD：`70e14a81817316ea225d6341e2c8670c84e544a1`。

**A）登记与守卫：通过本阶段判据**

独立验证结果：

- 指定基线至 HEAD 的 `scripts` 差异仅为 `scripts/lib/producer_history.py`，`+32/-0`，追加四条 ACTIVE。
- 使用 AST 逐条比较，原有 34 条全部不变；剔除新增区段后，其余源码字节与基线一致。
- 四条新增条目的字段、协议、commit、reason 均符合登记单；工作树文件与 HEAD 一致。
- 源码 commit 是 HEAD 的祖先；`git diff --check` 通过。

亲跑：

```sh
git show '59f88b84c9ab9eeb95c92a15e342d8cbe09925db:scripts/solana/sqd_gap_repair.py' | shasum -a 256
```

输出：

```text
15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33  -
```

另以 Python 对四条记录分别读取 Git 对象复算，并与工作树文件比较，全部相等。

亲跑 `python3 -B scripts/tests/test_producer_registry_current.py`：

| repair 协议 | 当前哈希检查 | 新增登记 Git 复现 |
|---|---|---|
| `sqd-solana-cache/v4` | ok | ok |
| `sqd-solana-repair-bundle/v1` | ok | ok |
| `sqd-solana-coverage-resolution/v1` | ok | ok |
| `sqd-solana-repair-pointer/v1` | ok | ok |

全部 38 条登记的 Git 复现、脚本集合、必要协议及其余当前哈希检查均为 `ok`。仅下列两项 FAIL，符合 WR-b 尚未登记的阶段预期：

- `scripts/solana/sqd_coverage_probe.py` — `sqd-solana-coverage/v1`
- `scripts/solana/sqd_coverage_probe.py` — `sqd-solana-coverage-pointer/v1`

对应当前哈希：

```text
ab2371f5350f6eb2be38a32c72a0703c258c2ea760f59fcc7f7dacfbf6dcde86
```

实际尾行 `producer registry: 2 FAIL`，退出码 `1`；该守卫不能记作整体 PASS。

**B）三类正式入口：均未执行**

已读取 W4 自包含构造器及真实消费入口，但夹具创建前置条件失败：

| 证据类型 | `validate_repair_bundle(deep=True, …)` | `resolve_formal_cache(MINT, case)` |
|---|---|---|
| 全旧 | 未调用：无法创建临时夹具 | 未调用 |
| 全新 | 未调用：无法创建临时夹具 | 未调用 |
| 混合 | 未调用：无法创建临时夹具 | 未调用 |

因此未验证 `kind`、`gid`、`binding`，也未验证 edge/meta 指向 CURRENT 所选代。没有用深验 helper 或已有测试报告替代这项验收。

**可复现的环境阻断**

在本会话相同执行权限下运行：

```sh
python3 -B -c 'import tempfile; tempfile.mkdtemp(prefix="wr-a-", dir="/tmp")'
```

实际退出码 `1`，异常原文：

```text
PermissionError: [Errno 1] Operation not permitted: '/tmp/wr-a-tg4cbohc'
```

随机目录后缀会变化。这是夹具创建失败的复现，不是正式入口拒收的反例。

**C）移除登记对照：未执行**

未在内存中移除登记后重复正式入口调用，故没有实测取得 `formal repair producer is not registered`，也不能声称已证明通过来自本次登记。

**执行边界**

全程离线，未读取 `~/.codex/`、memories 或其他禁读路径；`maintenance/` 仅读取允许目录内的登记单、完成报告与验收报告。未修改仓库、未 commit，结束时工作树仍干净。独立字节比较运行器曾因换行边界计算错误触发断言，修正内存中的比较代码后通过，未改仓库文件。

完成验收仍需在**仓库只读、系统 tempfile 可写**的执行环境中补跑 B/C；当前会话不允许提升写入权限。