# 【修复工单】F-03 批 1:共享 SQD 覆盖地图「动态 head 当身份」修复(主体段)

- 基线(冻结):main = `5156f6e9a51ac0235a6855033ed3f2b53fe35686`(VERSION 6.52.13)。施工期间不得 rebase/merge/commit。
- 施工方:codex。**只改文件,不执行任何 git 写操作(不 commit/不 add)**;验收与代 commit 由裁判方完成(两段提交协议:本单是第一段主体,producer_history 登记+版本面在第二段,本单禁改)。
- 出处:codex 六视角全量 review 2026-08-27 判 F-03 P1(修复中新引入,引入提交 b005a468);修复计划经 @CX 只读复核修订为 v2 并获用户批准(含 D1 裁决)。本工单自包含,无需读取外部报告。

## 工单五栏

**1. 不变量(这道闸永远要保证的事)**:
共享地图复用闸必须保证——(a) 只有当资产与当前 SQD 端点被证明是**同一数据集的同一段历史**(稳定身份全等 + 历史锚 slot 的 block hash 实测全等 + finalized head 单调不倒退)、且全部已知风险点(canary/candidate/refuted)逐 slot 重验通过时,才允许复用资产 counts;(b) ledger 中每一行 `counts_coverage=true` 的覆盖声明,必须与最终交付 counts 的字节来源**逐 slot 一致**——不得声明覆盖任何未实际验证/未实际拉取的 slot;(c) 任何身份不确定、字段未知、重验失败、请求失败的情形一律 fail-closed 回退全扫,不得部分放行。

**2. 同族清单(rg 全库,一起修到同一深度)**:
- `scripts/solana/sqd_coverage_probe.py::_load_known_map`(:394-484 复用闸主体)+ 调用点 `run_probe`(:923-941);
- `scripts/lib/solana_exact_validate.py::validate_shared_map`(:689 独立 validator,须与复用闸同深);
- `scripts/lib/solana_exact_validate.py::validate_coverage`(:483-489 producer 钉扎,D1 项);其四个消费面 `scripts/solana/replay_edges.py`、`scripts/solana/sqd_gap_repair.py`、repair bundle 深验、reconcile 深验——**只核实它们经 validate_coverage 受益、不单独改**;
- `scripts/solana/sqd_coverage_probe.py::export_shared_map`(:505 导出侧,核实其产物满足新校验,预期零改动);
- 测试夹具:`scripts/tests/test_sqd_coverage_probe.py::test_shared_map_lifecycle…`(手写资产夹具补字段);
- 施工时 `rg -n "metadata_normalized|_load_known_map|validate_shared_map|known.map" scripts/` 复核清单无遗漏,结果附 done 报告。

**3. 三件套测试**(全部先红后绿,红例证据落盘,见「红绿证据纪律」):
- a. 原反例:head 单调前进(资产 head=1000,当前 head=1010/新 hash)其余全同 → 基线代码判 `metadata-changed` 拒复用(红);修复后复用成功(绿);
- b. 同族变体:同一不变量的其他违反方式(详见测试清单——身份漂移族、锚不符、账本一致性);
- c. 失败分支:重验请求超时/中断/异常 → 整体回退全扫,不得部分放行。

**4. 新建代码自审**:本单新建/改写的每段代码,按六视角①(字段来源:身份判定的每个输入是实测还是自报?锚 hash 必须来自本次 SQD 实测,不得信资产自报)②(失败分支:每个 except/错误分支是否 fail-closed?)自查,结论写进 done 报告。

**5. 归因预判**:F-03 属「修复中新引入」(SQD 覆盖闸工程批 2 的新功能把动态观测写成身份)。流程段修正:修复新建代码此前未按「真实活链生命周期」出正例——本单的 head-forward 正例即补此缺口。

## 修复规格(按此施工,不得自行扩/缩范围)

### A. 身份模型(改 `_load_known_map`,替换 :423-424 全字典等式)

