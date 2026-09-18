# 工单F05复核：退回

v2 剩 **1 项 P2：存量迁移链缺少更新证据哈希的步骤**。r1 指出的代码回归和夹具问题已有对应修正；未发现按 v2 完成夹具迁移后，会使现有 `run_all.py` 用例变红的新增确定问题。

完整报告已打印到 stdout。本轮未修改文件，未运行完整套件或会写盘的端到端测试。

**F05-R2-01｜P2：证据迁移后直接 build，会被旧哈希阻断。**

工单位置：[§1.4，第 23 行](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260918-p0-f04-f07/workorder_F05.md:23)，对应 r1 的 F05-R1-04 迁移链要求。

事实：§1.4 要求改写证据文件后执行 `facts_gate.py build`，但未要求先更新：

```text
state_source.facts_inputs.peak_overrides[eid].evidence.sha256
```

生产者在读取证据内容前就校验该哈希，v2 保留了这段逻辑。实查命令：

```sh
grep -n -F '            if _sha256_path(ev_path) != str(ev["sha256"]).lower():' scripts/report/facts_gate.py
```

唯一命中第 412 行；相邻代码：

```python
# facts_gate.py:412–413
if _sha256_path(ev_path) != str(ev["sha256"]).lower():
    raise ValueError(f"peak_overrides.{eid}.evidence sha256 与案内实物不一致")
```

内存演算确认：只迁移证据 JSON、保留旧哈希时，立即报上述错误；同步哈希后，构建成功，`peak_raw=160`。

修订建议：§1.4 补成以下顺序：

```text
改写证据 JSON
→ 计算新 SHA-256
→ 更新所有引用该文件的 override.evidence.sha256
→ facts build
→ Figure 2 收据及后续绑定重封
```

路径变化时同步 `evidence.path`。A4 重封应先于 stage2 收口收据，因为 `stage2_closeout.py:608、659` 会绑定并复核 A4 哈希。无需扩大生产代码白名单。

**r1 八项处置**

| r1 项 | r2 结论 |
|---|---|
| R1-01：decimals 侵入 stage2 | 已闭合。新增函数仅挂 new-analysis；共享函数本体、签名不变。`stage2_closeout.py:578`、`test_report_facts.py:206–207` 不新增 decimals 检查。 |
| R1-02：Solana 链名 | 已闭合。登记表与函数演算确认：`solana/sol → solana`，`bsc/eth/base → evm`；未登记链抛 `ValueError`，被转换为 errors。 |
| R1-03：Solana 夹具缺 decimals | 已闭合。生产者 `accounting_gate_sol.py:226` 写该字段；白名单允许在 `test_repair_batch_d.py:984` 补 0，与 `:893` 观测值一致。 |
| R1-04：旧 override 用例及迁移 | 既有用例迁移已闭合；存量迁移链仍有本轮唯一退回项。 |
| R1-05：a/b 夹具不完整 | 已改用完整 P105 路径，静态核对可行；端到端两案基线仍须施工取证。 |
| R1-06：日期不严格 | 已闭合。回写比较拒绝 `20260102`，兼容真实 `wave_scan.py:87–88` 的 `%Y-%m-%d`。 |
| R1-07：峰值上界裁决 | 已闭合。§2.1/§4 一致选定保守阻断，准确条件为“真实峰值超过当前采用的总供应”。 |
| R1-08：docstring/import 范围 | 已闭合。docstring `:2–71` 仅放行 `:65`；imports `:72–78` 单独允许新增 datetime。 |

**实际核过的锚点和修法**

工单明示的施工锚均经 `grep -n -F` 确认唯一、行号吻合。指定区间全部回读，按 `311e6c4` 核对：

| 文件 | 已核区间 |
|---|---|
| `facts_gate.py` | 97–186、191–203、198–199、306–311、314–318、321、357–363、404–420、408、420、421–426、431、454–467；imports 72–78；docstring 65 |
| `audit_release_gate.py` | 111–118、1497–1502、1547–1548、1830–1832 |
| `test_audit_release_gate.py` | 59–60、202–224、271、1156 |
| `test_report_facts.py` | 49–74、77、153、278–293 |
| `shared_release_receipt.py` | 559–567、592–593、1834–1848、2031–2050 |

