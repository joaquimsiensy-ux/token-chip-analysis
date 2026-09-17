# 工单C7复核：通过

r2 结论：**C7-R01 已闭合，未发现新增问题。** 报告全文已打印到 stdout。

[工单 :536](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_C.md:536) 已改为：

```python
if "dual_basis" in fi and not isinstance(dual_basis, dict):
    raise ValueError("facts_inputs.dual_basis 须为对象")
```

[用例 15 :560](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260917-p0-four/workorder_C.md:560) 已加入 `None` 变体。内存实测确认：显式 `null` 被 `derive_facts` 拒绝，`build_main` 返回 2，发布闸重算也明确拒绝；缺键仍允许，显式 `{}` 和正常对象仍保留并通过。

实际核过：

- **a）锚点：**13 条 `grep -n -F` 均唯一命中且行号一致。两个目标源码均与 `1b317b3` 逐字节相同。
- **b）变量及宏：**按工单在内存替换后编译通过，四个变量及后续引用一致；实测 `metrics={}` 保持 `{}`。每项为对象的约定满足 `_metric_value` 的 `.get()` 调用要求，相关 AttributeError 路径已被拦截。
- **c）测试：**助手签名匹配，六个 lambda 默认参数捕获正确。注册计数为 **15 类、34 个独立用例**，同名项不会合并；原 14 类本轮未重跑。
- **d）兼容性：**对排除禁读路径后的 1556 个常规文件执行搜索。测试及夹具无旧文案依赖；合法构造路径未发现非字符串 symbol 或非对象 metrics。`TT/SOLX/FX` 均为字符串，共享助手的 metrics 为 `{}`。
- **e）回归及字节：**未发现新增回归点；`run_all.py` 按退出码汇总，不依赖“14 类”文案。stat 核验：`SKILL.md=8021 B`、`commands-staging=8798 B`、`references=930065 B`，均不变。

| 用例 15 输入 | 基线 1b317b3 | C7 v5 |
|---|---|---|
| `symbol=123` | RED：未拒绝 | GREEN |
| `decimals="18"` | GREEN：既有回归例 | GREEN |
| `metrics=[{"value":"7"}]` | RED：未拒绝 | GREEN |
| `metrics={"m1":"7"}` | RED：未拒绝 | GREEN |
| `dual_basis="x"` | RED：未拒绝 | GREEN |
| `dual_basis=null` | RED：未拒绝 | GREEN |

动态验证使用内存文件系统及真实生产函数；未执行落盘 CLI、完整集成测试或 `run_all.py`。结论为 **v5 工单复核通过**。

全程未写文件、未联网、无 commit；开工及收尾工作树均干净，`git diff --check` 通过。期间 HEAD 从 `3b790f4` 推进至 `6baac56`，仅涉及三份提示词；本工单及两个目标源码的 SHA-256 均未变。

禁读披露：启动曾检索 `~/.codex/memories/MEMORY.md`，已即时披露，未取得 C7 相关记录，此后未再访问 `~/.codex/`。其余禁读内容未读取；`references/attic.md` 仅参与获准的 stat 汇总。

Codex session ID: 01a0afdc-919e-7bd0-bf1e-f5b7b52c3970
Resume in Codex: codex resume 01a0afdc-919e-7bd0-bf1e-f5b7b52c3970
