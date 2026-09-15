# APU 离线回归

- r4：按 r3_fix_ruling.md，只读四份既有账本，逐一检查全部构成键、UNRESOLVED 合计、Σraw 和 pct；唯一精确的输出数量为 stock_raw，其余分别按 B=4·n·2^-52·S+2 与 B/stock_raw×100 判界，不要求展示值相同。APU 的 210 锚点、630 组策略明细共核对 10034 个原始键位置；非 UNRESOLVED 键 9025 个，全部 Δ=0。原始 gap/residual 标签迁移有 616 个数量非零变化位置，max|Δ|=478750745388 raw，全部在 B 内。 gap/residual 合桶对齐后所有来源键 Δ=0，UNRESOLVED 合计、Σraw 和 pct 差均为 0；全部检查通过。两案合计 224 锚点、666 组策略明细；原始标签迁移与合桶后数值分别披露，不混作同一口径。四份输入账本 SHA-256 未变，未重跑 trace；逐键两版 raw、Δ、界与哈希见 ledger_recheck_r4.json / existing_evidence_r4.log。既有账本不含逐笔短缺轨迹，该项由 T4 合成测试覆盖。

- 模式：704_diagnostic；退出码 2。
- T6 按调度裁决完成：下列数量证据来自诊断跑（只省略 --acknowledge-flip），补件后的原参数正式跑记录见文末；正式 exit 2 为旧收据指纹失配的设计内 fail-closed。
- 原始输入绑定逐项相同、生产算法 SHA-256 校验：True。
- 实体 105；锚点 210；T4 失败 0。
- data_gap 条目 105 → 0；fp_residual 条目 105。
- 三策略数量检查失败 0。
- 三策略来源 raw 变化键 426，非 gap/residual 变化键 0；指纹变化 118/210。
- 旧裁决收据指纹不匹配 8/10；补件后的正式运行实际拒收这 8 条旧收据；须重新裁决，本次未修改裁决收据。
- 全量来源 raw 差分、两版指纹及各项断言见 apu_diff.json。

## 命令

```sh
cd /Users/uravvv/.claude/skills/token-chip-analysis/.staging_eps/apu
/usr/local/bin/python3 /Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/entity_source_trace.py --edges-evm-v2 data/v2 --edges-table edges --case-root . --total-supply 420690000000000000000000000000 --entity-file data/stage2/s2_entity_members.json --labels-file data/stage2/provenance_labels_v3.json --mem-limit 6GB --depth-limit 10 --facility-min-degree 1000 --node-budget 200000 --edge-budget 3000000 --out provenance_ledger_704_diagnostic.json
```

## 尘埃字段

| 实体 | current_negligible_skipped 旧→新 | composition_usable 旧→新 |
|---|---|---|
| TE-02 | True → True | False → False |
| TE-04 | True → True | False → False |

## 逐实体、逐锚点

