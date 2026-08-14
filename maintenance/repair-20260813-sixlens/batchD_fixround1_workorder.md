# 批 D 消化循环第 1 轮工单（F-D1~F-D8 全量＋随轮更正三件）

基线＝b3ee352（批 D 主施工，裁判已 commit）。输入＝裁判派单＋`batchD_adversarial.md` 全文。八条全认全修（F-D7/F-D8 按"最小修＋评估"，做到与留档逐项写明）。**commit 由裁判执行**。

---

## 一、每条改了什么（大白话）

### F-D1（P1 主项）披露核对从"全文子串搜"升级为"位置锚定的章节切片核对"

**原来的洞**：`ident not in report_text or share not in report_text` 两个独立全文子串判断——无关附录里偶然同串就放行；`report_locations` 强制非空却零消费者；份额半边无测试锁。

**现在**（`a5_report_seal.py`）：
- 新函数 `_disclosure_slice(report_text, locations)`＝**report_locations 的消费者**：位置串必须命中报告某一行 Markdown 标题（子串匹配，容忍 "report.md §xx" 形态取段名再试），切片＝该标题至下一任意级标题。一个都定位不到＝收据声称的披露位置不存在，拒。
- 核对全部落在**同一切片**内，且要求三样齐备：**策略名**（pro_rata/fifo/lifo——并列披露的骨架）、每策略 top 终点标识串、每策略份额数字。全文他处的偶然同串不作数。
- 攻击者若想伪装：得在报告里造一个被收据 locations 点名的章节、里面同段写全三策略名＋正确终点＋正确份额——那这段事实上就是披露本身；剩余＝"作者故意把真披露写成看似无关的标题"＝F-12 已接受边界同族。
- locations 是冻结的裁决内容：改收据即 sha 失配（ledger 绑定＋F-D2 冻结绑定＋F-D7 A5 互绑三处咬死），攻击者不能事后改位置。

**反例（盲审攻击原样重放转拒）**：①无关附录（同地址串＋同占位数字，无位置标题）→拒"披露位置在报告中不存在"；②附录标题恰与 location 同名但无策略名→拒"缺策略名"；③ident 在场份额错→拒"缺份额数字"（**M2 变异锁补上**：中和份额半边此用例红）；④披露值散落切片外章节→拒；绿例=真披露段照过（含多章节报告）。位置锚整体中和（切片退化为全文）→独立变异红。

### F-D2 flip 收据入冻结绑定清单

`handoff_manifest.py --check-unseal` 的 `bound_records` 补 `binding.algorithm_params.flip_adjudications`（与 labels_file 同待遇）。反例：冻结后改写收据（裁决人换名）→rc 2"哈希漂移"；删除收据→rc 2"不存在"；复原→放行。变异（删该两行）→红。

### F-D3 同案连续端到端（EVM）

`t_fd3_e2e_single_case_evm`：**同一案根**连续走 ①批 C 真实 replay（replay_duck 产 series/sidecar/balances_final，mint 1000/burn 50 dead-sink 形态）→ `state_from_facts` formal 编译（producer-sidecar 绑定）→ ②`figures_from_facts check` 末点对账＋figure2 收据 → 分布 initial（快照＝同案 balances_final）→ ③`a4_gate register/finalize --workflow-type new-analysis`，**seal-files 真封 figure2_check_receipt.json＋analysis-state.json**（接缝：figures/state 真实产物被 A4 在同案封口）→ 分布终态链（final scan→record-round→LOW_SAMPLE terminal）→ ④`a5_report_seal` 同案收口。四段断言逐段落盘。

**如实声明**：Solana 链的 state→figures 段仍由批 C `t_f05_f04_solana_chain`（另案）承载——Solana 侧同案连续链未建，理由＝Solana replay 产物形态（sol-rows）接入完整发布案的夹具成本超本轮预算；批 D 的 B-2 Solana 端到端起点是发布闸（含 A5 重验），不冒充 state→figures 段。plan "EVM＋Solana 各一条"在本轮满足 EVM 一条，Solana 差额如实记 batchD_ledger 遗留。

### F-D4 裁决面形式 sanity 闸＋残余边界声明

`load_flip_adjudications` 增：`approved_by` strip 后 ≥2 字符（单字符占位拒）；`user_decided_at_utc` ∈ [2026-01-01, now＋1天]（1970/未来预签拒）；`evidence_refs` 每件实物 ≥16 字节（1 字节垃圾拒）。反例三条＋变异（时间闸中和）红。**残余边界声明（本工单 §四）与 scan-schemas §4a 注释同步**：这些是形式下限——**机器验不了裁决实质真伪**（approved_by 是不是真的用户、evidence 内容是否真是核对记录），与 tolerance-waiver 同款设计边界；防的是"形式上就不是裁决"的收据，不是防蓄意伪造完整裁决面的人。

