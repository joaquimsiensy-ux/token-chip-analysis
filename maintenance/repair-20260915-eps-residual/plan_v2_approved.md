# 修复 plan v2(最小改动版):溯源假 data_gap 改判为浮点残差(7.0.3 → 7.0.4)

状态:**v2 = Fable 设计 + codex 只读复核融合 + 用户两项裁决,待用户审批施工**。
基线:`main = 3b29e38`(7.0.3 逻辑 + agents/openai.yaml)。**不回退 7.0.3**,不改整数算术,不动账户扣减逻辑。根治方案另存 `maintenance/repair-20260915-provenance-exact-arith/workorder.md` 留待日后。
标 **[CX]** 的条目来自 codex 复核并经 Fable 复算采纳;**[用户]** 为本轮裁决。

## Context(为什么改、改到什么程度)

`scripts/report/entity_source_trace.py` 用 float64 模拟代币来源账户,代币 raw 量级 1e29,单步舍入噪声约 1e13。`EPS = 1e-6`(第 89 行)是**绝对**阈值,比噪声小 19 个数量级,于是 `simulate()` 第 465 行 `shortfall > EPS` 被纯噪声触发,记成"数据缺失"(`UNRESOLVED/data_gap`)。APU 0914 案实测:105 个实体里 91 个带 `data_gap_events>0`,构成里 105 条 `data_gap` 条目,raw 全部 ≤4.8e11、pct 全为 0.0,TE-02 一个实体记了 4,000 次。数值无害,语义误导复核人。

用户裁决:暂不根治,只消掉假 data_gap;顺带补 7.0.3 漏改的 `pyproject.toml` 版本与 CHANGELOG 详细段(`test_version_consistency.py` 因此在 main 上是红的)。

**v1 → v2 的关键转向 [CX,已复算]**:v1 想把账户判等/扣减的 6 处 EPS 一起放大,codex 给出四个反例我全部复算成立——①`Z→X 1, X→D 1`(总供应 10·2^90)放大后 X 被清空、D 构成为空、整数 peak=1 → **新增 peak 拒收**;②FIFO/LIFO 入账 7+7 被拒后转出 14 → **新增 14 的假缺口**;③20 万次 2^36 小额累加后假 shortfall 1.37e16 > 放大后阈值 1.24e16 → "n×eps 上界"不成立;④真实残留 < eps 时 pro-rata 会提前转给下游、FIFO/LIFO 直接丢弃。因此 **v2 只动"缺口判定"这一处,账户扣减阈值一字不改**,7.0.3 的模拟行为、尘埃降级、全部既有测试断言原样保留。

## 设计

### D1 唯一逻辑改动点:第 465 行的缺口判定 **[用户:改标签]**
```python
# 现状(7.0.3)
elif shortfall > EPS:
    gap_key = ("UNRESOLVED", "data_gap", None)
    comp[gap_key] = comp.get(gap_key, 0.0) + shortfall
    gap_events += 1
# 7.0.4
elif shortfall > gap_eps:            # 真缺口:量级超过浮点噪声容限
    gap_key = ("UNRESOLVED", "data_gap", None)
    comp[gap_key] = comp.get(gap_key, 0.0) + shortfall
    gap_events += 1
elif shortfall > EPS:                # 浮点残差:数量原样保留,只是不再叫"数据缺失"
    res_key = ("UNRESOLVED", "fp_residual", None)
    comp[res_key] = comp.get(res_key, 0.0) + shortfall
    residual_events += 1
```
- 数量**一个单位都不变**:构成合计、闭合、`policy_details`、`unresolved_total_pct` 与 7.0.3 完全相同,只是把噪声量级的缺口从 `data_gap` 改挂到新子类 `fp_residual`。这就是选"改标签"而非"丢弃"的理由:丢弃会让收款方构成少一块,累积后可能触发 0.5% 闭合拒收(**[CX]** 一个 1e-4 供应的锚点上,最坏累积 5.8e-7 供应 = 0.58% > 0.5%)。
- `EPS`(1e-6)保留原名原值,**其余 9 处引用不动**(账户判等 6 处、输出/策略筛选 3 处;**[CX]** 更正:第 296 行是拒绝入账、302 行是停止扣款,第 569/576 行参与稳定性判定与翻转指纹,不是纯展示——正因如此才一律不动)。
- 新增 `residual_events` 计数,`simulate()` 返回值加 `"fp_residual_events"`,实体 `simulation` 诊断块新增 `fp_residual_events`(**[CX]** 与 `data_gap_events` 分开,不能混计)。
- `comp_to_list` 第 549–551 行 `ev_map` 加 `"fp_residual": "onchain_pattern"`。