| 实体 | 锚点 | gap 条目旧→新 | residual 条目 | gap 事件旧→新 | residual 事件 | T4 | 指纹变化 |
|---|---|---:|---:|---:|---:|---|---|
| TE-01 | current | 1 → 0 | 1 | 4230 → 0 | 4230 | PASS | True |
| TE-01 | peak | 0 → 0 | 0 | 4230 → 0 | 4230 | PASS | False |
| TE-02 | current | 0 → 0 | 0 | 4000 → 0 | 4000 | PASS | False |
| TE-02 | peak | 0 → 0 | 0 | 4000 → 0 | 4000 | PASS | False |
| TE-03 | current | 1 → 0 | 1 | 4015 → 0 | 4015 | PASS | True |
| TE-03 | peak | 1 → 0 | 1 | 4015 → 0 | 4015 | PASS | True |
| TE-04 | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| TE-04 | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| TE-05 | current | 1 → 0 | 1 | 4484 → 0 | 4484 | PASS | True |
| TE-05 | peak | 0 → 0 | 0 | 4484 → 0 | 4484 | PASS | False |
| OD-791010 | current | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-791010 | peak | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-3c8f7da5 | current | 1 → 0 | 1 | 3981 → 0 | 3981 | PASS | True |
| OD-3c8f7da5 | peak | 1 → 0 | 1 | 3981 → 0 | 3981 | PASS | True |
| OD-0625e06e | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-0625e06e | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-9094a360 | current | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-9094a360 | peak | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-eadc64b7 | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-eadc64b7 | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-a3d23392 | current | 1 → 0 | 1 | 4147 → 0 | 4147 | PASS | True |
| OD-a3d23392 | peak | 1 → 0 | 1 | 4147 → 0 | 4147 | PASS | True |
| OD-445e1faf | current | 1 → 0 | 1 | 4081 → 0 | 4081 | PASS | True |
| OD-445e1faf | peak | 1 → 0 | 1 | 4081 → 0 | 4081 | PASS | True |
| OD-36273d14 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-36273d14 | peak | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-28bb7341 | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-28bb7341 | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-be31a54c | current | 1 → 0 | 1 | 4067 → 0 | 4067 | PASS | True |
| OD-be31a54c | peak | 1 → 0 | 1 | 4067 → 0 | 4067 | PASS | True |
| OD-9d60be4f | current | 1 → 0 | 1 | 4083 → 0 | 4083 | PASS | True |
| OD-9d60be4f | peak | 1 → 0 | 1 | 4083 → 0 | 4083 | PASS | True |
| OD-6aadc010 | current | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-6aadc010 | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-3ec52292 | current | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-3ec52292 | peak | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-fce06a9a | current | 1 → 0 | 1 | 4033 → 0 | 4033 | PASS | True |
| OD-fce06a9a | peak | 1 → 0 | 1 | 4033 → 0 | 4033 | PASS | True |
| OD-369e330e | current | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-369e330e | peak | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-22089f57 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-22089f57 | peak | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-60d3c6be | current | 1 → 0 | 1 | 4022 → 0 | 4022 | PASS | True |
| OD-60d3c6be | peak | 1 → 0 | 1 | 4022 → 0 | 4022 | PASS | True |
| OD-73d8bd54 | current | 1 → 0 | 1 | 3928 → 0 | 3928 | PASS | True |
| OD-73d8bd54 | peak | 1 → 0 | 1 | 3928 → 0 | 3928 | PASS | True |
| OD-2b980327 | current | 0 → 0 | 0 | 3981 → 0 | 3981 | PASS | False |
| OD-2b980327 | peak | 0 → 0 | 0 | 3981 → 0 | 3981 | PASS | False |
| OD-a795d3ef | current | 1 → 0 | 1 | 3977 → 0 | 3977 | PASS | True |
| OD-a795d3ef | peak | 1 → 0 | 1 | 3977 → 0 | 3977 | PASS | True |
| OD-53a6dcee | current | 1 → 0 | 1 | 3992 → 0 | 3992 | PASS | True |
| OD-53a6dcee | peak | 1 → 0 | 1 | 3992 → 0 | 3992 | PASS | True |
| OD-9eefec33 | current | 1 → 0 | 1 | 4034 → 0 | 4034 | PASS | True |
| OD-9eefec33 | peak | 1 → 0 | 1 | 4034 → 0 | 4034 | PASS | True |
| OD-4788ec0d | current | 0 → 0 | 0 | 4080 → 0 | 4080 | PASS | False |
| OD-4788ec0d | peak | 0 → 0 | 0 | 4080 → 0 | 4080 | PASS | False |
| OD-7932acea | current | 1 → 0 | 1 | 4001 → 0 | 4001 | PASS | True |
| OD-7932acea | peak | 0 → 0 | 0 | 4001 → 0 | 4001 | PASS | False |
| OD-cb5290e9 | current | 1 → 0 | 1 | 4033 → 0 | 4033 | PASS | True |
| OD-cb5290e9 | peak | 1 → 0 | 1 | 4033 → 0 | 4033 | PASS | True |
| OD-3e71de1a | current | 0 → 0 | 0 | 3984 → 0 | 3984 | PASS | False |
| OD-3e71de1a | peak | 0 → 0 | 0 | 3984 → 0 | 3984 | PASS | False |
| OD-81aba9e7 | current | 1 → 0 | 1 | 4030 → 0 | 4030 | PASS | True |
| OD-81aba9e7 | peak | 1 → 0 | 1 | 4030 → 0 | 4030 | PASS | True |
| OD-1507b752 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-1507b752 | peak | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-392d3b04 | current | 1 → 0 | 1 | 4017 → 0 | 4017 | PASS | True |
| OD-392d3b04 | peak | 1 → 0 | 1 | 4017 → 0 | 4017 | PASS | True |
| OD-307da664 | current | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-307da664 | peak | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-b5525c29 | current | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-b5525c29 | peak | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-99b9d97a | current | 1 → 0 | 1 | 3998 → 0 | 3998 | PASS | True |
| OD-99b9d97a | peak | 1 → 0 | 1 | 3998 → 0 | 3998 | PASS | True |
| OD-05dc1b1e | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-05dc1b1e | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-fcf1b0b6 | current | 1 → 0 | 1 | 4015 → 0 | 4015 | PASS | True |
| OD-fcf1b0b6 | peak | 1 → 0 | 1 | 4015 → 0 | 4015 | PASS | True |
| OD-283cf5ce | current | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | True |
| OD-283cf5ce | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | True |
| OD-cd312af5 | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-cd312af5 | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-8ae1b4d4 | current | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-8ae1b4d4 | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-2f36a775 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-2f36a775 | peak | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-dca60518 | current | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-dca60518 | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-658d9c90 | current | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-658d9c90 | peak | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-63f272bb | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-63f272bb | peak | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-39da727b | current | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-39da727b | peak | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | True |
| OD-504ce9e5 | current | 1 → 0 | 1 | 4030 → 0 | 4030 | PASS | True |
| OD-504ce9e5 | peak | 1 → 0 | 1 | 4030 → 0 | 4030 | PASS | True |
| OD-5ee01da2 | current | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-5ee01da2 | peak | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-481bc60a | current | 0 → 0 | 0 | 3998 → 0 | 3998 | PASS | False |
| OD-481bc60a | peak | 0 → 0 | 0 | 3998 → 0 | 3998 | PASS | False |
| OD-f16b1084 | current | 0 → 0 | 0 | 4000 → 0 | 4000 | PASS | False |
| OD-f16b1084 | peak | 0 → 0 | 0 | 4000 → 0 | 4000 | PASS | False |
| OD-2119f798 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-2119f798 | peak | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-ae7fb806 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-ae7fb806 | peak | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-67f8bf2c | current | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-67f8bf2c | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-c7470938 | current | 1 → 0 | 1 | 4058 → 0 | 4058 | PASS | True |
| OD-c7470938 | peak | 1 → 0 | 1 | 4058 → 0 | 4058 | PASS | True |
| OD-e614d9c2 | current | 1 → 0 | 1 | 3998 → 0 | 3998 | PASS | True |
| OD-e614d9c2 | peak | 1 → 0 | 1 | 3998 → 0 | 3998 | PASS | True |
| OD-549d5812 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-549d5812 | peak | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-19a71ae9 | current | 1 → 0 | 1 | 4031 → 0 | 4031 | PASS | True |
| OD-19a71ae9 | peak | 1 → 0 | 1 | 4031 → 0 | 4031 | PASS | True |
| OD-4f8e64bd | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-4f8e64bd | peak | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-0b1cda03 | current | 1 → 0 | 1 | 4080 → 0 | 4080 | PASS | True |
| OD-0b1cda03 | peak | 1 → 0 | 1 | 4080 → 0 | 4080 | PASS | True |
| OD-6eb13bf7 | current | 1 → 0 | 1 | 4016 → 0 | 4016 | PASS | True |
| OD-6eb13bf7 | peak | 1 → 0 | 1 | 4016 → 0 | 4016 | PASS | True |
| OD-da0c7f31 | current | 0 → 0 | 0 | 4080 → 0 | 4080 | PASS | True |
| OD-da0c7f31 | peak | 0 → 0 | 0 | 4080 → 0 | 4080 | PASS | True |
| OD-bec24b7a | current | 1 → 0 | 1 | 3975 → 0 | 3975 | PASS | True |
| OD-bec24b7a | peak | 1 → 0 | 1 | 3975 → 0 | 3975 | PASS | True |
| OD-6eeb9a6d | current | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-6eeb9a6d | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-21474e2e | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-21474e2e | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-e19ed111 | current | 1 → 0 | 1 | 4030 → 0 | 4030 | PASS | True |
| OD-e19ed111 | peak | 1 → 0 | 1 | 4030 → 0 | 4030 | PASS | True |
| OD-e1363ea5 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-e1363ea5 | peak | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-f85675e0 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-f85675e0 | peak | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-03e258f4 | current | 1 → 0 | 1 | 4002 → 0 | 4002 | PASS | True |
| OD-03e258f4 | peak | 1 → 0 | 1 | 4002 → 0 | 4002 | PASS | True |
| OD-170ff571 | current | 0 → 0 | 0 | 3996 → 0 | 3996 | PASS | True |
| OD-170ff571 | peak | 0 → 0 | 0 | 3996 → 0 | 3996 | PASS | True |
| OD-1bae9245 | current | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-1bae9245 | peak | 1 → 0 | 1 | 3997 → 0 | 3997 | PASS | True |
| OD-d0ee3ad5 | current | 0 → 0 | 0 | 3974 → 0 | 3974 | PASS | True |
| OD-d0ee3ad5 | peak | 0 → 0 | 0 | 3974 → 0 | 3974 | PASS | True |
| OD-3004892c | current | 1 → 0 | 1 | 4082 → 0 | 4082 | PASS | True |
| OD-3004892c | peak | 1 → 0 | 1 | 4082 → 0 | 4082 | PASS | True |
| OD-7b49f798 | current | 1 → 0 | 1 | 3998 → 0 | 3998 | PASS | True |
| OD-7b49f798 | peak | 0 → 0 | 0 | 3998 → 0 | 3998 | PASS | False |
| OD-9d06c300 | current | 1 → 0 | 1 | 3999 → 0 | 3999 | PASS | True |
| OD-9d06c300 | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-d8c495e9 | current | 1 → 0 | 1 | 4106 → 0 | 4106 | PASS | True |
| OD-d8c495e9 | peak | 1 → 0 | 1 | 4106 → 0 | 4106 | PASS | True |
| OD-ed2cb9c0 | current | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-ed2cb9c0 | peak | 0 → 0 | 0 | 3997 → 0 | 3997 | PASS | False |
| OD-c470aab2 | current | 0 → 0 | 0 | 4081 → 0 | 4081 | PASS | False |
| OD-c470aab2 | peak | 0 → 0 | 0 | 4081 → 0 | 4081 | PASS | False |
| OD-ba3e1d43 | current | 1 → 0 | 1 | 3975 → 0 | 3975 | PASS | True |
| OD-ba3e1d43 | peak | 1 → 0 | 1 | 3975 → 0 | 3975 | PASS | True |
| OD-876614a3 | current | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-876614a3 | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-9a353660 | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-9a353660 | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-93daecb2 | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-93daecb2 | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-11bf7447 | current | 1 → 0 | 1 | 3977 → 0 | 3977 | PASS | True |
| OD-11bf7447 | peak | 1 → 0 | 1 | 3977 → 0 | 3977 | PASS | True |
| OD-d622e2f5 | current | 1 → 0 | 1 | 3983 → 0 | 3983 | PASS | True |
| OD-d622e2f5 | peak | 1 → 0 | 1 | 3983 → 0 | 3983 | PASS | True |
| OD-e7300b42 | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-e7300b42 | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-b9b0014b | current | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-b9b0014b | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-08c64a8f | current | 0 → 0 | 0 | 4001 → 0 | 4001 | PASS | False |
| OD-08c64a8f | peak | 0 → 0 | 0 | 4001 → 0 | 4001 | PASS | False |
| OD-e8d1fe78 | current | 1 → 0 | 1 | 4030 → 0 | 4030 | PASS | True |
| OD-e8d1fe78 | peak | 1 → 0 | 1 | 4030 → 0 | 4030 | PASS | True |
| OD-4eaccd00 | current | 1 → 0 | 1 | 4106 → 0 | 4106 | PASS | True |
| OD-4eaccd00 | peak | 1 → 0 | 1 | 4106 → 0 | 4106 | PASS | True |
| OD-31680faa | current | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-31680faa | peak | 0 → 0 | 0 | 3999 → 0 | 3999 | PASS | False |
| OD-925b4da3 | current | 0 → 0 | 0 | 3974 → 0 | 3974 | PASS | False |
| OD-925b4da3 | peak | 0 → 0 | 0 | 3974 → 0 | 3974 | PASS | False |
| OD-48722b38 | current | 1 → 0 | 1 | 3978 → 0 | 3978 | PASS | True |
| OD-48722b38 | peak | 1 → 0 | 1 | 3978 → 0 | 3978 | PASS | True |
| OD-9acdeb16 | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-9acdeb16 | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-c71fcd7b | current | 0 → 0 | 0 | 4001 → 0 | 4001 | PASS | False |
| OD-c71fcd7b | peak | 0 → 0 | 0 | 4001 → 0 | 4001 | PASS | False |
| OD-7632ad6b | current | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-7632ad6b | peak | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-bf39044e | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-bf39044e | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-7b7adbc6 | current | 0 → 0 | 0 | 5 → 0 | 5 | PASS | False |
| OD-7b7adbc6 | peak | 0 → 0 | 0 | 5 → 0 | 5 | PASS | False |
| OD-5abb8f02 | current | 0 → 0 | 0 | 4000 → 0 | 4000 | PASS | False |
| OD-5abb8f02 | peak | 0 → 0 | 0 | 4000 → 0 | 4000 | PASS | False |
| OD-9488313d | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-9488313d | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-7e341a42 | current | 0 → 0 | 0 | 4080 → 0 | 4080 | PASS | True |
| OD-7e341a42 | peak | 0 → 0 | 0 | 4080 → 0 | 4080 | PASS | True |
| OD-343f75af | current | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-343f75af | peak | 0 → 0 | 0 | 0 → 0 | 0 | PASS | False |
| OD-c11d5b08 | current | 1 → 0 | 1 | 4017 → 0 | 4017 | PASS | True |
| OD-c11d5b08 | peak | 1 → 0 | 1 | 4017 → 0 | 4017 | PASS | True |
| OD-4ecb9d28 | current | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-4ecb9d28 | peak | 0 → 0 | 0 | 4016 → 0 | 4016 | PASS | False |
| OD-d9cb768e | current | 1 → 0 | 1 | 4056 → 0 | 4056 | PASS | True |
| OD-d9cb768e | peak | 1 → 0 | 1 | 4056 → 0 | 4056 | PASS | True |
| OD-2d4643da | current | 0 → 0 | 0 | 3975 → 0 | 3975 | PASS | True |
| OD-2d4643da | peak | 0 → 0 | 0 | 3975 → 0 | 3975 | PASS | True |

