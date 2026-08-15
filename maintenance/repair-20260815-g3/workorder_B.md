# 工单 B（AI-3 / repair-20260815-g3）：F-06 备用采集器完整性修复 + Alchemy 正式资格除名

## 你的角色与硬边界

你是施工方，在本 worktree（分支 repair-20260815-g3）纯改文件。工单 A 已完成验收，本工单是第二批。硬边界：
1. **禁止 git 操作**（不 add/commit/push）
2. **只准改动**：`scripts/evm/fetch_sqd_evm.py`、`scripts/evm/fetch_alchemy.py`、`scripts/evm/csv_collector_receipt.py`、`scripts/evm/channels_preflight.py`、`scripts/tests/test_round4_csv_adapters.py`、`references/data-pipeline-evm-channels.md`；**新建**：`scripts/tests/test_g3_alt_collectors.py`、`maintenance/repair-20260815-g3/evidence_B_red.txt`、`maintenance/repair-20260815-g3/workorder_B_done.md`。其余文件一律不碰
3. 不注册测试进 run_all.py；不动 invariant manifest（若发现需登记项，如实写进 done 报告交融合方）
4. 全程零真实网络请求（测试一律 monkeypatch）
5. 措辞纪律：新增注释/文字用中性词（负向测试/协议异常/守卫）
6. done 报告里的命令输出必须真实跑出，禁止只声称

## 背景与实测定案（必读，这是修法依据）

上游审查发现两个备用 CSV 采集器把"数据源残缺/空响应"签成"完整拉取"（细节见下）。调度方已对 SQD Portal 完成三场景协议实测，结论在 `maintenance/repair-20260815-g3/sqd_probe_notes.md`（开工先读），要点：
- **SQD 正常响应永不为空正文**：零匹配区间也返回首末块的 header-only 哨兵行；每次响应末行的 `header.number` = provider 侧扫描前沿（无论哨兵行还是事件行）；续拉 `cur = 末行 number + 1`。
- 因此：**空正文 = 协议/网络异常**，绝不能当"已扫描"推进。现有代码空正文时 `last_block` 保持 `cur`、再 `cur = last_block + 1`，等于把异常当"该块扫完"**悄悄跳块丢数据**——这是本工单要关死的核心缺陷。
- **SQD 保留正式 receipt 资格**（块游标语义成立）；**Alchemy 除名**（用户已裁决）：Alchemy 协议只有分页 pageKey、没有任何 provider 侧块进度证据，现有代码把请求参数 `a.to_block+1` 填进 receipt 的 `provider_next_block`（`evm-collector-run/v2` 定义该字段为 provider 块游标）属于自造值冒充数据源证据。schema 不升版。

## 任务 1：新建测试 test_g3_alt_collectors.py 并对基线取红证（先红后绿的"先红"步）

测试文件风格参照 `scripts/tests/test_round4_csv_adapters.py`（纯标准库、独立可执行、打印 PASS/FAIL、exit 0/非零）。用 tempfile 目录做所有输出。分三层：

**主路径层（mocked transport，修复前应红）**：
- R1（SQD 空响应假完成）：进程内 `import fetch_sqd_evm` 后替换其模块级 `requests` 引用为伪对象（`Session().post` 恒返回 status_code=200、text="" 的伪 Response；显式 `--to-block` 使 finalized-head 的 get 不触发）。patch `sys.argv` 为小区间（如 10→12）带 `--receipt` 调 `main()`，捕获 `SystemExit`。断言：**必须非零退出、receipt 文件不存在、输出带 `.partial` 后缀（或不存在）**。基线行为是零行"完成"+签出 receipt → 此断言在基线必红。
- R2（Alchemy 空 result 假完成）：`import fetch_alchemy` 后替换其 `attested_rpc_pool` 为伪 pool（`attest()` 无操作、`call()` 恒返回 `{"ok": True, "result": {}}`）。不带 `--receipt` 跑 main。断言：**必须非零退出**（协议错误重试尽）。基线行为是零转账 exit 0 打印 COMPLETE → 基线必红。
- R3（SQD 部分推进后遇异常不能签）：伪 post 第一次返回一行合法哨兵（如 `{"header":{"number":10,...}}`），之后恒空文本。断言：非零退出、receipt 不存在、输出 `.partial`。

