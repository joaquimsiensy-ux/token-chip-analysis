# 工单R11复核：退回

v1 需修正两点：D1 的依据遗漏 Helius 默认分支；references 净增 9 B 并非必要。两条问题本身成立，D1 修订后采纳，D2 原案采纳。完整报告已打印到 stdout。

1. **D1：错误成立，但依据和替换文本需调整。**

`scan_token_accounts.py:147` 的 `append` 原样收集参数，`:191` 直接采用 `args.rpcs`。`solana_attested_session.py:61–70` 校验非空、strip、去重，没有简称展开。离线构造 Request 实测：

- `api.mainnet-beta` 抛出 `ValueError: unknown url type`。
- 完整 URL 构造成功。
- 会话层 `:91–100` 会把请求异常包装为 `SolanaRpcError`。

但 [scan_token_accounts.py:126](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/scan_token_accounts.py:126) 明确优先使用非空 Helius key，公共 URL 只是兜底。工单对应依据应改为：

```text
`:126-132`（存在非空 Helius key 时默认用 Helius，否则回退至 `https://api.mainnet-beta.solana.com`）
```

因此，直接删掉 `--rpc` 不保证端点选择等价。保留完整 URL，删去“记得 ”和“同时 ”即可缩短，不减少操作要求。采纳的整行替换原文：

```text
1. **新全量快照**：`scan_token_accounts.py`（Token-2022 `--rpc https://api.mainnet-beta.solana.com` + 先把旧 `_gpa_raw_*` 改名存档，见 §9.8）；`getTokenSupply` 复验供给闭合（窗口内销毁体现在总量差）。
```

2. **D2：原案采纳。**

`1699/464≈3.661638`，增量倍率约 `2.661638`，漏计比例约 `72.689818%`，与 73% 相符；均不支持“差 8 倍”。

`gas_trace_bs.py:79` 确实只请求普通 transactions，执行路径没有 internal-transactions 请求。金额和 Across 归因属于文档案例信息，本次核验其算术自洽性，没有独立重验链上历史。

采纳的整行替换原文：

```text
- **★gas_trace_bs 只抓普通 tx，会整体漏掉 internal 转账入金**（VIRTUAL 实测：Safe 部署者军资表面 464E 实际 1,699E——73% 经 Across SpokePool 以 internal 交付）——大额资金溯源必须补 `/addresses/{a}/internal-transactions`（浏览器 UA）；"资金链断头"结论在补查 internal 前不得下（VIRTUAL 复核，07-16）
```

3. **回归面：允许读取的范围内未发现同款遗漏，白名单够用。**

显式白名单复检覆盖 49 份现行 Markdown，参数检索扩展至 363 份允许读取的文本与代码。具体参数值 `--rpc api.mainnet-beta` 仅 D1 一处；其他简称属于叙述，`<helius>`、`URL` 属于占位符，不应连带修改。“全库”应限定为“允许读取的现行文档与代码”。

其他“差 N 倍”命中已核上下文，例如：

- `3/0.75=4`
- `131833/6217≈21.20`
- `2600/169≈15.38`
- `21.9/8.33≈2.63`

未发现 D2 那样明显矛盾的同款残留，也没有仅因“差几倍”的措辞增列问题。

4. **字节计算正确，但 v1 的净增可以避免。**

整行字节不含末尾 LF；替换保留 LF。

| 对象 | 原文 | v1 替换后 | 本次建议 |
|---|---:|---:|---:|
| D1 整行 | 234 B | 253 B（+19） | 239 B（+5） |
| D2 整行 | 380 B | 370 B（−10） | 370 B（−10） |
| references 合计 | 929110 B | 929119 B（+9） | 929105 B（−5） |

实测 `SKILL.md=8021 B`、commands 合计 `8789 B`；references 三组分别为 `824155 / 74493 / 30462 B`。内存模拟仅改变两文件第 61、20 行，行数仍为 250、26，没有删行。

§1.1 应同步替换为：

```text
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 = 929105（基线 929110；两处整行替换按 UTF-8 字面模拟净变动 -5 B：D1 +5、D2 -10；实测数写入报告，须等于该值）。
```

缩短用于满足字节约束，不另算措辞漂移。两项均只改既定文本行，没有扩修代码、其他方法问题或新增规则。

| 审项 | 核验结果 | 裁决 |
|---|---|---|
| a 锚点 | 两条经 `grep -n -F`、`grep -n -F -x` 均恰 1 处；行号一致 | 通过 |
| b 依据与代码 | D1 默认端点依据遗漏条件；其余所核事实成立 | D1 退回修订 |
| c 字节与整行 | v1 声明数字准确；一行换一行，无删行 | 通过 |
| d 回归与白名单 | 允许范围内无同款遗漏；存在更短写法 | 白名单够用 |
| e 删除优先、上下文不增 | 合计 +9 B 可降至 −5 B | 退回修订 |
| f 范围控制 | 实际参数错误与算术矛盾，未越界扩修 | 通过 |

执行记录：HEAD 为 `6c6697c01c730ea9fb37b9ce85261e59f2f58547`；前后工作区均干净，指定内容路径相对 `8f73554` 无差异。未联网、未修改或新建文件、未 commit。未运行包含禁读遍历及临时文件写入的全套守卫，也未将其记为 PASS。

**纪律偏差披露：**一次 `rg` 的末尾 `*.md` 包含规则覆盖排除规则，已确认误读并输出 `archive/` 内容，也无法排除扫描了其他禁读 Markdown；该次结果未用于裁决，随后通过显式白名单重验。未读取 `~/.codex/` 或 memories。Git 启动器及一次 here-document 的临时文件创建均被沙箱拒绝，未落盘。本次不能作为“无禁读偏差”的复核签收。
