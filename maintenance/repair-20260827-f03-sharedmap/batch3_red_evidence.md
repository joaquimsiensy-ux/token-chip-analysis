# F-03b 批 3 RED 证据

- 冻结基线：`HEAD=9b1c4b5`（v6.52.14）
- 执行边界：离线；无 git 写操作；运行时仅有本批新增 RED 测试改动，生产代码仍为冻结基线。
- 反例：共享地图 `100..199`；canary 为 `100..163`；非 canary 已知段 `170..171` 的 recheck 请求持续失败。目标行为应为保留其余验证成功段、仅剔除 `170..171`，基线实际整体回退。

## RED 命令

```text
python3 -c 'import sys; sys.path.insert(0,"scripts/tests"); import test_f03_sharedmap_reuse as t; t.test_partial_request_failure_reuses_verified_ranges()'
```

退出码：`1`

## 原始失败输出

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import sys; sys.path.insert(0,"scripts/tests"); import test_f03_sharedmap_reuse as t; t.test_partial_request_failure_reuses_verified_ranges()
                                                                                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "/Users/uravvv/.claude/skills/token-chip-analysis/scripts/tests/test_f03_sharedmap_reuse.py", line 241, in test_partial_request_failure_reuses_verified_ranges
    assert reused is not None, info
           ^^^^^^^^^^^^^^^^^^
AssertionError: {'asset_path': '<temp>/map.json', 'version': '20260827', 'sha256': '<fixture-sha256>', 'supersedes': None, 'generated_at': '<fixture-generated-at>', 'reused_ranges': [], 'canary': {'slots': [], 'counts_sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'verified_at': '<runtime-utc>'}, 'fallback_reason': 'recheck-request-failed:170-171'}
```

`<temp>`、`<fixture-sha256>` 与时间字段是每次运行动态值；失败判据原样保留为 `reused is None` 及 `fallback_reason=recheck-request-failed:170-171`。

