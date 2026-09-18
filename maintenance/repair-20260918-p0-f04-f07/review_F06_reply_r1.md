# 工单F06复核：退回

退回 **1 项验收说明问题**。生产修法、定位锚点及三个用例的断言设计未发现错误；不需要新增 `invariant_manifest.json` 登记。

**F06-R1-01：§0.8 的 F12 例外不属于所列定向测试**

工单位置：[workorder_F06.md:15](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F06.md:15)。

事实：

- §0.8 列出 `test_stage2_closeout.py` 等定向测试，随后写“其中 `dry_run_touches_nothing`……若仅此项失败注明即可”。
- 所列定向测试中没有这个用例。实际归属的 `grep -n -F` 输出为：

```text
scripts/tests/test_stage2_reseal.py:
516:def dry_run_touches_nothing(cases):

scripts/tests/run_all.py:
210:SUITE += ['test_stage2_reseal.py']
```

- 其限制还包括旧验收白名单。[test_stage2_reseal.py:604](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_stage2_reseal.py:604) 的 `allowed` 不含 F06 的两个代码文件及两个交付文件；`:611` 明确执行：

```python
assert overlay <= allowed, "白名单外变更，停止验收：" + str(sorted(overlay - allowed))
```

因此，即使外部 worktree 检查通过，按工单保留 F06 未提交改动时，全套测试仍存在被该断言拒绝的路径。这属于已有 F12 验收约束，不能归为新增 consumer 逻辑回归。

**修订建议：**删除 §0.8 的这个括号，明确所列定向测试全部须 PASS；将 F12 说明放到调度方全套验收说明中，准确标为 `test_stage2_reseal.py::dry_run_touches_nothing`，说明外部 worktree 和 overlay 白名单限制。

**其余实际核验结果**

1. **锚点与行号**

   工单显式给出的五条定位锚均经 `grep -n -F` 核验，恰好一处：

   | 文件 | 实际行号 |
   |---|---|
   | `entity_identity_gate.py` | `273`、`277`、`278` |
   | `test_entity_identity_gate.py` | `65`、`67` |

   其余引用位置也逐段核对一致：生产文件 `88/89/115/257–260/267–270/327–345/336–337`；测试文件 `23–34/42`。

2. **插入逻辑**

   - 将工单代码仅在内存中插入后，AST 解析成功，新增判断直接位于 `for i, row in enumerate(rows)` 循环体内。
   - `expected_entities/address/label/flag` 分别已在 `213/234/257/267` 定义。
   - 非 dict 标签由 `isinstance` 短路；缺 tier 的 dict 得到 `None`。这两类不会新增重复错误或抛异常。
   - 非实体大户不在 `expected_entities`，即使 `tier=exclude` 也不被新增规则拦截，与 producer `:336–337` 对称。
   - 正确 INFRA flag 的 resolution 仍由原 `:278–279` 检查。

3. **全部 `tier=exclude` 夹具**

   已执行指定的 `grep -rn "exclude" scripts/tests/*.py`，其中实际设置 tier 的位置如下：

   | 位置（均在 `scripts/tests/`） | 实体成员及影响判断 |
   |---|---|
   | `test_arbitrum_label_consumers.py:29` | 标签/聚类测试，CEX 被排除；不进入 G8 |
   | `test_batch1_risk_flags.py:24` | 标签行默认参数，无 G8 实体行 |
   | `test_benchmark_labels.py:29` | 标签召回测试，无 G8 实体行 |
   | `test_cluster_quality.py:43` | CEX 在 `:129` 被放入实体成员，但测试调用 `accumulate_offenders.py`，不调用 G8 |
   | `test_label_snapshot_roundtrip.py:33` | 标签构建测试，无 G8 实体行 |
   | 同文件 `:36` | 同上 |
   | 同文件 `:40` | 同上 |
   | 同文件 `:43` | 同上 |
   | 同文件 `:47` | 同上 |
   | 同文件 `:50` | 同上 |
   | `test_roundtrip_check.py:23` | 标签表往返测试，无 G8 实体行 |

   上述位置均未发现因新增条件而变红的路径。

4. **指定关联文件及同族入口**

   | 文件 | 核验结论 |
   |---|---|
   | `identity_gate_fixture.py` | 生成绑定、调整 share，不改 label/flag |
   | `test_audit_release_gate.py` | 未发现受影响的 exclude 实体行 |
   | `test_a4_gate.py` | `:387/:584` 使用 `tier=identity` |
   | `test_stage2_closeout.py` | `:69` 使用 `tier=identity` |
   | `test_batch17_identity_chain_alias.py` | `:46` 的 `whale_groups=[]`，新增判断不触发 |
   | `test_round4_identity_emitter.py` | 检查 receipt 和 `load_snapshot_binding`，不改该路径 |
   | `test_v2_identity_history.py` | 检查采集器 identity/provenance，不是 G8 行校验 |

   另核过 `test_build_html.py`、`test_review_20260804_p201.py` 等调用者。CLI、`build_html.py:414`、`stage2_closeout.py:566` 共用 `validate_gate`，修复可覆盖这些入口。

5. **三个用例：静态推演成立，未实跑完成**

   | 用例 | 基线 `check` 返回值 | 按计划修改后 | 断言变化 |
   |---|---:|---:|---|
   | exclude 实体清空 flag/resolution，`n_flags=0` | `0` | `1` | RED → GREEN |
   | INFRA 无 resolution | `1` | `1` | GREEN → GREEN |
   | INFRA 带 resolution | `0` | `0` | GREEN → GREEN |

   已尝试运行：

   ```text
   python3 -B scripts/tests/test_entity_identity_gate.py
   ```

   在测试 `:24` 创建临时目录时退出，错误为：

   ```text
   FileNotFoundError: [Errno 2] No usable temporary directory found ...
   ```

   尚未执行任何断言；临时目录复现用例 1 **未实跑**。此环境限制不计为工单缺陷。

6. **清单、登记与完整 suite**

   - 除上述 §0.8 问题外，§0.4、§1、§4 与修法一致；原五段断言不需修改。
   - 元数据实核：`8021 / 930061 / 8798`，与 §1.1 一致。
   - 实际调用 `invariant_scan.scan_python` 比较原文与内存中的拟修改文本，结果完全一致：

     ```text
     producers: identity_gate_v3
     consumers: identity-holder-snapshot/v2, identity_gate_v3
     transports: []
     atomic writes: []
     ```

     新错误文案不产生登记项。
   - 未发现新增 consumer 条件导致既有用例变红的路径；全套测试的 F12 限制见退回项。未运行 `run_all.py`，不宣称全套 PASS。

全程离线、未修改文件，前后工作树均为空。复核期间 HEAD 从 `4931098` 前进至 `dae44c3`；已确认本工单及所核代码、约束文件未变化，`scripts/` 仍与 `311e6c4` 一致。