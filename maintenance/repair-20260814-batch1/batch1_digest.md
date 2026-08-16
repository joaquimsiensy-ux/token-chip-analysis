# 批 1 步骤⑧盲审消化记录

日期：2026-08-14  
版本：6.41.0（未升版）  
盲审报告 SHA-256（施工前后相同）：`630b9174375f3e3a0b1f06660a03a603ef18401267f33a48bb30f88d67474281`

## 结论

P1×1、P2×1 已修；P3×3 的处置为“修、注释、修”。RV-07 自评由 FAIL 转为 PASS：合法真 FAIL 在 SIGKILL 遗留锁后会先被明确拒绝，只有显式恢复命令通过活锁证据与两态状态机校验后才清盘；不可判定状态保持原字节、人工介入。

## P1：supersede 崩溃锁恢复

### 错误分码与人工入口

- 遗留/并发锁使用前缀 `SUPERSEDE_LOCK_PRESENT`，消息含锁文件绝对路径、明确说明不自动恢复，并给出 `python3 scripts/lib/receipt_kernel.py --recover <canonical>`。
- 普通 PASS 降级拒绝使用不同前缀 `PASS_DOWNGRADE_REJECTED`；原有五个真 FAIL 出口继续透传 kernel 异常文本，因此用户可区分“锁存在”与“非法降级”，无需改五出口业务逻辑。
- 锁写入 `receipt-supersede-lock/v1` 元数据：canonical、同一 `run_id`、PID、`owner_evidence=fcntl-flock/v1`、目标 FAIL 载荷 SHA-256 和建立时间。发布进程在锁 fd 上持续持有内核 advisory lock；恢复进程必须先非阻塞取得同一锁。活进程仍在时内核拒绝取得，崩溃时内核自动释放，因此该证据不受 PID 复用影响，属于“PID＋启动时间戳”的等价、可校验证据。

### 恢复状态机

1. **上次已提交**：canonical 必须是 `FAIL/2`，且文件 SHA-256 必须精确等于锁绑定的目标载荷；只清同 run 临时件和锁，保留已生成的 PASS 审计归档，返回 `COMMITTED / 上次已提交`。
2. **上次未提交已回滚**：canonical 必须是 `PASS/0`；同 run `.superseded-<runid>` 必须存在且与 canonical 为同一 inode；同 run `.tmp` 必须存在且哈希等于目标 FAIL。通过后依次撤销临时件与孤儿归档、清锁，返回 `ROLLED_BACK / 上次未提交已回滚`。
3. **人工介入**：锁损坏、canonical 缺失/损坏/变化、目标 FAIL 哈希不符、PASS 无同 run 归档、临时件不符等，统一 `SUPERSEDE_RECOVERY_MANUAL`、CLI exit 2，盘面不动。
4. **活锁拒绝**：发布进程仍持有 advisory lock 时，统一 `SUPERSEDE_RECOVERY_ACTIVE`、CLI exit 2，不自动恢复。

锁、tmp、archive 统一复用一个 `run_id`，避免把历史成功归档误认成本轮孤儿；canonical FAIL 还额外绑定目标载荷哈希，避免把旧 FAIL 误认成“上次已提交”。`invariant_manifest.json` 已登记新锁 schema 的 producer/consumer，minimum counts 各加 1。

### window_fetch 混合态评估

决定：**不改 `window_fetch.py`**。现有顺序可幂等恢复：若 receipt 已翻 FAIL、旧 data 仍在，显式恢复先只清 receipt 锁；随后用相同失败窗口重跑，`window_fetch` 会为仍在的旧 data 新建 `.stale.<runid>`，对已有 FAIL canonical 再执行 `publish_supersede`，成功后删除旧 data canonical 并更新 gaps mirror。新增注入测试真实留下“FAIL receipt＋旧 data＋.stale”，重跑 exit 2 后旧 data canonical 消失，所有 stale link 保留旧数据字节。恢复命令本身不猜测 window 多文件业务路径，职责保持在 receipt kernel。

### 先红后绿证据

