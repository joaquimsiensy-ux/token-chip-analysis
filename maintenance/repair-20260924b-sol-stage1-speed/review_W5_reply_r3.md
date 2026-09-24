# 工单W5复核r3：通过

**r2 唯一必改已闭环；未发现新的必改项。** 本结论是工单可执行性与正确性通过，不代表 W5 已施工或完成施工后验收。

本轮 HEAD：`99b96107e9d1ccbaab946b52adb6ee28ebd0937c`。工作树干净；§0.1 的基线祖先检查、指定路径基线差异检查均为 **exit 0**。

**1. §0.7：`detach()` 修正有效**

在本机 Python 3.14.6 中做了纯内存正反对照：将 `mkdtemp` 替换为虚拟路径、`_rmtree` 替换为计数函数，执行上下文退出及对象回收，没有创建或删除实际目录。

```text
noop_rmtree_calls=['/memory-only-w5-no-directory-created']
detach_rmtree_calls=[]
```

因此，`lambda self: self._finalizer.detach()` 确实同时避开显式删除并解除 finalize 回调，解决了 r2 指出的自动批量删除问题。

与 r2 审查时的工单逐行比较，v3 仅修改标题、增加版本说明并修正 §0.7；六处替换文本未变。r2 所审查的源码、文档、资产及版本文件与当前 HEAD 无差异，相关差异检查 **exit 0**。

**2. 六处锚点与字节预算**

对各文件的 `git show HEAD:<路径>` 输出实际执行 `grep -n -F -e <旧片段>`：六处均恰命中一行，片段也各只出现一次，行号全部一致。

| 条目／目标行 | 命中数 | 旧片段 B | 新片段 B | 净增 B |
|---|---:|---:|---:|---:|
| §2.1 `split-run.md:41` | 1 | 116 | 275 | 159 |
| §2.2 `token-analyze-1.md:12` | 1 | 32 | 127 | 95 |
| §2.3 资产 `README.md:5` | 1 | 77 | 199 | 122 |
| §2.4 `CHANGELOG.md:108` | 1 | 67 | 78 | 11 |
| §2.5 `CHANGELOG.md:109` | 1 | 146 | 456 | 310 |
| §2.6 `CHANGELOG.md:110` | 1 | 85 | 344 | 259 |

按工单逐字在内存替换，UTF-8 文件长度如下；当前文件与 `W5_BASE` 相同：

| 文件 | 修改前 B | 修改后 B | 预算 |
|---|---:|---:|---|
| `references/split-run.md` | 28,064 | 28,223 | +159 ≤260 |
| `commands-staging/token-analyze-1.md` | 2,382 | 2,477 | +95 ≤140 |
| 资产 `README.md` | 6,601 | 6,723 | +122 ≤160 |
| `CHANGELOG.md` | 271,014 | 271,594 | +580；无独立数值上限 |

**3. 退出码契约与措辞**

重新核对了[真实实现](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:1686)、[W2 §2.1](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_W2.md:66)及现有测试断言。源码先输出 chosen，再返回：

```python
return 1 if scan_failed else (0 if chosen else 2)
```

三处新文案与此一致：

- **exit 1**：扫描级故障可以保留非空 chosen，但调用方不得采用。
- **exit 2 且合法结果 JSON 中 chosen=null**：才按无图全扫，避免混同 argparse 参数错误。
- **exit 0**：采用 chosen。
- 无合法 JSON 或其他错误：先处理错误。

维持 r2 结论：未发现影响执行的措辞歧义。

**4. CHANGELOG 三处归并的事实依据**

本轮重新读取对应记录并交叉核对：

| 拟写事实 | 依据与判断 |
|---|---|
| probe 两协议登记 `d4adc0c8…`，旧 `c4980c98…` 保持 ACTIVE | `WR-b_acceptance.md:3`、`WR-b_formal_entry.md:12` 支持；另核当前注册表，新旧哈希对应的两协议均为 ACTIVE |
| docs_lint／changelog_lint PASS | `W2_acceptance.md:5` 明确记录 |
| run_all 150/151，唯一红为 reseal 验收 worktree 缺失；producer 守卫 0 FAIL | `WR-b_acceptance.md:4、10` 支持；“环境项”为原记录已有归因 |
| WR-a／WR-b 真实入口验收 PASS | 两份 `formal_entry` 报告支持；WR-a 覆盖全旧／全新／混合产物及移除登记拒收，WR-b 包含真实注册查询正负对照和 coverage 兼容验证 |
| 收官 review PASS、P0/P1 空 | `review_final_reply_r1.md:1、3` 支持 |
| W3 单 slot 传输字节 `4,516,539→736,729`、gzip、规范化结果摘要相同 | `fable_probes_20260924.md:41` 的 P5 支持，未混用 P1 数字 |
| W4 header 三方全等，transactions 与 census-only 相等，instructions 与 probe-only 相等 | 同文件 P3 第 25 行支持，比较对象准确 |
| 完整生产链路吞吐收益未证明 | §2.6 明确保留，与收官复核第 19 行一致 |

没有发现无依据 PASS 或收益夸大。上述 PASS 均是**既往验收记录**；“P2/P3 已按 W5 修正”是六处施工完成后的目标状态，本轮未将其认定为已经发生。

**5. 门禁、版本与纪律**

- 亲跑 `test_g3_docs_guards.py`：**4 项 PASS，exit 0**。源码只检查 analyze/research 两份文档，不检查 CHANGELOG。
- [docs_lint.py:317](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/docs_lint.py:317) 豁免 CHANGELOG 断链检查；新增链接目标也实际存在。
- 内存替换后，CHANGELOG 第 108–110 行各有 **2 个 `**`**；split-run 第 41 行有 **10 个**，均为偶数，不会因本次修改触发残缺粗体检查。
- 未运行完整 docs_lint／changelog_lint，也未运行需要创建夹具文件的其余套件；这些不计为本轮 PASS。
- 按“尚未 push、属于 9.2.0 同批收尾”的前提，不升版本可接受。[CHANGELOG 第 4 行](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:4) 定义变更档位，没有要求未发布版本的每次文档编辑另起版本。本地远端跟踪引用没有包含 `W5_BASE` 的分支；因离线，未验证实时远端状态。
- 四文件指定片段白名单、完成报告路径、不改清单之间无冲突。系统 tempfile 是 §0.6 明确允许的测试范围；§0.7 的保留措施现已有效。deploy_sync 预期 FAIL 与随后由调度方同步部署的安排一致。

本轮全程只读、离线，未新建、修改、删除文件，未 commit；未读取 `~/.codex/`、memories、其他 maintenance 目录或用户列明的任何禁区。