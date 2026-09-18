# 盲审 G1：PASS

指定范围 `git diff 40c090a..7a21bf1 -- scripts/` 未发现需退回的问题。原始反例已独立复现并确认关闭。当前 HEAD 为 `93419af`，其 `scripts/` 与 `7a21bf1` 无差异。

a）终点判据已满足。

使用用户指定的原始 facts：总量 `1000`、decimals `0`、`e1.label=大庄#1`、当前量 `100`、峰值 `200`、地址 `["A"]`，series 为 `[]`。

沙箱禁止创建临时文件，因此抽取并执行未改写的真实源码函数，包括 `main`、`mode_check`、`_write_check_receipt`、`fig2_check_errors` 和消费者；仅将文件读写、`fsync/replace` 接到内存文件系统。结果：

| 检查 | 基线 `40c090a` | HEAD |
|---|---|---|
| `check` 返回值 | `0` | `1` |
| 真实收据函数生成的 verdict | `PASS` | `FAIL` |
| 同 schema、真实输入哈希的手写 PASS 收据 | 消费者 `errors=[]` | 消费者拒绝 |

HEAD 消费者实际错误：

```text
figure2 发布期重算: 图 2 缺必画实体线 ['e1']（label 以 项目方/大庄/小庄/离场庄 起头的实体必须各有一条线；空 series 不得放行）
```

正式 HTML 路径也闭合：[build_html.py:433](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/build_html.py:433) 无条件执行正式发布闸并收集错误；[build_html.py:489](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/build_html.py:489) 在创建临时输出文件前退出 `1`。这是静态核验，本轮未执行完整 HTML 构建。

b）工单 §2 逐条符合。

| 条款 | 核验结论 |
|---|---|
| §2.1 共享规则 | 四种前缀、去首尾空白及实体键集合均按工单实现；观察实体、刷量地址不进入必画下限。 |
| §2.2 覆盖与重复 | 匹配后按事实实体 ID 去重；未知线不进入 `seen`；坏 pct 仍拒绝；末尾检查必画集合差集。 |
| §2.3 closeout 复用 | 两入口确实调用同一个 `fig2_required_entity_ids`，没有保留第二份图2前缀规则。 |
| §2.4 两条新增断言 | 空序列、重复线均能区分改前和改后。 |
| §2.5 四组用例 | 消费者在断言前执行；非空缺线被拒、补齐放行；非必画空序列保持通过。 |

同源调用点分别为 [figures_from_facts.py:351](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/figures_from_facts.py:351) 和 [stage2_closeout.py:177](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/stage2_closeout.py:177)。closeout 原有的有效标签、非空选材等额外约束仍保留；“同源”指必画集合规则一致。

另以 **192 组输入**执行新旧 `fig2_selection_errors`，`errors/notes` 完全相同。返回类型、非 list 固定错误句、装载异常转换及工单禁止修改的六个函数均核验保持不变。

c）六视角结论。

| 视角 | 结论与核验依据 |
|---|---|
| ① 字段来源 | 必画集合取自 `Facts.entities`；发布消费者重读并校验输入哈希，不信收据自报 PASS。`facts_gate` 从 `facts_inputs.entity_labels` 生成标签，发布期再重建 facts 比对。按标签而非 tier/category 判定属于 §4 明示边界。 |
| ② 失败分支 | 空序列、缺线、重复线均进入 FAIL 收据和非零返回分支；消费者重算错误继续传到 HTML 写入前退出。非有限数、空 pct、错误终值仍拒绝。 |
| ③ 存量迁移 | schema 仍为 v1。旧 PASS 若绑定缺线或重复线序列，会被新消费者重算拒绝；完整合法序列仍通过。§4 的重装配→重跑 check→更新受影响下游封口路径成立；是否重建某份封口取决于其实际绑定。 |
| ④ 同族调用面 | 已搜索并核查 `mode_check`、`check_figure2_receipt`、`fig2_selection_errors`、`fig2_series_errors`、`build_fig2_series` 及正式发布调用点。closeout 的序列检查也调用同一校验器；流转图自身规则未被误改。 |
| ⑤ 双向一致 | producer、发布 consumer 和 closeout 使用共同规则；工单、实现、测试一致。`fig2-series` 保留装配指定子集的职责，完整性由后续 check/发布闸核验。 |
| ⑥ 检查点可绕性 | 内存实测：手写同 schema PASS、序列文件改名、清空收据绑定、清空线标识或 pct、清空 closeout 必画声明、id/label 混用重复线均不能绕过。有效 ID 的展示标签改名正常通过；仅改标签导致无法匹配则拒绝。 |

限定说明：把事实源标签正式改成非必画前缀，会按工单规则退出必画集合；本段没有承诺从其他分类字段反推必画资格。只改单份 facts 的标签、实体集合，则由既有发布期重建比对约束。PNG 是否实际使用该序列仍是既有范围边界。

d）RED 与测试真实性通过。

- `G1_red_evidence.txt` 的六个源码哈希均与对应基线或新增测试文件吻合。
- `git show 40c090a:<path>` 确认基线没有覆盖检查和去重检查，空序列返回 `([], 0)`，重复线可计为两条成功线。
- 内存执行新增测试的真实 AST，独立得到：**基线 7 RED＋5 GREEN；HEAD 12 GREEN**，与记录一致。
- 去除本轮新增测试后，两份测试文件的剩余 AST 与基线完全一致，未弱化既有断言。

e）回归证据已核验，区分如下。

`G1_done.md` 引用的 **10 份原始日志全部在场，SHA-256 全部匹配，成功尾行全部吻合**。

| §0.8 测试 | 已核对的日志结果 | 本轮完整实跑 |
|---|---|---|
| `test_figures_from_facts.py` | PASS | 未跑 |
| `test_repair_batch_c.py` | PASS，259 checks | 未跑 |
| `test_stage2_closeout.py` | 28/28 PASS | 未跑 |
| `test_a4_gate.py` | 23 项通过 | 未跑 |
| `test_repair_batch_d.py` | 全部通过 | 未跑 |
| `test_review_20260804_p105.py` | PASS | 未跑 |
| `test_repair_batch_b.py` | 41/41 | 未跑 |
| `test_audit_release_gate.py` | PASS | 未跑 |
| `test_repair_g1_cross_target.py` | PASS | 未跑 |
| `invariant_scan.py` | PASS | **实跑 PASS，rc=0** |

前九项需要写入临时夹具、图片或收据，受只读沙箱限制未整跑；相关 G1 函数及新增断言已按上述方式内存执行。`test_stage2_reseal.py` 仅静态追踪，未实跑。

f）范围与工单符合度。

- `scripts/` 差异恰为四个白名单文件，**132 行新增、4 行删除**；`git diff --check` 通过。
- 生产逻辑、注释/docstring、空白及测试新增均可对应工单 §2，未发现范围外源码改动。
- `references/`、`SKILL.md`、`commands-staging/` 以及版本、CHANGELOG 等禁改路径均无差异。
- **完整提交并非只含 G1 白名单**：除两份施工证据外，还新增 `maintenance/repair-20260918b-p0-fig2-decimals/review_G2_reply_r2.md`。done 已披露该文件非施工者创建。它在本次明确限定的 `scripts/` 审查范围之外，可作为文档范围差异接受；不能据此宣称整个提交严格只有 G1 白名单。未读取其内容或复核 G2。

全程离线、只读，未改文件、未提交；结束时工作区干净。未读取 `~/.codex/`、memories 或指定禁读目录。