- 红：SIGKILL 子进程真实 returncode `-9`；随后 P1 独立反例进程 exit `1`，错误仍为旧 `concurrent or interrupted...<canonical>`，无锁绝对路径/恢复命令。
- 绿：`test_repair_batch1.py` exit `0`。覆盖 replace 前 SIGKILL→合法 supersede 被拒→CLI 恢复回滚→canonical FAIL 成功；replace 后“已提交”；无 archive 的不可判定状态 CLI exit 2 且目录逐字节不变；活进程持锁 CLI exit 2；window 混合态重跑闭合。

## P2：`--token-file` 回显抑制

四支入口的 `_load_token` 已统一为固定错误文案：`HyperSync token 文件缺失或为空（路径已隐去）；默认路径 ~/.config/hypersync/token，或设 HYPERSYNC_TOKEN`。原始 `--token-file` 参数值不再进入 stdout/stderr。

- 红：`test_token_no_positional.py` exit `1`，实测 `plaintext-secret` 出现在 argparse stderr。
- 绿：`test_token_no_positional.py` exit `0`，四支入口均对 `--token-file plaintext-secret` 断言 sentinel 不出现。

## P3 裁量项

### 枚举器 endpoint 与 `fetch_` 前缀

决定：**修**。当前缝隙会让非 `fetch_` 命名、直连 `*.hypersync.xyz`、不 import SDK 的新采集器漏出安全分母，确会重现 step6 的入口覆盖缺口。endpoint 字面证据现为独立充分条件；保留 SDK、命名、manifest 三路证据；显式排除 `accounting_gate.py`（它是 endpoint 政策 consumer，不接收凭据）。测试加入 `collect_direct.py` 模拟命中和排除项反例。

### replay_pass2 信任 `stats.gate_pass`

决定：**只补注释，不改逻辑**。盲审攻击依赖手写/篡改 `gate_pass=true`，不属于 F-03“pass1 自己算出 false 却放行”的原不变量。`replay_pass2.py` 已明确：pass2 消费 pass1 判定，不重算 merged；防篡改责任由 camp-series provenance 对 replay_stats 的绑定及下游 supply_truth 哈希链承担。

### stake_decode `all_sigs` cap 静默截断

决定：**修**。cap 命中就是观测不完整，继续输出正式 `[闭合]` 与 RV-17 口径冲突。`all_sigs` 现在精确多探一条：只有短页才能证明穷尽；发现第 `cap+1` 条即标记截断，main 写 `complete=false, verdict=ERROR`、exit 1，不解码部分账本、不打印正式闭合。

- 红：cap 独立反例 exit `1`，失败内容为旧产物 `complete=true, verdict=PASS`。
- 绿：该反例并入 `test_repair_batch1.py`，最终窄测 exit `0`，产物含截断错误且为 `complete=false, verdict=ERROR`。

## 最终验证

| 命令 | 退出码 | 结果 |
|---|---:|---|
| `python3 scripts/tests/test_repair_batch1.py` | 0 | P1/P3 新反例及原批 1 矩阵全绿 |
| `python3 scripts/tests/test_token_no_positional.py` | 0 | 自动枚举 4 支；位置 token 与 token-file sentinel 均不回显 |
| `python3 scripts/tests/invariant_scan.py` | 0 | producers=56、consumers=64、transport=62、atomic=49、formal=58、exceptions=0 |
| `python3 scripts/tests/docs_lint.py --all` | 0 | 58 个文档通过 |
| `python3 scripts/tests/changelog_lint.py` | 0 | 版本号唯一/顺序通过；6.41.0 末尾已补盲审消化条目 |
| `python3 scripts/tests/run_all.py` | 1 | 仅 2 项 loopback bind 沙箱失败；其余全部 PASS |

`run_all.py` 两项失败均发生在业务断言前：

- `test_batch3_solana_vertical_slice.py`：`ThreadingHTTPServer(("127.0.0.1", 0), ...)` → `PermissionError: [Errno 1] Operation not permitted`。
- `test_batch3_evm_vertical_slice.py`：同一 loopback bind → `PermissionError: [Errno 1] Operation not permitted`。

这两项与用户预告的沙箱能力限制一致；不记作业务全绿，也未绕过。盲审报告未改，`archive/` 未改，未执行任何 git 命令。
