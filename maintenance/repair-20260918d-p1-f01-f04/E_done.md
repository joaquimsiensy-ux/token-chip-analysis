# 施工 E：完成

版本已按工单 E v2 落地为 9.0.1；CHANGELOG 索引与详细条目直接提取工单代码块，逐字插入。仅修改四个白名单文件，另新增本报告。

工作目录：`/Users/uravvv/.claude/skills/token-chip-analysis`。

## 1. 开工检查

```console
$ git rev-parse HEAD
008beb5cf1bba2f63969415f29804ec81f37200d
$ git branch --show-current
main
```

§0 第一项，stdout 为空，退出码 0：

```console
$ git status --short
```

§0 第二项，stdout 为空，退出码 0：

```console
$ git diff --stat 868d3f61 HEAD -- references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md
```

两项均符合开工条件。修改前再次执行，两项仍为空；未以具体 SHA 判定派工基线。

## 2. 四文件 git diff 原文

命令：`git diff --no-ext-diff --no-textconv --no-color -- CHANGELOG.md VERSION pyproject.toml SKILL.md`，退出码 0。

```diff
diff --git a/CHANGELOG.md b/CHANGELOG.md
index 33fe049..8d3392d 100644
--- a/CHANGELOG.md
+++ b/CHANGELOG.md
@@ -10,6 +10,7 @@
 
 ## 版本索引（活跃窗口，新在上；每版一行，详情见下方对应条目）
 
+- **9.0.1**（2026-09-18）codex 9.0.0 六视角 review 两条 P1 修复（既定契约内加固，不改任何 schema/键，故记修版本）：F04 `camp_spec.validate_camp_spec` 对 EVM 链族拒 spec 显式配置「散户」（引擎残差桶；原先 replay_pass2/replay_duck 对显式散户同日 append 两次、rc=0 产坏形状序列，靠下游长度检查兜底）；F01 `price_check._load_series` 任一点非有限或非正即 `[fatal]` 退出 1、第二源非有限规范化为 None 走 SKIP、收据 `allow_nan=False`（原先 NaN 主价判 PASS 并写含 NaN 的收据），`stage2_closeout.price_receipt_errors` 逐点按 main/second_price 同规则重算 status 并核声明、主价非有限正数即拒（原先只核 status 集合）。references/SKILL/commands 零改动。F02/F03/F05–F10 用户裁决本轮不修。
 - **9.0.0**（2026-09-18）codex 8.0.0 六视角 review 三条修复（P1×2、P2×1），−2 收口价格双源收据契约收紧（旧收据/纯申报/FAIL 一律拒、存量案须重跑 price_check 迁移，故记主版本）：F04 `RpcPool._one` 对无 error 且缺 `result` 键的 JSON-RPC 响应判失败（原先记 `ok=True, result=None`，`rpc_batch getcode` 再把 None 折成 `0x` 记 EOA、摘要"失败 0"），getcode 只认 `0x`/偶数长度十六进制串，其余记 error 退出 1；F05 `stage2_closeout` 新增 `price_receipt_errors`——按 points 以 price_check 同规则重算 verdict 并要求一致、只放行 PASS/WARN（WARN 记 NOTE）、收据新字段 `price_file_sha256` 须等于 `bindings.price_source.sha256`、内联 `dual_source_check` 须带 receipt 引用（原先只核 {path,sha256} 在场，FAIL 收据绑进工单仍 PASS）；F02 `facts_inputs.circulating_supply {raw,asof,source}` 可选通道→`facts.token.circulating_supply_raw/circulating_supply_source`，扁平键 `circulating_supply_raw` 拒，closeout NOTE 记口径（原先流通量分母无任何生产者，"必画"按流通量口径永不触发）。references/SKILL/commands 零改动。F01（日线取最高价）用户裁决不修；F03 峰值 override 沿 8.0.0 裁决不修；Q13 三端点 failover 轮转、Q14 ALL_SKIP 人工回退口子登记待裁决。
 - **8.0.0**（2026-09-18）codex 7.2.1 六视角 review 两条 P0 修复，EVM 观测 bundle schema 升 v2（旧 v1 一律拒收，故记主版本）：G1 图 2 校验器 `fig2_check_errors` 增必画下限——label 以 项目方/大庄/小庄/离场庄 起头的实体须各有一条线，缺线/重复线/空 series 一律拒（原先空 series 可 PASS 0 条），closeout 选材复用同一规则、发布闸重算自动继承；G2 EVM 观测 `observe_evm_supply` 在冻结块补第 4 笔 eth_call `decimals()`（uint8），transcript 8→9 笔，bundle `supply.decimals`，accounting 写 `checks.decimals`＝观测值，shared receipt 核 checks≡bundle，发布闸 `check_facts_decimals` 两链族统一读 `accounting.checks.decimals` 并对 EVM 另核 verify_recon config.decimals≡观测（原先拿 config 自报当"链上观测"）。references +15 B（仅补 `decimals()` 一词），SKILL/commands 不变。峰值 override 自写证据与 metrics 自报按"威胁模型＝自己人"裁决登记残余不修。
 - **7.2.1**（2026-09-18）codex 7.2.0 六视角 review 主轨四条 P0 修复（闸从信自报改为按实物核）：F06 G8 身份闸消费侧对带 `tier=exclude` 标签的实体成员重推 `INFRA_IN_ENTITY`（清空 flag 不再解除 INFRA 义务）；F04 new-analysis 闸对图 2 收据在两输入实物在场时用 `fig2_check_errors` 发布期重算（收据自报 PASS 不作数）；F07 日级峰值闸按 summary/needs/followup 三件任一定位产物目录（改名 summary 不再绕闸），followup 须绑定当前 `replay_duck.py` sha、案内唯一 channels 实物、`value_type`、`count`；F05 facts 每实体 `peak_raw≤total_raw`、`peak_overrides` 证据须为 `{entity_id:{peak_raw,peak_date}}` 且与申报相等、`peak_date` 严格 ISO（provenance 当前锚点显式给出 date 时不得晚于该日）、闸侧 `token.decimals` 绑链上观测。references/SKILL/commands 字节全部不变。
@@ -94,6 +95,16 @@
 
 更早版本（6.20.0 及以前）详见 `archive/CHANGELOG-archive.md`。
 
+## [9.0.1] - 2026-09-18 — codex 9.0.0 六视角 review 两条 P1 修复（EVM 显式散户桶硬拒 / 价格非有限值 fail-closed＋收口逐点重算）
+
+- **出处与裁决**：codex 对 9.0.0（868d3f61）的六视角 review 判 PASS 需修复轮（P0 0 / P1 4 / P2 6 / P3 0）。用户 09-18 裁决：①只修 F01/F04；②原则＝skill 上下文不增、能删不增能改不增；③调度方只写工单/验收/调度，代码全由 codex 施工，codex 常规盲审、三次 FAIL 才换 opus；④版本 9.0.1。修的终点＝review 附录 A 两反例（`price_nan`、`retail`）在 HEAD 上必变拒，由盲审方与收官 review 独立复现，不以盲审 PASS 为准。
+- **F04**（`lib/camp_spec.validate_camp_spec`）：`chain_family == "evm" and camp == "散户"` → 既有 `_fail`（`[camp-spec] ` 前缀、exit 2），文案指明残差桶语义与改法；docstring 边界段补一句。四入口调用点、签名、返回形状不变；Solana 不拒（`build_evolution` 以「散户」为默认桶＋标量残差无重复 append，LAYOFF 案 `entity_camps.json` 27 处显式「散户」为存量；`replay_edges` producer 分列显式散户与动态桶、consumer `SOL_DYNAMIC_BUCKET_MERGE` 并桶，显式散户会触发既有末点对账冲突——登记不修）。不改两 EVM 引擎 append 结构（fail-closed 拒配置更小）。测试 `test_repair_batch_c`：`t_f05_unit` 加 EVM 拒/Solana 不误杀 2 check，`t_f05_evm_engines` 加 duck（exit 2 且全新目录不产 `camp_series.json`）/pass2（exit 2）各 1 check。
+- **F01**（`prices/price_check.py`；`report/stage2_closeout.price_receipt_errors`）：生产者 `_load_series` 解析后任一点 `not (isfinite(p) and p > 0)` → `[fatal] 价格文件含非有限或非正价格 N 点…` 退出 1（CSV/JSON/溢出 `1e309` 全覆盖，早于任何写盘）；`price_check.py:179`（施工前基线 :175）判点前 `p2 = p2 if p2 is None or isfinite(p2) else None`（第二源非有限＝对照不可得，走既有 SKIP，收据 `second_price=null` 可序列化）；`json.dump(..., allow_nan=False)` 纵深防御。消费者逐点：`main_price` 须有限正数（否则拒 `points[i].main_price`），`second_price` None/非有限/≤0 → SKIP，否则 `round(|a−b|/((a+b)/2)*100, 2)` 对 5/15 阈值判 PASS/WARN/FAIL，与自报 `status` 不一致拒 `points[i].status`；阈值常量 `PRICE_WARN_PCT/PRICE_FAIL_PCT` 复制自生产者（report 层不 import requests 类脚本），两端相等由测试断言守。汇总 verdict 规则、`price_file_sha256` 绑定、12 项 checks、返回类型不变；不新增收据键。兼容范围：主价格文件各点有限正数、第二源 None 或有限数的输入行为逐字不变；主价 0/负价由基线 SKIP 改为 fatal 属预期变化。测试 `test_stage2_closeout.price_receipt_content_enforced` 加 6b–6g 六段（生产者 NaN/0 fatal、第二源 NaN→ALL_SKIP 可序列化、收据主价 NaN/0 拒、第二价改 2.0 拒、阈值相等＋WARN 边界 1.0/1.052 手改拒）。
+- **工艺**：两份工单先 codex 只读复核（并行）：F04 r1 退回 4 条→v2 r2 通过；F01 r1 退回 5 条→v2 r2 退回 1 条→v3 r3 通过（十条意见全部亲核代码属实后吸收，含 R1 揭穿的第二源 NaN 撞 allow_nan 抛异常、消费者与生产者非正主价口径不一、6d 守不住阈值漂移、存量核验须用真实解析规则）。施工串行 codex `--write`：F04 attempt1 完成；F01 attempt1 按纪律停工（调度方在派工后写入未提交的盲审提示词草稿致 §0.1 树不干净——教训：施工期间对仓库零写入）、attempt2 `--resume-last` 续跑掉回只读沙箱再停工（教训：停工后一律 `--fresh` 重派）、attempt3 完成。每段 Fable 本机验收（diff 与工单逐字对照、RED 分布、定向测试、字节三处）后 commit，再 codex 常规盲审：F04 r1 PASS（反例独立复现 HEAD 拒×2/基线 RED×2/合法产物逐字节一致；6 项沙箱临时目录阻塞由本机 7/7 补验）；F01 r1 PASS（反例独立复现：三天 NaN 及首日 inf/0/−1 主价在 HEAD 均退出 1、无收据、不调第二源；第二源 NaN/inf → 完整收据 `second_price=null`、ALL_SKIP 退出 3 无异常；消费者对 NaN/0 主价、第二价改 2.0 伪报 PASS、WARN 边界 1.0/1.052 伪造 PASS 均拒；基线 6b–6g 逐段 RED；15 组合法输入退出码/stdout/收据字节与基线相同；两端偏差表达式 AST 相同、阈值邻界 8 例一致；5 项沙箱临时目录阻塞由本机 6/6 补验含 `test_stage2_closeout` 30/30）。收官 codex review r1 通过（`final_review_reply_r1.md`：`price_nan` 五组输入——四组坏主价（三天 NaN / 首日 inf / 0 / −1）基线 rc=0 写收据、HEAD `[fatal]` 退出 1 不写收据，第二源 NaN 基线收据含 NaN、HEAD 生成完整 ALL_SKIP 收据退出 3；五组收据——主价 NaN、主价 0.0、第二价 2.0 伪报 PASS、真实 WARN 收据全改 PASS 四组基线放行、HEAD 拒，真实 1.0/1.052 WARN 收据两版本均放行并记 NOTE；`retail` 两引擎基线「散户」长度 4 复现同日重复 append、HEAD exit 2 无 `camp_series.json`，Solana 与三组合法 EVM spec 在两版本逐字节相同；白名单恰五文件 +78/−5、三处字节不变、两段文件集合交集为空、invariant_scan PASS；7 项沙箱临时目录阻塞由本机 run_all 补验，见 `fable_local_acceptance.md` §3）。
+- **字节与测试**：references 930076、SKILL.md 8021、commands-staging 8798 三处零改动（契约由 CHANGELOG 与 docstring 承载；`invariant_manifest`/`contract_manifest` 不动，`invariant_scan` 两段前后均 PASS）。scripts 改动五文件：F04 camp_spec.py/test_repair_batch_c.py（+19/−1）；F01 price_check.py/stage2_closeout.py/test_stage2_closeout.py（+59/−4）。本机验收记录见同目录 `fable_local_acceptance.md`（命令、被验提交、退出码、尾行、worktree 提交；原始 stdout 在 `fable_run_all_84e70e5.log`/`fable_f04_local_tests.log`/`fable_f01_local_tests.log`）：`run_all` 于 84e70e5 上 PASS 151 / FAIL 0、`RUNALL_EXIT=0`（`MPLCONFIGDIR=$HOME/.matplotlib` 下，含 `test_stage2_reseal` 21/21，验收 worktree `/tmp/w3_acceptance` 同步 84e70e5）；九项守卫（`changelog_lint`、`docs_lint --all`、`test_version_consistency`、`invariant_scan`、`test_batch4_invariant_guards`、`test_exemption_guards`、`test_g3_docs_guards`、`casebook_lint`、`fixtures_lint`）于 268026c 上 9/9 rc=0。
+- **档位与存量说明**：9.0.1（修）——不改任何 schema/键。存量核验（调度方本机，真实解析规则）：案卷 28 个可解析价格文件 0 个非有限/非正点；案卷不存在任何 `price_check.py` 生成的收据（0 份含 `points`），故消费者收紧无迁移对象；EVM 正式案 spec 从未显式配置「散户」（review 全量检索记录）。APU 0914 案自定义收据仍按 9.0.0 Q8 在进 −3 时重跑。
+- **成本-质量指标**：生产逻辑文件 3（camp_spec、price_check、stage2_closeout）、新公开入口 0、新增产物输出键 0、新增 SUITE 入口 0；外部网络调用 0（第二源全部替身）；不运行真实案卷判断链，判断结论不自动变更。
+
 ## [9.0.0] - 2026-09-18 — codex 8.0.0 六视角 review 三条修复 P1×2、P2×1（RPC envelope 缺 result / −2 收口真读价格双源收据 / 流通量声明通道）
 
 - **出处与裁决**：codex 对 8.0.0（8b041842）的六视角 review 判 PASS 需修复轮（P0 0 / P1 5 / P2 2 / P3 1）。调度方对照三轮 review 归因：F02 为 7.2.0 R07 修复带入的半成品（`stage2_closeout.flow_selection_errors` 早已按流通量口径判"必画"，但 `facts_gate` 从未产出该分母）；F05 为 7.0.4 引入时即如此；F04 为 3.16.0 起历史漏审。用户 09-18 裁决：①F01（日线取最高价当收盘）影响面有限不修；②修 F02/F04/F05；③原则＝skill 上下文不增、能删不增能改不增；④调度方只写工单/验收/调度，代码全由 codex 施工，codex 常规盲审、三次 FAIL 才换 opus；⑤版本升主 9.0.0；⑥APU 0914 案暂不重跑 price_check（进 −3 时补）。修的终点＝review 附录 C 三反例（`rpc_missing_result`、`price_gate_content`、`flow_migration`）在 HEAD 上必变拒，由盲审方与收官 review 独立复现，不以盲审 PASS 为准。
diff --git a/SKILL.md b/SKILL.md
index 423ec9e..4f920ad 100644
--- a/SKILL.md
+++ b/SKILL.md
@@ -20,7 +20,7 @@ description: >-
   只查价格/K线/热榜/新币列表不要用本 skill。
 ---
 
-<!-- skill-version-source: VERSION; skill-version: 9.0.0 -->
+<!-- skill-version-source: VERSION; skill-version: 9.0.1 -->
 
 # 代币筹码分析（Token Chip Analysis）
 
diff --git a/VERSION b/VERSION
index f7ee066..37ad5c8 100644
--- a/VERSION
+++ b/VERSION
@@ -1 +1 @@
-9.0.0
+9.0.1
diff --git a/pyproject.toml b/pyproject.toml
index a0b04c3..8bcc6b0 100644
--- a/pyproject.toml
+++ b/pyproject.toml
@@ -12,7 +12,7 @@
 
 [project]
 name = "token-chip-analysis"
-version = "9.0.0"
+version = "9.0.1"
 description = "链上代币筹码分析工作流（数据引擎与工具脚本）"
 requires-python = ">=3.14"
 dependencies = [
```

