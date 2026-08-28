# 【修复工单】F-03b 批 3:重验失败分级——限流剔除段转全扫,不再整体回退(v6.52.15 主体段)

- 基线(冻结):main = `9b1c4b5`(v6.52.14)。施工方 codex,**只改文件、禁 git 写操作**;两段提交协议:本单为主体段,登记面/版本面另单。
- 出处:F-03 修复后 ARC live 实测(2026-08-27,92,643 个 recheck 请求/6.3h):91,461 成功、**1,182 失败全部是 SQD 服务端限流(529×1034+429×148,均匀散布)、零数据不匹配**,现行"任一请求失败即整体回退"使大地图复用在真实限流环境下几乎必然回退全扫。用户已裁决立本单。

## 工单五栏

**1. 不变量**:复用闸对"数据可疑"与"数据未知"必须分级——(a) 任何**值不匹配**(重验值≠资产值、canary 逐值不等)意味着地图可信度崩塌,仍整体回退全扫,一个都不放过;(b) 纯**请求失败**(限流/超时/截断/worker 异常)只意味着"这些 slot 本轮没验上":这些 slot **绝不复用**(从复用字节中剔除、交给 full 扫描重新拉取),已验证的其余部分照常复用;(c) 账本与交付一致性铁律不变:任何 `counts_coverage=true` 的行(含 map-reuse 行)声明的每个 slot,其最终交付字节必须来自该行所述来源——**map-reuse 覆盖声明必须按验证通过的子区间拆分,不得笼罩未验证段**(P1-1 同族,别再犯)。

**2. 同族清单**:`_recheck_known_slots`/`_load_known_map`(判定与回退)、`run_probe` 复用调用点(map-reuse ledger 行与 counts 写入 :1146-1170 附近)、`validate_shared_map`(不涉,预期零改动)、`validate_coverage`(核实对拆分后的 map-reuse 多行/full 补扫组合仍闭合,预期零改动)、文档 README/scan-schemas 复用语义段。施工时 `rg` 复核,结果附 done 报告。

**3. 三件套**:a. 原反例=live 实测场景缩样(部分 recheck 请求持续限流失败)→ 基线整体回退(红)→ 修后部分复用+失败段 full 补扫(绿);b. 同族变体=canary 段请求失败、值不匹配两类各自的正确行为;c. 失败分支=重试后仍失败→剔除;剔除逻辑自身异常→整体回退。

**4. 新建代码自审**:①②视角结论写 done 报告(重点:剔除段的界定必须来自本轮请求实测结果,不得信任何自报;每个新分支 fail-closed 方向=宁可多扫不可错用)。

**5. 归因预判**:F-03b=前单设计的实用性残余(fail-closed 粒度过粗),非代码错误;修"设计粒度"。

## 修复规格

### A. 失败分级与末尾重试(`_recheck_known_slots` + `_load_known_map`)

1. **分级**:每个 range 请求的结局三分——`verified`(成功且全部 slot 值==资产值)/ `mismatch`(成功但任一 slot 值≠资产值)/ `request-failed`(transport 失败、part 为 None、长度短于区间=分页截断、worker 异常);
2. **mismatch ⇒ 整体回退**(现行为不变,reason 仍 `recheck-mismatch:<slot>`;canary 值不等仍 `canary-counts-changed`);
3. **request-failed ⇒ 末尾重试一轮**:全部首轮失败的 range 在本轮结束后统一重试一次(同并发池;重试行照记 ledger,mode="recheck");重试成功且值全等 → 归入 verified;重试出 mismatch → 整体回退;重试仍失败 → 该 range 标记 `unverified`;
4. **canary 特例**:64 个 canary 点所在 range 若重试后仍 request-failed → **整体回退**(reason `canary-recheck-unavailable`)——canary 是地图可信度抽样核心,仅 64 点请求面极小,不允许带伤复用;
5. **unverified 段处理**:这些 slot 从复用中剔除——复用字节写入 counts 后把 unverified 段清零,`_missing_ranges` 自然把它们纳入 full 扫描;candidate/refuted 落在 unverified 段的,其案级判定由 full 扫描的新鲜值重新分类(诚实:未验证的驳回/候选不继承);
6. **shared_map info 增记**:`unverified_ranges`(列表)+ `recheck_stats`(verified/unverified/retried 计数)供审计;`reused_ranges` 语义改为"实际按验证结果复用的子区间列表"。

### B. 覆盖声明拆分(P1-1 同族,重点防线)

- map-reuse ledger 行与 scan_ranges 的 `map-reuse` 条目**按验证通过的连续子区间逐段生成**(每段一行,from/to=该段边界,response_sha256=该段实际复用字节哈希),未验证段与案区间外不得出现在任何 map-reuse 声明里;
- 失败的 recheck 行(首轮与重试)`counts_coverage` 直接置 false(它们本来就没提供交付字节;比 1b 的"事后降级"更干净——1b 的整体回退降级逻辑保留,用于 mismatch 路径);
- 核实 `validate_coverage` 对"多段 map-reuse + full 补扫"组合闭合(成功区间并集无洞等式),必要时只加测试不改闸。

### C. 文档

- `assets/sqd-solana-coverage-map/README.md` 复用条件段:补一句大白话——"重验时值对不上=整张地图作废全扫;个别请求被限流失败=只有那几段不复用、单独重扫补上,其余照常复用";
- `references/scan-schemas.md` 共享地图/复用段:`unverified_ranges`/`recheck_stats` 字段、map-reuse 多行拆分语义、mismatch vs request-failed 分级。

### 测试清单(`test_f03_sharedmap_reuse.py` 扩展;夹具按 §7.5 登记)

1. 部分限流:两个 range 首轮失败、重试仍失败(非 canary 段)→ 复用成功、`unverified_ranges` 正确、map-reuse 行只盖验证段、失败段被 full 扫描、端到端发布后 `validate_coverage` PASS、最终 counts 里 unverified 段字节来自 full 响应;
2. 重试拯救:首轮失败重试成功(需支持"同请求第 N 次不同响应"的 transport fake,§7.5 登记)→ 全段复用、ledger 含两行(失败+成功);
3. mismatch 仍整体回退(回归保持);canary 值不等仍整体回退(回归保持);
4. canary 段请求重试后仍失败 → `canary-recheck-unavailable` 整体回退;
5. 重试出 mismatch → 整体回退;
6. 全部 recheck 段都 unverified(极端)→ 复用退化为纯 full(行为等价全扫,声明零 map-reuse 行,发布仍 PASS)。

## 白名单(全集,越界停工)

`scripts/solana/sqd_coverage_probe.py`、`scripts/tests/test_f03_sharedmap_reuse.py`、`scripts/tests/test_sqd_coverage_probe.py`(既有 lifecycle/roundtrip 若受 map-reuse 拆分影响需适配)、`assets/sqd-solana-coverage-map/README.md`、`references/scan-schemas.md`、`maintenance/repair-20260827-f03-sharedmap/batch3_red_evidence.md`、`maintenance/repair-20260827-f03-sharedmap/batch3_done.md`。
**禁改**:`solana_exact_validate.py`(若确需动,停工请示并说明理由)、契约两件(拆分语义若需新 needle,停工请示)、VERSION/CHANGELOG/pyproject/SKILL/producer_history(第二段)、20260827 资产、任何 git 写操作、联网。

## 完工标准

先红后绿证据落盘(红=基线 9b1c4b5 整体回退行为);本机 run_all 全量原样贴报告;`validate_shared_map` 对 20260827 仍 ok=true;done 报告五栏回填+diff 摘要+§7.5 登记+工单外发现。
