# 工单 F-010：LIT 案实机回归（fresh 会话可独立执行）

一句话目标：在真实 LIT 案目录用已入库的正式修复（skill 仓库分支 fix/lit-regression-v6522，HEAD=93aa5b6）实证两处闸放行——F-007 序列编译不再末点假红、F-008 freeze 走通 evm_v2 溯源重放；报告数字零变化。

## 【开工门禁】（不符即写停工报告并停）
- skill 仓库：/Users/uravvv/.claude/skills/token-chip-analysis；`git -C <仓库> branch --show-current` = `fix/lit-regression-v6522`；`git -C <仓库> rev-parse --short HEAD` 以 `93aa5b6` 开头；`git -C <仓库> status --short` 干净。
- LIT 案目录存在：/Users/uravvv/Documents/5.6筹码分析/LIT分析（本工单工作根=案目录，唯一可写区）。
- 案内关键实物存在：`data/ethereum/replay/camp_series.provenance.json`（sidecar，series_format=evm-dict、denominator=mint_total_legacy）与 `data/ethereum/v2/` 目录。

## 背景（一句话）
LIT 案 2026-08-24 分析时被两道闸误拦（F-007 末点对账假红、F-008 evm_v2 目录被文件闸拒），当时靠工作区临时补丁绕过（该补丁已弃用未入库）。现正式修复已入库，须在原案实证放行。

## 第一步：探明当初调用
从案目录既有产物（receipt/state JSON/日志/manifest/done 文档）里找出当初 `state_from_facts` 与 `handoff_manifest` 的准确调用形式（参数、输入文件路径），逐条记录进回执；不确定处以 skill 仓库脚本 `--help` 与 references/ 文档为准。禁止臆造参数。

## 第二步：F-007 实证（序列编译）
- 以 skill 仓库 HEAD 脚本运行 state_from_facts 的序列绑定编译（`--series-source` 指向案内 sidecar），产物写案目录原位置。
- 验收断言：EXIT_CODE=0；endpoint_reconcile 不再报散户残差假红；产出 state 中末点「锁仓/销毁」=1.5639%、散户=6.5733%（与既有报告一致，容差按序列文件原值逐字比对）——**报告数字必须零变化**，若任何数字变动即为异常，停工写明差异。

## 第三步：F-008 实证（freeze 溯源重放）
- 运行 handoff_manifest.py freeze（按第一步探明的调用），走通 evm_v2 溯源重放。
- 验收断言：EXIT_CODE=0；不再报「路径不是常规文件」；重放语义摘要终比通过；生成/更新的 manifest 落案目录原位置。
- 若集合闸拒绝（当前目录命中集合 vs source.files 不等）：如实记录差集报错原文——这是 stale-ledger 正确拒绝而非修复缺陷，停工交调度裁决，不得改 ledger 或目录内容硬闯。

## 收尾（回执）
- 回执写案目录 `f010_lit_regression_receipt.md`：门禁证据、当初调用探明记录、两步命令原文＋原始输出（含 EXIT_CODE）＋关键数字比对表、案内产物变化清单（新增/覆盖了哪些文件）。
- 回执零行尾空格、零 EOF 空行。

## 边界（硬性）
- **skill 仓库一律只读**（脚本以其 HEAD 直接运行，不改任何仓库文件）。
- 案目录只允许写：本回执＋两步命令的正常产物（state JSON/manifest 及其临时文件）；**禁改** sidecar、序列文件、ledger、data/ 下任何已有数据实物。
- 不 commit、不联网（脚本本地运行，不发任何网络请求；如脚本试图联网即停工记录）。
