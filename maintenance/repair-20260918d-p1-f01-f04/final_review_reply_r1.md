# 收官review：通过

F01／F04 的指定反例均已独立复现：基线暴露原缺陷，HEAD 达到拒绝／降级终点，合法对照未被误杀。白名单、文档字节数、两段隔离及 invariant scan 均通过，未发现真实 FAIL。**7 项回归受沙箱阻断，仍需调度方本机 run_all 补验。**

审查范围：`868d3f61 → 268026ca0464ce860b2bfd7e9eabf2c5d59d7405` 的 scripts diff。未读取禁区文件；全程离线，无文件修改、删除或 commit。报告全文已打印到 stdout。

独立复现使用内存 CSV／文件系统，执行两版本原始生产函数与 main，捕获 SystemExit。第二源固定返回指定值；DuckDB 使用真实内存数据库，将 CSV 读取映射为相同字符串列的内存表，并替代磁盘容量探测。价格分类、通道预检、重放、阵营校验和序列生成逻辑均原样执行。

a) `price_nan`：

| 输入 | 基线 868d3f61 | HEAD |
|---|---|---|
| 三天 close=NaN；第二源 1.0 | rc=0、PASS；收据含 NaN | rc=1、[fatal]；未写收据 |
| 首日 inf，其余 1.0 | rc=0、PASS；收据含非有限值 | rc=1、[fatal]；未写收据 |
| 首日 0，其余 1.0 | rc=0；首点 SKIP，总 verdict PASS | rc=1、[fatal]；未写收据 |
| 首日 −1，其余 1.0 | rc=0；首点 SKIP，总 verdict PASS | rc=1、[fatal]；未写收据 |
| 主价均 1.0；第二源 NaN；带 --out | rc=0、PASS；收据含 NaN | rc=3、ALL_SKIP；完整三点收据，second_price／deviation_pct 均 null，无异常，严格 JSON 解析通过 |

拒绝位置：[price_check.py:86](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/prices/price_check.py:86) 检查 `not (math.isfinite(p) and p > 0)`；[第 88 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/prices/price_check.py:88) 执行 `sys.exit(...)`。三天 NaN 的实际 stderr：

```text
[fatal] 价格文件含非有限或非正价格 3 点（首个 ts=1767225600）：主价格文件先清洗再抽查
```

四组非法主价均在调用第二源前退出，输出收据未被打开。第二源非有限值在 [price_check.py:179](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/prices/price_check.py:179) 转为 None，第 204 行以 `allow_nan=False` 序列化。

消费者使用独立构造、完整绑定的内存工单：修改前两版本 `workorder_errors=[]`；每次修改收据后重算并绑定 SHA。下列 HEAD 拒绝均仅来自指定价格字段：

| 收据场景 | 基线 | HEAD |
|---|---|---|
| points[0].main_price=NaN，status=PASS | 放行 | 拒：points[0].main_price，要求有限正数 |
| points[0].main_price=0.0，status=PASS | 放行 | 同上 |
| points[1].second_price=2.0，status=PASS | 放行 | 拒：points[1].status，重算要求 FAIL |
| 真实 1.0／1.052 收据 | 放行 WARN | 放行 WARN；偏差 5.07%，记录 NOTE |
| 上述 WARN 收据全部 status 与 verdict 改 PASS | 放行 | 三点均拒：points[i].status，重算要求 WARN |

主价拒绝见 [stage2_closeout.py:275](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:275)，逐点状态重算与拒绝见 [第 283 行](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:283)。`price_receipt_errors` 与整份 `workorder_errors` 的价格错误一致。

b) `retail`：

独立输入为两天的 mint 100→A、A→B 40，`camps={大庄:[A],散户:[B]}`。每次从全新内存输出目录起跑；两引擎均实际重放得到 A=60、B=40、gate_pass=true。

| 引擎 | 基线 | HEAD |
|---|---|---|
| replay_pass1 → replay_pass2 | pass1=0、pass2=0；dates=2，「散户」长度=4 | pass1=0、pass2=2；stderr 含 [camp-spec]；无 camp_series.json |
| replay_duck | rc=0；dates=2，「散户」长度=4 | rc=2；stderr 含 [camp-spec]；无 camp_series.json |

