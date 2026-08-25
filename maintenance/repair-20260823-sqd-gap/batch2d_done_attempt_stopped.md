# 批 2d 施工尝试：停工请示

## 结论

已完成真实先红后绿与局部实现验证，但发现工单的 producer 登记、禁 commit、全量
suite 全绿三项不可同时满足。按工单停工线，未继续登记面与版本施工，未写
`batch2d_done.md`，未 commit、未联网。

## 已完成的施工与证据

- 基线核对：`main`、HEAD `e3969e1b36376ff64ad8f15124b1ec4515a2dd97`、
  VERSION `6.52.2`；初始工作树唯一项是用户提供的未跟踪工单。
- 新增 `scripts/tests/test_batch2d_stream_tail.py`。生产代码改前真实 RED：exit 1，
  失败于 200 空体续页仍是 `row["ok"] is False`。
- `scripts/solana/sqd_coverage_probe.py` 只对
  `category == decode && http_status == 200 && message == "curl returned empty stdout"`
  三条件全等作 SQD 流结束处理；台账采用 `canonical_json([])` 的 bytes/SHA256
  惯例，尾段全写 NO_HEADER。
- `scripts/lib/net.py` 仅增加交叉注释，逻辑零变更。
- focused GREEN：新测试 4/4；既有 coverage 12/12；`test_net_result.py` PASS；
  `test_recon_fifth_check.py` PASS。新测试还用未改的
  `solana_exact_validate.py` 独立验收发布件。
- 原始命令、退出码、hash 与 traceback 已逐步写入
  `batch2d_green_evidence.txt`。

## 硬矛盾

工单同时要求：

1. `producer_history.py` 两条 SQD probe ACTIVE 记录更新到当前脚本哈希；
2. 不 commit，由 Fable 验收后代 commit；
3. `python3 scripts/tests/run_all.py` 全量通过。

但现役仓库强制：

- `scripts/lib/producer_history.py:3-6` 明文规定 dirty worktree hash 不得登记；
- `scripts/tests/test_anchor_plan_v3.py:361-362` 要求每条记录的 `sha256` 为 64 位
  hex、`commit` 为 40 位 hex；
- 同测试 `:413-421` 对每条执行 `git show <commit>:<script>`，并要求所得字节
  SHA256 与登记值相等。

当前修改后脚本 SHA256 是
`bccf1802b6a5c9d9bbbdb12e19354ad761416c631e3cdfde2449f7fe1794f176`；HEAD
内脚本 SHA256 是
`e41370b185aef9bd16fea8ce1abc519a138ee4ce8923bdbc8058d64cdd0619bf`。
旧真实 commit 无法证明新哈希；40 位占位值无法通过 `git show`。因此工单所述
“占位／待验收方回填”在现役守卫下没有可执行协议。

## 停止位置

已停在局部绿之后，以下均未做：

- 未改 `scripts/lib/producer_history.py`；
- 未改 `scripts/tests/run_all.py`；
- 未改 VERSION、pyproject.toml、SKILL.md、CHANGELOG.md；
- 未跑全量 `run_all.py`，避免在已知硬矛盾后继续施工；
- 未写正式 `batch2d_done.md`。

当前局部修改保留在工作树，未回滚，供裁决后续接。

## 请示

请在以下两种可执行方案中裁决一种：

1. **两段提交**：Fable 先验收并提交 probe／net 注释／新测试；随后修订工单以该
   新 commit 为冻结锚，恢复施工更新 producer_history、run_all、版本与 CHANGELOG，
   再由 Fable 做第二次收口 commit。
2. **显式延期登记**：修订完成标准，允许本轮不改 producer_history 且不宣称全量
   发布绿；Fable commit 后另开登记收口工单。

未经裁决，不应填假 commit、放宽守卫或用旧 commit 冒充新生产者。
