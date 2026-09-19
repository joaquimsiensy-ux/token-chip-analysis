# 工单R5复核：通过

v1 的三条修复可采纳：六处锚点、现行依据和净减 **356 B** 均核验成立，未发现需要扩大白名单的同款遗漏。D3 可补明日志展示上限，但不影响完成判据，不构成退回理由。

复核 HEAD：`11e6b932e0401b262708af4ff99b17ad98505476`；指定内容范围相对 `de569f3` 无变化。开审工作区为空；收尾出现三份非本轮创建的未跟踪文件，故**当前尚不满足 §0.1 的开工条件**：

```text
maintenance/repair-20260919-drift-audit2/blind_r6a_prompt.md
maintenance/repair-20260919-drift-audit2/blind_r6b_prompt.md
maintenance/repair-20260919-drift-audit2/construct_r5_prompt.md
```

**D1：采纳。** [命令定义](/Users/uravvv/.claude/skills/token-chip-analysis/commands-staging/token-analyze-1.md:3) 的 argument-hint 含 `full`，第 16 行明确规定第二参数必须为 `full`，缺失或不符先询问；`split-run.md:104` 与之相符。

第 15 行替换原文如下，保留两个前导空格：

```text
  或 CC 开 Opus 会话（备轨）跑 /token-analyze-1 <币> full [链]
```

**D2：采纳两行替换。** [spl_edge_core.py:63](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/spl_edge_core.py:63) 按 `(slot,tx_index)` 分组；第 67–73 行在 digest 冲突时抛出 `RuntimeError`，一致时保留首份。无落盘签名不妨碍这种交易身份去重。

内存实测确认：同身份同内容留一份、不同 `tx_index` 留两份、同身份异内容硬失败、旧五元组拒绝进入 v4。两行只改变工单所述短语，其余逐字一致。

第 35 行替换为：

```text
- **失败原因（禁止推断）**：现役名单里没有＝历史上从未存在（按现仓筛选对已清零地址物理不可见，漏检静默发生、无任何自检报警）；阵营图上散户带收缩默认解读为"散户离场"（PYTHIA 案该时段实为 63% 控盘波次换手）；**"有历史大户兜底桶"＝"历史层处理完了"（桶存在≠桶内被检验过——桶里可能藏着整个协同波次）**。同样禁止把常规池清单当全池、把静默 0 行当无交易、把筛选边/缓存/榜单当完整真值、把旧五元组按五字段去重当无损、把末日闭合当中段正确，或把缺失 ATA 余额填成 0。
```

第 36 行替换为：

```text
- **必做区分检验**：①重放全期**逐地址 max 持仓**，按 max≥实体门槛筛跟踪集（而非现仓）；②③已代码化为 `scripts/report/wave_scan.py` 四指纹机械扫描（同窗建仓聚类×喂币专属度×集中清仓窗×等额面额组，阈值全用合并口径）——名册定稿前必跑，候选逐条裁决完毕前历史大户兜底桶不准关闸（analyze-workflow A3.6 硬闸；split-run 下 wave_scan_report.json 为 READY 必产件）。回收去向追踪（候选波次的 recycle_top 字段）：回市场还是进后续实体——后者是两轮同一控制人的关键证据（PYTHIA 案 7.85% 直入后续体系吸筹仓）。对新增 12 场景逐案执行：V4 单例补入池清单并核毛量占比；Pancake/Uniswap topic 与 data 布局分开且目标池 0 行即阻断；以 `daily_delta` 对筛选边做缺口审计；RPC 台账逐钱包对最新 `balanceOf`、历史曲线另用 archive 快照重建；浏览器榜只找候选；GPA 返回体须含合法 result、命中缓存报告 mtime、增量前真扫，冲突先用第三通道查 2–3 个关键址；大额变动地址 100% 定性；无交易身份的旧五元组不得判重，正负成对差异须用 ATA tx 级真值替换受害地址；中段数值用日采样或全重放并执行末两日 >1pp 阻断；ATA 不在 `postTokenBalances` 就跳过该采样点、保持前值。
```

**D3：采纳改写及两处整行删除。** [scan_bloxroute_seg.py:45](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/scan_bloxroute_seg.py:45) 确实读取 `<out>.done.json` 并跳过完成段；第 87–89、106 行写回完成段。第 81 行时间戳写空串，全文没有 `scan_meta`，也没有锚点采集流程。第 96–98 行累积失败段，108 行打印后返回，没有收尾第二轮补扫。

第 208 行替换原文：

```text
- 断点续传：`<out>.done.json` 记已完成段、重跑自动跳过；失败段打印在收尾 `DONE … fails=` 行，须重跑补采，fails 为空才算采集完成。（OPN，07）
```