## 补件后原参数正式运行

- 补件清单 `STAGING_SHA256_apu_extra.txt`：1/1 OK；证据 SHA-256 `d79fd8ce0b6405b72ef7473e168b6401add7387f9c2c20c81b3a74ffd347f677`。
- 原账本 params 全部保留，包括 --acknowledge-flip；仅 --out 指向新输出。
- 调度方已核实：变化的 118 个锚点指纹全部对应旧三策略明细含 data_gap 的锚点；此项结论归属调度方。
- 验收组合：诊断跑 105 实体 × 2 锚点的既有数量证据（r4 已按 r3 裁决对全部原始键及合桶后来源逐键只读复核）+ 正式跑旧收据 8/10 指纹失配且 exit 2。

```sh
cd /Users/uravvv/.claude/skills/token-chip-analysis/.staging_eps/apu
/usr/local/bin/python3 /Users/uravvv/.claude/skills/token-chip-analysis/scripts/report/entity_source_trace.py --edges-evm-v2 data/v2 --edges-table edges --case-root . --total-supply 420690000000000000000000000000 --entity-file data/stage2/s2_entity_members.json --labels-file data/stage2/provenance_labels_v3.json --acknowledge-flip flip_adjudications.json --mem-limit 6GB --depth-limit 10 --facility-min-degree 1000 --node-budget 200000 --edge-budget 3000000 --out provenance_ledger_704.json
```

