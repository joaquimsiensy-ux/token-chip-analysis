# 批 1 步骤⑥施工报告：F-04 v2 位置 token 移除＋枚举回归＋secret 不进输出

施工范围严格限定为 `maintenance/repair-20260814-batch1/plan.md` “修复 5：F-04 v2 位置 token 移除”及本任务书指定同族等深面。未执行任何 git 命令，未改 `archive/`，未触碰步骤①–⑤的 proxy/replay/fig1/A5/发布闸/receipt_kernel 生产面，未改版本号、CHANGELOG 或 manifest。SafeParser 采用四文件内联，没有新增 lib 登记项。

## ① 不变量

1. 现役 HyperSync 采集入口只接受文件或环境变量中的 API secret，不再接受位置 token；v2 删除 `api_token` 后只剩 `from_block` 一个位置参数。
2. 四入口 token 取用顺序统一为：显式 `--token-file` ＞ `HYPERSYNC_TOKEN` ＞模块常量 `DEFAULT_TOKEN_FILE` 指向的默认文件。
3. `--token-file` 的 argparse default 必须为 `None`；只有这样 `_load_token(ap, token_file)` 才能区分“用户显式指定文件”与“未指定，先查 env”。
4. token 文件缺失或为空统一走 `ap.error()`，退出码为 2；不再由 v2 的 `sys.exit(str)` 产生另一套失败语义。
5. 旧位置 token 无论落到 `from_block` 的整数解析失败，还是成为多余参数，都必须非零拒绝，并且 sentinel secret 不得出现在 stdout/stderr。
6. `fetch_hypersync_v2.py` 的 `verify-done` / `--refresh-manifests` argv 嗅探分发保持原样；唯一 shell 调用方仍以最后一个位置参数传 `from_block`，不传 token。
7. 自动枚举回归的分母不能依赖 `HYPERSYNC_TOKEN` 字面量；SDK import、`hypersync.xyz` endpoint/采集器命名、正式入口登记面三路证据取并集，发现新入口但缺参数夹具时测试硬失败。

## ② 同族 `rg` 清单与查证结论

### 施工查证命令

```bash
rg -n 'HyperSync|hypersync\.xyz|HYPERSYNC_TOKEN|api_token|token-file|from_block|parse_args|resolve_token' \
  scripts/evm/fetch_hypersync*.py scripts/evm/fetch_pool_swaps.py \
  scripts/tests/test_token_no_positional.py scripts/tests/test_repair_batch1.py

rg -n 'fetch_hypersync_v2\.py' scripts/evm \
  --glob '*.sh' --glob '*.py' --glob '!fetch_hypersync_v2.py'

rg -n 'hypersync-token-file|HYPERSYNC_KEY' \
  scripts/evm/accounting_gate.py scripts/robinhood/pull_transfers.py scripts/robinhood/gas_trace.py
```

### 同族实施点

| 同族面 | 文件 | 查证/处置 |
|---|---|---|
| v2 正式首选入口 | `scripts/evm/fetch_hypersync_v2.py` | 删除位置 `api_token`；抽模块级同步 `parse_args(argv=None)`；改 `_load_token(ap, token_file)`；新增 `DEFAULT_TOKEN_FILE`；`--token-file default=None`；main 消费 `a.token` |
| v1 Transfer 入口 | `scripts/evm/fetch_hypersync.py` | 内联 SafeParser；`from_block` 改用隐藏输入值的整数 type；多余参数不再逐字回显 |
| v1 logs 入口 | `scripts/evm/fetch_hypersync_logs.py` | 同深处理 SafeParser＋`from_block` 安全整数解析 |
| v1 pool swaps 入口 | `scripts/evm/fetch_pool_swaps.py` | 同深处理 SafeParser＋`--from-block` 安全整数解析；位置 sentinel 作为多余参数被隐藏拒绝 |
| 自动枚举回归 | `scripts/tests/test_token_no_positional.py` | 手写三文件白名单替换为组合判据自动分母；实际分母=4；每支覆盖位置拒绝、前置/尾随 sentinel 无输出、三层优先序、空/缺 token 文件 exit 2 |
| 批 1 回归 | `scripts/tests/test_repair_batch1.py` | 追加 F-04 v2 无 `--token-file` 时 env 生效、显式文件覆盖 env、无 env 时默认文件生效 |
| 权威文档 | `references/data-pipeline-evm-channels.md` | “三支 v1”改为 v1 三支＋现役 v2；补非法输入不得回显 secret |
| v2 模块说明 | `scripts/evm/fetch_hypersync_v2.py` | 删除旧位置兼容和反向优先序说明；`_load_token` docstring 同步新口径 |

