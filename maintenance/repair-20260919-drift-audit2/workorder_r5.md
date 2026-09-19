# 工单 R5：v9.0.1 口径漂移与文档-代码不符 3 条纯文本修复 v2（吸收 codex 复核三处更短等价改法）

内容基线：`de569f3`（R4 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R5a 2 条（`blind_r5a_report.md`）＋ R5b 1 条（`blind_r5b_report.md`），全 minor，Fable 逐条亲核两侧原文属实。本单全部为纯文本修复，零代码改动；**所有锚均为目标文件整行原文，按代码块内整行字面处理；D3 含两处整行删除**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat de569f3 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/split-run.md`、`references/casebook/supply-accounting.md`、`references/data-pipeline-evm-channels.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r5_done.md`。
0.4 删除 > 修改 > 新增；每处锚必须是目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换或整行删除（连同行尾换行），其他行不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 929965（基线 929965；四处整行替换＋两处整行删除按 UTF-8 字面模拟净减 416 B → 929549，实测数写入报告，须不高于基线）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r5_done.md。casebook 条目 S-04 六字段结构不变（只改句内措辞），`casebook_lint.py` 须仍 38 条通过。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均为整行，已由 Fable 逐行匹配验为恰 1 处；行号以 `de569f3` 内容态为准）

### D1（R5b D1）−1 会话示例漏写必填的 `full` 档位参数
`references/split-run.md:15`。锚（整行，保留行首缩进）：
```
  或 CC 开 Opus 会话（备轨）跑 /token-analyze-1 <币> [链]
```
→
```
  或 CC 开 Opus 会话（备轨）跑 /token-analyze-1 <币> full [链]
