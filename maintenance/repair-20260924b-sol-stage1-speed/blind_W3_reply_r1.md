# W3盲审：PASS

审查范围：`60c88b88a024bf463e819d846b1ba3a9e06c7ecd..6b36dcdd043d0b2b51c03de9ab0bb555b25f436a` 的 `scripts` diff。未发现违反工单 v3 的改动。此结论针对代码及离线契约，不包含真实链路压缩效果验收。

1. **范围与行数符合要求。**

   | 文件 | 新增 | 删除 |
   |---|---:|---:|
   | `scripts/lib/net.py` | 2 | 0 |
   | `scripts/tests/test_net_result.py` | 18 | 2 |

   diff 仅含两个白名单文件；生产 ≤6 行、测试新增 ≤25 行。`git diff --check` 通过。被审代码、工单和完成报告的工作区内容与 HEAD 一致。

2. **参数位置、解析顺序与错误契约保持不变。**

   `--compressed` 紧随 `--fail-with-body`；write-out 仍为 `\n__CURL_HTTP_STATUS__:%{http_code}`，URL 仍在参数末尾。

   代码仍先剥离状态码尾巴，再判断退出码，最后解析正文：22→`http_status`；其他非零→`transport`；仅退出码 0 后的空正文或坏 JSON/NDJSON→`decode`。`Result`、重试逻辑、`no_retry_statuses`、httpx 路径及 `REGISTERED_TRANSPORT_BACKEND = "curl"` 均未修改。

3. **新测试确实约束了要求，返回码 61 用例语义正确。**

   独立执行 `test_net_result.py` 的 `main()`：通过。在内存中仅移除命令列表里的 `--compressed` 后，同一测试在第 85 行唯一性断言处失败；恢复后通过。

   61 用例故意提供合法 JSON，验证“非零退出时，即使正文可解析，也不能接受”。已有断言同时要求 `ok=False`、`value=None`，新增断言要求保留 `returncode=61`、`http_status=200`、`retryable=True`。

   额外内存验证：61 分别搭配空正文、合法 JSON、坏 JSON，均保持 `transport`；`attempts=3` 均调用三次、退避为 1/2 秒；设置 `no_retry_statuses=(200,)` 后均只调用一次。

   本机 `curl -q --manual` 确认：61 表示无法识别传输编码；`--compressed` 请求支持的编码并自动解压，服务端仍可返回未压缩正文。该单测验证的是错误处理契约，并未模拟真实解压过程。

4. **四个调用方、登记和 SQD 空尾判断兼容。**

   生产直接调用方仍为 `sqd_coverage_probe.py`、`sqd_gap_repair.py`、`anchor_sampler.py`、`window_fetch.py`，均无需改动。检索未发现相关生产逻辑依赖 `Content-Length`、`Content-Encoding`、`size_download` 等传输层数值；所核对的 ledger 长度与摘要来自解析后重新序列化的数据或本地二进制切片。

   实际调用 `_scan_request` 验证：上述三种 61 响应均返回失败、不会成为正常空尾；0/200/空正文仍被既有三元匹配接受。

   独立运行完整 `invariant_scan.py` 主检查，通过：

   ```text
   PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0
   ```

   另逐项核对：net.py 识别为 `curl/httpx`，四个调用方识别为 `net.py`，均与 manifest 一致，无需修改登记。

5. **`W3_done.md` 与 diff 一致，未把受阻项记成通过。**

   改动行数、参数断言、61 用例、NDJSON 保留及未修改的接口，与实际代码一致。报告明确记录 `test_sqd_gap_repair.py` 因禁读拦截未完成，以及施工方尚未执行真实链路验收。

   本轮重现了其中的 net 测试和完整 invariant 主检查通过结果。其余历史执行记录、当时的工作区状态及拦截过程，仅核对报告陈述，未独立重现。

**未验证范围：**未运行 `test_sqd_gap_repair.py`；其余五项需要创建临时文件的定向测试也未运行。未执行 invariant 的写文件自测、真实 HTTP 请求、压缩/identity 对照或吞吐测试。调度方所述本机通过结果不计入本轮独立证据。

**纪律披露：**未读取 `~/.codex/` 或 memories，未读取任何指定禁区；全程离线，未修改或新建文件，未 commit。首次 heredoc 被只读沙箱拒绝，随后改用 `python3 -I -B -S -c` 在内存执行，并以审计钩子阻止禁区读取、文件写入、网络及测试启动子进程。
