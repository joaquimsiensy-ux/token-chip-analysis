# opus 一审报告存档（攻击型盲审 · 判 BLOCK）

> 审计对象：fix/sqd-solana-v4 至批 5 头 801f7cc（宣称 v6.49.0）。
> 本文件为验收方（Fable 调度）对 opus 一审最终报告的原文存档，供批 6 消化轮与二审对照。
> 批 6 已按 batch6_workorder.md 消化（全部 CONFIRMED），本文件仅作历史证据不再更新。

---

## 总判定：BLOCK — 4 条 BREACH，其中 BREACH-01 是本轮引入的正式发布链活故障

基线核验（一审自跑）：SUITE 120/120 PASS exit 0 属实；live_windows 两 gz 解包重算与 batch5_done 逐位相符；oracle 数字自洽（multiset 1,775,858 / DISTINCT 1,764,356 / 差 11,502 / 8,487 组 / 最高 23 倍）。

## BREACH-01：新增 wave v4 闸把全部 EVM/duckdb 边源判成 legacy 诊断产物，正式裁决与 READY 双断
- 定位：wave_scan.py:640-648（granularity：sol→transaction/instruction，evm-v2→"log"，duckdb→"source-defined"）；adjudication_validator.py:88-92 与 handoff_manifest.py:400-405 判据 `not in ("transaction","instruction")` → 拒收。
- 实证：真跑 `wave_scan.py --duckdb`（3