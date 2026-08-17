# 工单 U3 完成报告：HyperSync CSV 同哈希续采闸（方案 B）

## 1. 结论与基线

- 施工结果：**完成**。正式 HyperSync CSV 仅允许同一启动冻结哈希续采同一文件；脚本升级后必须封盘旧 CSV，以前驱覆盖终点另开 CSV/receipt，并作为新 channel 段接入。
- 动工前基线：`aadbe5985f3f5044342f4a13d499e2c1e82e6022`，满足工单要求的 `aadbe59`（6.47.1）。
- 未 commit、未 push；未改版本号、CHANGELOG、SKILL.md。
- 明确未改 `scripts/evm/channels_preflight.py` 与 `scripts/evm/csv_collector_receipt.py`。SQD 的单 segment 与 `fresh_output=True` 约束只在新回归测试中固化，生产 emitter 无须改注释。

## 2. 红态实证

生产代码尚未修改时执行：

```text
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_csv_resume_collector_gate.py
rc=1
PASS same-hash resume
FAIL cross-hash resume：旧代码完成续采并签发
FAIL missing/malformed collector：隔离 resume 读入层后旧代码完成续采并签发
FAIL duplicate collector key：旧 json.loads 按后值放行并签发
FAIL unknown prior schema：旧代码无显式分派白名单并签发
PASS SQD single-segment/fresh-only retention
PASS upgraded collector starts a new channel and multi-channel preflight
FAIL TOCTOU drift：旧代码按写时哈希签发
FAIL hash-wide REVOKED：旧代码仍启动并签发
```

同一阶段执行 `test_collector_history.py` 为 `rc=1`：

```text
FAIL U3 replaced CSV collector has its sole signing protocol registered
AssertionError: U3 predecessor must have exactly one protocol registration
```

说明：SQD“拒已存在输出”负例在修前已被 `fresh_output=False` 拒绝，单 segment 结构也已成立；本单元按工单要求把这两个既有保证固化为防退化断言，不把既有正确行为伪报成旧代码漏过。

## 3. 施工摘要

### 3.1 生产闸与 U1 传染修复

- 进程进入 `main()` 即计算 `collector_start_hash`，并按 `collector_history` 全表执行 hash-wide REVOKED 拒启动；错误面包含“当前脚本版本已被吊销”。
- `--resume-receipt` 改用 `scripts/lib/anchor_point_contract.strict_json_loads`，重复键在读入层拒绝，没有复制 duplicate-key 实现。
- prior receipt 顶层、schema、collector、collector.sha256、query、边界及 segments 均先收类型；schema 仅白名单接受 `evm-collector-run/v2`，未知值 fail-closed。
- 先完成既有 `_csv_collector_provenance` 重验，再独立要求前驱 collector SHA-256 等于启动冻结哈希；跨哈希错误包含工单指定的新 CSV/new channel 指引全文。
- 写 receipt 前重算脚本哈希；运行期漂移时删除临时 CSV、拒签且不发布正式 CSV/receipt。receipt 的 `collector.sha256` 使用启动冻结哈希，不再使用写时即时哈希。
- 为单文件 `spec_from_file_location` 审计/参数测试保留固定邻接 `collector_history.py` fallback；不开放运行时扩展路径。

### 3.2 历史登记

补登一条且仅一条：

```text
script   = fetch_hypersync.py
sha256   = cea82c7743f413555af0b913b1cb0662d52dbdd8e1686bc2443b2ca701266e84
commit   = 2d69373a2a2e0fdc08615e41c8a3dc9676cff22c
protocol = evm-collector-run/v2
status   = ACTIVE
```

Git 考证复现：

```text
git merge-base --is-ancestor 2d69373a2a2e0fdc08615e41c8a3dc9676cff22c HEAD
rc=0

git show 2d69373a2a2e0fdc08615e41c8a3dc9676cff22c:scripts/evm/fetch_hypersync.py | shasum -a 256
cea82c7743f413555af0b913b1cb0662d52dbdd8e1686bc2443b2ca701266e84  -
```

该 commit 的脚本 blob 中唯一签发 schema 是 `evm-collector-run/v2`（payload 行）；未发现第二种签发 protocol。因此按 U2b/B-02 的“每个生前 protocol 各一条”纪律，本脚本只需这一条，40 位 commit 全哈希已登记。

### 3.3 文档与测试

- 文档明确：本版本起顶层 collector 覆盖全部 segments；旧多段 receipt 只标 `legacy confidence`，不声称修复历史。
- CT-SEMANTIC-33 needle `evm-collector-run/v2` 与 CT-SEMANTIC-34 needle `--collector-receipt` 的原有文本未改；`docs_lint.py --all` 通过。
- 新增并注册 `test_csv_resume_collector_gate.py`，覆盖工单六条矩阵，并补充重复键、未知 schema、畸形类型和 hash-wide REVOKED 启动拒绝。
- `test_collector_history.py` 增加 `cea82c77…` 唯一 protocol 登记及 Git blob 可复算约束。

## 4. 绿态与全量验收

定向绿态：

```text
test_csv_resume_collector_gate.py  9/9 PASS
test_collector_history.py          9/9 PASS（含全部历史条目 Git 可复算）
docs_lint.py --all                 PASS
invariant_scan.py                  PASS
test_token_no_positional.py        PASS
test_fetch_failclosed.py           PASS
test_review_20260804_p0.py         PASS
test_round4_identity_emitter.py    PASS
test_g3_alt_collectors.py          13/13 PASS
```

第一次 `run_all.py` 除两个 loopback 外还暴露两项真实回归：新增 schema 判定被 invariant 扫描器计为未登记消费点，以及单文件加载缺 `collector_history` 搜索路径。两项均在 `fetch_hypersync.py` 白名单内修复，随后定向复验通过。

第二次完整执行 `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py`：suite 共 117 项，**115 项 PASS，只有以下两项失败**：

```text
test_batch3_solana_vertical_slice.py
test_batch3_evm_vertical_slice.py
PermissionError: [Errno 1] Operation not permitted
socket.bind(('127.0.0.1', 0))
```

两项正是工单预先声明的 sandbox loopback 例外；除此以外无业务失败。`run_all.py` 进程因此按原实现返回 1，不能表述为字面“全部通过”，但满足“除 loopback 外全绿”的完成标准。

## 5. 白名单与边界复核

施工改动仅有以下工单白名单路径：

```text
scripts/evm/fetch_hypersync.py
scripts/evm/collector_history.py
scripts/tests/test_csv_resume_collector_gate.py
scripts/tests/test_collector_history.py
scripts/tests/run_all.py
references/data-pipeline-evm-channels.md
maintenance/closure-20260817-threeunit/workorder_U3_done.md
```

`git diff --check` 通过。`workorder_U3.md` 是开工时已存在的未跟踪调度输入，本次只读且未修改；其当前 SHA-256 为 `9223481fba325cbb2a5aa03919f37bb28c5b470278e82dcdd72dd44aeefff59a`，不计入施工改动。

## 6. 未尽事项

- 需在允许绑定 `127.0.0.1` 的环境重跑上述 EVM/Solana 两个 vertical-slice 测试；本沙箱无法提供该能力。
- 无其他已知未尽业务项。
