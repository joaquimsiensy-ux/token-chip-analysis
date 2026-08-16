# 批 1 步骤②施工报告：RV-04 代理统一解析器＋RV-17 stake_decode 假闭合

施工范围严格限定为 `maintenance/repair-20260814-batch1/plan.md` 的“修复 4”。未执行任何 git 命令，未改 RV-07 生产实现，未改 `archive/`，未改 `references/environment.md:64-65` 历史坑记录。

## ① 不变量

### RV-04

1. 本批收编的 10 个现役代理取值点只从 `scripts/lib/proxy_config.py::resolve_proxy()` 取得代理；用户切换代理软件时，以 `CHIP_PROXY` 为单一环境配置面。
2. 优先序固定为：显式 CLI `--proxy`（包括空字符串）＞ `CHIP_PROXY`＞本机 TCP 端口探测（6152 后 7897）＞直连 `None`。
3. `--proxy ''`、大小写不敏感的 `none` 均表示显式直连，必须压过环境变量与探测。
4. 只接受 `http://`、`https://`、`socks5://`；非法 scheme/残缺 URL fail-closed。异常和日志不得泄露代理 URL 中的用户名、密码。
5. TCP 探测只证明端口有监听者，不证明代理协议或上游可用；探测命中必须打印固化 `CHIP_PROXY` 的提示，不做错误驱动的隐式多后端轮换。
6. 现役 Python/shell 文件不得在统一解析器之外出现旧端口字面量；`archive/` 与 `references/environment.md:64-65` 的考古/坑记录豁免。
7. `fetch_sqd_transfers_v2` 保持直连优先：只有 SSL/连接异常才切换解析出的候选代理，并在成功切换后粘住；不得改成代理优先。
8. `RpcPool.trust_env=False` 保持不动；显式解析结果经 `proxy=` 传入。`curl_json` 用 `-x` 消费显式代理，`http_get_many` 用 `httpx.AsyncClient(proxy=...)` 消费显式代理。

### RV-17

`stake_decode` 的闭合是“签名页完整观测＋每笔交易成功解码＋每个池 ATA 余额成功观测”三者的合取。任何一项缺测时：

- 不得把缺失值替换成 0；
- `data/stake_ledger.json` 必须写 `complete=false`、`verdict=ERROR` 和错误原因；
- 进程退出非零；
- stdout/stderr 不得出现正式字样 `[闭合]`。

只有三类观测全部成功后才计算账本与链上余额之差，才允许输出 `[闭合]`。

## ② 同族 rg 清单与查证结论

### 施工前查证

执行：

```bash
rg -n '7897|PROXY|--proxy|proxy=' scripts/solana scripts/evm scripts/lib --glob '*.py' --glob '!archive/**'
```

确认计划点名的 10 个硬编码/失效默认点：

- 无覆盖参数：`stake_decode.py`、`fast_probe_tops.py`、`gas_origin.py`、`trace_wallet.py`；
- 有失效默认/自动注入：`accounting_gate.py`、`fetch_sqd_transfers_v2.py`、`audit_closed_accounts.py`、`whale_deep.py`、`probe_escrows.py`、`probe_window_moves.py`。

另有不带硬编码默认的既有 `--proxy` 面：`decode_txs.py`、`decode_txs_v2.py`、`supply_truth_gate.py`、`verify_recon.py`、`price_check.py` 等。按计划“不在本批强制收编面”保留实现，仅点名 docstring/help 去掉固定端口示例；没有擅自扩大为全库网络层重构。

### 施工后查证

执行：

```bash
rg -n 'resolve_proxy\(' scripts --glob '*.py' --glob '!archive/**'
rg -n '7897' scripts --glob '*.py' --glob '*.sh' --glob '!archive/**'
rg -n '7897' references --glob '*.md' --glob '!archive/**'
rg -n -i 'clash' scripts references --glob '*.py' --glob '*.sh' --glob '*.md' --glob '!archive/**' --glob '!references/environment.md'
```

结论：

