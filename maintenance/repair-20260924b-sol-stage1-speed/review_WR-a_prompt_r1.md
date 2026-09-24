## 纪律
1. 只读、离线、不 commit、不新建/修改文件；禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**报告全文放最终答复消息里**，首行固定 `# 登记单WR-a复核r1：通过` 或 `# 登记单WR-a复核r1：退回`。
2. 这是对一份"登记单"（往 `scripts/lib/producer_history.py` 追加四条生产者哈希条目）的可执行性与正确性复核，不是施工。
## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_WR-a.md`（模板 v2 + 填实值）。请独立核：
a) 填实值：`git show <CODE_COMMIT>:scripts/solana/sqd_gap_repair.py | shasum -a 256` 是否等于工单 `<SHA256>` 且等于工作树文件 sha；`<CODE_COMMIT>` 是否为 HEAD 或其祖先且是该脚本最后一次改动的 commit；
b) `producer_history.py` 现有条目结构（字段名、元组闭合 `)` 行号 :283、现役 repair 条目 `3f89aab1…` 四协议）与工单 0.3 要求同构追加是否可行；是否需要把旧条目状态改为非 ACTIVE（按文件头 :3-6 登记纪律判断，工单要求"保留全部既有条目不改"是否与纪律冲突）；
c) 0.4 定向测试清单是否足够让 `test_producer_registry_current.py` 对 repair 四协议由 FAIL 转 PASS（probe 两协议仍会 FAIL 属预期，由 WR-b 处理）——工单是否应把该守卫列入 0.4；
d) 0.7 真实注册表入口验收的可构造性：`resolve_formal_cache` 与 `validate_repair_bundle(deep=True)` 在不替换 `historical_producer_hashes` 的前提下，用 W4 新增的自包含夹具（`test_sqd_gap_repair.py` W4 段）能否直接走通；若不能，指出缺什么；
e) 工单内部是否有自相矛盾或行号/锚过期。
退回须逐条给出必改项与依据；通过也要列核了什么。