## 3. 版本一致性检查

```console
$ python3 -B scripts/tests/test_version_consistency.py
PASS: M-03 version metadata consistent at 9.0.1
```

退出码 0；上方 PASS 行即输出尾行。

## 4. SKILL.md 改前后字节数

改前：

```console
$ wc -c SKILL.md
    8021 SKILL.md
```

改后：

```console
$ wc -c SKILL.md
    8021 SKILL.md
```

前后均为 8021 字节。`VERSION` 保持单个 LF；`pyproject.toml` 仅第 15 行、`SKILL.md` 仅第 23 行变更。CHANGELOG 活跃详细条目从 79 增至 80（仅计数本文件，未运行 lint）。

## 5. git diff --stat

```console
$ git diff --stat
 CHANGELOG.md   | 11 +++++++++++
 SKILL.md       |  2 +-
 VERSION        |  2 +-
 pyproject.toml |  2 +-
 4 files changed, 14 insertions(+), 3 deletions(-)
```

恰为四个白名单文件。新增的本报告未暂存，不计入上述 tracked diff；`references/`、`scripts/`、`commands-staging/` 未修改。`git diff --check` 退出码 0、stdout 为空。

`changelog_lint` 与 `docs_lint --all` 按工单由调度方本机执行，本轮未运行。

## 6. 执行纪律与禁读披露

全程离线；未 commit/push，未执行 stash/checkout/reset，未删除文件。除四个白名单文件和本报告外，未修改或新增仓库文件。

未读取 `~/.codex/`（含 memories）、`archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本工单目录以外的历史 maintenance 目录、`/Users/uravvv/Desktop` 或 `/Users/uravvv/Documents` 的内容。references 字节核对仅使用文件元数据，按既有验收记录的 `references/**/*.md` 口径为 930076 字节，未读取其中任何文件内容。