- 10/10 点均可查到 `resolve_proxy()` 接线；
- 现役 `.py/.sh` 的 7897 只剩 `scripts/lib/proxy_config.py` 的正式回退候选一处；测试守卫对解析器作唯一豁免，其他现役代码零命中；
- references 的 7897 只剩明确要求不改的 `references/environment.md:64-65` 两条历史坑记录；
- 排除该历史文件与 archive 后，“走 clash 代理”叙述族零命中，统一为 `CHIP_PROXY`/`--proxy`＋`scripts/lib/proxy_config.py` 口径；
- `scripts/lib/net.py:RpcPool._client_kwargs()` 的 `trust_env=False` 原样保留。

### 10 点接线结论

| 文件 | 接线结果 |
|---|---|
| `scripts/solana/stake_decode.py` | 新增 `--proxy`；curl 仅在解析结果非空时拼 `-x`；RV-17 独立 fail-closed |
| `scripts/solana/fast_probe_tops.py` | 新增 argparse/`--proxy`；mint 加载移到 parse 后，`--help` 不再依赖工作目录配置 |
| `scripts/solana/gas_origin.py` | 新增 `--proxy`；兼容 `none`/空串直连 |
| `scripts/solana/trace_wallet.py` | 新增 `--proxy`；curl 显式消费解析结果 |
| `scripts/evm/accounting_gate.py` | CLI 或 `CHIP_PROXY` 显式给值时统一解析；未给值的 Alchemy URL 才触发端口探测；非 Alchemy 默认直连语义保留 |
| `scripts/solana/fetch_sqd_transfers_v2.py` | `HS_FALLBACK_PROXY=None`；仅启用 HyperSync 时解析候选；保持直连异常后切代理并粘住 |
| `scripts/solana/audit_closed_accounts.py` | 默认改 `None`；解析后传给既有 `Rpc` |
| `scripts/solana/whale_deep.py` | 默认改 `None`；旧 `none` 语义收编到统一解析器 |
| `scripts/solana/probe_escrows.py` | 默认改 `None`；curl 可显式直连 |
| `scripts/solana/probe_window_moves.py` | 默认改 `None`；解析结果透传既有 `rpc(url, proxy, ...)` |

## ③ 三件套测试与先红后绿实跑证据

### a. 原反例：先红后绿

先只追加测试后执行：

```bash
python3 scripts/tests/test_repair_batch1.py
```

真实红态退出码：`1`。关键输出：

```text
RV17 LEGACY_COUNTEREXAMPLE rc=0 verdict=missing complete=missing false_closure=yes
AssertionError: (None, "... 签名拉取失败 ... 池链上余额 0 raw 差=0 [闭合] ...")
```

该反例在本地 `holders_accounts.json` 放入已知 ATA，并把全部 RPC 观测固定为 `None`；修前没有网络依赖，稳定重放“空账本 0 对默认余额 0”的假闭合。

修复后同命令真实退出码：`0`。关键输出：

```text
RV17 FIXED rc=1 verdict=ERROR complete=false false_closure=no
RV04 LEGACY_INJECTION chip_proxy_ignored=yes selected_fixed_port=yes
RV04 FIXED chip_proxy_wins_probe=yes selected_env=yes
PASS v6.41.0 batch1 steps 1-2 RV-07/RV-04/RV-17
```

RV-04 的原代码证据由施工前 `rg` 固定；回归内另保留等价 legacy 注入，证明旧固定端口路径忽略 `CHIP_PROXY`，再证明修后环境值压过探测。

### b. 同族变体

- 代理优先序：显式 CLI 胜 `CHIP_PROXY`；`CHIP_PROXY` 胜探测；`''`、`none`、` NONE ` 均显式直连并阻止探测。
- 探测：6152 命中立即选用；6152 拒绝后才尝试旧回退端口；提示行逐字断言。
- 凭据：带 user/password 的 CLI 与环境代理能正常返回真实值供 transport 使用，但 `redact_proxy()` 输出不含密码。
- RV-17：除“签名页失败”原反例外，另测“签名页成功但交易解码失败”和“签名页完整但余额失败”；三者全部 `rc=1/ERROR/complete=false` 且无 `[闭合]`。
- 结构接线：10 个目标文件必须各含 `resolve_proxy()`；`curl_json` 实际 subprocess 参数必须含 `-x socks5://...`。

