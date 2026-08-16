# 工单 C（AI-3 / repair-20260815-g3）：盲审第 1 轮消化——G3R1-01/02/03/05/06/07 六项

## 你的角色与硬边界

你是施工方，消化独立盲审抓到的缺陷。先读 `maintenance/repair-20260815-g3/blindreview_G3_round1.md` 全文。硬边界与工单 B 相同：
1. 禁止 git 操作
2. **只准改动**：`scripts/evm/fetch_sqd_evm.py`、`scripts/evm/fetch_alchemy.py`、`scripts/evm/csv_collector_receipt.py`、`scripts/tests/test_g3_alt_collectors.py`、`scripts/tests/test_g3_docs_guards.py`；**新建**：`maintenance/repair-20260815-g3/evidence_C_red.txt`、`maintenance/repair-20260815-g3/workorder_C_done.md`。**G3R1-04 涉及 SKILL.md，明确不修**（边界外，交融合方），不要碰它
3. 零真实网络；措辞中性；done 报告输出必须真实跑出

## 任务 1（G3R1-01，P0）：SQD 完成证据补上界

1. `parse_stream_response` 增加 `req_from, req_to` 两个必填参数：每行 `header.number` 先做类型收紧——**只接受 int 且非 bool**（float、字符串数字一律 ValueError），再校验落在 `[req_from, req_to]` 闭区间内，越界即 ValueError（走既有协议异常/连续 5 次硬退路径）
2. 主循环调用处传 `(cur, a.to_block)`
3. `csv_collector_receipt.py` 的 `emit_native_receipt` bounds 校验补上界：`provider_next_block > requested_to` 即 raise ValueError（SQD 语义下正常值恰等于 requested_to）。先 `rg emit_native_receipt` 确认全部调用面（应只有 fetch_sqd_evm 与测试），确保收紧不误伤
4. 负测（加进 test_g3_alt_collectors.py，先红后绿）：
   - R4：provider 只回一行越界哨兵（number 远大于 --to-block）→ 必须非零退出、不签 receipt、输出 .partial
   - R5：真实行+越界哨兵混合 → 同上
   - P1 纯函数补：number 为 float / 字符串数字 / 越界 → ValueError
   - emitter 单测：provider_next_block > requested_to → ValueError

## 任务 2（G3R1-02，P1）：SQD log 级逐字段校验

1. `parse_stream_response` 对每条 log 校验（任一不合即 ValueError 走协议异常路径）：
   - `topics` 为 list 且 `len >= 3`，每个 topic 为 `0x`+64 位 hex（66 字符，`re.fullmatch(r"0x[0-9a-fA-F]{64}")`）——本采集器只请求标准 ERC20 Transfer topic0，三 topic 恒成立
   - `data` 为合法 hex 串（`re.fullmatch(r"0x(?:[0-9a-fA-F]*)")`，允许 `0x` 空值按 0 处理的既有语义保留，但字符集必须合法）
   - `transactionHash` 为 66 字符 hex；`logIndex` 可安全 int 化（str 数字或 int，bool 拒），失败即 ValueError
   - `header.timestamp` 若存在必须可安全 int 化，不合法即 ValueError（不再静默空串——缺失仍允许按既有空串语义）
2. 负测：缺 topics / topics 仅 2 个 / topic 长度不对 / data 含非法字符 / logIndex 为乱串 → 各自 ValueError；主路径 R6：log 半残响应 → 非零退出不签

## 任务 3（G3R1-03+G3R1-07，P2/P3）：守卫测试强度拉齐

1. `check_f08_a0` 改为整串精确断言：A0 段内必含完整命令串（含 `--exploration --out accounting_mode.exploration.json` 的连续命令文本），并加负向断言：A0 段内**不得出现** `--out accounting_mode.json`
2. `check_f13` 锚定到"[输出 JSON schema"所在段落：该段内必含"逐字写入"与"不会静默覆盖或补入"，且旧句"由受控 runner 补入 role"全文件不得出现
3. `check_f05` 锚定到"机器化边界"段落：两份文档各自必须存在以"**机器化边界**"开头的段，且该段内含"机器已强制""机器未强制""路数与异构性"三个子串（防整段删除/降级注释）
4. 变异自证（写进 done 报告，不入库）：临时复现盲审 M1/M2/M3/M4 四个变异各自确认新守卫会红，然后还原（用临时副本推演或改后跑再还原均可，最终 worktree 必须与施工完成态一致）

## 任务 4（G3R1-05+G3R1-06，P3）：Alchemy 收尾

1. `validate_transfers_page` 的 `rawContract.value` 与 `blockNum` 校验改 `re.fullmatch(r"0x[0-9a-fA-F]+", value)`（拒负号/下划线/空白）
2. `--receipt` 的 argparse help 文本改为除名指引（与 ap.error 信息同义）："已除名：Alchemy 无 provider 侧完成证据，不支持正式 receipt，仅探索采集"
3. 负测：`"-0x5"` / `"0x_f"` / `" 0x5 "` → ValueError

## 任务 5：先红取证 → 施工 → 转绿 → 回归

1. 先把任务 1/2/4 的新负测写入 test_g3_alt_collectors.py、任务 3 的新断言写入 test_g3_docs_guards.py，对**当前代码**跑，红项输出存 `evidence_C_red.txt`（带 `git rev-parse HEAD` 与红项摘要；守卫强度类断言若在当前文档态本来就绿属正常，红证以任务 1/2/4 的行为负测为主）
2. 施工 → 两测试全绿
3. 回归全绿：`test_round4_csv_adapters.py`、`invariant_scan.py`、`docs_lint.py --all`、`py_compile`（三个改动 py 文件）
4. done 报告 `workorder_C_done.md`：逐 finding 处置表（G3R1-01/02/03/05/06/07 → 修法一句话+验证证据；G3R1-04 → 声明"边界外未修，交融合方"）、红绿证据摘要、变异自证记录、边界自查
