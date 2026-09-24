# W3 施工提示词（codex --write）
## 纪律（优先级高于工单）
1. 你是施工者。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。**只按下方工单施工**，不扩展范围。
2. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读纪律同样适用于你运行的子进程。
3. 离线；不 commit、不 push；禁 stash/checkout/reset；不建 worktree；只写工单白名单文件与完成报告；禁止批量删除。
4. 完成报告写到 `maintenance/repair-20260924b-sol-stage1-speed/W3_done.md`，**并把报告全文放在最终答复消息里**。停工同样写报告并说明原因。

---
# 工单全文
# 工单 W3（v3）：`scripts/lib/net.py::curl_json` 开启 HTTP 压缩（`--compressed`）—— 归属版本 9.2.0（登记在 W2）

> 出处：用户 2026-09-24 裁决第 3 条「Helius 下载也开压缩」。
> v3 变更：codex 复核 r2 通过（`review_W3_reply_r2.md`），采纳其唯一建议（改名说明改为四行同步）；施工顺序调整为 **W3 先行**（与 W1/W4 无文件交集，且已通过复核），派工基线＝当前 HEAD。
> v2 变更：吸收 codex 复核 r1（`review_W3_reply_r1.md`）7 条——必改 1–4 全采纳（事实③ ledger 来源改写、事实② 调用方明确为四脚本、§2.2 给可执行打桩原文＋返回码 61 用例、§1.1 明确错误分类与解析顺序）；建议 5/7 采纳（§1.2 manifest 核对结论、§0.1 基线命令）；存疑 6 采纳并补调度方本机 Helius 实测。
> 事实（调度方本机亲核，基线 `cc6298b`；行号按派工时基线重核）：
> ① `scripts/lib/net.py:106-121` 组装 curl 命令：`["curl","--silent","--show-error","--fail-with-body","--max-time",…,"--write-out","\n__CURL_HTTP_STATUS__:%{http_code}"]`＋可选 `-x proxy`＋headers＋`--data-binary`；**无 `--compressed`、无 `Accept-Encoding`**（`grep -rn -E "compressed|Accept-Encoding" scripts` 仅命中 `scan_token_accounts.py:10` 的说明文字）。
> ② HEAD 下直接调用 `curl_json` 的生产脚本共四个：`sqd_coverage_probe.py:119/121/123`（SQD head/stream，以及 reference RPC getSlot/getBlocks）、`sqd_gap_repair.py:106/109`（reference getBlock，以及 SQD census/probe/beta）、`anchor_sampler.py:37`、`window_fetch.py:43`。本单影响这四个脚本经共享入口发出的请求。invariant_manifest 的 `kind: curl`/`kind: net.py` 是传输实现登记，不能据此扩大 `curl_json` 消费者范围。已检索上述调用方及 scripts 内传输字节/响应头相关代码（`Content-Length|content-encoding|size_download|limit-rate|iter_raw|iter_bytes` 等），仅命中两份 vertical-slice 测试服务端，未发现依赖未压缩响应的生产逻辑；ledger 的内容长度不得用作压缩节省量统计。
> ③ 本次涉及的 ledger 字节数与响应摘要**不统计线上传输字节**。探针正常扫描对规范化块列表计算 `bytes/response_sha256`（`sqd_coverage_probe.py:355`），特定空响应按 `canonical_json([])` 记录（`:338-350`）；getSlot/getBlocks 对解析结果或本地错误对象计算（`:892-900`）；map-reuse 对复用计数的二进制切片计算（`:1233-1243`）。修复 RPC ledger 对解析后的 getBlock 结果重新序列化，记录 `bytes/result_sha256`（`sqd_gap_repair.py:1033-1042`）；SQD probe/census/beta 响应摘要对规范化块列表计算。**成功响应解析值相同且上层处理不变时，这些内容长度与摘要不因 HTTP 压缩改变；不承诺时间戳、错误记录或整个产物逐字节相同。**
> ④ 动机来自调度方案卷 PYTHIA-PERF-003：据其记录，Helius getBlock 平均 2.33 MB/块、链路约 7 MB/s、92 slot/min、总下载 366.7 GB；案卷不在本仓库，施工方不必核。仓库 `references/data-pipeline-solana-capture.md:107` 有 SQD 使用 `--compressed` 后约 21 倍吞吐的历史记录及「遗留 curl 件必须补 `--compressed`」要求，该记录不代表 Helius 的压缩率。**调度方 2026-09-24 本机对 Helius 实测**（`fable_probes_20260924.md` §P1）：同一 slot 相同 getBlock 请求体，明文 4,516,539 B，`--compressed` 传输 737,282 B，响应头 `content-encoding: gzip`，解码后逐字节相等，压缩比 6.1×。
> ⑤ `scripts/tests/test_net_result.py` 以 `mock.patch.object(net.subprocess, "run", …)` 打桩（`:18` `_run` 构造 CompletedProcess，`:72-74` 成功 JSON 用例）；支持 `side_effect`，现无对命令行参数的断言。
> ⑥ curl 8.7.1 `--manual`：`--compressed` 请求 curl 所支持的编码并透明解压；服务器可返回未压缩正文；不支持的响应编码报错（返回码 61）；`--fail-with-body` 的 HTTP 失败返回码 22；write-out 在传输完成后输出。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。派工基线 `60c88b88a024bf463e819d846b1ba3a9e06c7ecd`＝派工时 HEAD（本单为工程首个施工单）；开工记录 `git status --short`（须为空）、`git rev-parse HEAD`（须等于 `60c88b88a024bf463e819d846b1ba3a9e06c7ecd`）、`git merge-base --is-ancestor cc6298b HEAD`（须 exit 0）、`git diff --quiet cc6298b HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets`（须 exit 0）。0.2/0.5/0.6 同 W1（禁读 `~/.codex/`、`archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、其他 `maintenance/`、`/Users/uravvv/Desktop`、`/Users/uravvv/Documents`；锚整行 `grep -n -F -x` 恰 1 处；离线不 commit、禁 stash/checkout/reset、临时目录只用系统 tempfile、禁止批量删除）。本目录可读：`README.md`、`workorder_W*.md`、`review_W3_reply_*.md`、`fable_probes_20260924.md`。
- 0.3 **白名单**：生产 `scripts/lib/net.py`；测试 `scripts/tests/test_net_result.py`；完成报告 `W3_done.md`。
- 0.4 **不改**其他任何文件（文档句归 W2；`invariant_manifest.json` 不改，见 §1.2）。
- 0.7 定向跑：`test_net_result.py`、`test_repair_batch1.py`、`test_batch3_solana_producers.py`、`test_sqd_coverage_probe.py`、`test_sqd_gap_repair.py`、`invariant_scan.py`、`test_batch4_invariant_guards.py`、`test_exemption_guards.py`。

## 1. 硬约束

- 1.1 只在 `curl_json` 命令列表中**紧随** `"--fail-with-body"` 插入 `"--compressed"`，保留原有 write-out 格式及解析顺序。curl 负责协商压缩并解压正文；服务器返回未压缩正文时仍正常解析，不能把「不支持 gzip」本身视为失败。Python 在 subprocess 完成后先剥离状态码尾巴，再检查退出码，最后解析完整 JSON/NDJSON（现状 `net.py:133-166`，不改）。返回码 22 继续归 `http_status`；其余非零返回码，包括内容编码/解压失败产生的返回码（例如 61），继续归 `transport`，保留实际 returncode/http_status、retryable=True 及现有 attempts/no_retry_statuses 控制，不消费部分正文。只有返回码为 0 后的空正文或 JSON/NDJSON 解析失败归 `decode`。不得把解压失败改判为 SQD 正常空尾（`sqd_coverage_probe.py:340` 的 decode/200/空正文三元匹配不变）。
- 1.2 不改 `Result`、httpx 路径及任何调用方；保持 `REGISTERED_TRANSPORT_BACKEND = "curl"`。核对 invariant_manifest 中 `scripts/lib/net.py` 的 `curl/httpx` 登记及相关调用方登记不变。现有 invariant_scan（`:1151-1153/:1194-1202/:1273-1274/:1300-1301`）只识别传输种类，不固定 curl 完整参数列表；新增参数不需要修改 manifest，参数位置与 write-out 格式由 §2.2 测试约束。
- 1.3 生产改动 ≤ 6 行（含 docstring 一行）；测试新增 ≤ 25 行。

## 2. 逐条施工

- 2.1 `net.py`（锚 `    command = ["curl", "--silent", "--show-error", "--fail-with-body",`）：在 `"--fail-with-body",` 之后插入 `"--compressed",`；`curl_json` docstring 加一行原文：「`--compressed`：协商当前 curl 支持的压缩编码并由 curl 透明解压；上层既有字节数与哈希计算口径不变。」
- 2.2 `test_net_result.py:72-74` 的成功 JSON 用例（锚 `    with mock.patch.object(net.subprocess, "run", return_value=_run('{"ready":true}')):`起三行）**整体替换**为下列代码。保留现有 NDJSON 用例。`side_effect` 接收第一个位置参数 argv 和现有关键字参数，返回 `_run` 生成的 CompletedProcess；不得向 mocked stdout 填入 gzip 二进制，因为真实 subprocess stdout 已由 curl 解压。

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

  注意：该函数早前已有名为 `calls` 的变量用于重试计数（`assert len(calls) == 3`），上述代码在其之后重新绑定 `calls = []`，不影响前面的断言；若施工方认为易混淆，可将上述代码块中涉及 `calls` 的四行统一改用 `argv_calls`，包括断言失败信息中的引用。

- 2.3 在 `cases` 列表（锚 `        (_run("not-json"), "decode"),`）之后加入：

```python
        (_run('{"ready":true}', returncode=61, stderr="bad content encoding"), "transport"),
```

  并在既有循环的 `assert set(got.error) == expected_keys` 之后追加：

```python
        if completed.returncode == 61:
            assert got.error["returncode"] == 61 and got.error["http_status"] == 200
            assert got.error["retryable"] is True
```

  现有循环已断言 `got.ok is False` 与 `got.value is None`，该用例同时防止非零退出时误接受部分输出。

## 3. 完成报告 `W3_done.md`

首行 `# W3 完成：…`；§0.1 三条输出；diff 行数；§0.7 尾行；披露禁读路径。调度方本机验收另做（不入仓库）：对同一 finalized slot、相同 getBlock 请求体和端点，对比 identity 响应与 `--compressed` 响应；记录 curl 版本、实际 Content-Encoding、`size_download`、`time_total`、退出码及 HTTP 状态，并比较解析后结果的规范化摘要。压缩编码以实际协商结果为准，不固定要求 gzip；若返回 identity，则记录未观察到压缩收益。不得使用 ledger.bytes 衡量传输节省。
