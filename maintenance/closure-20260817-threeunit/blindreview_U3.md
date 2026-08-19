# U3 盲审报告（opus 攻击型盲审 · 2026-08-17 · 被审版本 3ee1383/6.48.0）

> 盲审方式：独立攻击 9 向量实跑取证 + 3ee1383^ 基线对照 + 全库存量清点。工作树全程未污染（破坏性实验在临时副本内）。
> 复现脚本遗留：session scratchpad/atk/（atk_sqd_toctou.py、atk_sqd_e2e_and_chainbreak.py、atk_types_and_pollution.py、atk_escape_fixed.py、atk_selfpath.py）。

# 结论：CONDITIONAL（可交付，须消化 1 BREACH）

被审 HEAD 3ee1383 核对无误，工作区干净，本机 run_all.py 117/117 PASS rc=0（含两项 loopback），与 CHANGELOG 自报一致。**闸体本身攻不破**——所有得手的攻击都落在射程边界外，不在 U3 新写的代码里。

## BREACH-01：同 protocol 另一签发者无 TOCTOU，归属谎报端到端假 PASS

`evm-collector-run/v2` 全库只有两个签发者：`fetch_hypersync.py`（本单元已收口）和 `scripts/evm/csv_collector_receipt.py` 的 `emit_native_receipt`（`fetch_sqd_evm.py` 调用）。后者第 30 行 `"sha256":_sha256_file(collector)` 是**写 receipt 时的实时哈希**，`fetch_sqd_evm.py` 全文无 hashlib／无启动冻结／无 REVOKED 检查。

用 U3 自带 `test_toctou_drift_rejected_before_receipt_signing` 的**同一手法**打 SQD，实测：

```
采集开始时脚本 : b1954b592d55d9ab…
采集结束时脚本 : d5811af3d058e343…  (采集期间被改)
receipt 署名   : d5811af3d058e343…  -> 漂移后版本
preflight      : PASS
```

数据由旧版本采集，正式回执署名新版本，native receipt → make_channel_receipt → preflight_channels 全链条零告警 PASS。同一手法在 hypersync 上被写前复验拒签。

定级理由（三条叠加，非单纯"既有缺口"）：
1. 工单 U3 第 2 条自己声明了"等深延伸（U2b/R6 语义）"，对 REVOKED 履行了跨单元等深，却对同 protocol 另一签发者的 TOCTOU 未履行；
2. 危害是**端到端假 PASS**，不是 fail-closed；
3. `references/data-pipeline-evm-channels.md` 新增段落写"同一 evm-collector-run/v2 receipt 的顶层 collector **保证**覆盖其全部 segments"——字面涵盖 SQD 签的回执，而其归属可被采集期改档改写，属过度声称。

公允标注：该缺口**非本单元引入**，且工单第 0 节明确把 `csv_collector_receipt.py` 划为"不改"。修复应另立单元：`emit_native_receipt` 增加调用方传入的启动冻结哈希参数，`fetch_sqd_evm.py` 在 main() 入口冻结 + 写前复验 + hash-wide REVOKED 拒启动。

## WEAK

- **W-01 方案 B 把补登纪律从瞬时依赖升为永久依赖，无反向断链守卫。** 旧路径下老哈希只在"续采那一刻"需在 historical_script_hashes 内，续采成功即被顶层覆盖；方案 B 强制分段后，老段 receipt 的 collector 永久是老哈希，**每次 preflight 都依赖登记在册**。实测模拟下次升级（改一字节、不补登）：test_collector_history/test_csv_resume_collector_gate/test_g3_alt_collectors 全部 rc=0 无告警，而用 6.48.0 采的老段直接被拒。test_git_evidence 只做正向验证，无"HEAD 前一版必须已登记"的反向守卫；本次新增 test_u3_replaced_csv_collector_registration 是硬编码单条。这笔新增维护债 CHANGELOG 与工单均未申明。
- **W-02 schema 常量三处表达分裂。** 本单元新增 fetch_hypersync.py:38 COLLECTOR_RECEIPT_SCHEMA，但同文件 :282 签发时仍用字面量 "evm-collector-run/v2"，channels_preflight.py:29 另有一份副本。升 v3 时改漏任一处即人机分裂。
- **W-03 `--out` 与 `--receipt` 同路径无前置校验（反向等深）。** 两者临时件命名规则完全相同，实测以**未捕获** FileExistsError 退出并残留 .collide.csv.tmp.53972。fetch_sqd_evm.py:126 有 realpath(a.out)==realpath(a.receipt) 校验，hypersync 没有。与工单 6.3"畸形输入不得以 TypeError/KeyError 逃逸"是同族错误面问题。

