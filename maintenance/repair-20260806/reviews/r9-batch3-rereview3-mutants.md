# R9 批三·循环2 复审 第三发（mutant 补完，ALL-CLEAR）

> 存档说明（Fable）：Opus 只读子代理（agent ab9772297a0180606）第三发，只做剩余 4 条 mutant 先红后绿。**报告文件因子代理状态幻觉未真落盘**（同第二发；子代理自称落盘 4934B 但磁盘无文件），Fable 据其 result 摘要转录。前两发因子代理自跑 `du` 卡死巨型 worktree Bash 队列中止，第三发工单禁 du+第一条命令建最小镜像脱离 worktree，执行成功。

## 总裁决：ALL-CLEAR
4 条 mutant（共 11 个放松点）全部先红后绿，无自嗨负例，新 finding=0。

## 避雷执行（前两发血泪）
第一条命令即建镜像 `cp -R .../scripts $MIRROR`，全程镜像内跑，零 du/find 大目录/ls-R/wc-l；连续故障（Write 静默失败、grep 终端串扰）未反复探活，改走 heredoc 写 + Read 取回的可靠通道。

## 4 mutant 转红裁定表（每条 M0 绿 + mutant 红）

| ID | 结论 | 关键证据 |
|----|----|----|
| **B3R9-03** 发布层6负例 | **CLOSED 6/6** | M0 绿 `release negatives 6/6`。负例1(L245 exploration)/3(L259 accounting slot)/5(L183 truth slots)/6(solana_observation L575 genesis) 均 (a) 形态转红（非法证据越闸："invalid release evidence accepted"/"guards passed"）；负例2(L248)/4(L175 bundle binding) (b) 形态转红（放松后 NPE，证明断言必要）。全 rc=1 命中各自 `test_release_rejects_*` |
| **B3R9-05** harness 两守卫 | **CLOSED H1+H2** | M0 绿。H1(L44 finally 恢复改 `pass`)→红：`test_activation_is_reversible_and_immutable` 抓 `...is empty_targets`；H2(删 L37-39 sol 条目)→红：抓 `formal_ready_chains()=={eth,bsc,base,sol}` 缺 sol |
| **B3R9-06** r7 断言 | **CLOSED** | M0 绿 `PASS R7-04`。MUT(supply_truth_gate L187 `observed_context_slot=int(bundle["supply"]["slot"])`→`=0`)→红：R7-04 "exploration...lacks mode/context binding; Solana receipt omits observed_context_slot"（exploration+formal 两处绑定断言均触发） |
| **B3R9-10** writable 判定器 | **CLOSED W1+W2** | M0 绿 `solana observation negatives 22`。W1(L164 lookup fail-closed 关)→红："unresolved lookup table did not fail closed"；W2(L157 explicit 覆盖 header)→红："header-derived writable must win over explicit readonly" |

## REFUTED-CANDIDATE：无

## 反幻觉自查（子代理记录）
B3R9-06 首版 mutant anchor 是子代理脑补的 dict 字面量（那次 supply_truth_gate 的 Read 实际未返回），被 driver 的 `assert mut!=orig` no-op 断言当场拦下 → 真读全文修正为真实 kwarg 源头 L187 → `anchor_present_in_orig=True` 确认后重跑，未拿残缺结果凑合。

## 工作区自查
- 未碰原 worktree：对 `r9-closure-worktree` 仅读（cp 到镜像、read_text 作复原基准），零写入；报告改落 scratchpad。
- 镜像已复原：solana_observation.py 三次就地变异后 finally 复原，driver 打印 `RESTORE_OK=True`（字节==原 worktree）；$MIRROR 为 mktemp 临时目录随会话弃。
- 零外网请求；密钥字面量均假值。

## Fable 补核（子代理未覆盖）
**B3R9-13**（第一发标 NOT-VERIFIED、Fable 补收清单亦漏）Fable 读码坐实 CLOSED：`solana_observation.py:433` `if supply_slot < snapshot_slot:` 已从硬 `SolanaObservationError` 改为 `RetryableObservationError`，注释说明 getTokenSupply 不支持 minContextSlot、落后节点失败可重试——正是修复要求。
