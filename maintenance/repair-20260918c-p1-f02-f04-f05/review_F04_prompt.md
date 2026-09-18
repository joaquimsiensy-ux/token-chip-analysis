# 工单 F04 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918c-p1-f02-f04-f05/` 以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单F04复核：通过` 或 `# 工单F04复核：退回`。退回时逐条给出：编号（F04-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**修复计划**的复核，不是攻击式验收：目标是拦住工单里"想得不周"的地方——锚点错、修法有副作用、既有测试会变红、同族入口漏了、迁移代价没说清、**工单前提与代码事实不符**（专门核每个"既有消费者已处理 ok=False"的断言是否属实：逐个打开 §1.4 列出的行，确认对 `ok=False` 的实际分支行为）。

## 任务
复核 `maintenance/repair-20260918c-p1-f02-f04-f05/workorder_F04_rpc_envelope.md`（v1）与同目录 `ruling_20260918.md`、`code_change_pending.md`。工作目录＝本仓库根（HEAD 含本工程工单 commit；`scripts/`、`references/` 与 8b041842 逐字节相同，行号按 8b041842 核）。逐项核：
a) §2 每个锚文本 `grep -n -F` 的命中数与行号是否与工单一致。
b) 修法正确性与副作用：读 `net.py:271-298` 与 `_run:349-385` 完整上下文，判断 envelope 校验插入点是否覆盖重试分支（`:286-293`）后的 `j`；`_run:373` 全失败 failover 是否会因本段产生非预期端点切换（例如单端点池）；`rpc_batch.py:77-90` 替换后 `continue` 是否在 `for addr, r in zip(...)` 循环内合法；摘要 `:88-90` 的 EOA 计数在新失败项下是否仍正确。
c) 回归面：列出所有会因本段变红的既有测试（含 run_all.py 登记的 143 个 test_*.py 里工单 §0.8 未列的）——重点：任何用 `mock.patch.object(net, "_request_json")` 返回**缺 result 键**响应、或断言 `rpc_batch` 对 `None`/`"0x0"` 判 EOA 的用例；给出行号与原因；判断工单 §1.5 断言是否成立。
d) 新用例 RED/GREEN 在基线与改后是否成立（沙箱允许则实跑 `test_batch1_rpc_attestation.py`，否则静态推演注明）；`test_rpc_batch_getcode_rejects_malformed_code` 用 `load()` 二次加载 rpc_batch 时 `from chain_registry import attested_evm_chains`/`from net import …` 的 sys.path 是否可解析（对照 `:296-298` 既有 rpc_batch 用例的加载方式）。
e) §0.3 白名单是否足够、§0.4 不改项是否自洽；`invariant_scan.py`/`test_batch4_invariant_guards.py`/`test_exemption_guards.py` 是否会因本段要求登记或报错。
f) 终点判据：`ruling_20260918.md` 的 `rpc_missing_result` 反例（握手 `eth_chainId`→`0x38`，业务 `eth_getCode` 返回 `{"jsonrpc":"2.0","id":N}`）按工单改后是否**必然**变为：`rpc_batch.py getcode` 退出 1、该地址 `{"error": …}`、摘要"失败 1"——给出拒在哪一行、哪句文案。
g) 台账 Q5/Q6（不校验 id/jsonrpc；合法 null 继续 ok=True 由消费者自核）的边界是否会让 review 的"合法 null 与缺字段须区别对待"要求落空。
