# 工单W3复核：退回

开启压缩的方向成立，但 v1 存在两处源码事实错误，以及测试断言、错误分类边界不够明确的问题。修正工单即可，无须扩大生产代码改动范围。

复核基线为 `HEAD=0ff40352cbb4e0b0264661d20868e29675c437b7`，已确认包含 `cc6298b`；工作树干净，工单涉及的生产源码相对 `cc6298b` 无差异。本次只读、离线，未修改文件、未 commit，未读取任何禁读路径或 memories。一次 heredoc 被只读沙箱拒绝，随后改用不落盘的 `python3 -B -c`。

事实①–⑤的亲核结论：

| 事实 | 结论 |
|---|---|
| ① 命令组装及压缩缺失 | 成立。`net.py:106–121` 无压缩选项；源码文本检索仅命中 `scan_token_accounts.py:10` 的说明。原样递归 grep 另命中已有 `.pyc`，不改变源码结论。 |
| ② 消费者范围 | 不准确。manifest 登记不是 `curl_json` 调用关系；`getBlocks` 属于 reference RPC。 |
| ③ ledger 来源及产物不变 | 不准确。存在二进制计数片段、错误对象及空响应约定；修复 RPC ledger 的哈希字段名是 `result_sha256`。 |
| ④ 性能动机 | 仓库文档引述成立；案卷数字不在允许读取范围内，无法独立核实。 |
| ⑤ 测试打桩 | 成立。该文件支持 `side_effect`，目前未断言 argv；其他测试已有代理参数断言。 |

**1.「必改」事实③：不能写成“全部来自 JSON、任何产物字节不变”。**

依据：

- 探针正常扫描对规范化块列表计算长度及哈希；特定空响应使用 `canonical_json([])`：`sqd_coverage_probe.py:338–356`。
- `getSlot/getBlocks` 失败记录可来自本地构造的错误对象：同文件 `892–900、928–935`。
- `map-reuse` 对计数数组的二进制切片计算长度及哈希：同文件 `1233–1243`。
- 修复 RPC ledger 对解析后的 `block` 重新序列化，字段为 `bytes/result_sha256`：`sqd_gap_repair.py:1033–1042`。
- ledger 另含时间戳；网络耗时和失败情况也可能改变。因此不能推导整个产物逐字节相同。

替换 `workorder_W3.md:7`，锚「③ 各生产者 ledger」：

> ③ 本次涉及的 ledger 字节数与响应摘要不统计线上压缩传输字节。探针正常扫描对规范化块列表计算 `bytes/response_sha256`，metadata 与 identity-anchor 对对应解析值计算；getSlot/getBlocks 对解析结果或本地错误对象计算；特定空响应按 `canonical_json([])` 记录；map-reuse 则对复用计数的二进制切片计算。修复 RPC ledger 对解析后的 getBlock 结果重新序列化，记录 `bytes/result_sha256`；SQD probe/census/beta 响应摘要对规范化块列表计算。成功响应解析值相同且上层处理不变时，这些内容长度与摘要不因 HTTP 压缩改变；不承诺时间戳、错误记录或整个产物逐字节相同。

同步替换 `workorder_W3.md:26` 的 docstring 指定原文：

> `--compressed`：协商当前 curl 支持的压缩编码并由 curl 透明解压；上层既有字节数与哈希计算口径不变。

这也避免把 `--compressed` 错写成固定只协商 gzip/deflate。

**2.「必改」事实②：明确真正受影响的调用方。**

生产代码直接调用 `curl_json` 的脚本共四个。`kind: net.py` 只说明导入该模块，可能实际使用 httpx；`kind: curl` 也可能是脚本自行调用 curl。

替换 `workorder_W3.md:6`，锚「② `curl_json` 消费者」：

> ② HEAD 下直接调用 `curl_json` 的生产脚本共四个：`sqd_coverage_probe.py:119/121/123`（SQD head/stream，以及 reference RPC getSlot/getBlocks）、`sqd_gap_repair.py:106/109`（reference getBlock，以及 SQD census/probe/beta）、`anchor_sampler.py:37`、`window_fetch.py:43`。本单影响这四个脚本经共享入口发出的请求。invariant_manifest 的 `kind: curl`/`kind: net.py` 是传输实现登记，不能据此扩大 `curl_json` 消费者范围。

关于“调用方是否依赖未压缩”，已执行递归检索：

```sh
grep -rnI -E --include='*.py' --include='*.sh' \
  'Content-Length|content-length|content_length|Content-Encoding|content-encoding|size_download|speed_download|limit-rate|iter_raw|iter_bytes|bytes_received' scripts
```