```
依据 `commands-staging/token-analyze-1.md:3`（`argument-hint: <代币名或合约地址> full [链名等补充信息]`）、`references/split-run.md:104`（mode 值来源＝命令档位参数，未给档位时 −1 开工前先问）。

### D2（R5a D1）casebook 把"无 sig"一律判为不可去重，与 Solana v4 交易身份去重规则冲突（两行）
`references/casebook/supply-accounting.md:35`。锚（整行）：
```
- **失败原因（禁止推断）**：现役名单里没有＝历史上从未存在（按现仓筛选对已清零地址物理不可见，漏检静默发生、无任何自检报警）；阵营图上散户带收缩默认解读为"散户离场"（PYTHIA 案该时段实为 63% 控盘波次换手）；**"有历史大户兜底桶"＝"历史层处理完了"（桶存在≠桶内被检验过——桶里可能藏着整个协同波次）**。同样禁止把常规池清单当全池、把静默 0 行当无交易、把筛选边/缓存/榜单当完整真值、把无 sig 去重当无损、把末日闭合当中段正确，或把缺失 ATA 余额填成 0。
```
→
```
- **失败原因（禁止推断）**：现役名单里没有＝历史上从未存在（按现仓筛选对已清零地址物理不可见，漏检静默发生、无任何自检报警）；阵营图上散户带收缩默认解读为"散户离场"（PYTHIA 案该时段实为 63% 控盘波次换手）；**"有历史大户兜底桶"＝"历史层处理完了"（桶存在≠桶内被检验过——桶里可能藏着整个协同波次）**。同样禁止把常规池清单当全池、把静默 0 行当无交易、把筛选边/缓存/榜单当完整真值、把旧五元组去重当无损、把末日闭合当中段正确，或把缺失 ATA 余额填成 0。
```
`references/casebook/supply-accounting.md:36`。锚（整行）：
```
- **必做区分检验**：①重放全期**逐地址 max 持仓**，按 max≥实体门槛筛跟踪集（而非现仓）；②③已代码化为 `scripts/report/wave_scan.py` 四指纹机械扫描（同窗建仓聚类×喂币专属度×集中清仓窗×等额面额组，阈值全用合并口径）——名册定稿前必跑，候选逐条裁决完毕前历史大户兜底桶不准关闸（analyze-workflow A3.6 硬闸；split-run 下 wave_scan_report.json 为 READY 必产件）。回收去向追踪（候选波次的 recycle_top 字段）：回市场还是进后续实体——后者是两轮同一控制人的关键证据（PYTHIA 案 7.85% 直入后续体系吸筹仓）。对新增 12 场景逐案执行：V4 单例补入池清单并核毛量占比；Pancake/Uniswap topic 与 data 布局分开且目标池 0 行即阻断；以 `daily_delta` 对筛选边做缺口审计；RPC 台账逐钱包对最新 `balanceOf`、历史曲线另用 archive 快照重建；浏览器榜只找候选；GPA 返回体须含合法 result、命中缓存报告 mtime、增量前真扫，冲突先用第三通道查 2–3 个关键址；大额变动地址 100% 定性；无 sig 数据不得判重，正负成对差异须用 ATA tx 级真值替换受害地址；中段数值用日采样或全重放并执行末两日 >1pp 阻断；ATA 不在 `postTokenBalances` 就跳过该采样点、保持前值。
```
→
```
- **必做区分检验**：①重放全期**逐地址 max 持仓**，按 max≥实体门槛筛跟踪集（而非现仓）；②③已代码化为 `scripts/report/wave_scan.py` 四指纹机械扫描（同窗建仓聚类×喂币专属度×集中清仓窗×等额面额组，阈值全用合并口径）——名册定稿前必跑，候选逐条裁决完毕前历史大户兜底桶不准关闸（analyze-workflow A3.6 硬闸；split-run 下 wave_scan_report.json 为 READY 必产件）。回收去向追踪（候选波次的 recycle_top 字段）：回市场还是进后续实体——后者是两轮同一控制人的关键证据（PYTHIA 案 7.85% 直入后续体系吸筹仓）。对新增 12 场景逐案执行：V4 单例补入池清单并核毛量占比；Pancake/Uniswap topic 与 data 布局分开且目标池 0 行即阻断；以 `daily_delta` 对筛选边做缺口审计；RPC 台账逐钱包对最新 `balanceOf`、历史曲线另用 archive 快照重建；浏览器榜只找候选；GPA 返回体须含合法 result、命中缓存报告 mtime、增量前真扫，冲突先用第三通道查 2–3 个关键址；大额变动地址 100% 定性；旧五元组不得判重，正负成对差异须用 ATA tx 级真值替换受害地址；中段数值用日采样或全重放并执行末两日 >1pp 阻断；ATA 不在 `postTokenBalances` 就跳过该采样点、保持前值。
```
依据 `references/data-pipeline-solana-capture.md:158-163`（无签名但有 `(slot,tx_index)` 身份且 digest 一致者只留一份；旧五元组不得按五字段 DISTINCT）、`scripts/solana/spl_edge_core.py:63`（按 `(slot,tx_index)` 分组）、`:67-73`（同身份 digest 冲突硬失败，首现保留）。两行各只改该短语，其余逐字不动。

### D3（R5a D2）bloXroute §3.3 三句承诺是旧 `scan_transfers.py` 行为，新入口 `scan_bloxroute_seg.py` 不成立
`references/data-pipeline-evm-channels.md:208`。锚（整行）：
```
- 断点续传：done-segments 清单跳过已完成段；多线程必留失败段，扫完自动列 remaining 并补扫，remaining=0 才算采集完成。（OPN，07）
```
→
```
- 断点续传：`<out>.done.json` 记已完成段，重跑跳过；收尾 `fails=` 最多列 20 个失败段，须重跑补采至 `fails=[]`。（OPN，07）
```
`references/data-pipeline-evm-channels.md:210`。锚（整行）→ **整行删除**：
```
- 同脚本顺带采时间戳锚点：每隔固定块距 eth_getBlockByNumber 取块头时间戳（数百个锚点几分钟采完），分析期 bisect 线性插值，省数千次逐块 RPC。（OPN，07）
```
`references/data-pipeline-evm-channels.md:211`。锚（整行）→ **整行删除**：
```
- **起点缓存坑**：`<chain>_scan_meta.json` 缓存 start_block/head，改 config 的 start_time_utc 后必须删除该文件才会重新二分，否则沿用旧起点空跑。（哈基米，07-18）
```
依据 `scripts/evm/scan_bloxroute_seg.py:45-47`（另 `:67` 每段最多五次尝试，"无补扫"仅指无收尾第二轮；`:108` 打印 `fails[:20]`）（`<out>.done.json` 跳过已完成段）、`:96-98`、`:108`（失败段只累进 `fails` 并在 `DONE` 行打印，无补扫）、`:81`（时间戳列写空串，不采锚点）、全文无 `scan_meta`；`scripts/evm/scan_transfers.py:71`、`:165-168`（`<chain>_scan_meta.json` 与锚点采集属旧脚本）。`:209` 起始块定位属通用方法不绑脚本，不动。

## §3 完成报告 `r5_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
