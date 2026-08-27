# 批 9 done：`validate_repair_bundle_deep` 校验侧流式/惰性化

## 裁定

代码改造与离线回归完成；真实 ARC 代的性能验收被 Codex 文件访问沙箱阻断，不能裁定峰值 RSS 是否达到 `< 6GB`，也不能把本批标成完整验收通过。未 commit，等待验收方在具备 ARC 案根读取权限的本机复跑工单命令。

开工门禁：HEAD=`5db0abe`，分支=`main`，目标函数及工单锚点一致。未运行 skill 默认同步脚本，因为同步会改动白名单外工作树，与本工单硬边界冲突。

## 改造内容

仅修改 `scripts/lib/solana_exact_validate.py`：

- evidence manifest 仍逐项执行 `_repair_ref`、文件哈希、JSON 解析和 `canonical_json`；不再保存全部 evidence 内容。后续按路径惰性读取，LRU 固定容量为 2。
- `repair_layer.jsonl`、`slot_index_map.jsonl`、`rpc_ledger.jsonl` 改为逐行解析；header、行契约、ledger seq/slot/count、layer signature、slot 集合等仅保留必要聚合。
- formal 严格触达集仍为候选集、confirmed 集、repair layer slot 的并集；批 7 的检查、触发条件和 reason 文本保留。
- 正常有序代按 slot 流式联结 map 与 base edge，只保留单 slot 映射和边；乱序/重复 map 或乱序 base 输入走标准库临时 SQLite 回退，保留旧的 last-write/map-sort 语义。
- repair edges 写入系统临时 SQLite 并按原 `_edge_sort` 顺序惰性读取；merged edge 比较、coverage window 检查、logical SHA256 和行数均逐行完成。
- GID 按 canonical JSON 的原键序增量哈希，`transactions` 和 `slot_index_map` 从 JSONL 流式消费；返回结构不变。
- `state_by_slot` 不再复制完整 coverage state 字典，严格 slot 校验直接按下标读取既有 recomputed state 列表。
- 未引入第三方依赖；仅使用 Python 标准库 `heapq`、`sqlite3`、`tempfile`、`itertools.groupby`。

最终目标文件 SHA-256：`75befca02c62d770feaf6de57dd5b889dda0f391de2b2f741c7c7131f602835d`。

## 测试与等价性

通过：

- `python3 -m py_compile scripts/lib/solana_exact_validate.py`
- `git diff --check`
- `python3 scripts/tests/test_sqd_gap_repair.py`：exit 0；functional repair、formal/exploration deep validation、E25/E26/E27、consumer repaired-order、29a/29b/29c 全绿。
- `python3 scripts/tests/test_batch7_validator_coverage_gaps.py`：exit 0；合法 formal 代放行，缺口 1 注入与缺口 3 超窗口边均被预期 reason 拒绝。
- `python3 scripts/tests/test_batch8_repair_scale.py`：exit 0；`PASS batch8: key-neutral identity/pool failover/ordered workers/resume/streaming`。
- HEAD 旧实现与当前实现对同一 formal 夹具逐字段对照：以下四例的 `ok`、`reasons`、`gid`、`effective_verdict`、`edge_rows`、`bundle` 完全相同：
  - 合法 formal：`ok=True`，`reasons=[]`
  - current base SHA 错误：`['bundle base edge sha256 differs from current base']`
  - `live_canary=True`：`['live_canary must be a nonnegative integer']`
  - ledger seq 篡改：`['rpc_ledger sha256 mismatch', 'RPC ledger sequence is not contiguous']`

全套：

- `python3 scripts/tests/run_all.py`：127 PASS / 2 FAIL。
- 两个失败均为沙箱禁止 loopback bind，与本批代码无关：
  - `test_batch3_solana_vertical_slice.py`：`ThreadingHTTPServer(("127.0.0.1", 0), ...)` → `PermissionError: [Errno 1] Operation not permitted`
  - `test_batch3_evm_vertical_slice.py`：同一 loopback EPERM
- 本批相关的 `test_sqd_gap_repair.py`、`test_batch8_repair_scale.py`、`test_batch7_validator_coverage_gaps.py` 在该全套中均 PASS。

没有新增测试文件，也没有改动既有测试。

## ARC 真实代只读实测

按工单以 `/usr/bin/time -l` 启动指定 bundle，并从 bundle 内取 `base.edge_sha256` 作为 `current_base.edge_sha256`。命令未执行到 `validate_repair_bundle_deep`：首次打开 bundle 即被文件访问沙箱拒绝。

原样结果：

```text
PermissionError: [Errno 1] Operation not permitted: '/Users/uravvv/Documents/5.6筹码分析/ARC分析/data/sqd_repair/6b99816bc26d8c53bac165b4efeb03a2b0beee563bf242e05b8906ae8dff3cb8/gen-80c6929bb5fd3c1d/bundle.json'
     1363.81 real         0.03 user         0.02 sys
time: sysctl kern.clockrate: Operation not permitted
```

- exit code：1
- 校验函数耗时：未开始，无法记录
- `maximum resident set size`：未输出，无法记录
- `ok`：未产生
- `reasons`：未产生
- `< 6GB` 目标：未裁定
- ARC 案根写入：0；命令只尝试读取 bundle

验收方必须在可读取该案根的本机复跑工单原命令，取得真实 RSS、耗时、`ok` 和完整 `reasons` 后，才能完成本项验收。

## 边界与交接

- 本轮写入仅有：`scripts/lib/solana_exact_validate.py`、本报告。
- `maintenance/repair-20260823-sqd-gap/batch9_workorder.md` 是开工前已存在的用户未跟踪文件，本轮只读且未改。
- 未改协议、schema、其他脚本、既有测试或文档。
- 未触发 ARC runner、resume 或发布。
- 未 commit；HEAD 仍为 `5db0abe`。
