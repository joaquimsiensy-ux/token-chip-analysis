# 工单 F-04 施工结果

## 状态

生产修复和专属先红后绿测试已完成；工单点名的存量验收未全部通过，已按“其他测试打红即停止、不得扩大修改”约束停止施工。

- 专属 F-04 测试：PASS，5/5。
- 授权存量测试：2 组 PASS。
- 未授权存量测试：`test_supply_truth_gate.py` 因旧 EVM bundle 夹具与本刀新协议不兼容而 FAIL；未修改。
- loopback 纵切片：沙箱在 `socket.bind` 处返回 EPERM，未进入业务验证；留调度方在允许 loopback 的环境复跑。

## 改动清单

### `scripts/lib/evm_observation.py`

- `_eth_call_value`：保留 `_HEX_VALUE` 原正则，仅对 `eth_call` returndata 增加严格 66 字符断言，拒绝 `0x0` 等非 32 字节 ABI word。
- `observe_evm_supply`：`eth_getCode` 改用已经构造的 EIP-1898 `block_selector`，与三笔 `eth_call` 锚定同一 block hash；合法 hex data 后再拒绝空 runtime code `0x`。
- `_validate_transcript`：对称要求 getCode 使用相同 block selector、三笔 `eth_call` 结果恰为 66 字符、getCode 结果不得为 `0x`。
- `validate_evm_observation_bundle`：用 `hashlib.sha256(b"").hexdigest()` 计算并拒绝空字节串 runtime code 哈希，未硬编码哈希字面量。

### `scripts/tests/test_evm_observation_nonempty_code.py`（新增）

独立 `main()` runner，覆盖：

1. producer 拒绝 getCode=`0x`；
2. producer 拒绝 totalSupply=`0x0`；
3. validator 拒绝与空 code transcript 一致的空字节串哈希 bundle；
4. transcript validator 拒绝第 7 笔 getCode 的旧块号参数；
5. 零供应、非空 runtime code 合约从 producer 到持久化 bundle validator 全链通过。

## 先红后绿证据

- 红灯：`maintenance/repair-20260815-g2/f04_red.log`
  - 在生产代码未修改时运行 `python3 scripts/tests/test_evm_observation_nonempty_code.py`。
  - 4 个负向用例均因“基线接受了无效观测”而 FAIL；零供应合约绿例通过。
- 绿灯：`maintenance/repair-20260815-g2/f04_green.log`
  - 修复后运行同一命令。
  - 输出：`PASS F-04 EVM nonempty code and ABI word checks: 5/5`。

两次命令均设置 `PYTHONDONTWRITEBYTECODE=1`，避免测试在仓库生成缓存文件。

## 授权存量测试适配

- `scripts/tests/test_evm_observation.py`
  - FakePool 的三笔 `eth_call` 成功值改为 32 字节 ABI word。
  - 理由：原 `hex(value)` 是本刀明确拒绝的短 returndata；不改变 transport fake 的测试语义。
- `scripts/tests/test_evm_observation_release.py`
  - 对该测试复用的旧共享 bundle fixture 做本地适配：三笔调用结果补成 32 字节、getCode 参数改为 EIP-1898 selector，并刷新 transcript 输入绑定。
  - 理由：共享 helper 位于未授权文件 `test_supply_truth_gate.py`，不能直接修改；release 测试本身在授权范围内。

## 验收运行结果

- `python3 scripts/tests/test_evm_observation_nonempty_code.py`：PASS，5/5。
- `python3 scripts/tests/test_evm_observation.py`：PASS，10/10。
- `python3 scripts/tests/test_evm_observation_release.py`：PASS，11/11。
- `python3 scripts/tests/test_supply_truth_gate.py`：FAIL，exit 1。首个协议错误为 `transcript eth_getCode params mismatch`；其 `write_evm_bundle` 仍生成旧块号 getCode 参数，且三笔结果仍为短 `hex(...)`。该文件不在授权适配清单，故未修改并停止扩面。
- `python3 scripts/tests/test_batch3_evm_vertical_slice.py`：未完成，`ThreadingHTTPServer` 绑定 `127.0.0.1` 时触发 `PermissionError: [Errno 1] Operation not permitted`。静态检查同时可见其 fixture 仍以 `hex(amount)` 返回短 `eth_call` 值；调度方在可用环境复跑后预计仍需裁决该未授权夹具适配，本文不把未实际到达的业务结果写成已验证失败。

## 遗留问题与调度方事项

1. 决定是否另行授权适配 `scripts/tests/test_supply_truth_gate.py` 的 `write_evm_bundle` 夹具；当前该验收项确定为红。
2. 在允许 loopback 的本机环境复跑 `test_batch3_evm_vertical_slice.py`，并根据实际结果裁决其短 returndata fixture 是否授权适配。
3. 在上述两项收口前，不应声明本工单全部验收全绿。

## 约束自查

- 仅修改 1 个授权生产文件、1 个新增专属测试和 2 个授权存量测试；另新增工单要求的红绿日志与本 done 报告。
- 未触碰授权清单之外的任何生产文件。
- 未修改 VERSION、CHANGELOG、SKILL.md、r10_ledger.md、pyproject、`scripts/report/`、`scripts/evm/`、`scripts/tests/run_all.py` 或任何 manifest。
- 未执行任何 git 命令或 git 写操作。
