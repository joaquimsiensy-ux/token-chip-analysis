# 工单D复核：通过

D-R3-01、D-R3-02 均已闭合；本轮增量未发现新问题。按 r4 范围，未重跑其余已闭合项。

**D-R3-01：末笔金额修正有效。** [workorder_D.md:352](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_D.md:352) 的实际 `grep -n -F -o` 结果：

```text
352:(ADDRS[1], ADDRS[0], 5*10**18, 1)
```

工单实际列出 **5 笔正常事件**；第 6 笔是另加的 `value="BAD"` 拒收反例。逐笔整数重算六个普通地址余额如下，单位为 `10**18`：

| 区块 | ADDRS[0] | ADDRS[1] | ADDRS[2] | ADDRS[3]/[4]/[5] 各自 |
|---|---:|---:|---:|---:|
| 101 | 100 | 0 | 0 | 0 |
| 102 | 90 | 10 | 0 | 0 |
| 103 | 90 | 5 | 5 | 0 |
| 104 | 88 | 7 | 5 | 0 |
| 105 | 93 | 2 | 5 | 0 |

每一步均非负，总余额均为 `10**20`。使用真实 DuckDB SQL，在内存叠加工单代码执行主流程，核得：

- 全量 `exit=0`、`neg_balance_addrs=0`、`gate_pass=true`；恢复旧末笔金额，对照为 `exit=4`、负余额地址 1 个。
- 全量与补算结果一致：ADDRS[1] 为 **10^19@102**，ADDRS[2] 为 **5×10^18@103**；ADDRS[5] 为 `{"peak":"0","peak_blk":null}`。
- 正常补算退出 0，inputs/channels SHA 匹配，四份既有全量产物字节未变。
- 追加坏事件后，`n_bad_fields=1`、退出 1，全量产物未变且无新补算收据；恢复旧无条件写入分支，确实检出 `replay_stats.json` 被覆盖，反例仍有效。

**D-R3-02：异常取证要求已闭合。** [workorder_D.md:334](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_D.md:334) 与 §0.7 的实际 grep 摘取：

```text
334:但 `except` 改捕获 `Exception`——记录 `type(exc).__name__` 与原文
17:基线抛非 AssertionError 异常也记为 RED，不得当 GREEN
```

按该要求在内存搭建循环：基线 `summary=[]`、`trigger=null` 两变体均保留 `AttributeError` 类型及原文、计入失败并继续执行，最终汇总为 RED；叠加 D2 后，两变体均返回预期错误文案，对应测试为 GREEN。

另已机械比对 v3→v4：除版本说明、这两项修订及 §0.7 补充外，工单无其他变化；全部 Python 代码块和九个施工白名单文件均未改变。

验证边界：上述为内存验证，文件操作、CSV 来源、通道预检及 provenance 使用替身；未执行完整落盘 CLI、完整测试套件或 `run_all`，不作为施工验收。全程离线、未改文件；开工与收尾工作树均为空，HEAD 均为 `11f1bcb`，工单、r3 报告及九个白名单文件共 11 份 SHA-256 均未变。

Codex session ID: 01a0b00d-ff17-7490-8168-424fecaeae0e
Resume in Codex: codex resume 01a0b00d-ff17-7490-8168-424fecaeae0e