1. **显式键分类**,模块级常量:
   - 稳定键 `{"dataset_id", "start_block", "real_time"}`:资产 normalized 与当前 normalized 逐值全等,不等 → fallback reason `metadata-identity-changed`;
   - 动态键 `{"finalized_head", "number", "hash", "height"}`:豁免全等,进入单调/锚检查;
   - **未知键无论类型一律拒绝** → `metadata-identity-changed`。⚠ 实现要点:`_normalize_metadata`(:189-193)只复制 str/int/bool,浮点/数组/对象/null 被静默丢弃——未知键检查必须对**原始 head 响应**(`head_result.value`,解包 "result" 后的 dict)做,不能只比两份 normalized。需要把原始值传入 `_load_known_map`(签名扩参)。资产侧只有 normalized(历史如此),资产侧检查基于 normalized 键集;当前侧检查基于原始键集;
   - **别名矛盾拒绝**:当前原始响应中 `number`/`height`/`finalized_head` 若同现,必须逐对相等,矛盾 → `metadata-alias-conflict`;head 值必须是非 bool 的非负整数(bool/负数/字符串 → 结构化 fallback,不许抛裸异常)。
2. **head 单调闸**:
   - 资产 `sqd.finalized_head_at_scan` 缺失或非整数(bool 算非整数)→ `head-at-scan-missing`;
   - 当前 finalized_head < finalized_head_at_scan → `head-regressed`;
   - 资产 `slot_counts.to_slot > finalized_head_at_scan` → `map-exceeds-scan-head`。
3. **历史锚查询**(裁判方已实测可行,证据见下):复用判定通过 1/2 后、逐 slot 重验之前,向 SQD stream 发**独立请求体**(不动主扫描模板 `sqd_query_body`):
   ```json
   {"type":"solana","fromBlock":<finalized_head_at_scan>,"toBlock":<finalized_head_at_scan>,
    "includeAllBlocks":true,"fields":{"block":{"number":true,"hash":true}}}
   ```
   要求返回块的 `header.number == finalized_head_at_scan` 且 `header.hash == 资产 metadata_normalized.hash`(资产该字段缺失或非字符串 → `identity-anchor-unavailable` 回退;hash 不等 → `identity-anchor-mismatch` 回退;请求失败 → 结构化回退)。该请求记 ledger 一行:`mode="identity-anchor"`、`counts_coverage=false`、provider="SQD"、query_body_sha256/response_sha256 照实。
   【裁判方 2026-08-27 实测证据】对 `https://portal.sqd.dev/datasets/solana-mainnet/stream` 发上述请求体(slot 441536664)返回 `{"header":{"number":441536664,"hash":"DobpLyavu7y3Fc5zwuB9QpeviCV6A4fuAdPkwLC7ZsxS"}}`,与入库资产 `20260827.json` 记录的 hash 逐字节全等。
4. **查询模板绑定**:资产 `sqd.query_body_sha256` 缺失/非 64hex → `query-template-missing`;≠ 当前 `sqd_query_template_sha256()` → `query-template-changed`。
5. **必须核实**:新增的 `identity-anchor` ledger 行不被 `validate_coverage` 的覆盖并集/成功区间逻辑(`_successful_coverage_range`、scan_ranges 对账)误算为覆盖来源(`counts_coverage=false` 应已排除,核实并写进 done 报告;若需容错新 mode,同步改 validator 并加测试)。
6. **保持不动**:TTL 30 天、endpoint_fingerprint 全等、三件套 sha256/size/区间/编码校验、canary/candidate/refuted 重验语义、overlap 裁剪、fallback 时 counts 归零。

### B. 重验通道:纯并发化(禁止跨 gap 范围合并)