### c. 失败分支

- `ftp://...`、无 scheme、残缺 `http://` 均抛“非法代理”，不降级到直连或探测。
- 没有 CLI、没有 `CHIP_PROXY`、两个候选端口均未监听时返回 `None` 直连；不伪造一个不可达代理。
- TCP 探测命中僵尸/错误协议端口的已知边界保持显式：解析器不假定请求成功；本批没有加入透明错误驱动换路。
- RV-17 的部分账本即使已经形成，只要后续余额缺测，仍覆盖为诊断 `ERROR`，不发布正式闭合结论。

## ④ 新建代码六视角①②自审

### ① 字段来源审计

- `resolve_proxy()` 的结果只来自三类可重验输入：argparse 交付的 CLI 值、真实进程环境 `CHIP_PROXY`、对 `127.0.0.1` 两个登记端口的实时 TCP connect；没有调用者另传“探测成功”布尔值。
- CLI 是否显式直连由原始值 `''`/`none` 直接判定；环境变量是否设置用键存在性判定，空环境值不会误落入探测。
- URL scheme/host/port 从 `urllib.parse.urlsplit` 解析；日志展示值统一经 `redact_proxy()`，transport 仍取得未破坏的真实 URL。
- `stake_decode.complete` 不是调用者自报：只有签名页循环自然完成、所有目标交易取得结果、所有 ATA 余额取得且可解析时才写 `true`。
- `stake_decode.verdict` 来自实际 `onchain - ledger total`；任何缺测的 `ERROR` 来自捕获的具体观测阶段，不用 0 或空集合冒充原始观测。

结论：没有发现关键准入字段依赖无法离线/重放验证的自报值。端口探测的证据强度只声明为“监听存在”，未升级声称“代理可用”。

### ② 失败分支审计

- 非法 CLI/环境代理立即非零；错误信息只带脱敏值。显式空串/`none` 是用户选择，不属于错误回退。
- connect 失败按顺序尝试下一候选；均失败才直连。connect 命中会提示固化配置，不吞掉探测来源。
- `curl_json`/`http_get_many` 只透传解析结果；`RpcPool.trust_env=False` 未放宽，不会重新引入隐式 shell 代理。
- HyperSync 仍先直连；没有候选代理时连接异常按原异常路径处理，不用 `proxies={http: None}` 假重试；切换日志对候选 URL 脱敏。
- `stake_decode` 的签名页、交易、余额任一路失败都走同一诊断写入和 `return 1`；成功闭合输出位于 try 成功路径之后，错误路径无法到达。
- 诊断文件写入本身若发生 OS 级写失败会让异常继续向上形成非零进程，不会落到 `[闭合]`；没有“warning 后继续成功”路径。

结论：新解析器与 RV-17 重写在六视角①②下未发现新的自报准入或 fail-open 成功分支。未把本批范围外其他分析工具的既有业务完整性语义混入本修复。

## ⑤ 归因预判确认

### RV-04

确认归因：**历史漏检**。固定端口和分散代理取值早于本批基线；08-12 从 Clash 切换到 Surge 只是让既有假设失效并暴露问题，不是本批 repair diff 新造，也不是此前某一 finding 的未闭合修复。

最强替代解释是“老问题修复不全”：过去已有若干脚本支持 `--proxy`，可视为代理问题曾被局部处理。但此前没有“现役代码不得硬编码代理端口、凡本批代理值经单一解析器”的已批准不变量，也没有统一修复工单；无默认值的既有入口本批仍被计划明确排除。因此本次按历史漏检，不按半修残留。流程动作：保留全库固定端口守卫和 10 点接线守卫，代理软件迁移后不再靠人工搜索逐件改。