### D2 `gap_eps` 的定义与量级
```python
GAP_EPS_REL = 1e-13                       # 相对总供应量的系数
def gap_eps(total_supply: int) -> float:
    return max(EPS, float(total_supply) * GAP_EPS_REL)
```
- 噪声实测:APU 最大假 gap 4.8e11 = 1.1e-18 倍供应;float64 理论单步 ε·量级 ≈ 2.2e-16 × 周转(APU 0.31 倍供应)≈ 7e-17 倍供应。`1e-13` 比实测高 1e5、比理论高 1e3。
- 不取 1e-12 的原因 **[CX]**:改标签方案里 gap_eps 只影响"叫什么",不影响数量,所以宁可小一点——它决定的是"多大的缺口才算真缺口",阈值越小漏判真缺口的风险越小;APU 下 1e-13 × 4.2e29 = 4.2e16 raw ≈ 0.04 个币。
- 下限 `EPS`:小供应量(测试 fixture 1e4–1e6)下 gap_eps == EPS,`fp_residual` 分支永远不触发,行为与 7.0.3 逐字一致。
- **[CX]** 明确不承诺"假 gap 全消":极端累加序列(反例③)的假缺口可超过 gap_eps,仍会记成 data_gap;这是浮点根因未除的固有残留,写进 scan-schemas 与 CHANGELOG。

### D3 传参路径 **[CX 修正]**
- `simulate(edges_iter, Mset, ancestors, term_key, term_plen, policy, T_peak, gap_eps=EPS)` —— **带默认值**,因为 `scripts/tests/test_sqd_gap_repair.py:159/160/344/346` 直接调用 `entity.simulate()`(v1 说"唯一外部 import"是错的),默认值使其行为不变、不需进白名单。
- `trace_entity()` 第 ~596 行三策略循环:`simulate(..., gap_eps=gap_eps(total))`。
- 账户类 `__slots__`(第 252、288 行)**不动**——v2 不给账户类加属性(**[CX]** v1 会因 `__slots__` 直接 AttributeError)。
- freeze 重放是 `subprocess` 跑本脚本(handoff_manifest.py 第 1352 行),自算 gap_eps,**不改 freeze**。
- `source_binding()` 的 `algorithm` 字典(第 159–163 行)追加 `"gap_eps_rel": GAP_EPS_REL`(**[CX]** 已核实 handoff 按名读键、不校验键集;`references/scan-schemas.md:249–251` 的结构示例同步加该键)。

### D4 版本与登记面(含 7.0.3 遗漏)
- 版本 **7.0.4**:`VERSION`、`pyproject.toml:15`(当前仍 7.0.2,7.0.3 漏改)、`SKILL.md:23` 版本注释、`CHANGELOG.md` 索引行 + 详细段。
- `CHANGELOG.md` 先补 **`## [7.0.3]`** 详细段(7.0.3 只写了索引行;`test_version_consistency.py:20` 要求详细段首标题 == VERSION,补完 7.0.3 段再加 7.0.4 段即满足)。六栏格式照 7.0.2。出处只写"APU 案触发的工具故障",禁写代币结论。
- `references/scan-schemas.md`:第 307 行 UNRESOLVED 子类枚举加 `fp_residual`;第 285 行诊断块加 `fp_residual_events`;第 249–251 行 algorithm 示例加 `gap_eps_rel`;§4 追加一段:gap_eps 定义、量级依据、"极端累加仍可能记 data_gap"的残留声明、fp_residual 的语义("浮点噪声量级的账户短缺,数量保留、不代表链上数据缺失")。
- `entity_source_trace.py` 模块 docstring 同步一句。
- `scripts/tests/invariant_manifest.json` 预计不动;`invariant_scan.py` 报差异时先判断是否误改登记面。
- **[CX]** CHANGELOG 消费面须写明:算法文件哈希变化 → 旧账本 freeze 重放与 `--check-unseal`(handoff_manifest.py 第 1401–1404 行)都会拒 → "已封存不动"只指不重写文件,不指复验仍过。

### D5 明确不做
不改账户判等/扣减/入账阈值、不改闭合门禁(trace/freeze 0.5%)、不改 7.0.3 尘埃降级与两个标记、不改输出/策略筛选阈值、不改 `ORDER_MATERIAL_PCT`/`order_raw` 判定、不改 `unresolved_total` 汇总(fp_residual 属 UNRESOLVED 如实计入)、不改 schema(仍 v2)、不改 freeze、不引入整数算术、不处理第 559/575 行 `int(float)` 截断成 `"raw":"0"` 的既有现象(**[CX]** 记入"已知未修")。