## NOTE

- **N-01** SQD 用 REVOKED 版本可跑完整采集并签发正式回执，只在消费侧被兜底拒——浪费一次完整采集，非假 PASS；hypersync 侧现已拒启动。
- **N-02** fetch_hypersync.py:149 的 `{COLLECTOR_RECEIPT_SCHEMA: True}[schema]` + except KeyError 是全库唯一同形写法，5 行等价于一行 !=，与同族 channels_preflight.py:158 风格分裂。
- **N-03** `--receipt` 缺席而 `--resume-receipt` 给出时，该参数被静默忽略并落入 legacy resume 路径，无任何警告。
- **N-04** prior receipt 被 resume 层（:142）与 _csv_collector_provenance（内部 rp.read_text()）各独立读一次，存在双读窗口；不放大攻击者能力，仅记设计瑕疵。

## DEFENDED（实跑攻不动）

1. 跨版本续采拒绝 + 指引全文，CSV 零改动、不签发；
2. **10 个类型/解析向量全拒**（顶层非对象／schema=null／schema=数字／requested_from=True／requested_to=10.0／requested_to="10"／query=null／segments=对象／segments=null／重复 query 键），其中 6 个测试未覆盖；
3. legacy 无回执续拉污染 CSV 尾部后再走正式续采 → 被 provenance 的 output!=actual 整文件绑定拒；
4. 同哈希三段链无误杀，segments 正确累积 [(0,10),(10,20),(20,30)]，顶层 collector 恒等当前脚本；
5. resume 途中漂移拒签（测试未覆盖场景）：已有正式 CSV 字节级零损伤、无临时件残留、不签发；
6. **出路端到端可达**：老段（历史 collector）+ 新段（当前 collector）两段异 collector channel → preflight_channels PASS → 真实 replay_pass1.py rc=0、[gate] PASS、余额守恒（90%/10%）。方案 B 的"另开新 channel 段"不是纸上出路；
7. hash-wide REVOKED 拒启动生效；
8. **破坏性注入三连**（摘同哈希闸／退回写时实时哈希／摘 REVOKED 拒启动）各**精确红对应单一用例**，测试非装死；
9. 跨脚本冒名、--resume-receipt 指向 symlink 均 fail-closed。

## 事实主张核验（全部属实）

- **存量清点**：Desktop+Documents 全盘顶层 schema=="evm-collector-run/v2" 回执 105 份，段数分布 {1:105}，多段件 0——CHANGELOG"105 份全单段零迁移"逐字成立。
- **git 考证**：merge-base --is-ancestor 2d69373 HEAD rc=0；git show 2d69373:…fetch_hypersync.py|shasum = cea82c77… 逐字符一致；该 blob 内 "schema" 签发点仅一处 evm-collector-run/v2，"一条即全"判断成立；2d69373→3ee1383 之间该文件无其他改动，补登完备无跳版。
- **诚信项**：workorder_U3.md 实测 sha256 = 自报值，施工方只读未改调度输入；红态实证如实区分"旧代码漏过"（6 FAIL）与"既有正确行为固化"（SQD／upgrade-channel 2 PASS），未伪报。
- 版本号三处一致（VERSION／pyproject:15／SKILL.md:23 = 6.48.0）。