仅命中两份 vertical-slice 测试服务端的 `Content-Length` 读写：`test_batch3_evm_vertical_slice.py:43/119`、`test_batch3_solana_vertical_slice.py:53/113`。未发现生产调用方按传输字节限速、读取响应长度头或二次解压的依赖。`Result` 本身也不暴露响应头或传输字节数。

建议在上述替换段后追加：

> 已检索上述调用方及 scripts 内传输字节/响应头相关代码，未发现依赖未压缩响应的生产逻辑；ledger 的内容长度不得用作压缩节省量统计。

**3.「必改」§2.2：给出可执行的打桩原文，并验证“紧随”。**

现有 `>` 只能证明排在后面，不能验证 §1.1 要求的紧邻；仅检查 `--write-out` 存在，也不能保证状态码格式字符串保留。应替换完整成功用例，避免“在 with 锚之后新增”产生缩进歧义。

替换 `workorder_W3.md:27`，锚「2.2 `test_net_result.py`」：

> 2.2 将 `test_net_result.py:72–74` 的成功 JSON 用例整体替换为下列代码。保留现有 NDJSON 用例。`side_effect` 接收第一个位置参数 argv 和现有关键字参数，返回 `_run` 生成的 CompletedProcess；不得向 mocked stdout 填入 gzip 二进制，因为真实 subprocess stdout 已由 curl 解压。

```python
    url = "https://fixture.invalid"
    calls = []
    def capture(argv, **kwargs):
        calls.append(list(argv))
        return _run('{"ready":true}')
    with mock.patch.object(net.subprocess, "run", side_effect=capture):
        got = net.curl_json(url, attempts=1)
    assert len(calls) == 1, calls
    argv = calls[0]
    assert argv.count("--compressed") == 1, argv
    assert argv.index("--compressed") == argv.index("--fail-with-body") + 1
    assert "--write-out" in argv, argv
    assert argv[argv.index("--write-out") + 1] == "\n__CURL_HTTP_STATUS__:%{http_code}"
    assert argv[-1] == url, argv
    assert got.ok is True and got.value == {"ready": True} and got.error is None, got
```

再追加以下施工原文：

> 在 `cases` 列表加入下列条目，并在既有循环的 `assert set(got.error) == expected_keys` 后追加对应断言；测试新增行数仍可保持在 25 行以内。

```python
        (_run('{"ready":true}', returncode=61, stderr="bad content encoding"), "transport"),
```

```python
        if completed.returncode == 61:
            assert got.error["returncode"] == 61 and got.error["http_status"] == 200
            assert got.error["retryable"] is True
```

现有循环已经断言 `got.ok is False` 和 `got.value is None`，因此这个用例还能防止非零退出时误接受部分输出。捕获 argv 的写法已在当前源码上离线验证兼容。

**4.「必改」§1.1：明确压缩失败归类及解析顺序。**

本机 `curl 8.7.1 --manual` 确认：压缩协商允许服务器返回未压缩正文；不支持的响应编码会报错；write-out 在传输之后输出；`--fail-with-body` 的 HTTP 失败返回码为 22。

源码实际行为是先剥离状态尾巴，再按退出码分类，最后才解析 JSON。NDJSON 也是 `subprocess.run` 收集完整 stdout 后逐行解析，并非 Python 增量流式解码。

替换 `workorder_W3.md:20`，锚「1.1 只在」：

> 1.1 只在 `curl_json` 命令列表中紧随 `"--fail-with-body"` 插入 `"--compressed"`，保留原有 write-out 格式及解析顺序。curl 负责协商压缩并解压正文；服务器返回未压缩正文时仍正常解析，不能把“不支持 gzip”本身视为失败。Python 在 subprocess 完成后先剥离状态码尾巴，再检查退出码，最后解析完整 JSON/NDJSON。返回码 22 继续归 `http_status`；其余非零返回码，包括内容编码/解压失败产生的返回码（例如 61），继续归 `transport`，保留实际 returncode/http_status、retryable=True 及现有 attempts/no_retry_statuses 控制，不消费部分正文。只有返回码为 0 后的空正文或 JSON/NDJSON 解析失败归 `decode`。不得把解压失败改判为 SQD 正常空尾。

交互判断：

- 正常压缩响应不会把 curl 自行追加的状态尾巴一起压缩，现有 `rsplit(marker, 1)` 可继续使用。
- 正常压缩的 HTTP 错误响应仍按返回码 22 分类；同时发生传输/解压错误时，以实际退出码为准。
- 不支持 gzip 但返回正常未压缩正文的端点透明兼容；返回错误编码头或坏压缩体不在此保证内。
- 当前无 Python 流式解码边界问题；完整正文仍会被捕获到内存中。

**5.「建议」§1.2：补上登记核对结论，无须修改 manifest。**

AST 守卫仅识别列表首元素 `"curl"`、变量传递及 `REGISTERED_TRANSPORT_BACKEND`，没有钉死完整 argv。manifest 对照键为 `(script, kind)`。

