# 工单 U1b 施工报告：单元1 盲审消化轮

## 0. 结论与边界

- 施工基线已核对：`HEAD=main=a2294e200e4bf36ae1e21c99f15e11aeda89b8d6`。
- R1-R9 已按工单完成；生产逻辑、测试与 invariant manifest 的改动均在白名单内。
- 未修改版本号、CHANGELOG、工单或盲审报告；未 commit、未 push。
- 开工时两份输入文件即为未跟踪文件，施工前后 SHA-256 未变：
  - `workorder_U1b.md`: `ee7d43e56551bdd4a09e09ac58b5885606c4cdd96a2d3d9a42547b6c22b8ef92`
  - `blindreview_U1.md`: `3c45ecb91be7968deeed9e526a4c3ea26b68ec99663622a81e1ad5465a52d2fe`
- 技能说明要求的 `sync-from-cc.sh` / `SYNC.md` 在仓库及上级检索范围内均不存在；本仓库本身位于 `.claude/skills` 权威路径，因此未执行不存在的同步入口，以已核验的固定 SHA 施工。

## 1. R1-R9 红绿实证与改动

### R1：拒绝 anchor plan/receipt 重复 JSON 键（V-31）

- 红态：原盲审 `g6_dupkey_kind.py` 的 V71 中，重复 `balance_block_source` 的 plan 被执行侧、发布权威链、发布深验和 CLI 全部接受，CLI `exit=0`；另构造重复 `plan_schema` 的 receipt，执行侧与发布侧也均接受。
- 改动：在 `anchor_point_contract.py` 新增共享 `strict_json_loads` / duplicate-key hook；仅接到 anchor plan 链的 plan/receipt 读入点：`time_spotcheck.load_validated_plan` 与 `shared_release_receipt._validated_time_plan_authority`。其他 JSON 消费未扩散修改。
- 绿态：V71 回打时执行侧、发布权威链和发布深验均以 `duplicate JSON key rejected: 'balance_block_source'` 拒绝，CLI `exit=2`；新增测试同时覆盖 plan/receipt × 执行/发布四个组合。

### R2：producer 历史协议随被验 plan schema 动态选择（V-01）

- 红态：v3 plan 挂 v2 历史哈希 `e5168a...` 或 `1a4611...`，`load_validated_plan` 与发布权威链均 `ACCEPTED`。
- 改动：两侧均先严格解析 plan，再对白名单 `{anchor-plan/v2, anchor-plan/v3}` 校验 schema，随后以实际 `plan_schema` 调用 `historical_producer_hashes`，最后校验 receipt。
- 绿态：两个 v2 历史哈希给 v3 plan 背书时，两侧均拒绝 `producer hash mismatch`；真实 v2 NES 历史件仍接受。

### R3：schema 分派显式白名单化并收敛常量（V-17/V-18）

- 红态：`schema=anchor-plan/v9` 直调 `classify`、`balance_query_block`、`_plan_point` 均退化到 v2 路径并返回结果。
- 改动：三处均改成明确的 `if V3_SCHEMA / elif V2_SCHEMA / else raise ValueError`；`time_spotcheck.PLAN_SCHEMA` 与 `SUPPORTED_PLAN_SCHEMAS`、发布闸分派统一引用共享 `V2_SCHEMA` / `V3_SCHEMA`，删除发布闸裸 v3 字面量。
- 绿态：V70 回打三处均拒绝 `unsupported plan schema: 'anchor-plan/v9'`。

### R4：v2 点拒绝携带 v3 机器字段（V-28）

- 红态：v2 余额点携带与 `day_end_block=123` 矛盾的 `balance_block_source=final_block` 时，分型、查询块解析和发布 `_plan_point` 均接受并忽略该字段。
- 改动：共享 legacy 点契约在 v2 schema 下发现 `balance_block_source` 键即抛 `v2 plan point carries v3 machine field`。`anchor_plan.py` 不在白名单，未直接修改；其 `_validate_probe_blocks` v2 分支必经该共享谓词，因此同样被收口。
- 绿态：新增回归覆盖签发 `_validate_probe_blocks`、`classify`、`balance_query_block`、发布 `_plan_point` 四路并全拒；原 V60 回打三个消费者全拒。

### R5：不可哈希枚举值统一为 ValueError（V-23）

- 红态：`balance_block_source=["day_end_block"]` 在签发、分型、查询块和发布点解析四处均抛 `TypeError: unhashable type`。
- 改动：集合成员判定前先要求 `source` 为 `str`。
- 绿态：原 V32 回打四处均为 `REJ(ValueError)`；定向测试断言错误文案包含 `balance_block_source invalid`。

### R6：恢复 anchor-plan producer 单源守卫（V-36）

- 红态：在内存 manifest 注入第二个 `anchor-plan/v3` producer 后，旧守卫仍因先按 `EXPECTED_PLAN_PRODUCER` 过滤而错误通过，`filtered_count=1`。
- 改动：先全 manifest 按 schema 收集，再排除显式说明的非 producer 误报，最后要求只剩唯一 `EXPECTED_PLAN_PRODUCER`。`invariant_scan.py` 的 `exceptions` 仅校验例外元数据、不参与扫描过滤，故按工单备选方案在测试内保留带理由的显式豁免表。R3 常量收敛后扫描器已不再把 `time_spotcheck.py` 误列为 anchor-plan producer；manifest 同步真实扫描面。
- 绿态：同一内存注入会使过滤后数量变为 2，守卫拒绝；`test_time_spotcheck.py` 对真实 manifest 通过；`invariant_scan.py` PASS。

