# 工单 C7 复核提示词（只读，r1：只复核 workorder_C.md v4 新增的 C7 段；C1–C6 已落地 1b317b3 并经盲审 r1，唯一 minor C-01 即本段来源，见 `blind_C_reply_r1.md`）

## 纪律
1. 禁读 `~/.codex/`（插件启动搜索若已读 memories 如实披露一次，之后不再读）；禁读本仓库 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md` 的内容；禁读 `/Users/uravvv/Desktop` 下任何文件。
2. 只读、离线、不 commit、不改任何文件。报告全文打印到 stdout，首行固定为 `# 工单C7复核：通过` 或 `# 工单C7复核：退回`。退回时逐条给出：编号、工单位置、事实（附 `grep -n -F` 或代码原文）、修订建议。通过时也要列出你实际核过的项。

## 任务
复核 `maintenance/repair-20260917-p0-four/workorder_C.md` **C7 段**。工作目录＝本仓库根（HEAD 的 `facts_gate.py`/`test_report_facts.py` 与 1b317b3 相同）。逐项核：
a) 锚文本 `grep -n -F` 恰 1 处且行号一致（facts_gate.py :69/:357-360/:368/:446/:447-448；test_report_facts.py :121/:257/:283/:285）。
b) 替换后 `symbol`/`decimals`/`metrics`/`dual_basis` 变量在 `derive_facts` 后续引用处（:446-448 及其他）是否全部一致；`metrics` 为空对象时 facts.metrics 仍为 `{}`；`dual_basis` 显式 `{}` 时保留；`Facts._metric_value`（:146-150）对"每项为对象"的约定是否足够（宏渲染不再 AttributeError）。
c) 用例 15 五变体在基线（1b317b3）与改后的 RED/GREEN 是否如工单所述（decimals "18" 基线即绿属回归例）；`edit`/`reject`/`run` 助手签名是否匹配；lambda 默认参数捕获是否正确；`14 类`→`15 类` 后汇总行是否与 `results` 计数逻辑无冲突。
d) 全仓测试/夹具（`grep -rn` `缺失或非法`、`facts_inputs`）有无依赖旧文案或传非字符串 symbol / 非对象 metrics 的调用（尤其 `build_facts_from_ledgers` 助手 `symbol="SOLX"/"FX"/"TT"`、`metrics: {}`）。
e) 有无任何一处会让 `run_all.py` 现有用例变红；§1.1 字节不变（脚本不计入）。