替换 `workorder_W3.md:21`：

> 1.2 不改 `Result`、httpx 路径及任何调用方；保持 `REGISTERED_TRANSPORT_BACKEND = "curl"`。核对 invariant_manifest 中 `scripts/lib/net.py` 的 `curl/httpx` 登记及相关调用方登记不变。现有 invariant_scan 只识别传输种类，不固定 curl 完整参数列表；新增参数不需要修改 manifest，参数位置与 write-out 格式由 §2.2 测试约束。

依据为 `invariant_scan.py:1151–1153、1194–1202、1273–1274、1300–1301`，以及 `invariant_manifest.json:742–747、858–863`。

**6.「存疑」事实④：区分仓库证据与案卷转述；验收不应固定要求 gzip。**

`references/data-pipeline-solana-capture.md:107` 确有 21 倍吞吐记录，但它是 SQD 实测，不能据此证明 Helius 的压缩收益。PYTHIA 的下载量及速度本次无法亲核。

替换 `workorder_W3.md:8`：

> ④ 动机来自调度方案卷 PYTHIA-PERF-003：据其记录，Helius getBlock 平均 2.33 MB/块、链路约 7 MB/s、92 slot/min、总下载 366.7 GB；案卷不在本仓库，本次离线复核未独立验证这些数字。仓库 `references/data-pipeline-solana-capture.md:107` 确有 SQD 使用 `--compressed` 后约 21 倍吞吐提升的历史记录及遗留 curl 补压缩要求；该记录不代表 Helius 的实际压缩率或提速倍数。

建议同时将 `workorder_W3.md:31` 的调度方验收句替换为：

> 调度方本机对同一 finalized slot、相同 getBlock 请求体和端点，对比 identity 响应与 `--compressed` 响应；记录 curl 版本、实际 Content-Encoding、`size_download`、`time_total`、退出码及 HTTP 状态，并比较解析后结果的规范化摘要。压缩编码以实际协商结果为准，不固定要求 gzip；若返回 identity，则记录未观察到压缩收益。不得使用 ledger.bytes 衡量传输节省；结果只作验收记录，不入仓库。

**7.「建议」§0.1：展开后续工单基线检查，避免照抄 W1 导致停工。**

README 明确顺序为 W1→W4→W3。W1 的 §0.1 要求生产文件相对 `cc6298b` 无差异，W1/W4 完成后该条件自然不再成立。“派工时填入基线”最好明确到命令。

替换 `workorder_W3.md:13`：

> 0.1 工作目录同 W1。调度方派工时填入 W4 收官提交 `<W3_BASE>` 并重核本单行号；开工记录 `git status --short`（须为空）、`git rev-parse HEAD`（须等于 `<W3_BASE>`）、`git merge-base --is-ancestor cc6298b HEAD`（须 exit 0）。不继承 W1“生产文件相对 cc6298b 无差异”的检查，完成报告写入本目录 `W3_done.md`。0.2/0.5/0.6 同 W1；本目录可读范围按本单列示。

验证范围：现有 `python3 -B scripts/tests/test_net_result.py` 已通过；另用内存 mock 核实 argv 捕获、状态尾巴、返回码 61→transport、22→http_status、零退出码坏 JSON→decode。未运行会创建测试文件的其余套件，也未进行真实 HTTP 压缩验收。

| 条目 | 等级 | 依据文件:行 |
|---|---|---|
| 1. ledger 来源及“不改任何产物” | 必改 | `scripts/solana/sqd_coverage_probe.py:338、355、892、1233`；`scripts/solana/sqd_gap_repair.py:1033` |
| 2. 调用方范围与传输依赖 | 必改 | `scripts/solana/sqd_coverage_probe.py:119`；`sqd_gap_repair.py:106`；`anchor_sampler.py:37`；`window_fetch.py:43`；`scripts/lib/net.py:50` |
| 3. argv 打桩与紧邻断言 | 必改 | `scripts/tests/test_net_result.py:18、32、72`；`scripts/lib/net.py:126` |
| 4. 解压失败分类及状态尾巴 | 必改 | `scripts/lib/net.py:72、133、142、151、166`；`scripts/solana/sqd_coverage_probe.py:340` |
| 5. backend/manifest 核对 | 建议 | `scripts/tests/invariant_scan.py:1151、1194、1273、1300`；`scripts/tests/invariant_manifest.json:742` |
| 6. 性能证据归属与验收指标 | 存疑；验收建议 | `references/data-pipeline-solana-capture.md:107`；本工程 `README.md:5`；`workorder_W3.md:8、31` |
| 7. W3 派工基线 | 建议 | 本工程 `README.md:9–14`；`workorder_W1.md:16`；`workorder_W3.md:13` |
