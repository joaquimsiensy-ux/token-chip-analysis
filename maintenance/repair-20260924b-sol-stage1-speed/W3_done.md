# W3 完成：curl_json 开启 HTTP 压缩；7 项检查通过，1 项因禁读纪律受阻

代码施工完成，完整验收尚缺 `test_sqd_gap_repair.py`。版本归属 9.2.0，由 W2 登记；本单未修改版本文件。

开工基线核验（§0.1）：

```text
$ git status --short
（输出为空；exit 0）
$ git rev-parse HEAD
2cbbcbc5859b0ce389ddcfeebd68f19b506d7735
（exit 0）
$ git merge-base --is-ancestor 60c88b88a024bf463e819d846b1ba3a9e06c7ecd HEAD
（输出为空；exit 0）
$ git diff --quiet 60c88b88a024bf463e819d846b1ba3a9e06c7ecd HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets
（输出为空；exit 0）
$ git merge-base --is-ancestor cc6298b HEAD
（输出为空；exit 0）
```

三个施工锚均用 `grep -n -F -x` 核验，各恰好 1 处。生产文件仅新增 docstring 原文与紧随 `--fail-with-body` 的 `--compressed`。测试使用 `argv_calls`，约束参数唯一性、位置、write-out 格式和 URL；新增返回码 61 用例，验证仍为 transport、保留 returncode/http_status、retryable=True 且不接受正文。原 NDJSON 用例保留。

`git diff --numstat`：

```text
2       0       scripts/lib/net.py
18      2       scripts/tests/test_net_result.py
```

生产改动 2 行 ≤ 6 行；测试新增 18 行 ≤ 25 行。`git diff --check` 通过。`Result`、解析顺序、httpx 路径及四个调用方未改；`REGISTERED_TRANSPORT_BACKEND = "curl"` 保持不变。manifest 中 net.py 的 curl/httpx 登记及四个调用方的 net.py 登记已核对，manifest 无改动。

§0.7 定向检查结果及输出尾行（路径均在 `scripts/tests/`）：

| 检查 | 退出码 | 输出尾行 |
|---|---:|---|
| `test_net_result.py` | 0 | `PASS: net Result 显式状态与 curl_json 失败分类` |
| `test_repair_batch1.py` | 0 | `PASS v6.41.0 batch1 steps 1-6 RV-07/RV-04/RV-17/F-03/F-01/A5v3/F-04` |
| `test_batch3_solana_producers.py` | 0 | `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards` |
| `test_sqd_coverage_probe.py` | 0 | `PASS SQD coverage probe: 12/12 offline groups` |
| `test_sqd_gap_repair.py` | 1（纪律拦截） | `PermissionError: W3 forbidden path: /Users/uravvv/.claude/skills/token-chip-analysis/.staging_b3/routeA_pilot/426649168.json.gz` |
| `invariant_scan.py` | 0 | `PASS invariant manifest: receipt_producers=81, receipt_consumers=118, transport_calls=65, atomic_writes=62, formal_entrypoints=61, exceptions=0` |
| `test_batch4_invariant_guards.py` | 0 | `PASS B4-G1: bare pool / labels / vertical slice / denominator injections` |
| `test_exemption_guards.py` | 0 | `PASS: exemption guards (EX-01 full-F-03)` |

修复测试在第 428 行调用 `parse_routea_cache` 时触发禁读拦截，文件打开前已拒绝，未读取夹具内容。未改测试夹具或绕过该限制；这项整套测试不能记为通过。

测试使用 `python3 -B scripts/tests/<文件>`，通过系统 tempfile 内的 `sitecustomize.py` 向 Python 子进程继承禁读、离线和禁止批量删除的拦截，并关闭字节码写入、保留临时目录。额外尝试的 `sandbox-exec` 因系统拒绝嵌套沙箱而未启动测试，随后采用上述 Python 拦截。辅助文件、测试日志和缓存位于 `/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/w3-checks-lzu3n9l5/`；测试生成的其他系统临时目录同样保留，未批量删除。

禁读披露：未读取 `~/.codex/` 或 memories，未读取 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`、其他 maintenance 目录、Desktop 或 Documents；子进程对上述 staging 夹具的访问已在打开前拦截。全程离线，未 commit、push、stash、checkout、reset 或创建 worktree。仓库内仅修改两个白名单代码文件及本报告。

调度方本机验收尚未执行：须对同一 finalized slot、相同 getBlock 请求体和端点比较 identity 与 `--compressed`，记录 curl 版本、实际 Content-Encoding、size_download、time_total、退出码、HTTP 状态及解析结果规范化摘要。编码以实际协商结果为准；若为 identity，应记录未观察到压缩收益。不得使用 ledger.bytes 衡量传输节省。