- 重验点集合 = canary ∪ candidate ∪ refuted(现状不变);
- **只合并 slot 真正连续**(相邻差 1)的重验点为一个 range 请求;**禁止跨任何 gap 合并**——理由(不变量 b):`_scan_request` 对整个请求范围写 `counts_coverage=true`,跨 gap 合并会让 ledger 声明覆盖未验证的中间 slot、与交付字节断契约;
- 并发:ThreadPoolExecutor,并发数取 `args.workers`(`_load_known_map` 扩参传入;默认 1 时与现串行等价);
- 比较语义逐字不变:仍在重验点位置逐值比对,任一不等 → `recheck-mismatch:<slot>` / `canary-counts-changed` 回退;
- **失败整体回退**:任一请求失败(超时/429/分页截断/worker 异常)→ 整个复用回退全扫,不得拿部分完成结果放行;已记的 ledger 行保留(诚实审计),但 reused 判 None;
- ledger 行:每个 range 请求一行 `mode="recheck"`,from/to 为该 range 实际边界(全部由连续重验点构成,零多余覆盖声明);行内 seq/时序遵守 `_append_ledger` 现约定。

### C. `validate_shared_map` 增补(与 A 同深;全部结构化 reason,禁裸异常)

- sqd 段:`metadata_normalized` 为 dict;`metadata_sha256` 与其 canonical 哈希相符(资产带此字段时;20260827 带);`dataset` 与 `metadata_normalized.dataset_id` 一致;`metadata_normalized.finalized_head` 为整数且 `== finalized_head_at_scan`;normalized 内别名键同现须一致;`query_body_sha256`/`endpoint_fingerprint` 为 64 位 hex;`finalized_head_at_scan` 为整数;
- 区间:`slot_counts.to_slot <= finalized_head_at_scan`;
- counts 字节不得含 0(UNSCANNED);
- `candidate_slots`/`refuted_slots` 逐元素:整数(显式拒 bool)、在 [from_slot, to_slot] 内;
- `generated_at` ISO 时间可解析;
- ⚠ 硬约束:**新校验必须对 tracked 资产 `assets/sqd-solana-coverage-map/20260827.json` 全部通过**(裁判方已核:五字段齐、441536664 等式成立、to_slot=440368381 ≤ head)。若发现任何新校验会拒真资产,停工在 done 报告说明,不得改资产、不得放宽校验。

### D1. `validate_coverage` 历史 producer 准入(用户已裁决)

- :483-489 验章改为:producer.sha256 == 当前工作树探针哈希,**或** `producer_history.PRODUCER_HISTORY` 中 `script == "scripts/solana/sqd_coverage_probe.py"` 且 `status == "ACTIVE"` 且协议匹配(coverage 校验对 `sqd-solana-coverage/v1`,pointer 侧对 `sqd-solana-coverage-pointer/v1`——按 validate_coverage 实际校验对象选对协议,两处都涉及则各自对各自协议)的登记哈希;
- 消费 `historical_producer_hashes`(`scripts/lib/producer_history.py` 提供,收据消费端已有同款用法,照抄其调用形态);
- 负例三条:未登记随机哈希拒 / status 非 ACTIVE(构造 REVOKED)拒 / 协议不匹配拒;正例一条:bccf1802…(已登记 ACTIVE)放行;
- **不改 producer_history.py 本身**(第二段的事)。

### 文档(与代码同段)

- `assets/sqd-solana-coverage-map/README.md`::15-24 sqd 示例补 `finalized_head_at_scan`/`query_body_sha256`;:49 复用条件改写为「稳定身份全等 + 历史锚实测 + head 单调 + 查询模板一致 + TTL 未过期 + 全部已知点重验」,写明动态 head 不再参与全等、未知字段仍 fail-closed。大白话,专有名词带注释;
- `references/scan-schemas.md` 共享地图段(:624 附近)同步:metadata_normalized 语义(含动态 head 观测,复用时按稳定/动态/未知三分类)、`finalized_head_at_scan`/`query_body_sha256` 标复用必检、identity-anchor ledger 行语义;
- 契约:`scripts/tests/contract_manifest.json` 增 CT-SQDGAP 下一号(以文件内实际最大号+1 为准)绑 scan-schemas 新增措辞的稳定 needle;`scripts/tests/contract_ids_snapshot.json` **同步更新**(双向快照,漏改必挂对账测试)。

### 测试清单(改/增于 `scripts/tests/test_sqd_coverage_probe.py`;如体量需要可新建 `test_f03_sharedmap_reuse.py` 并登记进 `run_all.py`)