## 测试(先红后绿;`scripts/tests/test_entity_source_trace.py` 沿现有 `check()` 风格追加)

- **T1 假 gap 改判(RED→GREEN 主证据)[CX 提供的必现三笔构造,已复算]**:总供应 `10·2^90`,同天三笔精确顺序:`Z→X 2^90`、`X→D 2^90−1`、`X→D 1`。7.0.3 下三策略各记 1 次 `data_gap` raw=1(RED 证据:`simulation.data_gap_events == 1`、构成含 `data_gap` raw "1")。7.0.4 GREEN:`data_gap_events == 0`、`fp_residual_events == 1`、构成含 `("UNRESOLVED","fp_residual")` raw "1"、无 `data_gap` 条目、`exit 0`、两锚点 `stock_raw == 2^90`、闭合 Σ 与 7.0.3 相同(mint 条目 raw 相同)。
- **T2 真缺口仍报**:①总供应 `10**6`(gap_eps 落到 EPS 下限):X 空账户 → `X→D 100` → `data_gap` raw 100、`data_gap_events == 1`、无 fp_residual;②总供应 `10·2^90`:X 空账户 → `X→D 2^60` → `data_gap` raw 2^60。
- **T3 小供应行为逐字不变**:`gap_eps(10**4) == gap_eps(10**6) == 1e-6`(import 模块断言);7.0.3 全部既有 trace 测试(含 4 组 dust)一字不改仍绿;**[CX]** 额外对 `test_dust_current_precision_loss(nonempty=True)` 案例断言三策略 `policy_details` 与 7.0.3 运行结果逐条相同(先用 7.0.3 跑一次落盘作对照)。
- **T4 数量不变性(核心不变量)**:对 T1 边表与一个多来源 pro-rata 反复扣减边表,分别用 7.0.3 与 7.0.4 跑,断言每实体每锚点:`stock_raw` 相同、`Σraw` 相同、除 `data_gap`/`fp_residual` 两键外的每条构成 raw 相同、`data_gap raw(7.0.3) == data_gap raw(7.0.4) + fp_residual raw(7.0.4)`。
- **T5 登记**:账本 `input_binding.algorithm.gap_eps_rel == 1e-13`;`simulation.fp_residual_events` 键存在。
- **T6 APU 真实回归**(离线;在保持案根布局的隔离副本里跑,trace 用 `--out` 父目录当案根,第 728 行):对比 7.0.3 账本 —— 按实体×锚点×终点键对齐,断言 T4 不变量对全部 105 实体成立;记录 `data_gap` 条目 105 → x、`fp_residual` 条目 → y、各实体 `data_gap_events`/`fp_residual_events`;TE-02/TE-04 两标记是否仍在**如实记录**(**[CX]** 不预设);三策略 `policy_details` 逐来源 raw 差分、翻转指纹是否变化(预期:仅含 gap 的锚点指纹变,其余不变)。结果落 `maintenance/repair-20260915-eps-residual/apu_regression.md`,只记数字不记结论。
- **T7 PYTHIA 对表 [用户:纳入]**:按 `scripts/tests/fixtures/pythia_anchors.json` 约定,在 PYTHIA 真库隔离副本重跑 trace,与 `provenance_v2` 锚点比对;数量类锚点须逐项相等,若锚点里含 data_gap 条目则按 T4 不变量比对并**人工更新**该文件(数值权威=文件,更新须在 done.md 写明每项旧值/新值/原因),`fixtures_lint.py` 绿。
- **T8 freeze 重放**:**[CX]** 复用 `scripts/tests/test_handoff_manifest.py:293` 一类完整案根搭建(manifest、data_map、成员、裁决材料),对 T1 边表跑 `handoff_manifest.py freeze`:新代码重放通过;用 7.0.3 生成的旧账本 → 算法哈希变化被拒(fail-closed 证据)。
- **T9 版本一致性 + 全套**:`test_version_consistency.py` 绿;`run_all.py` 全绿(nohup 落盘);SUITE 数不变(测试追加在既有文件内)。