### R7：producer history status 枚举守卫（V-06）

- 红态：注入 `status="Revoked"` 时撤销意图静默失效，旧哈希仍 admitted=`True`。
- 改动：`historical_producer_hashes` 遍历前逐条校验 status 只能是 `ACTIVE` / `REVOKED`；测试保留登记表结构断言并新增运行时错拼反例。
- 绿态：原 `g1_producer.py` 在 V06 处明确抛 `ValueError: producer history entry[2] status invalid: 'Revoked'`。

### R8：登记表 commit 统一为 40 位全哈希（V-12）

- 红态：登记表两条 commit 长度分别为 `[40, 7]`。
- 改动：`0ec6d1e` 改为 `0ec6d1e2365c339d200fc26d17344f962fbdb7a9`；结构守卫正则收紧为 40 位十六进制。
- 绿态：两条长度均为 `[40, 40]`；现有 `git show <commit>:<script>` SHA-256 可复现断言通过。

### R9：`allowed_producer_hashes` 调用方责任注释（V-07）

- 红态：`validate_receipt.__doc__` 为空，未声明 hash 集必须对应 `receipt.producer.path`。
- 改动：只补 docstring，不改逻辑：调用方必须传与 receipt producer 路径对应的登记哈希集，本函数不验证 script-to-set 对应关系。
- 绿态：源码级回归确认 docstring 同时包含 `receipt.producer.path` 与 caller responsibility。

## 2. 文件级改动摘要

- `scripts/lib/anchor_point_contract.py`：共享 v2/v3 schema 常量、严格 JSON parser、v2 机器字段拒绝、枚举类型收口。
- `scripts/lib/time_spotcheck.py`：严格读入、按 plan schema 取历史哈希、三分支显式分派。
- `scripts/lib/producer_history.py`：status 运行时枚举守卫、commit 全哈希。
- `scripts/lib/receipt_validate.py`：仅补 `allowed_producer_hashes` 调用方责任 docstring。
- `scripts/report/shared_release_receipt.py`：严格读入、按 plan schema 取历史哈希、共享 schema 常量与显式分派。
- `scripts/tests/test_anchor_plan_v3.py`：新增重复键、协议错配、未知 schema、v2 机器字段、枚举类型、status、commit 与 docstring 回归；总数由 12 增至 15。
- `scripts/tests/test_time_spotcheck.py`：恢复全 manifest 单源语义并显式记录非 producer 豁免理由。
- `scripts/tests/invariant_manifest.json`：同步 R3 常量收敛后的真实 producer/consumer 扫描面。

## 3. 定向测试与攻击回打

- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_anchor_plan_v3.py`：`15/15 PASS`。
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_time_spotcheck.py`：`20/20 PASS`。
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py`：PASS，计数 `receipt_producers=62, receipt_consumers=88, transport_calls=63, atomic_writes=54, formal_entrypoints=58, exceptions=0`。
- `git diff --check`：PASS。
- 原盲审攻击脚本回打：V01、V06、V32、V60、V70、V71 均由原失败面转为明确拒绝；V72 kind 文案免疫正例仍通过。

## 4. NES 三份存量深验与 dry-run 重放

按 U1 施工报告 §5 的原 plan/receipt/input、chain、token、final-block 参数复跑，仅把 `--out` 改到 `/tmp/*-u1b-final.json`：

```text
根 BSC：exit=0  balance_points=1   tx_points=1   total=2   need_final_block=0
BSC 目录：exit=0  balance_points=13  tx_points=11  total=24  need_final_block=0
Ethereum：exit=0  balance_points=14  tx_points=3   total=17  need_final_block=1
```

三次均为只读 dry-run；未重签、未覆盖 NES 案例产物。v2 历史 producer 深验与完整语义重放继续成立。

## 5. 全量 suite

最终代码状态执行：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py
```

`SUITE` 共 115 项：113 项 PASS，只有工单预期的两个 loopback 能力失败：

1. `test_batch3_solana_vertical_slice.py`
2. `test_batch3_evm_vertical_slice.py`

两项原始失败均发生在 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 的 `socket.bind`，异常为 `PermissionError: [Errno 1] Operation not permitted`。其余业务测试全部通过；没有把这两个环境能力失败写成全绿。

## 6. 白名单与仓库状态

- 报告写入前，`git diff --name-only a2294e2 --` 仅包含以下 8 个白名单 tracked 文件：
  - `scripts/lib/anchor_point_contract.py`
  - `scripts/lib/producer_history.py`
  - `scripts/lib/receipt_validate.py`
  - `scripts/lib/time_spotcheck.py`
  - `scripts/report/shared_release_receipt.py`
  - `scripts/tests/invariant_manifest.json`
  - `scripts/tests/test_anchor_plan_v3.py`
  - `scripts/tests/test_time_spotcheck.py`
- 本报告 `maintenance/closure-20260817-threeunit/workorder_U1b_done.md` 亦在白名单内。
- 未 commit，未 push；`HEAD` 仍为 `a2294e2`。

## 7. 按工单维持/遗留

- V-04/V-11/V-20/V-24/V-34 按调度方既有裁决维持，本轮未施工。
- V-32/V-33 发布闸深度差为另立旧账；本轮仅按 R3 改其 schema 分派结构，未增加发布闸重放或探测块上界校验。
- 全量 suite 的两个 loopback 失败是当前沙箱网络能力限制，未修改测试绕过，也未声称通过。
