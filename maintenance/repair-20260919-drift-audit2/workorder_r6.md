# 工单 R6：v9.0.1 口径漂移与文档-代码不符 2 条纯文本修复 v1

内容基线：`8e54242`（R5 施工落地后的内容态；施工 HEAD 可含 maintenance/ 提交，但 §0.1 差异校验须为空）。来源：盲审 R6a 2 条（`blind_r6a_report.md`），R6b 0 条（`blind_r6b_report.md`）；两条均 minor，Fable 逐条亲核两侧原文属实。本单全部为纯文本修复，零代码改动；**所有锚均为目标文件整行原文，按代码块内整行字面处理**。

## §0 施工纪律
0.1 开工先确认 `git status --short` 为空并记录施工 HEAD；`git diff --stat 8e54242 HEAD -- SKILL.md references scripts commands-staging VERSION CHANGELOG.md` 须为空，不符即停工汇报。
0.2 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`（§1.1 统计字节时 attic.md 只计大小不读内容；守卫脚本自身遍历文档属被测代码既有行为，允许并要求原样运行）；`maintenance/` 下只读本工程目录。
0.3 **白名单**：`references/data-pipeline-evm-channels.md`、`references/playbook-entity-cluster-methods.md`，以及新建 `maintenance/repair-20260919-drift-audit2/r6_done.md`。
0.4 删除 > 修改 > 新增；每处锚必须是目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致；不符停工；按整行替换，其他行不动。
0.5 不 commit、不 push、不部署；不改 `scripts/`、`commands-staging/`、`CHANGELOG.md`、两份 manifest。

## §1 硬约束
1.1 字节：`SKILL.md` = 8021、`commands-staging/*.md` 合计 = 8789 不变；references 三组 glob（`references/*.md references/casebook/*.md references/labels/*.md`）合计 ≤ 929549（基线 929549；两处整行替换按 UTF-8 字面模拟净减 18 B → 929531，实测数写入报告，须不高于基线）。
1.2 守卫全绿：`python3 scripts/tests/docs_lint.py`、`docs_lint.py --all`、`casebook_lint.py`、`changelog_lint.py`、`test_contract_routes.py`、`test_sixlens_docs.py`、`test_g3_docs_guards.py`、`test_version_consistency.py`、`test_commands_deploy_sync.py`，原始输出贴进 r6_done.md。
1.3 `git diff --stat` 只含 §0.3 白名单。

## §2 逐条施工（锚均为整行，已由 Fable 逐行匹配验为恰 1 处；行号以 `8e54242` 内容态为准）

### D1（R6a D1）Alchemy 续采条写"下游按 tx hash 去重"，现行重放键含事件序号
`references/data-pipeline-evm-channels.md:201`。锚（整行）：
```
- pageKey 有有效期，长任务中断后必过期：断点续拉一律读 CSV 末行区块号置 fromBlock 重开游标，容忍少量重复、下游按 tx hash 去重。（SIREN，07）
```
→（删去"、下游按 tx hash 去重"短语，其余逐字不动）
```
- pageKey 有有效期，长任务中断后必过期：断点续拉一律读 CSV 末行区块号置 fromBlock 重开游标，容忍少量重复。（SIREN，07）
```
依据 `scripts/evm/replay_pass1.py:72`（`li` 取 log_index 或 uniqueId 尾号）、`:79`（键 `(c["tag"], tx.lower(), li)`，同一 tx 内不同序号保留多条）；`references/data-pipeline-evm-sources.md:64`（跨通道拼接去重键陷阱：段内用自家键去重，replay_pass1 已固化）。删除后去重规则以 evm-sources:64 为唯一出处，不新增说明。

### D2（R6a D2）聚类措辞总括句"一律高度疑似"与判级表类型②可"链上铁证"冲突
`references/playbook-entity-cluster-methods.md:184`。锚（整行）：
```
**措辞锁定：** 聚类结论一律"高度疑似同一实体"，不写确权——共用出纳也可能是做市商/OTC 服务商同时服务多个独立客户；把证据链逐条列出（每条边标日期+金额）让读者自判（IO，07）。
```
→（仅把"聚类结论一律"改为"共用出纳型聚类一律"，其余逐字不动）
```
**措辞锁定：** 共用出纳型聚类一律"高度疑似同一实体"，不写确权——共用出纳也可能是做市商/OTC 服务商同时服务多个独立客户；把证据链逐条列出（每条边标日期+金额）让读者自判（IO，07）。
```
依据 `references/playbook-entity-cluster-tiering.md:53`（类型②互转/gas 同源/首笔注资同源可"链上铁证 / 高度疑似"）、`:60`（实锤①②与高度疑似③分开报）；本句案源 IO 与破折号后半句均只讲共用出纳（做市商/OTC 同服多客户），收窄到共用出纳型即与 `data-pipeline-solana-scan.md:116`（共用中转地址→措辞锁定高度疑似）一致；`methods.md:102` 把共用中转列为强证据不动（强证据≠确权）。

## §3 完成报告 `r6_done.md` 必含
①逐条改前→改后 diff；②§1.1 字节实测（三组数）；③§1.2 各守卫原始输出；④`git diff --stat`；⑤差异/停工点；⑥禁读披露。
