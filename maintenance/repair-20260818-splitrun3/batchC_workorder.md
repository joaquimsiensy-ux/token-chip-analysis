# 批 C 工单｜版本收口批（v6.50.0 工程）

> 执行者：codex（workspace-write）。工作目录：`/Users/uravvv/.claude/worktrees/tca-splitrun3`。前置：批 A/B 已验收。
> 白名单外改动＝违规。**不 commit**（裁判代 commit）。部署 cp 不在本工单内（合并 main 后在 canonical checkout 做）。

## 白名单（4 个文件）

1. `CHANGELOG.md`
2. `VERSION`
3. `pyproject.toml`（仅 :15 version 行）
4. `SKILL.md`（仅 :23 版本注释行）

## 五栏

① 不变量：版本五处同值 6.50.0（VERSION/pyproject/CHANGELOG 索引行/CHANGELOG 详情标题/SKILL 注释）；CHANGELOG 活跃窗口严格降序。
② 同族清单：`rg -n "6\.48\.1|6\.49\.0|6\.50\.0" VERSION pyproject.toml SKILL.md CHANGELOG.md | head -20` 记录现状。
③ 三件套：changelog_lint 先跑（写入前）再跑（写入后）；test_version_consistency 红→绿（改 VERSION 后其余未同步时应红，全同步后绿——记录实证）。
④ 自审：CHANGELOG 条目不得记任何代币分析结论（红线）；条目内引用的契约 id 必须已在 manifest（docs_lint 悬空引用检查）。
⑤ 归因预判：撞号风险——基线 main=6.48.1，6.49.0 已被 fix/sqd-solana-v4 分支占用（本分支从 main 分叉，本地 CHANGELOG 无 6.49.0 条目，跳号合法：lint 只查降序与撞号不查连续）。

## 施工任务

### T1｜CHANGELOG.md

索引行（:13 上方插入，全角括号格式）：
`- **6.50.0**（2026-08-18）split-run 三段化＋刀 1 外包公告：新增 /token-analyze-3 装配段（−2 收口前移至报告正文＋装配工单，A5 装配独立 Opus 会话）；ET-1 报警证据采集前置 −1（停止线拆采集/定性）；刀 1 机械档扩为 14 项公告＋6 条纪律（唯一权威源）；新契约 CT-SEMANTIC-61/62、CT-BANNED-16，命令四元；版本号跳过 6.49.0（已被并行 SQD 工程占用）`

详情条目（`## [6.48.1]` 上方插入）：
```
## [6.50.0] - 2026-08-18 — split-run 三段化＋刀 1 外包公告体系

- **−3 装配段**：新增 /token-analyze-3 命令＋split-run §3b（A5 装配执行侧：三图/流转图/双 receipt/a5-report-seal/v3/build_html G11/发布闸；建议 Opus 会话）；−2 收口前移＝报告正文亲笔成稿＋四条收口自查＋产 a5_assembly_workorder.json 即停（非正式件无 validator，兜底=既有 A5 链闸；图表基数与工单完备性属文字纪律，残余风险用户拍板接受、首战后评估）
- **ET-1 前置**：−1 停止线"大户报警深挖"拆分——证据采集（保守超集分母、观察事实零定性、落 et1_evidence_packs.json，optional 但存在即入 manifest allowlist）归 −1，归属定性深挖留 −2；−2 冻结后与 packs 双向对账
- **刀 1 公告**：context-discipline 机械档扩为 14 项完整清单＋6 条外包纪律（sealed 禁读/盲化对子代理生效、装配线程不当 A4 怀疑者、非权威中间产物边界、零结果自证、禁手抄、交付自查申报），唯一权威源制；research-workflows §二b 钉法改指针消双源；刀 2/刀 3 编号重号 bug 顺手修复
- **契约与测试**：新增 CT-SEMANTIC-61（token-analyze-3 required a5-report-seal/v3）/CT-SEMANTIC-62（required G11）/CT-BANNED-16（banned A5 seal v2），contract_ids_snapshot 同步 157 条；deploy-sync EXPECTED 与 batch3 gates COMMANDS 扩四元＋−3 四类负例等深
- **版本**：跳过 6.49.0（被并行 fix/sqd-solana-v4 工程占用，避免合并撞号）
- **回归**：run_all 全量 PASS（worktree 内 test_commands_deploy_sync 因部署 cp 待合并后执行而预期红，合并 main 后 cp＋复跑绿）
```
（正文可按实跑结果微调"回归"行的实况措辞，但版本跳号说明与三契约点名不可省。）

### T2｜VERSION → `6.50.0`；pyproject.toml :15 → `version = "6.50.0"`；SKILL.md :23 注释 → `skill-version: 6.50.0`

## 验收命令

```
cd /Users/uravvv/.claude/worktrees/tca-splitrun3
python3 scripts/tests/changelog_lint.py
python3 scripts/tests/test_version_consistency.py
python3 scripts/tests/run_all.py > /tmp/splitrun3_batchC_suite.log 2>&1; echo "exit=$?"; tail -20 /tmp/splitrun3_batchC_suite.log
```
run_all 判定标准：除 `test_commands_deploy_sync.py`（预期红，原因=部署 cp 在合并 main 后执行）外全 PASS。done 报告需列出红项清单证明只有这一项。

## 完成标准

四文件落盘；验收达标；done 报告 `batchC_done.md`。**不 commit。**
