# 工单 F-04 补充轮：调度方裁决——授权适配两个存量夹具

> 前置：workorder_F04.md 主体已完成（done 报告在案）。本补充轮处理其"遗留问题"第 1/2 项。
> 调度方已本机复核两项红因，均为存量夹具生成本刀明确拒绝的旧协议形态，裁决授权适配。

## 授权适配范围（仅此两文件，仅夹具形态）

1. `scripts/tests/test_supply_truth_gate.py` 的 `write_evm_bundle` 共享夹具 helper：
   - 三笔 eth_call 结果从短 `hex(...)` 补成 66 字符 32 字节 ABI word；
   - transcript 第 7 笔 getCode params 改为 EIP-1898 block selector 形态（与生产 `_validate_transcript` 新期望一致）；
   - getCode 结果保证非空 code；
   - 若 bundle 的 `code.runtime_code_sha256` 由夹具计算，保持与 transcript code 一致且非空字节串哈希。
2. `scripts/tests/test_batch3_evm_vertical_slice.py` 的 FixtureHandler：
   - eth_call 供给三值改为 66 字符 word（本机复核确认现返回 `hex(amount)` 短值被拒）；
   - eth_getCode 分发按新 selector 参数形态响应且返回非空 code；
   - ⚠️ 不改动该测试的其他业务断言与场景旋钮（错链负测、methods 录音带等）。

## 验收

- `python3 scripts/tests/test_supply_truth_gate.py` 绿（你可直接跑）；
- `test_batch3_evm_vertical_slice.py` 你的沙箱 loopback EPERM 跑不了——做完静态适配即可，由调度方本机复跑验收；
- 重跑 `test_evm_observation.py`、`test_evm_observation_release.py`、`test_evm_observation_nonempty_code.py` 确认不回归；
- 在 `workorder_F04_done.md` 末尾追加"补充轮"一节：改动点、理由、验收输出。

## 硬约束（同主工单）

仅改上述两个测试文件；禁碰一切生产文件与其他测试；禁止 git 操作。
