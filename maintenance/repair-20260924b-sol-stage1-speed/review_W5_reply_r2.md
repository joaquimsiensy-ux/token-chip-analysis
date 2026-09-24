# 工单W5复核r2：退回

**仅剩 1 项必改：§0.7 给出的临时目录保留方法无效，仍会触发自动批量删除。** 六处替换锚点、退出码文案、CHANGELOG 事实及字节预算均通过。

**一、r1 三条必改的吸收情况**

| r1 必改 | r2 核验 |
|---|---|
| W4 明确三个比较关系 | 已完整吸收。事实段及 §2.6 均正确区分 header 三方、transactions 两方、instructions 两方比较 |
| §2.2／§2.3 补合法 JSON 及其他错误处理 | 已完整吸收，与 r1 建议逐字一致 |
| 禁用测试临时目录自动删除 | 要求已写入，但提供的实现仍会删除，未闭环 |

**必改 1：修正 §0.7 的 `cleanup` 补丁。**

[工单第 14 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_W5.md:14) 指定：

```python
patch.object(tempfile.TemporaryDirectory, "cleanup", lambda self: None)
```

这只能阻止上下文退出时的显式清理，**没有解除对象回收时的自动清理回调**。

本机 Python 3.14.6 的 [tempfile.py:910](/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/tempfile.py:910) 在构造时注册 `_weakref.finalize(..., self._cleanup, ..., delete=True)`；`_cleanup` 在第 958 行调用 `_rmtree`。正常 `cleanup()` 原本还负责解除该回调；替换为空函数反而遗漏了这一步。

本轮做了纯内存复现：将 `mkdtemp` 替换为返回虚拟路径，将 `_rmtree` 替换为计数函数，没有创建或删除实际文件。

```text
cleanup_noop_rmtree_calls=['/memory-only-w5-no-directory-created']
cleanup_detach_rmtree_calls=[]
```

因此，按工单示例执行仍与 §0.6“禁止批量删除”冲突。至少应将示例改为：

```python
patch.object(
    tempfile.TemporaryDirectory,
    "cleanup",
    lambda self: self._finalizer.detach(),
)
```

保留现有的目录路径记录、禁写字节码、不修改测试源码及断言等要求。“或等价方式”不能消除显式示例本身的错误。

**二、HEAD 锚点及字节预算**

本轮 HEAD：

```text
d5fa368ebfd10d26c4d0262c0daacc7bdc49bcf0
```

工作树开始、结束均干净；基线祖先检查和 §0.1 指定路径的基线差异检查均为 **exit 0**。

对 `git show HEAD:<文件>` 输出逐条实际执行 `grep -n -F -e`，六处均恰命中一次，行号全部一致。新旧片段 UTF-8 实算如下：

| 条目／目标行 | 命中 | 旧片段 B | 新片段 B | 净增 B |
|---|---:|---:|---:|---:|
| §2.1 split-run:41 | 1 | 116 | 275 | 159 |
| §2.2 commands:12 | 1 | 32 | 127 | 95 |
| §2.3 README:5 | 1 | 77 | 199 | 122 |
| §2.4 CHANGELOG:108 | 1 | 67 | 78 | 11 |
| §2.5 CHANGELOG:109 | 1 | 146 | 456 | 310 |
| §2.6 CHANGELOG:110 | 1 | 85 | 344 | 259 |

在内存完成六处替换后：

| 文件 | 修改前 B | 修改后 B | 预算判断 |
|---|---:|---:|---|
| references/split-run.md | 28,064 | 28,223 | +159 ≤260 |
| commands-staging/token-analyze-1.md | 2,382 | 2,477 | +95 ≤140 |
| 资产 README | 6,601 | 6,723 | +122 ≤160 |
| CHANGELOG.md | 271,014 | 271,594 | +580，无独立数值上限 |

**三、退出码契约及措辞**

通过。[实际源码](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:1686) 先计算、输出 `chosen`，再返回：

```python
return 1 if scan_failed else (0 if chosen else 2)
```

三处新文案正确表达：

- `exit 1`：即使保留非空 chosen，也不得采用。
- `exit 2` 且合法结果 JSON 中 `chosen=null`：才按无图全扫。
- `exit 0`：采用 chosen。
- 无合法 JSON 或其他错误：先处理错误。

这与 [W2 §2.1](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_W2.md:66) 一致，也避免把 argparse 的 `exit 2` 误当无图；[既有测试](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_sqd_coverage_probe.py:1518) 明确覆盖这些区别。未发现影响执行的措辞歧义。

**四、CHANGELOG 三处归并事实**

| 拟写事实 | 核验结果与依据 |
|---|---|
| probe 两协议登记 `d4adc0c8…`，旧 `c4980c98…` 保持 ACTIVE | 成立；[WR-b 验收](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/WR-b_acceptance.md:3)、[正式入口报告](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/WR-b_formal_entry.md:12) 支持；当前注册表四条状态也已核对 |
| docs_lint／changelog_lint PASS | [W2 验收第 5 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/W2_acceptance.md:5) 有历史记录 |
| run_all 150/151，唯一红为 reseal worktree 缺失；producer 守卫 0 FAIL | [WR-b 验收第 4、10 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/WR-b_acceptance.md:10) 支持；“环境项”为该记录已有归因 |
| WR-a／WR-b 真实入口验收 PASS | [WR-a 报告](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/WR-a_formal_entry.md:1)、[WR-b 报告](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/WR-b_formal_entry.md:1) 支持 |
| 收官 review PASS、P0/P1 空 | [收官复核第 1、3 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/review_final_reply_r1.md:1) 支持 |
| W3 单 slot `4,516,539→736,729`、gzip、规范化结果摘要相同 | [P5](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/fable_probes_20260924.md:41) 支持 |
| W4 三个内容比较关系 | 与 [P3](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/fable_probes_20260924.md:25) 一致，没有再扩大为 transactions／instructions 三方全等 |
| 完整生产链路吞吐收益未证明 | §2.6 明确保留，与收官复核一致 |

这些 PASS 都有既往记录，**不能当作 W5 修改后的验收结果**。“P2/P3 已按 W5 修正”属于施工完成后的目标状态，只有六处实际修正完成后才成立；本轮没有将其记为已完成。未发现新增的无依据 PASS 或吞吐收益夸大。

**五、文档门禁、版本及纪律**

- 亲跑 `test_g3_docs_guards.py`：**4 项 PASS，exit 0**。源码只读取 analyze/research 两份文档，不检查 CHANGELOG。
- [docs_lint.py:317](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/docs_lint.py:317) 明确豁免 CHANGELOG 断链检查；新增两个链接的目标也实际存在。
- 内存替换后的 CHANGELOG 三行各含 **2 个 `**`**；split-run 修改行含 **10 个**，均配对，不会因本次修改触发残缺粗体。
- 未运行完整 docs_lint/changelog_lint，它们涉及禁读范围；交调度方运行的安排合理。未运行需要创建测试文件的其他套件。
- 按“尚未 push、属于 9.2.0 同批收尾”的前提，保持版本可接受。[CHANGELOG 第 4 行](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:4) 将文档修订归入修档，但没有要求未发布版本的每次编辑都另起版本。本轮只核了本地远端跟踪引用，未联网验证远端状态。
- 除临时目录自动删除问题外，四文件白名单、指定片段限制、不改清单与纪律没有冲突。完成报告已写全路径；deploy_sync 预期 FAIL 与 staging 修改后由调度方同步部署的安排一致。

本轮全程只读、离线，未新建、修改或删除文件，未 commit；未读取 `~/.codex/`、memories、其他 maintenance 目录或用户列明的任何禁区。