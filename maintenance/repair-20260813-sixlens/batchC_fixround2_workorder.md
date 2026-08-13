# 批 C 消化循环第 2 轮工单（F-C1 终关＋N-C1/N-C2/N-C3）

施工方：Fable 5 直接施工。基线 `e26dac6`（轮 1 已 commit 为 `eb6bee2`，裁判台账更正入 `e26dac6`）。盲审复核（batchC_adversarial.md「消化轮 1 复核」节）判 5 关 1 开＋3 条新 P2；本轮 4 项全收口。工作树未 commit，留裁判验收。

---

## 逐项完成态

### 1. F-C1 终关（REOPEN P0→P1 → 本轮关死）✅

盲审定性：轮 1 的编译期三道全关，但发布闸 `check_series_binding` 是**自证式**——state 自报的 sidecar 块、案内同名文件、sha 比对三样都不建立"state 里的序列内容"与"序列文件内容"的联系，两攻击放行（A=手改标记＋自补块指向任意序列；B=formal 编译后篡改 series）。

修法照盲审建议逐字落地：
- `state_from_facts.bind_series_source` 的 `camp_series_sidecar` 块**补 `series_format` 字段**（发布闸重转换需要分派键）；
- `audit_release_gate.check_series_binding` 在 sha 相符之后，**用编译器同一转换器 `series_to_state_form`（纯函数，直接 import）把案内序列实物重转换一遍，与 state 的 `camp_share_series` 逐点比对**——不等即拒（"state 里的序列不是该 producer 文件产出的"）；绑定块缺 `series_format` 即拒；转换失败即拒。
- 反例实测：**攻击 A**（伪 state＋producer-sidecar 标记＋自补块指向案内真序列、sha/format 全真）→ 拒（重转换比对）；**攻击 B**（formal 合法产物改 `camp_share_series` 一个值、provenance 原样）→ 拒；绑定块缺 format → 拒；formal 正常产物绿例照过（编译器注入的 series 本就是同一转换器的输出，逐点必等——json float round-trip 无损）。
- 为什么两攻击同死：A 的伪 series 与真文件转换结果必不等；B 的改动使 state 侧偏离转换结果。发布闸从"验 state 自洽"变成"验 state 由案内实物机械可再生"。

### 2. N-C1（P2，轮 1 新引入）✅

`check_figure2_receipt` 拆出 `_figure2_input_check`：series 与 facts 两个输入实物**无条件**三段验——basename 在案根**找不到即拒**（轮 1 的 `if cand.is_file()` 条件式整段跳过是穿透点，"收据宣称对账过就必须能验"）、符号链接拒、sha 不符拒；facts 从完全不验改为必验。盲审三攻击转拒实测：b) `series.path` 写不存在的名字 → 拒；c) series sha 真＋facts sha 乱填 → 拒；收据缺 facts 绑定段 → 拒。真实生产者产的收据（p105/a4_gate 夹具真跑 check）零误伤。

### 3. N-C2（P2，数字更正＋复扫）✅

**失真归因（一句话）**：轮 1 诊断脚本直接复用 raise 式 `validate_series_payload`（fail-fast，抛**首个**违例即停），我把首个违例点当"最差点"抄进上报表——是**报告摘录方式错误**，不是分类逻辑 bug（分类判据是"过/不过"二值，与违例点取哪个无关）。

**更正后的 C 类数字**（收集模式全量复核，与盲审独立核数一致）：
- MOG：最差闭合点 **idx 177＝99.7433（偏离 0.2567pp）**，是轮 1 上报"第 93 点 99.9440 差 0.056pp"的 4.6 倍——0.26pp 不是 round(4) 舍入能攒出来的，定性只能是数据问题（裁判台账 e26dac6 已按此更正，MOG 裁决不变、不放宽容差）。
- KOGE：日期轴重复 **2 处**（idx 8='2025-06-15'、idx 12='2025-07-18'），轮 1 只报 1 处。

**A/B 类复扫（裁判 ⚠️ 条款：确认"取首个"问题不影响分类）**：收集模式重扫 A 类全部 5 文件（QUQ/ASTEROID/APU 旧版/TAG×2）——负值 0、超 100 零、非有限零、最差闭合偏离全部 **0.0002pp**、日期违例零，"数值面全过、仅桶名不合"的 A 类定义逐案成立；B 类判据=形态检查（与违例点无关），且盲审已用旧编译器（2582c81）对照证实非本批引入。**分类结论零翻案**。

### 4. N-C3（P2，F-C3 加深）✅