- 实际退出码：**2**；耗时 1263.646 秒。
- 算法 SHA-256：`e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1`。
- 完整日志：`apu_formal_followup.log`；运行回执：`apu_formal_followup_result.json`。

### stderr 原文

```text
(empty; 0 bytes)
```

### stdout 中的拒收原文

```text
[source_trace]   ✗ OD-7932acea current 裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决
[source_trace]   ✗ OD-d9cb768e peak 裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决
[source_trace]   ✗ OD-e1363ea5 current 裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决
[source_trace]   ✗ OD-e19ed111 current 裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决
[source_trace]   ✗ OD-e19ed111 peak 裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决
[source_trace]   ✗ OD-e8d1fe78 current 裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决
[source_trace]   ✗ OD-e8d1fe78 peak 裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决
[source_trace]   ✗ TE-05 current 裁决收据指纹与当前三策略明细不符——底层数据已变化，旧裁决失效，须重新裁决
[source_trace] 敏感性不稳：消费策略主导翻转未获合法裁决收据覆盖，或事件顺序未决量达到实质线——结论不得发布（exit 2）。真实多来源结构须造 flip-adjudications/v1 裁决收据（含逐锚点 flip_fingerprint 与三策略披露）后 --acknowledge-flip <收据> 重跑；顺序未决须补齐 block/slot + tx + log/instruction 序号
```