### 调用方与外围剔除

- `scripts/evm/staged_capture.sh` 是实际命中的唯一 v2 shell 调用方；两处调用均以 `"$FROM"` 传唯一位置块高，没有位置 token，删除兼容参数不破坏下游。
- `scripts/evm/config.example.json:21` 已明确写成“显式 `--token-file`、`HYPERSYNC_TOKEN`、默认文件”，与修后实现一致，核对后不改。
- `scripts/evm/accounting_gate.py` 的 `--hypersync-token-file` 是文件路径，不把 secret 放入 argv/ps；它不是本次位置明文 token 漏洞。
- `scripts/robinhood/pull_transfers.py` 与 `scripts/robinhood/gas_trace.py` 使用 `HYPERSYNC_KEY`、优先读 exploration 的 `config.json`，不属于正式候选链入口；按计划点名核对但不改。

## ③ 三件套测试与先红后绿实跑证据

### 修前红灯

先只改 `test_token_no_positional.py`，未动生产代码。自动枚举器修正为准确分母后，命令真实退出码为 **1**：

```text
AssertionError: fetch_hypersync_token_contract 将 sentinel secret 写入 stdout/stderr
... error: argument from_block: invalid int value: 'plaintext-secret'
```

这条红灯证明旧 v1 同族会把 sentinel 经 argparse stderr 泄进日志。

v2 修前没有模块级 `parse_args`，因此另用不改文件的等价探针运行它原有 `main()` 内 parser，并在 `resolve_token` 调用点截获 namespace。输入为 `['plaintext-secret', '0', '--token-addr', ...]`；探针约定“`api_token` 等于 sentinel 且 `from_block==0`”时退出 17，真实结果为 **exit 17**。这证明旧 parser 接受位置 secret；不是通过源码推测代替运行。

测试开发期间第一次组合枚举把只在说明文字提到 HyperSync 的 replay 误纳入，exit 1（`ModuleNotFoundError: channels_preflight`）。该次不计作 F-04 红灯；枚举条件随后收紧为采集器证据，实际分母稳定为四入口。

### 修后绿灯

| 场景 | 结果 |
|---|---|
| 自动枚举分母 | 4：`fetch_hypersync`、`fetch_hypersync_logs`、`fetch_hypersync_v2`、`fetch_pool_swaps` |
| sentinel 放在参数前部 | 四支均 SystemExit 非零，stdout/stderr 不含 sentinel |
| sentinel 放在完整合法 argv 尾部 | 四支均按“未识别参数，输入值已隐去”拒绝，stdout/stderr 不含 sentinel |
| 显式 token 文件＋env 同时存在 | 四支均取显式文件 |
| 无显式文件、env 存在 | 四支均取 env；v2 的 `args.token_file is None` |
| 无显式文件、无 env | 四支均取测试冻结的默认文件 |
| 显式空文件或缺文件 | 四支均 `ap.error()` / exit 2 |
| v2 旧双位置输入 | 第一个值落到安全整数解析，SystemExit 非零且不回显 secret |

## ④ 新建代码六视角①②自审

