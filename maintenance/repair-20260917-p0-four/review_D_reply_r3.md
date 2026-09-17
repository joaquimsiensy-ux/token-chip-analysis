# 工单D复核：退回

发现 **1 项会使新增测试必红的问题，另有 1 项 RED 取证建议**。r2 要求的生产代码修订已落实，但 D4-b 的“先成功全量运行”前提不成立。

**D-R3-01〔P2，需修订〕D4-b 的事件夹具实际退出 4，不能完成后续验收。**

工单位置：[workorder_D.md:351](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_D.md:351)。

工单最后一笔事件原文：

```python
(ADDRS[1], ADDRS[0], 10**19, 1)
```

这使 `ADDRS[1]` 的最终余额为：

```text
10^19 − 5×10^18 + 2×10^18 − 10^19 = −3×10^18
```

执行原文主流程、真实 DuckDB SQL，文件操作使用内存替身，结果为：

```text
neg_balance_addrs = 1
gate_pass = false
exit = 4
```

对应实际 `grep -n -F` 证据：

```text
315:             "unique_addrs": uniq, "gate_pass": su == mint_total and neg == 0}
603:    sys.exit(0 if stats["gate_pass"] else 4)
```

因此，工单要求的首次全量 `rc 0` 断言必失败，补算及坏事件反例尚未执行便会停止。**r2 的峰值 SQL 对表没有覆盖这个完整退出条件。**

修订建议：将最后一笔转出量改为 `5*10**18`，保留 `rc == 0` 断言。内存验证该修法后：

- 全量退出码为 **0**。
- 两址峰值仍分别为 `10000000000000000000 / block 102`、`5000000000000000000 / block 103`。
- 追加 `value="BAD"` 后，collector/channel 收据校验通过，确实到达 `n_bad_fields=1` 分支。
- v3 保留原全量产物字节；恢复旧的无条件写入后，`replay_stats.json` 字节改变，反例能识别原缺陷。

**D-R3-02〔P3，取证建议〕明确用例 13 的异常如何记为 RED。**

工单位置：§0.7:16、D4-a:333/349。

`grep -n -F` 核得 §0.7 要求“逐例捕获 AssertionError”；指定参照的 B 段循环为：

```text
scripts/tests/test_audit_release_gate.py:730:
        except AssertionError as exc:
```

但用例 13 的基线执行结果为：

```text
summary=[]   → AttributeError: 'list' object has no attribute 'get'
trigger=null → AttributeError: 'NoneType' object has no attribute 'get'
```

照该循环直接调用，会让异常逃出，不能形成该例的 FAIL 记录及汇总。建议在测试层把异常转换成 `AssertionError`，或逐例捕获 `Exception`、保留原异常类型并记为 RED；不能把抛异常视为 GREEN。此项不单独作为退回依据。

**r2 五项处置核验**

| 编号 | v3 核验结果 |
|---|---|
| D-R2-01 | 已闭合。summary/trigger 顶层先验对象；逐日 `active_candidates` 缺项、null 均拒。 |
| D-R2-02 | 已闭合。整数、字符串、字典、null、缺项及非法列表成员均走 `_fail`，退出 2。 |
| D-R2-03 | 条件写入及反例结构已修；原样执行仍受 D-R3-01 阻断。修正夹具后，坏事件可达目标分支，反例有效。 |
| D-R2-04 | 用例 2/12 已标 GREEN→GREEN，子函数范围已改为 1..13；新增第 13 例另见上述建议。 |
| D-R2-05 | 已闭合。非法及负 peak 只报根因，不再追加虚假的 `peak==0` 区块错误。 |

**其余实际核过的项目**

