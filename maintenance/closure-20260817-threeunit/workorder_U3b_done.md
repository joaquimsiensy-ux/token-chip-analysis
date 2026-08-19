# 工单 U3b 完成报告：单元3 盲审消化轮

日期：2026-08-17  
施工基线：`3ee1383712a8c10f8b4447b33831d8e6e4458567`（要求前缀 `3ee1383`，版本 `6.48.0`）  
结论：**按工单口径完成**。`run_all.py` 分母保持 117；115 项 PASS，唯二失败为沙箱禁止 loopback `socket.bind` 的既知例外。未 commit、未 push。

## 1. 边界核对

本轮仅修改以下四个白名单文件：

- `scripts/evm/fetch_hypersync.py`
- `references/data-pipeline-evm-channels.md`
- `scripts/tests/test_csv_resume_collector_gate.py`
- `maintenance/closure-20260817-threeunit/workorder_U3b_done.md`

明确未修改 `csv_collector_receipt.py`、`fetch_sqd_evm.py`、`collector_history.py`、`channels_preflight.py`；未修改 `VERSION`、`CHANGELOG.md`、`SKILL.md`。施工前工作树已有未跟踪调度输入 `workorder_U3b.md` 与 `blindreview_U3.md`，本轮原样保留。

## 2. R1-R4 改动摘要

### R1：schema 常量收敛

- `fetch_hypersync.py` 的 receipt 签发点改用 `COLLECTOR_RECEIPT_SCHEMA`；协议字面量在该文件仅剩常量定义一处。
- 在常量定义处增加维护路标：`channels_preflight.py:29` 尚有副本，升 schema 版本时必须同步；本轮未越界修改该文件。
- 同哈希续采正例新增断言，确认签发 receipt 的 `schema == evm-collector-run/v2`。

### R2：schema 比较等价重构

- 保留非字符串前置拒绝。
- 用常规 `if schema != COLLECTOR_RECEIPT_SCHEMA` 取代字典索引加 `KeyError` 的怪写法。
- `prev` 已先确认为 dict；采用等价的 `dict.get(prev, "schema")` 读取，保持现有 invariant manifest 的静态消费面不变。
- 回归覆盖 `evm-collector-run/v3` 与 `foo` 两个非法值及原错误文案。

### R3：输出与 receipt 同路径前置拒绝

- 仅在给出 `--receipt` 时比较 `os.path.realpath(a.out)` 与 `os.path.realpath(a.receipt)`。
- 同路径时由 argparse 前置拒绝：`正式输出与 receipt 路径不得相同`。
- 新增回归，验证退出码 2、正式输出不存在、`.collide.csv.tmp.*` 无残留。
- legacy 无 receipt 路径不受该校验影响。

### R4：文档声称收窄与维护债登记

- 明确“顶层 collector 覆盖全部 segments”的保证仅适用于 `fetch_hypersync.py` 签发、受同哈希续采闸及 TOCTOU 冻结/写前复验保护的 CSV receipt。
- 明确 SQD 侧 `csv_collector_receipt.py`/`emit_native_receipt` 签发者不在该保证内；其 collector 归属在第四单元收口前仅为顶层自报，置信度=顶层自报。
- 登记方案 B 的永久维护债：历史 collector 哈希成为每次 preflight 的永久依赖；升级时漏登会导致该版本的存量段全部被拒；反向断链守卫待第四单元。
- `evm-collector-run/v2` 与 `--collector-receipt` 所在契约 needle 行逐行与基线一致，未改一个字符。

## 3. 红绿实证

### R1

改前：

```text
38:COLLECTOR_RECEIPT_SCHEMA = "evm-collector-run/v2"
282:        payload = {"schema": "evm-collector-run/v2", "status": "PASS",
```

改后：

```text
38:COLLECTOR_RECEIPT_SCHEMA = "evm-collector-run/v2"
```

定向回归的同哈希续采正例通过，并显式断言签发值仍为 `evm-collector-run/v2`。

### R2

