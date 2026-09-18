# 工单 E 复核提示词（只读，r1）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260918-p0-f04-f07/` 与 `maintenance/repair-20260918b-p0-fig2-decimals/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`（统计大小只用 stat）。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单E复核：通过` 或 `# 工单E复核：退回`。退回时逐条给出：编号（E-R1-NN）、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。
3. 这是对**版本登记文案**的复核，不是攻击式验收，也不重新评价 G1/G2 两段施工本身。专门核每个"来源/观测"断言是否与生产者代码写出点一致（`evm_observation.py` 的 `SEL_DECIMALS` eth_call 与 `supply.decimals` 写出、`accounting_gate.py` 的 `checks.decimals` 写出）。

## 任务
复核 `maintenance/repair-20260918b-p0-fig2-decimals/workorder_E_version.md`（v1）。工作目录＝本仓库根（HEAD 含 G1 7a21bf1、G2 9ecc962 两段落地与两份盲审 PASS 报告）。逐项核：
a) 锚点：CHANGELOG.md :13 索引首行与 :95 详细段标题 `grep -n -F` 恰 1 处且行号一致；VERSION、pyproject.toml:15、SKILL.md:23 当前值均为 7.2.1；`7.2.1`→`8.0.0` 等长故 SKILL.md 字节不变。
b) **文案与仓库事实逐项核对**（本单重点，任何不符退回本单而非改事实）：两段施工 commit 各自 `git show --stat` 触及文件与文案相符（G1 4 文件；G2 19 文件＝6 生产＋8 测试＋2 清单＋3 文档）；引用的函数/常量/字段名（`FIG2_REQUIRED_LABEL_PREFIXES`、`fig2_required_entity_ids`、`fig2_check_errors`、`fig2_selection_errors`、`check_figure2_receipt`、`observe_evm_supply`、`SEL_DECIMALS`＝`0x313ce567`、`validate_evm_observation_bundle`、`validate_accounting_receipt`、`check_facts_decimals`、`checks.decimals`、`supply.decimals`、`_g1_case_1..4`）在源码中存在且行为与描述一致；错误文案原文（"线重复出现"、"图 2 缺必画实体线"、"与链上观测 … 不一致——对账 human 供应量级自报"、"checks 非对象"）与源码一致；transcript 方法序 9 笔与 `_validate_transcript` 一致；schema 字面量 18 处（scripts 8＋invariant_manifest 6＋contract_manifest 1＋references 3）用 `grep -rn --exclude-dir=__pycache__ 'evm-observation-bundle/v2'` 计数核实；字节（references 930076、SKILL 8021、commands-staging 8798，只 stat；references 相对 7.2.1 基线 930061 恰 +15 且只在 `data-pipeline-evm-recon.md`）；台账 `code_change_pending.md` 含 Q1–Q8 且 Q1/Q2/Q5/Q6 表述与文案一致；盲审轮次与 `blind_G1_reply_r1.md`/`blind_G2_reply_r1.md` 首行一致；复核轮次与 `review_G1_reply_r1..r2.md`、`review_G2_reply_r1..r4.md` 文件数及各首行"通过/退回"一致；迁移三类分述与 `receipt_validate.py:115-120`、`shared_release_receipt.py:75/:2145` 一致；用户裁决引述与 `ruling_20260918.md` 一致。
c) 版本号档位：用户已裁决 8.0.0（`ruling_20260918.md` 追加段），本单不再讨论档位；只核"档位与迁移说明"里给出的 8.0.0 依据（bundle schema v1→v2 不兼容）是否与 CHANGELOG 头部规则一致、表述是否准确。
d) 体例：索引行与详细段格式与 7.2.1/7.2.0 条目一致（日期、破折号、粗体小节、成本-质量指标）；`changelog_lint` 改后应 78 条无撞号倒排；`test_version_consistency`、`docs_lint --all` 无必红点。
e) 是否遗漏应登记事项（如 G1 对 closeout 的复用、G2 对非标 ERC20 的目标行为、Solana 侧另单）；有无不该写进 CHANGELOG 的代币分析结论（红线）。