基线两引擎的「散户」均为 `[0.0, 0, 40.0, 0]`，复现同日重复追加。HEAD 在 [camp_spec.py:62](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/camp_spec.py:62) 命中 EVM 保留桶检查，第 63 行调用 `_fail`。实际 stderr：

```text
[camp-spec] /__memory__/evm/camps.json 阵营「散户」是 EVM 引擎的残差桶（100−已知阵营），不得在 spec 里配置——显式配置会让 replay_pass2/replay_duck 同日写两个元素；把这些地址归入其他阵营或删掉
```

Solana 的 `validate_camp_spec({"散户":[SA]}, chain_family="solana")` 及默认 chain_family 的 `load_addr_camp_json`，均在两版本接受并原样返回。

另实跑三组合法 spec：项目方／大庄、含大小写与空白地址及空营、空 camps。两引擎均 rc=0，规范化结果及 `camp_series.json`／`entity_series.json` 在基线与 HEAD 间逐字节相同。

c) 白名单与文档：

指定范围的 diff --stat 恰为：

```text
 scripts/lib/camp_spec.py              |  5 ++++-
 scripts/prices/price_check.py         |  9 +++++++--
 scripts/report/stage2_closeout.py     | 23 +++++++++++++++++++++--
 scripts/tests/test_repair_batch_c.py  | 15 +++++++++++++++
 scripts/tests/test_stage2_closeout.py | 31 +++++++++++++++++++++++++++++++
 5 files changed, 78 insertions(+), 5 deletions(-)
```

| 文档范围 | 基线字节数 | 当前字节数 |
|---|---:|---:|
| SKILL.md | 8021 | 8021 |
| references/**/*.md，42 文件 | 930076 | 930076 |
| commands-staging/*.md，4 文件 | 8798 | 8798 |

文档仅核目录元数据与 Git 差异，未展开 attic.md。references、SKILL.md、commands-staging、VERSION、pyproject.toml、CHANGELOG.md 均无该区间差异；maintenance 不纳入议题。

d) 两段隔离与回归：

F04 提交 `de281c6` 仅改 camp_spec.py、test_repair_batch_c.py；F01 提交 `84e70e5` 仅改 price_check.py、stage2_closeout.py、test_stage2_closeout.py，文件集合交集为空。五个工作区文件均与 HEAD 字节相同；结束时 tracked worktree clean。

`python3 -B scripts/tests/invariant_scan.py`，rc=0，尾行：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

以下测试均以 `python3 -B scripts/tests/<文件>` 原样启动，子进程继承 `PYTHONDONTWRITEBYTECODE=1`：

| 测试 | rc | 结果 | 尾部异常 |
|---|---:|---|---|
| test_repair_batch_c.py | 1 | SANDBOX-BLOCKED | P |
| test_engine_equivalence.py | 1 | SANDBOX-BLOCKED | T，随后为 Hypothesis 反例附注 |
| test_stage2_closeout.py | 1 | SANDBOX-BLOCKED | T |
| test_a4_gate.py | 1 | SANDBOX-BLOCKED | T |
| test_audit_release_gate.py | 1 | SANDBOX-BLOCKED | T |
| test_batch4_invariant_guards.py | 1 | SANDBOX-BLOCKED | T |
| test_exemption_guards.py | 1 | SANDBOX-BLOCKED | T |

P 的原样尾行：

```text
PermissionError: [Errno 1] Operation not permitted: '/private/tmp/c-blind-fix1-9tdlngfs'
```

T 的共同原样异常行：

```text
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/', '/tmp', '/var/tmp', '/usr/tmp', '/Users/uravvv/.claude/skills/token-chip-analysis']
```

批 C 使用显式 `/private/tmp`，因此错误措辞不同；已复核为 `test_repair_batch_c.py:1827` 创建临时目录失败，未进入该用例断言，同列沙箱阻断，未记作测试 PASS。其余按指定豁免规则处理。本轮没有需要退回的 FR 项；本机 run_all 补验仍待调度方执行。
