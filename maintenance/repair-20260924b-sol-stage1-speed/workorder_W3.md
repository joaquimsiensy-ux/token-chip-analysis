# 工单 W3（v1）：`scripts/lib/net.py::curl_json` 开启 HTTP 压缩（`--compressed`）—— 归属版本 9.2.0（登记在 W2）

> 出处：用户 2026-09-24 裁决第 3 条「Helius 下载也开压缩」。
> 事实（调度方本机亲核，基线 `cc6298b`；行号按派工时基线重核）：
> ① `scripts/lib/net.py:106-121` 组装 curl 命令：`["curl","--silent","--show-error","--fail-with-body","--max-time",…,"--write-out","\n__CURL_HTTP_STATUS__:%{http_code}"]`＋可选 `-x proxy`＋headers＋`--data-binary`；**无 `--compressed`、无 `Accept-Encoding`**（调度方 `grep -rn -E "compressed|Accept-Encoding" scripts` 仅命中 `scan_token_accounts.py:10` 的说明文字）。
> ② `curl_json` 消费者：`sqd_coverage_probe.py`（LiveTransport，SQD stream/head/getBlocks）、`sqd_gap_repair.py:106/:109`（Helius getBlock 与 SQD census/probe/beta）、其他登记为 `kind: curl`/`kind: net.py` 的脚本（`scripts/tests/invariant_manifest.json:743-747/:859-863`）。
> ③ 各生产者 ledger 的 `bytes` 字段来自**解码后** canonical JSON 长度（探针 `_scan_request` `row.update(bytes=len(raw)…)`、修复 `:1041 "bytes": len(raw)`），与线上传输字节无关；`response_sha256` 同样对解码后规范化 JSON 计算。故开压缩不改任何产物字节。
> ④ 实测动机：PYTHIA-PERF-003（案卷）修复阶段 Helius `getBlock` 平均 2.33 MB/块未压缩、链路 ≈7 MB/s、92 slot/min、总下载 366.7 GB；`data-pipeline-solana-capture.md:107` 已写明 SQD 侧 `--compressed` 实测 21 倍、「遗留 curl 件必须补 `--compressed`」。
> ⑤ `scripts/tests/test_net_result.py` 以 `mock.patch.object(net.subprocess, "run", …)` 打桩，可捕获 argv；现无对命令行参数的断言。

## 0. 开工纪律

- 0.1/0.2/0.5/0.6 同 W1（基线由调度方派工时填入）。本目录可读：`README.md`、`workorder_W*.md`、`review_W3_reply_*.md`。
- 0.3 **白名单**：生产 `scripts/lib/net.py`；测试 `scripts/tests/test_net_result.py`；完成报告 `W3_done.md`。
- 0.4 **不改**其他任何文件（文档句归 W2）。
- 0.7 定向跑：`test_net_result.py`、`test_repair_batch1.py`、`test_batch3_solana_producers.py`、`test_sqd_coverage_probe.py`、`test_sqd_gap_repair.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`。

## 1. 硬约束

- 1.1 只在 `curl_json` 命令列表加 `"--compressed"`（紧随 `"--fail-with-body"` 之后）；`--write-out` 状态码尾巴、`--fail-with-body` 语义、重试与错误分类不变。
- 1.2 不改 `Result`、不改 httpx 路径、不改任何调用方；`REGISTERED_TRANSPORT_BACKEND` 不变。
- 1.3 生产改动 ≤ 6 行（含 docstring 一行）；测试新增 ≤ 25 行。

## 2. 逐条施工

- 2.1 `net.py`（锚 `    command = ["curl", "--silent", "--show-error", "--fail-with-body",`）：列表插入 `"--compressed"`；`curl_json` docstring 加一行「`--compressed`：请求 gzip/deflate 并由 curl 透明解压；ledger 的 bytes/sha 均对解码后 JSON 计算，不受影响」。
- 2.2 `test_net_result.py`（锚 `    with mock.patch.object(net.subprocess, "run", return_value=_run('{"ready":true}')):`）之后新增：用 `side_effect` 捕获 `subprocess.run` 的第一个位置参数，断言 `"--compressed" in argv`、`argv.index("--compressed") > argv.index("--fail-with-body")`、`"--write-out" in argv`、`argv[-1] == url`。

## 3. 完成报告 `W3_done.md`

首行 `# W3 完成：…`；§0.1 输出；diff 行数；§0.7 尾行；披露禁读路径。调度方本机验收另做：对真实 Helius 端点单块 `getBlock` 以 `curl -v --compressed` 观察响应头 `content-encoding: gzip` 与传输字节/耗时对比明文（只作验收记录，不入仓库）。
