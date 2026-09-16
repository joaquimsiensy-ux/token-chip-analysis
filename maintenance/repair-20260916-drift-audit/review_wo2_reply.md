<!-- 由 Fable 从 codex 只读复核任务 task-mu4e3tgw-zgu84e 的 Final output 段原样搬运 -->
# 工单R2复核：退回

**11 个锚点全部通过。** 退回原因：字节超限、守卫执行边界未闭合，以及 D3、D7 的白名单内遗漏。

HEAD=`b6652932421b67fd2eadc1331fe14e3d5271990a`，VERSION=`7.1.1`；相关内容与 `445d7ac` 一致，工作树前后均为空。全程离线，未写文件、未 commit、未打开禁读文件。

## 逐条核对表

下表文档路径均相对 `references/`；锚点均实际执行了 `grep -n -F`。

| 条目 | 锚命中 | 事实一致 | needle/守卫 | 意见 |
|---|---|---|---|---|
| D1 | `lp-fee-accounting.md:62`，1 处 | 通过：校准后的池流入腿绝对值；traps 第 12 条编号正确 | 未撞 needle | 保留动态费、协议费、hook 限定 |
| D2 | `retrospective.md:102`，1 处 | 跨案行为正确；默认根为 `~/Desktop/老公用/fable筹码分析` | 未撞 needle | 补明每案优先 appendix，缺失才取 analysis-state |
| D3 | `data-pipeline-robinhood-channels.md:34`，1 处 | 二维 list 正确；整段依赖归属仍错 | 未撞 needle | LP 脚本不读取小时线，须整行修订 |
| D4 | `independent-audit-protocol.md:105/106`，各 1 处 | 通过：案目录后的选项进入 REMAINDER；删除后使用默认值 | 未撞 needle | 已在内存执行原 parser 验证 |
| D5 | `scan-schemas.md:17`，1 处 | 通过：wave/flow 六字段齐全；分布扫描不齐 | 未撞 needle | 可压缩措辞满足字节预算 |
| D6 | `data-pipeline-robinhood-channels.md:33`，1 处 | 通过：CLI pools 优先，否则取 config.pools；out 默认 `data/lp_events.json` | 未撞 needle | `--from-block` 必填；两处均无池地址时退出 |
| D7 | `labels/MAINTENANCE.md:86/87`，各 1 处 | 两行修法正确；默认 CSV 为 `scripts/labels/sources/serial_actors.csv` | 未撞 needle | :70–80 仍有同族 cwd 错误 |
| D8 | `playbook-state-anomaly.md:36`，1 处 | 通过：目标为 sources §4，表项在 :26 | 未撞 needle | 无额外问题 |
| F2 | `monitoring-package.md:43`，1 处 | 通过：chain_registry 的 robinhood 为 exploration | 未撞 needle | 本轮已确认档位 |

代码核对依据：

- D1：`scripts/robinhood/pull_swaps_v4.py:9,98–99`，以及 traps :51–53。
- D2/D7：`scripts/labels/accumulate_offenders.py:42–44,200–206,226,265–269,317–327`。
- D3：`scripts/robinhood/cost_engine.py:25,29–35`。
- D4：`scripts/report/reproduce_receipt.py:53–60,81–99`。
- D5：`scripts/report/wave_scan.py:830–848`、`flow_anomaly_scan.py:385`、`holder_distribution_scan.py:710–716,866–869`。
- D6：`scripts/robinhood/pull_lp_events.py:28–46`。
- F2：`scripts/lib/chain_registry.py:117–121`。

D5 六字段为 `schema/generated_at/params/total_supply_raw/edges/note`。分布扫描使用 `generated_at_utc`，成功与失败输出均不具备上述后五项。

**受影响文件的 53 条 required/banned needle 全部满足。** 原 `docs_lint` 的逐文件断链、粗体配对检查在八份内存替换文本上通过。原样执行通过的守卫为 `casebook_lint.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`；不代表全量守卫通过。

## 退回理由

1. **字节必超。** 按工单逐字在内存替换，references 三组从 **929850 → 930112 字节，净增 262**，违反 §1.1。SKILL=8021、commands=8798 均不变。42 份 references 文件通过逐文件 `stat -f %z` 汇总；attic 未读正文。