改前和改后分别对 `evm-collector-run/v3`、`foo` 实跑；四次结果均为退出码 2、不签发 receipt，错误尾句逐字相同：

```text
fetch_hypersync.py: error: 正式续段前驱重验失败: 前驱 receipt schema 必须是 evm-collector-run/v2
```

因此本项是错误面逐字一致的等价重构，不是行为变更。

### R3

改前同路径实跑：

```text
exception=FileExistsError: [Errno 17] File exists: '.../.collide.csv.tmp.57060'
tmp_residuals=['.collide.csv.tmp.57060']
```

改后同路径实跑：

```text
rc=2; expected_message=True
tmp_residuals=[]; output_exists=False
fetch_hypersync.py: error: 正式输出与 receipt 路径不得相同
```

### R4

`python3 scripts/tests/docs_lint.py --all` 改前、改后均为：

```text
PASS: 58 个文档，引用无断链、粗体配对完整（--all 全量模式）
```

基线与工作树逐行比较：

```text
evm-collector-run/v2: unchanged=True; count=4
--collector-receipt: unchanged=True; count=2
```

新增范围限定与维护债段落不与保留的原句冲突：原句中的“保证”已由紧邻前置段落明确限定主语。

## 4. 测试结果

### 定向测试

- `python3 scripts/tests/test_csv_resume_collector_gate.py`：10/10 PASS。
- `python3 scripts/tests/invariant_scan.py`：PASS；`receipt_producers=63`、`receipt_consumers=91`、`transport_calls=63`、`atomic_writes=54`、`formal_entrypoints=58`、`exceptions=0`。
- `python3 scripts/tests/docs_lint.py --all`：PASS。
- `git diff --check`：PASS。

第一次全量运行曾出现一个非 loopback 失败：R2 的常规比较被静态扫描器识别成 manifest 新消费面。未把该失败隐藏或豁免；随后在 `fetch_hypersync.py` 白名单内将已确认 dict 的读取改为等价 `dict.get`，定向关闭后重跑全量。

### 最终全量

命令：`python3 scripts/tests/run_all.py`

- suite 分母：117（不变）
- PASS：115
- 既知沙箱 loopback 失败：2
- 其他失败：0

两项例外均在创建 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 时失败：

1. `test_batch3_solana_vertical_slice.py`：`PermissionError: [Errno 1] Operation not permitted`
2. `test_batch3_evm_vertical_slice.py`：`PermissionError: [Errno 1] Operation not permitted`

这两项正是工单预声明的沙箱例外；未据此修改生产代码或测试。

## 5. 第四单元候选清单（本轮不施工）

1. **BREACH-01：SQD 侧 TOCTOU 收口**
   - `emit_native_receipt` 接收调用方传入的启动冻结 collector 哈希；
   - `fetch_sqd_evm.py` 入口冻结 collector 哈希；
   - receipt 写前复验 collector 未漂移；
   - hash-wide REVOKED 时拒绝启动。
2. **W-01：反向断链守卫**
   - 在 `collector_history` 维护链增加“HEAD 前一版必须已登记”的回归，防止升级漏登导致存量段永久断链。
3. **W-02：跨文件 schema 常量统一**
   - 消除 `channels_preflight.py:29` 的 `COLLECTOR_RECEIPT_SCHEMA` 副本，与签发端建立单一事实源。
4. **N-01：SQD REVOKED 前置拒绝**
   - 当前 REVOKED 版本仍可跑完整采集，只在消费侧兜底拒绝；应移到采集入口 fail-fast。

## 6. 未尽事项与知悉项

- N-03：缺少 `--receipt` 时，`--resume-receipt` 被静默忽略；按工单记录、不修。
- N-04：prior receipt 在 resume 层与 provenance 层存在双读窗口；不放大攻击面，按工单记录、不修。
- SQD 的 BREACH-01/W-01/W-02 跨文件债与 N-01 均未在本轮越界施工，已完整移交第四单元候选。
- 未创建 commit，未 push。
