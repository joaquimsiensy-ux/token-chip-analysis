---
description: 分段执行·机械段（−1）：A0–A2 全部＋A3 机械子层，产交接契约后完成即停（适配 GPT-5.6/Opus 执行）
argument-hint: <代币名或合约地址> full [链名等补充信息]
---

调用 token-chip-analysis skill 的**分段执行·机械段（−1）**，标的：**$ARGUMENTS**

唯一权威源＝`references/split-run.md` §1（范围）＋ §2（交接契约），逐条照做。硬性要点：

1. **模型自检**：本段设计给 GPT-5.6（codex 主轨）或 Opus（CC 备轨）执行；若检测到自己是 Fable/主力判断模型，提示我"机械段建议换 Opus 会话，Fable 留给 −2"后继续（不硬停）。
2. **开工探针＋案级锁**：split-run §1.1 探针不过不启动全量采集；§1.2 先抢 `.stage1.lock`，抢不到即退出报告在跑者。
3. **范围**＝A0–A2 全部＋A3 机械子层（split-run §1.3），其中第 9 项必须运行 initial 持仓分布扫描并产 `distribution_scan.json`；CEX 黑箱关卡维持点名制——仅当我在命令里附加"CEX 黑箱 ≤N% 才继续"类要求时执行。
4. **停止线（越线＝流程事故）**：聚类合并裁决/实体冻结/判级/casebook 过闸/大户报警深挖/正式 entity_identity_gate/状态评估定性/A4/A5 一律禁做（split-run §1.4）。初步定性只准写 `sealed/stage1_hypotheses.sealed.md`。
5. **未档异常 → 停下写 blocker 进 anomalies.json，禁自创解法。**
6. **全程盲化**：`export CHIP_BLIND_SERIAL=1`；每步跑 `handoff_manifest.py receipt` 记收据。
7. **收工**：先确认 `distribution_scan.json` 为 stage=initial，工作图只在 `charts/distribution_stage1.png`，再跑 `scripts/report/handoff_manifest.py generate --mode full` 产 `handoff/v3`；本命令第二个参数必须是 `full`，缺失或不符时开工前先问我，禁猜禁缺省。状态如实报 READY/PARTIAL/BLOCKED/BLOCKED_CEX_GATE，打印交接摘要＋提示我"新开 Fable 会话跑 /token-analyze-2 <币> full"，**完成即停，不多做一步**。