### F-D5 GPT-F-06 两格补齐

- "深挖全 fetch_failed"独立用例（mock getSignaturesForAddress 返回 None）——盲审存活变异 M1 复测**转红**（删判据该用例红）。主工单"由②一并覆盖"的错误自报在此更正：②走的是 all_zero_delta 路径，fetch_failed 判据此前确无锁。
- `CLEAN` 正例格：销户账户深挖到区间内事件且边集覆盖 → exit 0、status=CLEAN、events={checked:1,covered:1,missing:0}、invalid_reasons=[]。

### F-D6 prepare 期临时件泄漏

`refresh_manifests` 的 `staged.append` 移到写 tmp **之前**（先登记再写）——写到一半抛错的 tmp 落在清理循环遍历范围内。新用例：mock `json.dump` 第 2 次抛 OSError（且先写半截污染 tmp）→正式件字节原样＋**零临时件残留**＋exit 2＋注入命中标志（计数＋stderr 串）。回退型变异（append 挪回写后）→红。

### F-D7 收据三处口径统一（最小修全做，无留档差额）

- **trace**：收据必须在案根（--out 所在目录）内，案根检查先于结构验证（案外收据报位置错，不报次生错）→exit 2。
- **A5**：废除硬编码 `flip_adjudications.json`——按 **ledger `input_binding.algorithm_params.flip_adjudications` 的 path＋sha/size 定位并三验**，与 freeze 前置 3 消费同一实物。反例：改名收据合法案（`flips_receipt.json`）不再误伤（DISCLOSED 且 receipt.path 如实记新名）；换收据（同名另一份、裁决人被换）→"sha256/size 不符"拒——**"甲收据过 freeze、乙收据过 A5"封死**；变异（sha 互绑中和）红。
- **freeze**：`check_bound_file` 原有语义（案根拼接三验）不动——trace 已限案根＋sha 绑定后，三处閉合：案根内＋同一 sha。`check_bound_file` 对绝对路径无案根强制这一残余记 batchD_ledger 遗留（存量 ledger 记绝对路径的兼容面，收紧属 R10 设计）。

### F-D8 最小修＋评估（逐项写明做到哪）

1. **"封死删/换 ledger 旁路"表述改准**（三处：CHANGELOG 6.40.0 条目、scan-schemas §4a、a5 docstring）→"封死**单边改动**；freeze 自身无上位 sha 锚，连 freeze 一起改写属批 C 终验定性的自洽小件残余边界"。**评估落点落地**：发布闸 new-analysis 段新增 **A5 seal 重验**（`a5_report_seal.validate_seal` 入 `run()`，此前发布闸只查 a5 文件存在）——A5 的 final scan 绑定链（`final_bindings.entity_freeze` 等三验）与 provenance_flip_bundle 由此进入发布必经路：完整案删 freeze 实测发布闸红（新用例）；缺 `--report` 无法重验＝fail-closed 报错（新用例）。单元层"删 freeze＋删 ledger→NO_LEDGER"保留＝无溯源简报案的合法语义，机器锚在发布闸层，此口径已写进 scan-schemas。freeze 自身 sha 锚（案外/上位锚）设计留 R10（见 r10_ledger 追加）。
2. **审计早退落报告**：`bail_invalid()`——边集缺失/签名史失败/抽样零命中三条早退路径全部落精简 INVALID_SAMPLE 报告（身份＋原因，不编造样本统计）再 exit 1；capture.md 补"不存在失败无报告形态"。新用例：边集缺失→rc 1＋报告 status 在场。
3. **A-1 参数错不归档**：`--tolerance-bps < 0` 改回普通拒绝（"参数错误，不作废旧收据"）——作废语义只属于"政策判定拒绝了放大请求"，手滑负数不构成对上一轮结论的否定。新用例：负容差→exit 2＋旧 PASS 收据原地未动＋零归档件。

### 随轮更正三件

- CT-SEMANTIC-56 needle：`superseded` → `supply_truth.json.superseded-`（带上下文短语，contract routes 复验过）。
- 本工单节拍句式：**commit 由裁判执行**（前两批把"未 commit"写成完成态描述的记账问题，本轮起统一此句式）。
- batchD_ledger 新增「二d 批 D 消化轮 1 遗留」：报错换岗致断言精度下降（旧闸误删不红）＋恢复精度的做法（新旧闸各立独立定向用例）。