正例:
1. head 前进(1000→1010/新 hash)+ 锚命中 → 复用成功、重验行数正确;
2. export→advance head→reload roundtrip → 复用成功;
3. 离线实资产准入:读 tracked `20260827.json`(**仅 JSON,不解压 93MB 二进制**),对纯身份判定逻辑(建议把 A 的 1/2/4 抽成可单测的纯函数)断言全过。**禁止依赖真实时钟**(TTL 09-24 到期会让含真实加载的断言腐烂)——不测 TTL 分支或注入固定时钟。

身份负例(每条断言具体 fallback_reason):dataset_id 变 / 当前原始响应含未知标量键 / 含未知数组键(证明非标量真 fail-closed)/ number≠height 同现 / head 为 bool、负数、字符串 / head 倒退 / 锚 hash 不符 / 资产 hash 字段缺失 / finalized_head_at_scan 缺失 / to_slot 超头 / query_body_sha256 缺失、不符 / endpoint fingerprint 变(保留现有断言)。

B 负例:某 candidate 位置计数被篡改 → recheck-mismatch;连续点合并成单 range、断开点不合并(断言 ledger 行 from/to);并发下单请求失败 → reused=None 整体回退;回退产物 fallback_reason 结构化。

validator 负例:counts 含 0 / candidate 含 bool、字符串、越界 / metadata_sha256 不符 / dataset 与 dataset_id 不一致 / head 等式不成立 / malformed 输入(sqd 段为 None、canary 为字符串等)返回 reasons 不抛异常。

D1 用例:四条(见 D1 节)。

夹具:lifecycle 手写资产补 `finalized_head_at_scan`/`query_body_sha256`;transport fixture 新增响应按维护件 §7.5 五字段登记(生产 callsite/协议/fake backend/测试 ID/允许理由)写入 done 报告。

### 红绿证据纪律(无 commit 模式)

先写测试,对**未修改的基线代码**运行,把失败输出存 `maintenance/repair-20260827-f03-sharedmap/batch1_red_evidence.md`(至少覆盖:正例 1 红、锚不符负例在基线不可表达的说明);再实施修复,全部转绿。绿证据 = done 报告附本单相关测试的运行输出。

## 边界与白名单

**允许改动(全集,越界=停工请示)**:
- `scripts/solana/sqd_coverage_probe.py`
- `scripts/lib/solana_exact_validate.py`
- `scripts/tests/test_sqd_coverage_probe.py`(及可选新建 `scripts/tests/test_f03_sharedmap_reuse.py` + 相应 `scripts/tests/run_all.py` 登记行)
- `scripts/tests/contract_manifest.json`、`scripts/tests/contract_ids_snapshot.json`
- `scripts/tests/invariant_manifest.json`(仅当 invariant_scan 因新 transport 调用/入口先红时按其登记纪律补,理由写 done 报告)
- `assets/sqd-solana-coverage-map/README.md`、`references/scan-schemas.md`
- `maintenance/repair-20260827-f03-sharedmap/batch1_red_evidence.md`、`maintenance/repair-20260827-f03-sharedmap/batch1_done.md`(done 报告本身,显式入白名单)

**禁止**:改 `VERSION`/`pyproject.toml`/`SKILL.md`/`CHANGELOG.md`/`scripts/lib/producer_history.py`(第二段);改 `assets/sqd-solana-coverage-map/20260827.*` 任何字节;任何 git 写操作;联网请求(锚查询的实测证据已由裁判方提供,施工用 fixture);删除本单外文件。

**发现工单外问题:只记录进 done 报告,不修正。**

## 完工标准

1. 本单全部新旧测试本机通过:`python3 scripts/tests/run_all.py` 全量跑一遍,结果原样贴 done 报告(已知环境性失败如 sandbox loopback 如实标注,不许改写历史结果);
2. `batch1_done.md` 落盘:五栏回填(同族 rg 结果/自审结论/归因确认)、diff 摘要(按文件列 hunk 目的)、红绿证据指针、§7.5 fixture 登记、工单外发现清单;
3. 工作树只含白名单内改动。