## 施工纪律与产物
- 独立工单目录 `maintenance/repair-20260915-eps-residual/`(workorder.md、red_evidence.txt、apu_regression.md、pythia_regression.md、done.md)。
- 白名单:`scripts/report/entity_source_trace.py`、`scripts/tests/test_entity_source_trace.py`、`scripts/tests/fixtures/pythia_anchors.json`(仅 T7 人工更新)、`references/scan-schemas.md`、`CHANGELOG.md`、`VERSION`、`pyproject.toml`、`SKILL.md`(仅版本注释)、`scripts/tests/invariant_manifest.json`(仅当扫描要求)、本工单目录。**不碰 handoff_manifest.py、不碰 test_sqd_gap_repair.py、不碰 test_handoff_manifest.py 的既有断言。**
- 施工 = codex `--write --fresh`;先 RED 后 GREEN;完工不 commit;Fable 验收后 commit + push。
- 禁止读取 `~/.codex/skills/_archive/` 与 tag `codex-frozen-20260915` 的实现。

## 调度与验收纪律 **[用户 2026-09-15 裁决]**
- **Fable 只负责验收与多 Agent 调度**,不亲手改任何代码;所有代码相关改动(生产代码、测试、文档、CHANGELOG、版本文件)一律由 codex 施工。
- **上下文隔离**:Fable 不读取、不展开、不透传子 Agent 的原始会话痕迹、内部执行栈帧、中间 scratchpad 日志;只消费子 Agent 回传的结论文件(done.md / red_evidence.txt / 回归表)与退出码。子 Agent 大输出一律落盘,不回流主线。
- **盲审 = codex 正常只读盲审**,不做攻击性验收(v1 里的 opus 攻击型盲审条款作废)。盲审对象:施工产物 + 本 plan 的 D1–D5、T1–T9 逐条核对。
- **失败升级规则**:codex 盲审若**连续三次**失败(同一轮施工产物三次盲审都判 FAIL,或盲审本身三次无法完成),改由 opus 执行盲审;施工方仍是 codex。
- 验收顺序:codex 施工 → Fable 按 done.md 与退出码验收 → codex 盲审 → 全绿后 Fable commit + push。

## 案卷影响 **[用户裁决:APU 不重跑]**
- APU 0914 案**不重跑、不重封**:账本、freeze、a4_seal、装配工单全部保持 7.0.3 产物,−3 装配按现有工单完成。后果如实记录:该案 `provenance_ledger.json` 仍含 105 条 `data_gap` 标签条目(pct 全 0.0),报告与复核读到时按"7.0.3 已知假标签"理解;若日后用 7.0.4 工具对该案做复验/`--check-unseal`,会因算法文件哈希漂移被拒,属预期。
- T6 的 APU 回归只在**隔离副本**上跑,作为工具验收证据,**不写回案卷、不改案卷任何文件**。
- 其他案:再次跑 trace/freeze 时自动生效;已封存文件不重写,但新版工具复验/`--check-unseal` 会因算法漂移拒收(**[CX]** 措辞)。

## 复核融合记录(codex 意见 → 裁决)
| codex 意见 | 复算 | 裁决 |
|---|---|---|
| 放大账户阈值新增 peak 拒收(`Z→X 1,X→D 1`) | 成立 | **采纳**:账户阈值一律不动,只改缺口判定 |
| FIFO/LIFO 拒收小额入账制造新假缺口 | 成立 | 同上 |
| 20 万次累加假缺口超阈值,n×eps 上界不成立 | 成立 | 采纳:不承诺全消,写残留声明;gap_eps 取 1e-13 |
| 真实残留 < eps 被吞/提前转给下游 | 成立 | 采纳:不动账户阈值即无此问题 |
| 展示三处保持 1e-6 方向正确,但不是"纯展示" | 成立 | 采纳,更正措辞 |
| `algorithm` 加键不会被拒 | 核实 | 采纳,并同步 scan-schemas 结构示例 |
| v1 T1 fixture 不能复现;三笔构造必现 | 复算 gap=1 | 采纳为 T1 |
| `__slots__` 漏加会报错 | 属实 | v2 不给账户类加属性,问题消失 |
| `test_sqd_gap_repair.py` 直接调 simulate | 属实 | 采纳:`gap_eps` 带默认值 |
| 四组 dust 测试绿不等于行为不变 | 成立(v1 下 FIFO/LIFO 会变) | v2 账户不动故不变;仍加 T3 三策略明细对照 |
| T6/T8 验收不足、PYTHIA 对表约定 | 属实 | 采纳;PYTHIA 纳入(用户) |
| 建议"只把相对阈值用于缺口报告" | — | 采纳并进一步改为"改标签"(用户裁决),数量零变化 |