2. **守卫执行边界未闭合。** [docs_lint.py:266](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/docs_lint.py:266) 默认扫描包含 attic，`--all` 还纳入 archive；:129–134 另有全库 Markdown 读取。[changelog_lint.py:41](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/changelog_lint.py:41) 读取归档，[test_sixlens_docs.py:22](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sixlens_docs.py:22) 未排除 attic。这四次调用未执行；`test_contract_routes.py:76` 因创建临时 fixture，在本轮只读复核中也未执行。不能记为全绿。

3. **D3 留下错误依赖。** [channels:34](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-robinhood-channels.md:34) 仍挂在 LP 脚本条目下，声称依赖小时线及首次 FileNotFoundError 属预期。LP 脚本的文件输入只有 config；两列小时线实际由 `build_price.py:25–34` 消费。仅改 dict/list 没修正消费者归属。

4. **D7 漏修同页 cwd。** 页首约定在 `scripts/labels/` 执行，但 [MAINTENANCE.md:70](/Users/uravvv/.claude/skills/token-chip-analysis/references/labels/MAINTENANCE.md:70) 开始的下载块未进入 sources，:79–80 的 `../probe_codetype.py` 指向不存在的 `scripts/probe_codetype.py`；下载文件也没有进入后续构建使用的 sources 目录。

## 修订建议（可直接粘贴）

D4、D6、D7 原 :86–87、D8、F2 沿用工单。以下位置均按改前文本计算。

**D1：原锚不变，替换为：**

```text
gross_input_j = 经同 tx Transfer 校准的输入腿负值绝对值（data-pipeline-robinhood-traps 第 12 条）
```

**D2：原锚不变，替换为：**

```text
——跨案回灌惯犯库（扫描 `DEFAULT_ROOT` 或所传案根父目录；每案优先 appendix.json，否则 analysis-state.json；跨案合并并自动落印）
```

**D3：将 channels 原 :34 整行替换为以下一行，保留两个前导空格：**

```text
  cost_engine 的 `data/quote_usd_hour.json` 为 `[[ts,o,h,l,c],...]`；`data/ethusdt_1h.json` 属 build_price 输入，列为 `[[ts,close],...]`；pull_lp_events 不读小时线。
```

同文件原 :30，锚 `+ transit_contracts.json；config 可选 fee_distributor。` 替换为 `+ data/transit_contracts.json；config 可选 fee_distributor。`。

**D5：原锚不变，替换为：**

```text
仅 wave-scan／flow-anomaly 保证齐全，其他产物见各自 schema
```

**D7 补项：**在 `MAINTENANCE.md` 原 :70 前插入一行 `(cd sources || exit`，原 :80 后插入一行 `)`；原 :70–80 内容保持不变。下载和 probe 共用 sources 工作目录，块结束后返回 labels 目录。两端锚及 D3 新锚均已验证恰一处、行号一致。

以上组合内存重算为 **929831 字节，净减 19**；SKILL/commands 不变，53 条 needle 保持满足，标签页三个 shell 示例均通过 `zsh -n`。未实际应用。

**§1.2 建议改为：**

```text
1.2 禁读边界优先。逐项记录守卫的 PASS / FAIL / BLOCKED 及原因；
不得把限定读集的检查记为原版全量守卫 PASS。触及禁读路径的守卫
留待另行明确读取授权的完整验收阶段执行；未补齐前不得宣称全绿
或全部验收完成。只读复核不执行创建临时 fixture 的测试。
```

## 同族遗漏（白名单内 / 建议下轮）

- **白名单内：**channels :34 的小时线消费者归属、:30 的 `data/transit_contracts.json` 路径；MAINTENANCE :70–80 的 cwd 连续性。上述修订已覆盖。D2 同时补明每案文件择一优先级。
- **建议下轮：**[pull_lp_events.py:11](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/robinhood/pull_lp_events.py:11) 的 docstring 声称支持 `pools 或 v3_pools`，实际 :44 仅回退 `config.pools`；脚本不在本轮白名单。

指定替换未发现额外新增的代码事实矛盾；D3/D7 属于修复后仍残留的同族漂移。
