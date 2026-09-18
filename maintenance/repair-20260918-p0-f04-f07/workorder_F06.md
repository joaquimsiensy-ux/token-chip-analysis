# 工单 F06（v1）：G8 身份闸消费侧重推公共设施 flag —— repair-20260918-p0-f04-f07 第一段

> 出处：codex 对 7.2.0（311e6c4）的六视角 review F06（P0）：`entity_identity_gate.validate_gate` 只验 flag 属于枚举，对"无标签实体成员"重推 BIG_UNLABELED/PDA_UNRESOLVED，却**不对已带 `tier=exclude` 标签的实体成员重推 INFRA_IN_ENTITY**——把 flag 清空并同步 n_flags 即可跳过 resolution 义务。反例：`review 附录 D repro_core.py` F06 段（真实 replay_pass1/identity snapshot receipt 绑定、余额 100、row label tier=exclude、flag 清空后 `validate_gate` 返回 `[]`）。用户 2026-09-18 裁决：修（威胁模型＝自己人抄近路，不是外人造假）。总原则：**skill 上下文不增**（references/SKILL.md/commands-staging 零改动）；能删不增、能改不增。
> 内容基线：commit `311e6c4`（v7.2.0）；本工单与提示词单独 commit，HEAD 会晚于 311e6c4，但 `scripts/`、`references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md` 与 311e6c4 逐字节相同。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `F06_done.md`：`git status --short`（须为空）和 `git diff --stat 311e6c4 HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。任一不空即停工写 `F06_done_attempt1_stopped.md`。
- 0.2 **禁读** `~/.codex/` 下任何文件（插件启动搜索若已读 memories，在 done 里如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、`maintenance/repair-20260917-p0-four/` 以外的历史 maintenance 目录；禁读 `/Users/uravvv/Desktop` 与 `/Users/uravvv/Documents` 下任何文件。
- 0.3 **白名单**（只允许改/建）：生产 `scripts/report/entity_identity_gate.py`；测试 `scripts/tests/test_entity_identity_gate.py`；本目录新建 `F06_done.md`、`F06_red_evidence.txt`，停工时 `F06_done_attempt1_stopped.md`。RED 取证用内联 Python。
- 0.4 **不改**：`entity_identity_gate.py` 的 producer `build`（`:327-345`，含 `:336-337` 的 INFRA 生成规则）、`FLAGS`（`:89`）、`GATE_SCHEMA`（`:88`，仍为 `identity_gate_v3`——本改动不升 schema）、`load_snapshot_binding`（`:115-159`）、`validate_gate` 其他分支；任何 `references/`、`SKILL.md`、`commands-staging/`、`VERSION`、`pyproject.toml`、`CHANGELOG.md`、`scripts/tests/contract_manifest.json`、`scripts/tests/invariant_manifest.json`；其他测试只跑不改。
- 0.5 行号均指施工前基线；改动前 `grep -n -F '<锚文本>'` 核验恰 1 处且行号一致，不符**停工**不猜改。删除 > 修改 > 新增。
- 0.6 离线；不 commit（Fable 代 commit）、不 push、不部署 `~/.claude/commands/`；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.2 新用例先在改动前跑取 RED 写 `F06_red_evidence.txt`，再改生产代码，再取 GREEN。
- 0.8 不跑 `run_all.py`。定向跑：`python3 -B scripts/tests/test_entity_identity_gate.py`、`test_batch17_identity_chain_alias.py`、`test_round4_identity_emitter.py`、`test_v2_identity_history.py`、`test_audit_release_gate.py`、`test_a4_gate.py`、`test_stage2_closeout.py`（其中 `dry_run_touches_nothing` 依赖外部 worktree 属已知环境项 F12，若仅此项失败注明即可）、`python3 -B scripts/tests/invariant_scan.py`。除注明项外须全 PASS。

## 1. 硬约束

- 1.1 文档三处字节不变：`SKILL.md` 8021、`references/**/*.md` 合计 930061、`commands-staging/*.md` 合计 8798。只用元数据：`stat -f %z SKILL.md`；`find references -name '*.md' -print0 | xargs -0 stat -f %z | awk '{s+=$1} END{print s}'`；`stat -f %z commands-staging/*.md | awk '{s+=$1} END{print s}'`。改后三数贴进 done。
- 1.2 `git diff --stat` 只含 0.3 白名单。
- 1.3 既有用例（`test_entity_identity_gate.py:23-65` 五段断言）不改且全 PASS。

## 2. 逐条施工

### 2.1 `scripts/report/entity_identity_gate.py` —— consumer 对 exclude 标签实体成员重推 INFRA_IN_ENTITY

定位锚：`:273`（锚 `        if address in expected_entities and label is None:`，全文件唯一）；其块 `:274-277` 以 `                errors.append(f'{address} 无标签实体成员必须为 {required}')` 结束（`:277`，唯一）。在 `:277` 之后、`:278`（锚 `        if require_resolved and flag and not str(row.get('resolution', '')).strip():`）之前插入：

```python
        # 与 producer（build，tier=exclude 的实体成员必出 INFRA_IN_ENTITY）对称：consumer 按
        # 绑定标签重推必需 flag，不让 flag 字段自行清空来解除 resolution 义务。
        if address in expected_entities and isinstance(label, dict) \
                and label.get('tier') == 'exclude' and flag != 'INFRA_IN_ENTITY':
            errors.append(f'{address} 公共设施标签（tier=exclude）实体成员必须为 INFRA_IN_ENTITY')
```

说明：①`:267-270` 已保证到达此处时 `flag in FLAGS`；②`:257-260` 已对 `label` 非 null 时要求含 `tier` 键，本检查用 `isinstance(label, dict)` 兜底不重复报错；③`address in expected_entities` 与 producer `:336` 的 `meta['entity'] != '(non-entity big holder)'` 等价（非实体大户不在 expected_entities）；④INFRA_IN_ENTITY 仍需 resolution 由既有 `:278-279` 负责，本条不重复。

### 2.2 `scripts/tests/test_entity_identity_gate.py` —— 新用例

在 `:65`（锚 `        assert gate.check(str(mismatch_path)) != 0, "逐行实体必须与 state 一致"`，唯一）之后、`:67`（锚 `    print("PASS: P1-01 无标签实体成员 + 严格 identity gate schema/计数/唯一性/实体绑定")`）之前，仍在 `with tempfile.TemporaryDirectory() as tmp:` 块内插入三段（都基于 `built` 的深拷贝 `json.loads(json.dumps(built))`，label 改为 `{"name": "public-infra", "category": "dex", "tier": "exclude", "source": "test"}`）：

1. `F06 清空 flag 不得解除 INFRA 义务`：`flag=""`、`resolution=""`、`n_flags=0` → `gate.check(path) != 0`。**RED**（基线 `[]`→exit 0）。
2. `F06 INFRA 无 resolution 仍拒（既有行为回归）`：`flag="INFRA_IN_ENTITY"`、`resolution=""`、`n_flags=1` → `!= 0`。GREEN→GREEN。
3. `F06 INFRA 带 resolution 放行`：`flag="INFRA_IN_ENTITY"`、`resolution="已核：DEX 池地址，已从实体成员剔除"`、`n_flags=1` → `== 0`。GREEN→GREEN。

每段各写独立 JSON 文件（`f06_a.json`/`f06_b.json`/`f06_c.json`）。`print` 行 `:67` 文案追加 `/F06 exclude 标签重推 INFRA`（一行内改）。

RED 证据：改生产代码前用内联 Python 复现用例 1（复制 main 里 build 的四行夹具 `:25-34` 建 gate，改 label/flag 后调 `gate.validate_gate`），把返回值 `[]` 与 `check` 退出码 0 写入 `F06_red_evidence.txt`（含被测文件 sha256）。

## 3. 完成报告 `F06_done.md` 必含

①0.1 两条命令原始输出；②2.1/2.2 `git diff` 原文；③RED 摘要与文件路径；④0.8 各测试结果尾行；⑤1.1 三个字节数；⑥`git diff --stat`；⑦与工单差异/停工点；⑧禁读披露。stdout 首行 `# 施工 F06：完成` 或 `# 施工 F06：停工`。

## 4. 登记不修（`code_change_pending.md`，调度方维护）

- consumer 不重推 `PDA_UNRESOLVED`/`BIG_UNLABELED` 之外、由标签 category（非 tier）推导的风险：现行 producer 也只按 tier=exclude 出 INFRA，producer/consumer 已对称，不扩。
- 人工裁决豁免：协议已有 `resolution` 字段承载，本段不新增豁免通道。