**纯函数层（修复后新函数的行为规格，基线跑不了属正常——测试里对函数缺失时给出 SKIP-RED 计数即可）**：
- SQD `parse_stream_response(text)`：空/全空白文本 → `(rows, None)`；含哨兵行 → last_block 正确提取；行缺 `header.number` 或非法 JSON → raise ValueError
- Alchemy `validate_transfers_page(...)`：缺 `transfers` 键 → ValueError；transfer 缺 `rawContract.value` 或值非合法 hex → ValueError；`blockNum` 超出本次请求区间 → ValueError；`pageKey` 重复出现 → ValueError；合法空 `transfers`+无 `pageKey` → 正常返回（合法零事件页）

**除名负测层（基线应红）**：
- `emit_native_receipt` 以 `fetch_alchemy.py` 为 collector → 必须 raise ValueError（基线接受 → 红）
- `channels_preflight` 对 alchemy 签的 receipt → 必须拒（用其现有校验入口构造最小 receipt fixture；基线接受 → 红）
- `fetch_alchemy.py --receipt x.json` → argparse SystemExit code 2（基线要求显式 to-block 但不拒 receipt 本身 → 红）

**取红证**：写完测试先跑 `python3 scripts/tests/test_g3_alt_collectors.py`，把输出（应含各红项的 FAIL 明细）前 80 行原样存 `maintenance/repair-20260815-g3/evidence_B_red.txt`，注明基线 SHA（git rev-parse HEAD 只读允许）。

## 任务 2：fetch_sqd_evm.py 修复

1. 抽纯函数 `parse_stream_response(text)` → `(rows, provider_last_block | None)`：rows 为八列 CSV 行值列表（沿用现有解析逻辑：topics 提取 from/to、data 转 value、ts 转 ISO）；空正文/全空白 → `([], None)`；任一行 JSON 非法或 header 缺 number → raise ValueError（协议异常）
2. 主循环改造：
   - 200 响应 → 调纯函数。`provider_last is None` → 空响应计数 +1，打印告警，退避重试**不推进 cur**；连续 5 次 → 硬退（exit 3）
   - ValueError → 走现有 errs 退避路径（同 http 非 200），同样计入连续异常上限
   - 正常 → 计数清零、写行、`provider_frontier = max(provider_frontier, provider_last)`；`provider_last >= a.to_block` 才 break；`cur = provider_last + 1`
3. receipt 签发：显式断言 `provider_frontier >= a.to_block`（不满足硬退不签）；`emit_native_receipt(..., a.from_block, a.to_block + 1, provider_frontier + 1, ...)`——游标改为 provider 派生值（替换自造的 `a.to_block + 1`）
4. 正式前置（`--receipt` 时，在任何网络调用前）：receipt 路径与输出路径 `os.path.lexists` 均必须不存在（零字节/符号链接都算存在）；两路径 `os.path.realpath` 后不得相同。替换现有 `existed_before` 的 size>0 判据（探索模式的 resume 逻辑保留不动）
5. 失败卫生：本次运行新建的输出文件（mode=="w"），在任何非零退出路径上改名加 `.partial` 后缀且不打印 `[COMPLETE]`；探索续传（mode=="a"）的既有文件不改名，只打印告警

## 任务 3：fetch_alchemy.py 修复 + 除名