`registry_anchor_check` evm 分支补 target 案身份锚（真实收据形态 TAG 实物核对：`target={chain,token,as_of_block}`）：
- target 三键在场合法（dict、chain/token 非空串、as_of_block 正整数），缺即拒；
- `target.chain` 必须与收据顶层 `chain` 一致（真实生产者两处同源，撕裂即拼接/伪造）；
- `target.token` 必须等于**案内 `channels_preflight.json` 的 token**（EVM replay 数据链必产的采集链身份件、自身有 receipt 三验链；preflight 缺席即拒——不留条件式跳过，N-C1 同错不再犯）。
- 反例实测：盲审 1792B 全套伪造链（schema/verdict/位绑定全对但无 target）→ 拒；target 齐但 token 不对案内锚（他案收据复制）→ 拒；target.chain 与顶层撕裂 → 拒。诚实边界（工单如实记）：伪造者把 target.token 写对仍可过本检查——但此时必须命中案内 channels_preflight 的真实 token，伪造成本继续沿数据链上移一环（preflight 自身被 collector receipt 链验）；**sol 侧 reconcile 收据（solana-reconcile/v2）schema 现状无身份键，target 锚加不上去，留 R10 台账**（加身份键属 producer 输出 schema 扩面，超本轮"登记面函数"授权范围）。

## 变异法自检（轮 2 新校验 5/5"删掉即红"，每次变异清 __pycache__）

| # | 校验 | 结果 |
|---|---|---|
| 1 | FC1 终关内容重转换比对 | ✅ 中和后攻击 B 放行 |
| 2 | NC1 series 实物无条件验 | ✅ 中和"不在案根即拒"后攻击 b 放行 |
| 3 | NC1 facts sha 必验 | ✅ 中和 facts 调用后攻击 c 放行 |
| 4 | NC3 token 对案内 preflight 锚 | ✅ |
| 5 | NC3 target 三键结构检查 | ✅（三道同关才放行；只关结构检查一道时后续 chain 检查以 AttributeError 崩住——结构检查的独立价值=把崩溃变明确 exit 2＋可读消息，与轮 1 F-05 缺 camps 情形同型，如实记录） |

施工中方法学记录：变异脚本初版把多行 `if A \\ or B \\ or C:` 的 A 换成 `False and A`——**and 短路只护自己右侧，or 分支照样求值**（target=None 时 B 里的 `.get` 崩），中和多行 or 条件必须改动作行（raise→pass）而不是改条件头；此坑随 pycache 提醒一并留给后续维护。

## 测试与退出码证据

- `python3 scripts/tests/test_repair_batch_c.py` → **rc=0**（103→**112 checks**：F-C1 终关两攻击＋缺 format、N-C1 三攻击、N-C3 三反例）
- `python3 scripts/tests/invariant_scan.py` → **rc=0**（54/61/45——本轮零新 schema 字面量：重转换 import 的是函数、target 检查在既有 consumer 文件内，manifest 无需变更）
- `python3 scripts/tests/docs_lint.py --all` → **rc=0**
- 受影响契约组逐一 rc=0：test_audit_release_gate / test_review_20260804_p105 / test_repair_batch_b（41/41）/ test_a4_gate（23 项）/ test_state_from_facts / test_figures_from_facts
- `counterexamples/fake_series_dualfeed.py` → **rc=0**（夹具补 target 后三场景仍全符合预期）
- `python3 scripts/tests/run_all.py` 全量 → **rc=0（"全部通过"）**

## 改动文件与 owner

| 文件 | owner |
|---|---|
| `scripts/report/state_from_facts.py`（绑定块 +series_format 一处） | F-C1 |
| `scripts/report/audit_release_gate.py`（check_series_binding 重转换比对；_figure2_input_check 无条件双验） | F-C1＋N-C1 |
| `scripts/lib/camp_series_provenance.py`（registry_anchor_check +target 三键/chain 一致/token 对 preflight 锚） | N-C3 |
| `scripts/tests/test_repair_batch_c.py`（+9 checks；write_supply_truth 夹具补 target；FC3"sha 塞顶层"反例带 target 保持命中位绑定分支） | 轮 2 测试 |
| `maintenance/.../counterexamples/fake_series_dualfeed.py`（夹具补 target） | N-C3 配套 |
| `references/scan-schemas.md` §13（终关句/无条件双验句/target 锚句） | 文档同批 |

## 边界自查（铁律逐条）

- 版本三处 6.39.5 未动；contract manifest/snapshot 未动；批 D 生产文件未动；批 A/B 已收口实现未动；**已 CLOSED 的 F-C2~F-C6 实现未重开**（N-C3 动的 `registry_anchor_check` 属 F-C3 加深、裁判显式允许；F-C4 的 closure_mode、F-C5 的收据落盘、F-C6 的 producer 硬拒与 fsync 零触碰；F-C2 只做数字更正与复扫，闸本体零改动）。
- 未 git commit；未为绿改弱断言（夹具补 target=输入合法化；FC3 反例带 target 是让反例继续命中原分支，断言 needle 未弱化）。

批C消化轮2施工完成
