# 批 18 第四轮复核施工记录

日期：2026-09-01  
工作基线：`ec7c5927520000b6169f6a4c57805aad4d27213b`  
等价代码基线：`ad44909`  
版本：`7.0.0 -> 7.0.1`  
状态：**机械施工完成，RED/定向 GREEN/版本与 lint/白名单均完成，未 commit。本沙箱全量为 144/146 PASS，2 项仅因 localhost bind 权限失败，不记为 146 全绿。**

## 1. 开工门与先红证据

- `main/HEAD=ec7c592`；`git diff --name-status ad44909..main` 仅有 `batch18_review4_workorder.md`，代码零差异，按用户明确授权的等价工作基线开工。
- 开工时工作树 clean；生产改动前先追加 review4 两态回归，再落 `batch18_review4_red_evidence.txt`。
- RED SHA-256：`52effb55972791ecd7b38b8bce89e8df567333a3a31d474faf89993f3e880e3f`。
- RED 退出码 1；原文同时证明 `([], True, False)` 与 `([], False, False)` 均被错写为 `{"total": 0, "complete": None, "in_range": 0}`，而期望分别为 `complete=True/False`。

## 2. 唯一生产修复

- 仅改 `scripts/solana/audit_closed_accounts.py` 的 `signature_discovery` 空签名早退 `state.update`：
  `"sig_stat": {"total": 0, "complete": complete, "in_range": 0}`。
- 未改 `fetch_mint_sigs`、报告 builder、其他 bail 点、blocks/auto 语义或主路径。
- `complete=true` 只表达“完整查询且成功签名结果为空”，不表达“链上绝对没有任何历史”；`complete=false` 保留截断/失败语义。

## 3. 两态回归与既有契约

- review4 新回归对两份完整报告一次性成对断言 `mint_sig_history` 分别等于 `complete=True/False`，并再断言序列 `[True, False]`。
- 两态均锁定 `sampling_phase="signature_discovery"`、`counts_complete=false` 与直接原因“`mint 签名史为空/拉取失败`”。
- `scripts/tests/test_batch18_review_digest.py` 只追加 1 个 review4 回归函数并接入既有入口；SUITE 分母保持 146。
- `test_repair_batch_d.py` 未改，并在本次全量中 PASS。

## 4. GREEN 与门禁记录

| 命令 | 结果 |
|---|---|
| review4 两态定向函数 | PASS，`complete=[True, False]` |
| `python3 scripts/tests/test_batch18_review_digest.py` | PASS 11/11 |
| `python3 scripts/tests/changelog_lint.py` | PASS；活跃 68 条＋归档 139 条 |
| `python3 scripts/tests/docs_lint.py --all` | PASS；59 个文档 |
| `python3 scripts/tests/test_version_consistency.py` | PASS；五处一致为 7.0.1 |
| `python3 scripts/tests/run_all.py` | rc=1；144/146 PASS，2 项环境失败 |

全量仅失败：

1. `test_batch3_solana_vertical_slice.py`
2. `test_batch3_evm_vertical_slice.py`

两者均在 `ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)` 的 `socket.bind` 处报 `PermissionError: [Errno 1] Operation not permitted`。这是当前沙箱禁止 localhost bind，不是本次生产逻辑回归；但在验收机实际返回 rc=0 前，不宣称 146/146。

验收机复跑：

```bash
python3 scripts/tests/test_batch3_solana_vertical_slice.py
python3 scripts/tests/test_batch3_evm_vertical_slice.py
python3 scripts/tests/run_all.py
```

## 5. 版本、CHANGELOG 与白名单

- 版本五处已同步为 7.0.1：`VERSION`、`pyproject.toml`、`SKILL.md` 版本标记、CHANGELOG 活跃索引、CHANGELOG 详情标题。
- CHANGELOG 7.0.1 具备出处与根因、设计与实现、消费面与防回流、测试、盲审与验收、成本-质量指标六栏。
- 实际施工改动限于工单白名单：生产文件 1、测试文件 1、版本/发布文件 4、review4 RED/done 文件 2。
- 白名单外零改动；未 commit。