1. 文件顶部加 `FORMAL_CHANNEL_ELIGIBLE = False`，docstring 补一段除名说明：Alchemy 协议无 provider 侧块进度证据（仅分页 pageKey），`evm-collector-run/v2` 的块游标语义对它不成立，不支持正式 receipt，仅探索采集；恢复正式资格需升分型收据（后续候选）
2. `--receipt` 参数保留，argparse 解析后**立即** `ap.error("Alchemy 通道无 provider 侧完成证据，不支持正式 receipt，仅探索采集；正式备用通道请用 SQD")`——此检查与 config 校验都在建 pool/attest 之前
3. 删除文件尾部的 emit_native_receipt 调用块
4. 抽纯函数 `validate_transfers_page(res, req_from, req_to, seen_pagekeys)` → `(transfers, page_key)`：
   - res 非 dict、缺 `transfers` 键、或 transfers 非 list → ValueError
   - 每条 transfer：`blockNum` 为 hex str 且 int 落 `[req_from, req_to]`（req_to 为 None 时只验下界）；`hash`/`from`/`uniqueId` 非空 str；`to` 键必须存在（值可为 None）；`rawContract` 为 dict 且 `value` 为可 `int(v,16)` 的非空 str——**删除 float value×1e18 回退**
   - `pageKey` 若存在：非空 str 且不在 seen_pagekeys（重复 → ValueError），返回前加入 seen
5. 主循环：**整页先经纯函数验证，再写任何 CSV 行**；ValueError 走协议错误重试（现有 attempt 循环 err 分支），重试尽 `sys.exit(2)`；CSV 的 val 一律 `int(raw, 16)`
6. 失败卫生同任务 2 第 5 条

## 任务 4：除名三件套

1. `csv_collector_receipt.py`：`SUPPORTED` 改为 `{"fetch_sqd_evm.py"}`，旁加一行注释：`# fetch_alchemy.py 已除名：其协议无 provider 侧块进度证据，v2 块游标语义不成立；恢复需升分型收据`
2. `channels_preflight.py`：allowed 三支名单（hypersync/sqd/alchemy）去掉 alchemy
3. `test_round4_csv_adapters.py`：native-receipted 循环名单只留 `fetch_sqd_evm.py`；nonformal 断言名单（`FORMAL_CHANNEL_ELIGIBLE = False`）加入 `fetch_alchemy.py`

## 任务 5：references/data-pipeline-evm-channels.md 改口

先读该文档现状再改（保持原文风格）：
1. 约 36 行把 Alchemy 也纳入"严格前进且到达目标的 cursor"语义的表述，改为如实二分：SQD＝provider 哨兵行扫描前沿（附一句实测依据：零匹配区间也返回首末哨兵，空正文即协议异常）；Alchemy＝仅分页标记、无块进度证据
2. Alchemy 通道段补降级说明：仅探索采集、不支持正式 receipt、除名原因、恢复条件（升分型收据）
3. 不删既有契约字符串（`evm-collector-run/v2` 等原样保留）

## 任务 6：转绿与回归（全部真实跑）

1. `python3 scripts/tests/test_g3_alt_collectors.py` exit 0（全绿）
2. `python3 scripts/tests/test_round4_csv_adapters.py` exit 0
3. `python3 -m py_compile scripts/evm/fetch_sqd_evm.py scripts/evm/fetch_alchemy.py scripts/evm/csv_collector_receipt.py scripts/evm/channels_preflight.py` exit 0
4. `python3 scripts/tests/invariant_scan.py` exit 0（若因新写法报未登记项：不改 manifest，如实记 done 报告停等裁决）
5. `python3 scripts/tests/docs_lint.py --all` exit 0
6. `python3 scripts/tests/test_g3_docs_guards.py` exit 0（工单 A 产物不被本单破坏）

## 任务 7：done 报告 workorder_B_done.md

含：改动文件清单（每处一句话）、**红证据摘要**（evidence_B_red.txt 的关键 FAIL 行）、转绿输出摘要（任务 6 六条命令各 2-3 行）、存量口径声明（改脚本后旧 SQD/Alchemy native receipt 重验会拒；备用通道应零正式存量）、留账面（SQD receipt 无 chain 字段/dataset 任意名——本单不修交融合方；Alchemy 恢复资格候选）、边界自查声明。

执行顺序：读 sqd_probe_notes.md → 任务 1（先红取证）→ 2 → 3 → 4 → 5 → 6（转绿）→ 7。行号漂移按内容定位并如实记录；真边界冲突（必须动边界外文件）则停工写明等裁决。
