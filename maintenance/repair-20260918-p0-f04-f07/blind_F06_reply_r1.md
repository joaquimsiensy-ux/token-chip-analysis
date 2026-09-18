# 盲审 F06：PASS

未发现本段实现错误、既有断言弱化或工单外脚本改动。`invariant_scan.py` 独立实跑通过；主测试因只读沙箱无法创建临时目录，未执行到断言，不计为测试通过。

审查固定为 `4278857..8df17dd -- scripts/`。当前 HEAD 为 `92ff4fe`，已确认其 `scripts/` 与候选提交一致，工单、复核回复、done、RED 证据也与候选提交一致。

**不变量与原反例**

以下生产行号对应 [entity_identity_gate.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/entity_identity_gate.py:162)，测试行号对应 [test_entity_identity_gate.py](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_entity_identity_gate.py:67)。

| 工单要求 | 核验结果 |
|---|---|
| exclude 标签实体不得清空 flag 解除义务 | `280–282` 根据实体成员集合、标签 tier 强制要求 `INFRA_IN_ENTITY`，不依赖自报 `n_flags`。原反例闭合。 |
| INFRA 无 resolution 必须拒绝 | 原检查保留于 `283–284`；测试 `76–83` 覆盖。 |
| INFRA 有 resolution 可以通过 | 新条件对正确 flag 不报错；测试 `85–92` 保留放行断言。 |
| 非实体大户不受新增条件误拦 | 新条件限定 `address in expected_entities`；与 producer `341–342` 的适用对象一致。 |
| 受保护逻辑不变 | 已逐字节还原比较，并核对 AST：`build`、`load_snapshot_binding`、`FLAGS`、`GATE_SCHEMA` 及其他消费分支未改。 |

**六视角**

| 视角 | 结论与代码依据 |
|---|---|
| ① 字段来源 | 通过。成员集合来自哈希绑定的 state（`177–222`）；标签读取行内 `label`（`257`）；所需 flag 由 consumer 重推（`280–282`）。符合工单以已有 `tier=exclude` 标签为前提的范围。 |
| ② 失败分支 | 通过。非法 label、非法 flag 分别已有错误检查（`257–270`）；新增判断用 `isinstance` 短路，违规追加错误。CLI `370–379` 返回非零。HTML 的错误最终在 [build_html.py:489](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/build_html.py:489) 阻止输出；closeout 在 [stage2_closeout.py:493](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:493) 转为 BLOCK。 |
| ③ 存量迁移 | 通过。工单无 §1.4，schema 仍为 `identity_gate_v3`，producer 未变。符合既有 producer 规则且已填写 resolution 的产物继续通过；历史清空 flag 的违规产物将被拒绝。 |
| ④ 同族调用面 | 通过。搜索确认 CLI `check`、[build_html.py:414](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/build_html.py:414)、[stage2_closeout.py:566](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:566) 共用该 validator，未发现另一个 INFRA 校验实现需要同步。 |
| ⑤ producer/consumer 双向一致 | 通过。producer `338–342` 生成的 INFRA 规则与 consumer `280–282` 对应；resolution 仍使用既有机制。新增三个用例与工单逐项一致。 |
| ⑥ 检查点可绕性 | 通过，静态核验。同 schema 手写文件、改文件名后调用 `check`，仍走相同判断。清空 flag 并同步计数不能消除新增错误；缺字段、清空 rows 分别受 `247–249`、`285–287` 拦截。正式 HTML 强制提供 state，并消费固定 gate 路径，改名会导致缺件拒绝。 |

**RED 与测试真实性**

已用 `git show 4278857:scripts/report/entity_identity_gate.py` 读取基线。SHA-256 与 [F06_red_evidence.txt:3](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/F06_red_evidence.txt:3) 完全一致：

```text
62eecf07ccb6ebffc096e493bbc33bdc6e596940e85d83b229ab184530dc1232
```

基线 `273–279` 只对无标签成员重推 flag；完整 exclude 标签配空 flag 不触发该规则，也不触发 resolution 检查。同步计数后返回 `[]`，与 RED 记录一致。

| 新用例 | 基线静态推演 `check` | 修后静态推演 `check` | 判断 |
|---|---:|---:|---|
| 清空 flag/resolution，`n_flags=0` | 0 | 1 | 真正区分改前改后 |
| INFRA、空 resolution | 1 | 1 | 既有拒绝行为回归 |
| INFRA、非空 resolution | 0 | 0 | 合法放行回归 |

夹具调用真实 `replay_pass1.py` 和 receipt emitter，见 [identity_gate_fixture.py:33](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/identity_gate_fixture.py:33)。新用例保留这些绑定，只修改指定行字段。既有测试前 65 行逐字节不变；移除三段新增用例、还原打印文案后，整个测试文件与基线一致，未弱化既有断言。

**回归与实跑范围**

[F06_done.md:118](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/F06_done.md:118) 包含全部八项命令、PASS 尾行和 `exit_code=0`；尾行与对应测试源码相符。这些属于施工记录，本轮独立结果如下：

| §0.8 项目 | 本轮结果 |
|---|---|
| `test_entity_identity_gate.py` | 已尝试，exit 1；在 `:24` 创建临时目录失败，未执行断言 |
| `test_batch17_identity_chain_alias.py` | 未实跑；需要临时目录 |
| `test_round4_identity_emitter.py` | 未实跑；需要临时目录 |
| `test_v2_identity_history.py` | 未实跑；需要临时目录 |
| `test_audit_release_gate.py` | 未实跑；需要临时目录 |
| `test_a4_gate.py` | 未实跑；需要临时目录 |
| `test_stage2_closeout.py` | 未实跑；需要临时目录 |
| `invariant_scan.py` | **实跑 PASS，exit 0** |

主测试的环境错误为：

```text
FileNotFoundError: [Errno 2] No usable temporary directory found ...
```

守卫实际尾行为：

```text
PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=61, formal_entrypoints=61, exceptions=0
```

r1 指出的 F12 例外归属问题已在最新版工单修正。未运行 `run_all.py` 或 `test_stage2_reseal.py`。

**白名单与工单符合度**

完整区间仅含两份脚本和 `F06_done.md`、`F06_red_evidence.txt`，全部属于白名单。`references/`、`SKILL.md`、`commands-staging/` 及其他受保护文件零改动。

生产 diff 精确等于工单指定的五行插入；测试仅增加三段用例及指定打印后缀，没有额外注释、docstring 或空白改动。`scripts/` 的 `git diff --check` 通过。完整区间检查提示 done 的 `70/101/102` 行尾空格，均为报告所保留原始 diff 的空白上下文行，可接受。

全程离线、未修改文件、未 commit，前后工作树均为空。启动上下文自动提供了记忆摘要；本轮未通过工具读取 `~/.codex/`。未读取其他禁读路径；六视角依据使用了任务点名的文档，未开展边界外攻击验收。