| 视角 | 自审结论 |
|---|---|
| ① 正确性/不变量 | v2 `parse_args` 与三支 v1 结构一致：SafeParser → 单一块高参数 → `--token-file default=None` → `_load_token` → `a.token`；显式文件、env、默认文件三条互斥分支均有测试 |
| ② 反例/失败分支 | 覆盖 from_block 非整数、多余参数、前置/尾随 sentinel、空文件、缺文件；拒绝不仅看非零，还检查 stdout/stderr 全量拼接中无 sentinel |
| ③ 证据链/分母 | 自动枚举不以“已实现 env 读取”为入选条件，避免新入口恰好漏实现 `HYPERSYNC_TOKEN` 时被分母漏掉；实际枚举数强制 ≥4 且四个已知入口必须为子集 |
| ④ 兼容/迁移 | v2 的 verify/refresh 分发未改；`staged_capture.sh` 调用形态已复核；删除的只是明文位置 token 兼容，属于不变量要求的有意破坏性收紧 |
| ⑤ 安全/日志 | 自定义整数 type 不拼入原值；SafeParser 对 extras 只报固定文案；token 内容不参与错误消息；测试同时捕获 stdout/stderr |
| ⑥ 可维护/登记 | SafeParser 仅在四个现役入口各内联约 15 行，避免新增共享 lib 与步骤⑦登记债务；自动枚举让未来入口默认进入安全回归，缺 fixture 即 fail-closed |

保留边界：argparse 的其他业务参数仍使用既有类型；本步按计划封闭的是旧位置 token 可能落入 `from_block` 或 extras 的泄密路径，不扩张为全库通用敏感参数框架。

## ⑤ 归因预判确认

**确认：老问题修复不全（半修残留）。**

- r9 RA-07 已明确点名三支 v1 有“禁止位置 token”回归，但现役首选 v2 未纳入同族清单并保留位置明文 token。
- 修前自动分母是手写三文件，v2 正好落在分母外；这不是新功能引入后尚未来得及覆盖，而是同一密钥治理修复只关了 v1、没有把现役 v2 关到同一深度。
- 同族等深复核又证明 v1 的“拒绝”仍会把非法值回显到 stderr；原安全目标只做到“拒绝位置 token”，没有做到“secret 不进输出”，因此仍属同一修复面的半闭合。
- 按归因从严规则①，已有修复声明/测试面但同族和失败输出未闭合，不能降格为普通历史漏检。

## 改动文件清单

- `scripts/evm/fetch_hypersync.py`
- `scripts/evm/fetch_hypersync_logs.py`
- `scripts/evm/fetch_hypersync_v2.py`
- `scripts/evm/fetch_pool_swaps.py`
- `scripts/tests/test_token_no_positional.py`
- `scripts/tests/test_repair_batch1.py`
- `references/data-pipeline-evm-channels.md`
- `maintenance/repair-20260814-batch1/step6_f04_report.md`

## 验证命令与结果

| 命令 | 退出码 | 结果摘要 |
|---|---:|---|
| `python3 scripts/tests/test_token_no_positional.py` | 0 | 自动枚举 4 个入口；位置 secret 拒绝、sentinel 不进 stdout/stderr、三层优先序、空/缺文件失败全过 |
| `python3 scripts/tests/test_repair_batch1.py` | 0 | 步骤①–⑤既有回归继续通过，新增 F-04 v2 优先序三分支通过 |
| `python3 scripts/tests/invariant_scan.py` | 1 | **按步骤⑦边界预期**，仍精确 4 discrepancy：`figure1-legend/v1` producer 新缺/旧多 2 项＋fig1 receipt/PNG atomic writer 2 项；F-04 零新增差异 |
| `python3 scripts/tests/docs_lint.py --all` | 0 | 58 个文档引用无断链、粗体配对完整 |
| `python3 -m py_compile scripts/evm/fetch_hypersync.py scripts/evm/fetch_hypersync_logs.py scripts/evm/fetch_hypersync_v2.py scripts/evm/fetch_pool_swaps.py scripts/tests/test_token_no_positional.py scripts/tests/test_repair_batch1.py` | 0 | 四入口与两测试文件语法通过 |

`invariant_scan.py` 的 exit 1 不是本步新失败；四条输出与步骤⑤报告记录逐项相同，留待步骤⑦统一登记收口。
