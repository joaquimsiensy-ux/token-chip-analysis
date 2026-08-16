# 工单 F-04：EVM 观测件拒空 runtime code / 拒短值 / getCode 分叉对齐

> 执行者：codex（纯施工，改文件+跑测试，**禁止任何 git 操作**——commit 由调度方完成）
> 工作目录：本 worktree 根（分支 repair-20260815-g2，基线 ddba1871 v6.44.0）
> 总计划：同目录 plan.md 第 1 刀节（本工单为其可执行展开，冲突时以本工单为准）

## 背景

外部审查 F-04（P1）：`scripts/lib/evm_observation.py` 的正式 supply 观测 bundle 会接受"冻结块上 runtime code 为空"的目标（EOA 或该块尚未部署的地址），产 PASS bundle、供给 0——把不存在的 token 状态当权威冻结锚。同时 totalSupply/balanceOf 的 eth_call 返回值只用 `_HEX_VALUE`（`0x[0-9a-fA-F]+`）校验，接受 `0x0` 这类短值，不符合 ERC-20 ABI 定长 32 字节 returndata。另有一处分叉缝隙：三笔 eth_call 用 EIP-1898 blockHash selector，而 eth_getCode 用块号 `hex(as_of_block)`——code 指纹与供给读数可能属于不同分叉。

## 修改点（全部在 `scripts/lib/evm_observation.py`）

1. **`_eth_call_value`（约 :66-70）**：在现有 `_HEX_VALUE.fullmatch` 之后追加长度断言——返回值必须**恰为 66 字符**（`0x`+64 hex，严格 32 字节 ABI word）。零值合法形态是 `0x` 加 64 个 `0`，`0x0` 短值必须拒。⚠️ 不要改 `_HEX_VALUE` 正则本身——它还被 `_quantity` 用于块号/chainId 等 QUANTITY 类型，短 hex 在那里是 JSON-RPC 规范合法形态。
2. **producer `observe_evm_supply` 的 getCode 段（约 :191-198）**：
   a. `code_params` 从 `[canonical_token, hex(as_of_block)]` 改为 `[canonical_token, block_selector]`（复用 :169 已构造的 `{"blockHash": …, "requireCanonical": True}`），使 code 读数与三笔供给调用锚定同一条已确认分叉；
   b. 在现有 `_HEX_DATA.fullmatch` 校验后追加：`code_raw == "0x"` → raise `EvmObservationError`（正式观测目标必须是已部署合约；零供应合约合法但 code 必非空）。
3. **`_validate_transcript`（约 :260-326）对称收紧**：
   a. :298 处 getCode params 期望从 `[token, hex(as_of)]` 改为 `[token, selector]`（selector 已在 :289 构造）；
   b. :311-316 三笔 eth_call 结果值追加 66 字符断言；
   c. :317-319 getCode 结果追加拒 `"0x"`。
4. **`validate_evm_observation_bundle`（约 :392-395）**：`runtime_code_sha256` 不得等于空字节串的 SHA256 常量 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`（用 `hashlib.sha256(b"").hexdigest()` 计算比对，不要硬编码字符串字面量）。

## 新测试文件 `scripts/tests/test_evm_observation_nonempty_code.py`

仿照 `scripts/tests/test_evm_observation.py` 的 FakePool + `mock.patch.object` 手法（可 import 复用其 FakePool，若不可直接 import 则本地精简复制并注明来源）。用例至少覆盖：

- 负向：getCode 返回 `0x`（EOA 形态）→ producer raise；
- 负向：totalSupply 返回 `0x0` 短值 → raise；
- 负向：人为构造 bundle，`code.runtime_code_sha256` 为空字节串哈希 → validator raise；
- 负向：transcript 第 7 笔（getCode）params 用旧块号形态 → transcript 校验 raise；
- 绿例：零供应但已部署合约（三笔返回 66 字符全零 word、code 非空）→ 全链通过。

测试文件风格对齐仓库惯例：自建 `main()` runner、非 pytest、退出码 0/1。

## 先红后绿纪律（必须按此顺序）

1. 先写测试文件，对**未修改的基线代码**运行：负向用例应体现"基线不拒绝"（测试 FAIL）。把完整输出保存到 `maintenance/repair-20260815-g2/f04_red.log`。
2. 再改生产代码，重跑测试全绿，输出保存到 `maintenance/repair-20260815-g2/f04_green.log`。

## 存量测试适配（授权范围，仅限因本刀语义变更必然打红的）

getCode selector 与 66 字符收紧会打红既有夹具/断言。**只允许**适配以下文件中与本刀语义直接相关的断言与夹具（每处修改在 done 报告列明理由）：
- `scripts/tests/test_evm_observation.py`（FakePool 的 getCode params 处理、transcript 期望）
- `scripts/tests/test_evm_observation_release.py`
- 其他测试若因本刀打红：**停下，把红名单写进 done 报告，不要扩大修改**——由调度方裁决。

## 验收标准（codex 自查后在 done 报告声明）

- `python3 scripts/tests/test_evm_observation_nonempty_code.py` 绿；
- `python3 scripts/tests/test_evm_observation.py`、`test_evm_observation_release.py`、`test_supply_truth_gate.py`、`test_batch3_evm_vertical_slice.py` 绿（最后一项需本机 loopback，若沙箱 EPERM 则如实记录留调度方复跑）；
- 未触碰授权清单之外的任何生产文件。

## 硬约束

- 只改：`scripts/lib/evm_observation.py` + 新测试文件 + 上述授权存量测试。
- 禁碰：VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、`scripts/report/`、`scripts/evm/`、`scripts/tests/run_all.py`、invariant/contract manifest（中心登记归末刀）。
- 禁止 git add/commit/push/branch 等一切 git 写操作。
- 完成后写 `maintenance/repair-20260815-g2/workorder_F04_done.md`：改动清单（文件+函数+行为）、红绿证据文件指引、存量适配清单及理由、遗留问题。
