# 批 11 Fable 验收记录（2026-08-26）

裁决依据：延续用户方案 A。批 10 关 target 层后，ARC 五查实跑暴露文件绑定层同族矛盾
（同文件绑定逼第五查吃活快照＋活观测覆盖封账件事故），批 11 关此最后一层。

## 验收项与结论

1. **diff 逐 hunk 审查**：shared_release_receipt 两态分立（静态态原代码原文案逐字保留、
   冻结态三重绑定）＋handoff required-set 共用函数化（generate/verify 同源，冻结态才加
   冻结 bundle）。零 EVM 外溢。✅
2. **防伪链闭合独立核实**（关键项）：
   - `validate_receipt`（receipt_validate.py:125-146）确实对每个 input **重哈希实物**
     （size+sha256 双验）——信封不是纸闸；
   - `validate_observation_bundle`（solana_observation.py:551 起）bundle_path 在场时做
     holder_outputs **文件级三验**（存在+sha256+size，B-1 锚）＋canonical bytes 对
     账＋主网 genesis attestation＋三向 supply 闭合；
   - exact receipt 的 holders_owners 哈希经其自身信封物理验证 → 与冻结 bundle owners
     指纹全等 → 冻结 bundle 自身信封+深验密封。链条：物理文件 ↔ exact 收据 ↔ 冻结
     bundle，三点互锁。✅
3. **ARC 实物实测**：新校验器对 ARC 冻结 bundle 精准咬中唯一真实缺口
   （gpa_rpc 43MB 原件被活观测覆盖、size+hash 双 mismatch），其余全部通过——
   闸的判别力得到真实事故验证。✅
4. **红绿证据**：R1 红为改前真实同文件闸拒绝输出；绿证据含 G1/N1-N5＋静态端到端
   （test_repair_batch_d）＋契约/invariant/py_compile。✅
5. **run_all**：codex 沙箱 133/135（2 项 loopback 纯环境）；Fable 本机 **135/135 全绿
   EXIT=0**。✅
6. **禁改面**：replay_edges/runner/EVM/版本登记面/密钥/ARC 案根零触碰，
   `git diff --check` 干净。✅

## 附：ARC 案封账件覆盖事故与逐字节恢复（验收方操作记录，案内实物）

- 事故：批 10 前的五查旧协议 runner 多轮重跑中，supply 观测（--work-dir data）把封账
  快照三件与三个 inputs 全部覆盖为活链版。
- 恢复（全部哈希对照密封指纹逐字节验证）：holders_owners/holders_accounts 从案内密封
  复合快照 holder_snapshot.json 提取重建（sha256 MATCH）；holders_snapshot_meta 以同构
  模板+密封 bundle 字段逐字节重建（sha256 MATCH）；_supply.json 与 _gpa_raw_all.meta.json
  按生产者 payload 模板重建（sha256 MATCH）；冻结 bundle 从 .bak_20260826_102407 归位。
- 残留缺口：`data/_gpa_raw_all.json` 封账版（66f0a4aa…, 43,067,708 B）不可重建
  （复合快照仅存 45,958 非零行，原响应含 180,241 户）；唯一副本在本机 TM 快照
  （2026-08-25-143540），已请用户协助提取（三选一方案已发）。此缺口只阻塞
  handoff/release 深验，不阻塞五查 runner。
- 防复发：job spec supply --work-dir 分家至 data/observe_live（本批文档化）＋
  arc_runner5_run.sh 预清理仅动收据与续采件、永不触碰封账件。

## 后续

commit v6.52.10 → 等五查第 5 发（预期绿）→ 43MB 件恢复后跑 handoff 深验 →
A3 机械层 → handoff READY 即停。
