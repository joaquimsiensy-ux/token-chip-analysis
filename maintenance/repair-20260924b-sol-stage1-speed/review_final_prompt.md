# 工程收官 review 提示词（只读；repair-20260924b Solana −1 提速 → 9.2.0）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程（触及 `.staging_b3` 的用例不要运行；本机结果见各 `*_acceptance.md`）。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放最终答复消息里**。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。
3. 首行固定 `# 收官review：PASS` 或 `# 收官review：FAIL`。判据：**P0/P1 为空才 PASS**。每条发现标 P0/P1/P2/P3 并给可复现依据；PASS 也要列独立验证了什么、没验证什么。
4. 这是软件工程收官正确性审查，不涉及任何系统安全或对抗行为。
## 背景
用户 2026-09-24 四项裁决：①驳回过的 slot 记进共享地图，后案只做一次便宜的 SQD 状态确认就继承；②让 −1 执行者（codex/opus）强制使用共享地图；③Helius 下载开压缩；④同一候选 slot 被 SQD 探两次要修。工程 README `README.md` 记录单序 W3→W1(+W1F)→W4→WR-a→W2→WR-b；每单工单/复核/施工报告/验收/盲审均在本目录（`workorder_*.md`、`review_*_reply_*.md`、`*_done.md`、`*_acceptance.md`、`blind_*_reply_*.md`、`WR-a_formal_entry.md`、`WR-b_formal_entry.md`）。基线 `cc6298b`（v9.1.1），HEAD 为 9.2.0。
## 任务
对 `git diff cc6298b HEAD -- scripts references assets commands-staging SKILL.md VERSION pyproject.toml CHANGELOG.md` 做整体收官审查：
a) **四项裁决是否都真正解决**：①W1 继承路径（`INHERITED_REFUTED`、副本见证、时效、fail-closed 校验）；②W2 `find-known-map`＋split-run/commands 开工硬性；③W3 `curl_json --compressed`；④W4 单次 census。对每项指出实现位置并说明"问题是否真正解决"，不接受"测试通过"作为唯一依据；
b) 跨单一致性：W1 校验器与 W4 修复生产者对 `INHERITED_REFUTED` 的 α/β 规则一致；W2 文档描述与 W1/W4 实现一致（TTL 起点、resume 不加载地图、evidence 摘要同值等）；CHANGELOG 9.2.0 四条与各 `*_done.md` 一致；
c) 登记与正式入口：producer_history 新增六条（repair 四、probe 两）sha 由 `git show` 可复算；`test_producer_registry_current` 0 FAIL；WR-a/WR-b 的 formal_entry 报告所述验收是否与源码入口一致；
d) 回归面：既有无继承路径、旧资产（`assets/sqd-solana-coverage-map/20260827.json`）在新校验器/新 find 下行为；旧 repair 代产物（前代 sha）经认领仍可深验；β 搜索未变；`invariant_scan` PASS；
e) 残余风险与未做项是否如实写明（继承只证块头在/零 nonce；W3 线上收益未记录；案卷侧 PYTHIA 导出待做；旧地图已过期）——不得有"隐含 PASS"；
f) 文档字节预算与 SKILL ≤8,192 B；版本四处 9.2.0。
输出：P0/P1/P2/P3 分级清单（空则写"无"）＋结论。
