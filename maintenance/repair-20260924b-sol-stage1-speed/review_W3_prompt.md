# 工单 W3 复核提示词（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读本工程目录 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放在最终答复消息里**（不要只 print 到 stdout）。工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`，基线＝HEAD（须含 `cc6298b`）。
3. 每条意见须给出可直接替换进工单的原文（含行号/锚），并标注「必改/建议/存疑」；结尾给汇总表（条目/等级/依据文件:行）。你复核的是**工单定形**，不是施工；发现工单事实与源码不符的地方优先级最高。
首行固定 `# 工单W3复核：通过` 或 `# 工单W3复核：退回`。

## 任务
复核 `maintenance/repair-20260924b-sol-stage1-speed/workorder_W3.md`（v1；背景先读同目录 `README.md`）。逐条审：
a) 事实段 ①–⑤ 亲核（`net.py:106-121` 命令组装；`grep -rn -E "compressed|Accept-Encoding" scripts`；各 ledger `bytes`/`response_sha256` 的计算来源；`test_net_result.py` 打桩方式）。
b) 风险：`--compressed` 与 `--write-out`/`--fail-with-body`/NDJSON 流式解码是否有交互问题；对不支持 gzip 的端点是否透明；对 `http_status` 尾巴解析是否有影响；curl 解压失败时的返回码归类（transport 还是 decode）是否需要在工单明确。
c) 是否有调用方**依赖**未压缩（例如按传输字节做限速/统计、或对 `Content-Length` 有假设）——`grep -rn` 证明。
d) 测试 2.2 断言写法是否与现有打桩兼容（`side_effect` 捕获 argv 的具体写法给出原文）。
e) 是否应把 `REGISTERED_TRANSPORT_BACKEND`/invariant_manifest 的 `kind: curl` 登记一并核对（是否有 AST 守卫钉 curl 参数列表）。