| 项目 | 结果 |
|---|---|
| a：锚点 | 27 项 `grep -n -F` 均唯一且行号一致：peaks_daily 的 60–63/171/202/213；gate 的 408/457/603/1074/1103/1676；replay 的 36/191/194/330/556/577/587；测试的 960/970/972、236、113；文档的 132、149。 |
| b：定位与咬合 | 内存路径案例命中 `data/peaks_daily/`；排除隐藏目录、`_history`、`.duck_tmp`、文件及父目录符号链接。零份 return、多份拒；三个伴随文件均相对 `pd`。needs 缺 SHA 明确提示“升级脚本重跑”。 |
| b/j：形状与错误 | needs 各档与触发日候选取小写并集；收据 schema、engine、输入绑定、地址覆盖和 peak/peak_blk 检查成立；大小写重复地址被拒。原有六条错误文案逐字保留。结构失败后的 return 会遮住后续检查，但已经拒收，且后续依赖无效结构，可以接受。独立错误允许累计，无须全局互斥。 |
| c：受保护逻辑 | deltas 抽取保留原 SQL；pass1 除替换调用外等价；`build_events`、`emit_merged`、`replay_pass2` 原文不变。followup 窗口 SQL 与原 :285–290 逐字相同。 |
| c/j：入口与计算 | `_fail` 后定义可用，`sys` 已导入；:577 位于 main，不触及保护函数。HUGEINT、VARINT 实算一致；强制窗口失败后，Python 回退结果一致。低于全量门槛的 peak=1 地址仍被保留；无事件地址为 `0/null`。 |
| c：产物与哈希 | 首输入目录、逐输入 SHA、channels SHA 均复算一致。用调用哨兵及内存写记录确认 only-addrs 跳过 pass1/merged/pass2，未写 §1.3 列出的产物。坏 JSON、空并集、坏形状退出 2，原补算收据未更新。 |
| d：D4-a | 独立执行子闸场景：1、3–6、7 前半、8–11、13 均为 RED→GREEN；2、12 为 GREEN→GREEN；7 补齐绑定及覆盖后放行。第 13 例基线的异常另见 D-R3-02。 |
| d：旧夹具与 D4-c | e/f/k/g 原断言仍成立。h 不改会因旧断言漏检而假绿；按工单补 needs、两字段及断言后错误为空。D1、夹具助手、D4-c 字段一致；新增 needs SHA 断言在基线失败、内存叠加后通过。 |
| e：登记 | 扫描器基线实跑无差异；内存叠加并补 producer、consumer、`followup_peaks / overwrite_single` 三处登记后，`validate_manifest=[]`。计数变为 producer 81、consumer 118、atomic 61；transport 65、formal 61 不变。`minimum_counts` 是下限，无需修改。 |
| f：文档 | 替换实算 61→48 B、30→39 B；references 为 **930061**，SKILL.md 为 8021、commands-staging 为 8798。两目标文档粗体、引用和相关 13 条契约 needle 通过；日期戳保留。并集每址覆盖承接被删句的补算义务。 |
| g：回归与同族 | 全 `scripts/` 搜索仅发现现有 e/f/k/g/h 五处手写 summary；其他读取者为本段生产者、发布闸及 test_peaks_daily，另有 test_repair_batch1 的子闸 mock。§0.8 其余三个测试夹具未见 summary，仍走零份 return。当前 D4-b 会使 test_engine_equivalence 及包含它的 run_all 变红。 |
| i：范围 | L1/L2、门槛、既有格式及契约针未改变；P2/P3 维持，P13 的 channels 同源验证留待另单，与本段边界一致。r1 其余已闭合修改未见被 v3 破坏。 |

`run_all` 另有既有 W3 验收耦合：[test_stage2_reseal.py:604](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_reseal.py:604) 的 overlay 白名单不允许 D 的多数改动。D 未提交工作树进入该路径仍会失败；这不是 v3 新引入的业务回归。

**§4 APU 推演**

在 `ub_formula` 正确、`trigger_days_file=True`，且子目录触发日产物其他字段合法的前提下：

| 前提 | 改后错误 |
|---|---|
| 子目录 trigger 在场且 SHA 咬合，summary 无 needs SHA | `needs_block_precision.json 缺失或与 peaks_summary 登记的 sha256 不咬合（旧版 peaks_daily 未登记该哈希＝升级脚本重跑）` |
| 子目录 trigger 缺失 | `peaks_summary 声称产出触发日但 trigger_days.json 缺失`，随后返回。 |

与 §4 一致。案根残留的 `trigger_days.json` 不是 summary，不计入“多份”，也不能替代子目录文件。未访问真实 APU 案。

全程离线、未修改文件。六个需要落盘夹具的完整测试、run_all、完整 docs_lint 未运行；上述动态取证使用原文函数／主流程、内存文件替身和真实 DuckDB，不能替代完整 CLI 验收。

开工及收尾工作树均为空。期间 HEAD 从 `1a5e832` 前进至 `fd7da2b`，仅新增另一份复核文档；本工单及九个施工白名单文件的 SHA-256 均未变化。工具未读取禁读路径。

Codex session ID: 01a0aff9-772a-7863-81e9-9b3592863149
Resume in Codex: codex resume 01a0aff9-772a-7863-81e9-9b3592863149