- **EVM 收据选择正确。** `shared_release_receipt.py:71、1445、1508、2034–2045` 确认键为 `"balance"`，对象是含 `inputs.config` 的 verify_recon 收据；`:593` 已有同款 `_bound_json_input` 调用。
- **缓存行为正确。** `run :1755` 建缓存；`:1792 → check_reconciliation :543` 早于 facts 检查。局部演算确认成功对象复用、异常重抛并转 errors，均不重复深验。
- **日期检查兼容真实产物。** `entity_source_trace.py:638` 的 peak 日期来自 `day_str`；`:639` 的 current 锚不写 date。用例 20 只覆盖显式提供 current.date 的分支，§4 已登记。
- **用例 21 文案成立。** 数组证据短路，报“证据内容与申报”。对象内非法 raw 可能报 `invalid literal for int()` 或“不得为负”；用例 21 未使用这些输入。
- **既有 override 三类断言保留。** 合法断言在 `test_report_facts.py:164–167`；坏哈希设置在 `:156–157`；缺证据设置在 `:158–159`；共同拒绝断言在 `:161–163`。迁移后局部演算均成立。
- **文档约束相容。** R07 CHANGELOG 未承诺任意 JSON 均可作证据，无须改写历史条目；§0.4 的 docstring 例外与其余文档不改要求一致。

**夹具覆盖与回归面**

`build_case(root, historical=False)` 单独缺全部六项 new-analysis 专属资产，也缺 `identity_gate.json`。v2 采用的 P105 助手补齐了这些资产：

| NEW_ANALYSIS_REQUIRED | build_case 单独生成 | P105 生成位置 |
|---|---|---|
| distribution_scan.json | 无 | 167–169 |
| distribution_rounds.json | 无 | 232–236 |
| a5_report_seal.json | 无 | 247–251 |
| fig1_legend_receipt.json | 无 | 240–244 |
| figure2_check_receipt.json | 无 | 222–228 |
| facts.json | 无 | 214；identity_gate 在 203–213 先生成 |

P105 的修改范围足够且最小：`:141` 加默认参数、`:214` 传参，a/b 可放在 `main` 既有两组用例之后、`:271` 收尾打印之前。

`grep -rn add_new_analysis_distribution scripts/tests` 确认源码调用者仅 P105 `:260`、batch B `:417`；默认 `decimals=0` 保持既有调用语义。

共享 facts 助手调用已全部核对：stage2 `:76`、batch D `:1205`、P105 `:214`、a4 `:498`。迁移助手证据格式后均继承新格式；Solana 另执行指定的一行 decimals 补齐。

G2 对现有正例成立：facts/figures 峰值为供应量的 68.7%；R07 为 150/1000、合法 override 为 160/1000；state 测试为 4000/10000；Solana 为 60/100；stage2/a4 和 P105 的 confirmed 均不超过同源总供应。额外检查的 batch C 手写 facts 也未发现超供应正例。

stage2 的 `facts_vs_ledgers` record，以及 reseal 复用路径，不受新增 decimals 检查影响。峰值、日期和证据格式的收紧仍按本工单设计经过共享 derive 路径生效。

**局部 RED/GREEN 结果**

使用实际源码及 v2 代码块做内存演算；文件 I/O、三账前置校验和深验输入使用内存替身，不能替代端到端验收。

| 用例 | 基线 → 拟议实现 |
|---|---|
| 16：证据不一致 | 接受 → 按指定文案拒绝 |
| 17：证据一致 | 接受 → 接受，peak=150 |
| 18：peak 超供应 | 接受 → 报“超过总供应” |
| 19：非法日期、20260102 | 两例均接受 → 均报“非 YYYY-MM-DD” |
| 20：晚于显式 current.date | 接受 → 报“晚于” |
| 21：数组证据 | 接受 → 报“证据内容” |
| a/b：decimals 2/0、观测 0 | 新函数对 2 产生指定错误，对 0 返回空错误；完整 P105 基线须按 §2.4 实跑取证 |

按 v2 拼接两个生产文件后编译成功；`invariant_scan.scan_python` 登记集合均未变化，当前改法无需新增 manifest 项。未运行完整 scanner。§0.8 的定向清单与调度方承担完整 suite/reseal 验收的安排没有新增矛盾。

文档大小仅用 stat 核对，仍为 **8021 / 930061 / 8798**。

复核期间 HEAD 从 `4278857f` 推进到 `92ff4fe1`，涉及并行 F06 和其他提示词；9 个受审文件的 SHA-256 复查无变化，结束工作树干净。本轮未修改文件、联网或 commit。首次系统 git 尝试建立 `/tmp/xcrun_db` 缓存被沙箱拒绝，随后已改用 CommandLineTools git；该环境信息不计退回项。