## 二、diff-finding-map（hunk→owner）

| 文件 | hunk | owner |
|---|---|---|
| scripts/report/a5_report_seal.py | `_disclosure_slice` 新函数＋provenance_flip_bundle 重写（位置锚/策略名/同切片） | F-D1 |
| scripts/report/a5_report_seal.py | 收据按 ledger 绑定定位＋sha/size 三验 | F-D7 |
| scripts/report/a5_report_seal.py | docstring"单边改动"改口 | F-D8-1 |
| scripts/report/handoff_manifest.py | check-unseal `bound_records` 补 flip 收据 | F-D2 |
| scripts/report/handoff_manifest.py | load_flip_adjudications：approved_by ≥2／时间范围／证据 ≥16B | F-D4 |
| scripts/report/entity_source_trace.py | 收据案根检查前移（先位置后结构） | F-D7 |
| scripts/report/audit_release_gate.py | new-analysis 段 A5 seal 重验（含缺 --report fail-closed） | F-D8-1 |
| scripts/evm/fetch_hypersync_v2.py | staged.append 前移 | F-D6 |
| scripts/solana/audit_closed_accounts.py | `bail_invalid` 三早退接线 | F-D8-2 |
| scripts/lib/supply_truth_gate.py | 负容差改参数错（不归档） | F-D8-3 |
| scripts/tests/test_repair_batch_d.py | F-D1 五例并入 t_f06_a5_disclosure＋t_fd2/4/5/6/7/8/3 七新函数＋收据 locations 约定对齐 | 全部 |
| scripts/tests/contract_manifest.json | CT-56 needle 加强 | 随轮① |
| references/scan-schemas.md | §4a 披露锚定口径/证据下限注/单边改动改口 | F-D1/4/8 |
| references/data-pipeline-solana-capture.md | 早退也落报告 | F-D8-2 |
| CHANGELOG.md | 6.40.0 条目两处表述改准（不新增版本号——消化轮属 6.40.0 工程内） | F-D8-1 |
| maintenance/.../batchD_ledger.md | 二d 遗留节 | 随轮③ |
| maintenance/.../r10_ledger.md | R10-14 追加（freeze sha 锚设计） | F-D8-1 |

## 三、红绿与变异证据（实跑）

- `test_repair_batch_d.py` rc=0（F-D1 五例／F-D2 四例／F-D4 四例／F-D5 两例／F-D6 两例／F-D7 三例／F-D8 四例／F-D3 四段全 ok；主施工既有用例零删改、A5 夹具 locations 按新约定对齐＝夹具跟随新契约，断言不放宽）。
- 消化轮变异 8/8 全红（清 pycache）：盲审存活 M1（fetch_failed 判据）/M2（份额半边）**双双转红**＋FD1 位置锚/FD2 绑定/FD4 时间闸/FD6 回退/FD7 互绑/FD8 重验删除。
- 受影响既有测试 9/9 rc=0：p105／a4_gate／round4_a5_seal／handoff（67 项）／audit_release_gate／entity_source_trace／repair_batch_a/b/c。
- 三守卫＋契约路由 PASS；counterexamples 三脚本重放 rc=0（flip_receipt_chain 自动携带 F-D1 新反例）。
- 全量 `run_all.py`：EXIT 见回传实测。

## 四、残余边界声明（F-D4 点名补全＋本轮新增）

1. **机器验不了裁决实质真伪**（F-D4）：sanity 闸只拦"形式上就不是裁决"的收据（占位主体/荒谬时间/垃圾字节）；approved_by 是否真是用户、evidence 内容是否真是核对记录、reason 是否言之有物——机器无从判定，与 tolerance-waiver 同款设计边界。蓄意伪造完整裁决面＝控制案目录者的自洽小件族（批 C 终验定性）。
2. `entity_freeze.json` 自身无上位 sha 锚（F-D8-1）：单边改动已封；"连 freeze 一起改写"在发布闸层由 A5 重验的 final scan 绑定链拦（完整案），单元层／无分布链案剩余属 F-12 边界同族。freeze 案外锚设计＝R10-14。
3. `check_bound_file` 对绝对路径绑定无案根强制（F-D7 残余）：trace 已限案根后新产 ledger 无此形态；存量绝对路径 ledger 的兼容面收紧留 R10。
4. Solana 同案连续端到端未建（F-D3 差额）：如实声明于 §一，记 batchD_ledger 遗留。
5. 主工单 §④ 既有四条声明继续有效。

修复轮1完成（commit 由裁判执行）