### RV-17

确认归因：**历史漏检**。`rpc() -> None`、`all_sigs()` break、余额默认 0、最终比较 0==0 的链条在本批前已经存在；代理修复只能提高当前连通率，不能关闭上游未来失效时的假闭合。

最强替代解释是“RV-04 的半修残留”：假闭合常由旧代理不可达触发，表面上像代理修好即可消失。不采纳理由是反例直接 mock RPC 为 `None`，完全绕开代理选择仍稳定假闭合；故病根是独立的观测完整性 fail-open。流程动作：对闭合/对账工具把“每个必需观测失败”纳入失败分支测试，不以当前网络可连替代完整性证明。

## 改动文件清单

### 新建

- `scripts/lib/proxy_config.py`
- `maintenance/repair-20260814-batch1/step2_rv04_rv17_report.md`

### 生产代码与测试

- `scripts/lib/net.py`
- `scripts/evm/accounting_gate.py`
- `scripts/solana/stake_decode.py`
- `scripts/solana/fast_probe_tops.py`
- `scripts/solana/gas_origin.py`
- `scripts/solana/trace_wallet.py`
- `scripts/solana/fetch_sqd_transfers_v2.py`
- `scripts/solana/audit_closed_accounts.py`
- `scripts/solana/whale_deep.py`
- `scripts/solana/probe_escrows.py`
- `scripts/solana/probe_window_moves.py`
- `scripts/tests/test_repair_batch1.py`

### docstring/CLI help 与 references

- `scripts/lib/supply_truth_gate.py`
- `scripts/evm/fetch_alchemy.py`
- `scripts/evm/staged_capture.sh`
- `scripts/solana/decode_txs_v2.py`
- `scripts/prices/price_check.py`
- `references/data-pipeline-solana-capture.md`
- `references/data-pipeline-solana-scan.md`
- `references/data-pipeline-evm-channels.md`
- `references/data-pipeline-evm-sources.md`
- `references/labels/MAINTENANCE.md`

## 验证命令与结果

| 命令 | 退出码 | 结果摘要 |
|---|---:|---|
| `python3 scripts/tests/test_repair_batch1.py` | 0 | RV-07 保持绿；RV-04 legacy/fixed、优先序/探测/非法 scheme/残留守卫；RV-17 三类缺测均 ERROR |
| `python3 -m py_compile <全部 17 个改动 .py>` | 0 | 无语法错误 |
| `python3 scripts/tests/invariant_scan.py` | 0 | `receipt_producers=54, receipt_consumers=63, transport_calls=62, atomic_writes=47, formal_entrypoints=58, exceptions=0` |
| `python3 scripts/tests/docs_lint.py --all` | 0 | `58 个文档，引用无断链、粗体配对完整` |
| `python3 scripts/solana/stake_decode.py --help` | 0 | 显示 `--proxy PROXY`，未读取 mint/未探测网络 |
| `python3 scripts/solana/fast_probe_tops.py --help` | 0 | 显示 `--proxy PROXY`，不再因缺 `config.json` 阻断 help |
| `python3 scripts/solana/gas_origin.py --help` | 0 | 显示 `--proxy PROXY` |
| `python3 scripts/solana/trace_wallet.py --help` | 0 | 显示 `--proxy PROXY` |
| `python3 scripts/tests/test_net_result.py` | 0 | net Result/curl_json 既有分类保持通过 |
| `python3 scripts/tests/test_sqd_merge_equiv.py` | 0 | `fetch_sqd_transfers_v2` 六条契约全过 |
| `python3 scripts/tests/test_batch1_rpc_attestation.py` | 0 | wrong-chain/fail-closed/failover 回归通过 |

本步骤没有执行 live token/地址采集；四件无参数工具按本步骤硬验收要求执行的是 `--help`，网络选择与失败路径由无外网依赖的 mock 反例覆盖。最终交付状态以本报告落盘后的再次强制验收结果为准。