第 210、211 行均整行删除，替换文本为空，各自连同 LF 删除；第 209 行通用起始块定位方法保留。

两点精度说明：

- 第 108 行实际打印 `fails[:20]`，21 个失败段只展示 20 个。v1 未承诺完整列出，且展示列表为空当且仅当失败列表为空，故完成判据仍成立。
- 第 67 行已有每段最多五次尝试，“无补扫”仅指没有收尾第二轮，不能解释成“无重试”。旧脚本的缓存、锚点实现在 [scan_transfers.py:71](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/evm/scan_transfers.py:71)、165–180 行；其 `fill` 也是单独调用，不能把工单标题进一步解释为旧脚本自动执行收尾补扫。

**回归面及白名单：通过。** 在排除禁区的 49 份 Markdown 中定向检索，结果如下：

- `/token-analyze-1` 没有其他同款漏写 `full` 的调用示例；命令目录和规则指针不构成调用示例。
- S-04 第 34 行是触发现象，第 39–40 行是 TROLL 历史案源和指纹，不是“无 sig 一律禁去重”的现行规则，不应连带改写。`scan-schemas.md:17` 已正确区分 v4 身份与旧五元组。
- `scan_meta` 的同款现行操作指令仅命中拟删除行。Robinhood 分册明确要求另拉锚点；其他锚点库、Solana 采样说明不归本问题。
- EVM 通道表第 150 行的“失败段补扫”未承诺自动执行；`playbook-supply-recon.md:52` 的 remaining=0 是补齐后再验收的通用条件，没有足够依据扩大修复范围。
- 三份目标文档加维护完成报告的白名单够用；未发现契约或测试固定引用被替换的旧短语。

**结构与范围：通过。** S-04 六字段全部保留。当前文件与 v1 内存替换副本分别运行 casebook lint，均输出：

```text
casebook lint 通过：6 册 38 条，ID 唯一、六字段齐全
```

四处整行替换、两处整行删除均为文本修复；没有新增执行段落、代码或运行时文档，SKILL 与命令上下文大小不变。没有夹带两份盲审中的 KOGE/PDA 待确认问题，也没有把措辞偏好当作漂移。

**存在更短等价改法，但不构成退回项。** D2 两处新短语可分别压为 `把旧五元组去重当无损`、`旧五元组不得判重`，比 v1 再省 12 B、18 B。D3 可用下面整行，在更短的同时写清日志上限，比 v1 再省 30 B：

```text
- 断点续传：`<out>.done.json` 记已完成段，重跑跳过；收尾 `fails=` 最多列 20 个失败段，须重跑补采至 `fails=[]`。（OPN，07）
```

三个可选精简若全部采用，references 为 **929549 B，净减 416 B**，工单预算须同步更新。下表核验的是原 v1。

**汇总表。** 六锚均从工单代码块直接提取，分别执行 `grep -n -F` 和 `grep -n -F -x`；两种结果均恰好一处且行号吻合。字节按 UTF-8 实算，包含行尾 LF：

| 项目 | 原文件锚点 | 命中数 | 修改前 B | 修改后 B | 净变化 B | 意见 |
|---|---|---:|---:|---:|---:|---|
| D1 | split-run.md:15 | 1 | 69 | 74 | +5 | 采纳 |
| D2a | supply-accounting.md:35 | 1 | 649 | 665 | +16 | 采纳 |
| D2b | supply-accounting.md:36 | 1 | 1384 | 1400 | +16 | 采纳 |
| D3a | data-pipeline-evm-channels.md:208 | 1 | 171 | 189 | +18 | 采纳 |
| D3b | data-pipeline-evm-channels.md:210 | 1 | 207 | 0 | −207 | 连 LF 删除 |
| D3c | data-pipeline-evm-channels.md:211 | 1 | 204 | 0 | −204 | 连 LF 删除 |
| 合计 | 四处替换、两处删除 | 6 | 2684 | 2328 | **−356** | 预算正确 |

SKILL：**8021 → 8021 B**；四份 commands：**8789 → 8789 B**；三组 references 共 42 份：**929965 → 929609 B**，不高于基线。两个删除行正文分别为 206、203 B，另各计 1 B LF。`attic.md` 仅取得文件大小及 Git blob 元数据，未读取内容。

本轮未运行会读取禁区、其他 maintenance 目录或创建临时夹具的整套守卫，因此不声称施工后的九项守卫已全绿。报告已打印至 stdout。全程离线，未读 `~/.codex/`、memories 或其他禁读内容，未修改、新建文件或 commit。Git 启动缓存与 heredoc 临时文件创建尝试均被只读沙箱阻止，随后改用直接 Git 可执行文件和 `python3 -B -c`。
