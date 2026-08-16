# 批 C 消化循环第 3 轮工单（止损轮：仅 N-C4）

施工方：Fable 5 直接施工。基线 `70096b4`（轮 2 已 commit）。盲审轮 2 复核判 4 条全 CLOSED、边界外一步抓 N-C4（P2，"同步一致造假"）；裁判裁定本轮只修这一条、范围最小化；N-C5（as_of_block 无真实对锚＋sol 侧 reconcile schema 无身份键）已裁决入 R10 台账不扩面。工作树未 commit，留裁判验收。

## N-C4 完成态 ✅

**问题**（盲审攻击 C' 实测放行）：发布闸从不读磁盘 `.provenance.json` 实物、不复算登记面与末点链——自造一份原生格式序列文件＋state 用它的转换结果＋绑定块自填（sha/format 全自洽），轮 2 的重转换比对必然通过，案内不需要 sidecar 也不需要 supply_truth。

**修法（盲审给定，逐字落地，净 +26 行）**：`check_series_binding` 在重转换比对通过后，复用编译期同三件现成纯函数发布期复算——
1. `load_series_with_sidecar(案内序列实物)`：**sidecar 实物强制在场**＋输出 sha＋camps_spec/final_balances/inputs 逐项三验；
2. `registry_anchor_check`：supply_truth 三验＋target 三键＋token 对案内 preflight 锚＋位绑定；
3. `endpoint_reconcile`：camps spec＋同源终态快照末点对账。
另加一道交叉：**绑定块 producer 必须与磁盘 sidecar 实物的 producer 一致**（state 自报块不得与实物撕裂）。三件套异常统一 `SeriesProvenanceError→errors.append`（fail-loud 不静默）。

**同步一致造假攻击转拒确认（test_repair_batch_c 新增 3 checks，112→115）**：
- 攻击 C'（盲审原样：`camp_series_v2.json` 自造＋state=其转换结果＋绑定块自填）→ **拒**（"序列缺 provenance sidecar"——sidecar 实物强制在场）；
- 强化变体：连 sidecar 也用公开函数自造、camps_spec/final_balances/replay_stats 全绑案内真件（登记面全过）→ **仍拒**（"末点对账失败"——伪末点对不上真实终态快照的机械重算）。剩余残余=保真末点只改中间点＋伪造整案数据链＝F-12 已接受边界同族（盲审 :520 判"此链上不再有第四层"）。

**误伤三查结果（裁判点名）**：①formal 正常产物（案内 sidecar/supply_truth/preflight 全链在场）发布期复算**零 error 放行**（显式 check"NC4 误伤查① formal 正常产物复算放行"＋既有下游闸绿例本轮起自带三件套复算双重坐实）；②旧简报型 state（无 camp_share_series）**不强加**（既有 check 回归绿）；③exploration 标记产物**按设计拒**（既有 check 回归绿，非误伤）。p105/a4_gate 两处 new-analysis 夹具 state 均无 camp_share_series，不触发新链（本轮预检先查后动，未再出现轮 1 的 run_all 首跑红）。

**变异法自检（2/2"删掉即红"，每次清 __pycache__）**：①三件套整段中和（load 行改 return）→ 攻击 C' 放行；②单层中和 `endpoint_reconcile` → 自造 sidecar 绑真件的强化攻击放行（末点对账是该场景的独立命中层）。

## 测试与退出码证据

- `python3 scripts/tests/test_repair_batch_c.py` → **rc=0（115 checks）**
- `python3 scripts/tests/invariant_scan.py` → **rc=0**（54/61/45——三件套 import 无新 schema 字面量，manifest 零变更）
- `python3 scripts/tests/docs_lint.py --all` → **rc=0**
- 受影响契约组：test_audit_release_gate / test_review_20260804_p105 / test_repair_batch_b / test_a4_gate 逐一 **rc=0**
- `counterexamples/fake_series_dualfeed.py` → **rc=0**
- `python3 scripts/tests/run_all.py` 全量 → **rc=0（"全部通过"）**

## 改动文件

| 文件 | 内容 |
|---|---|
| `scripts/report/audit_release_gate.py` | check_series_binding 追加三件套复算＋producer 交叉（其余零触碰） |
| `scripts/tests/test_repair_batch_c.py` | +3 checks（攻击 C'/强化变体/误伤查①） |
| `references/scan-schemas.md` §13 | 发布期复算一句＋残余边界定性 |

## 边界自查（铁律逐条）

版本三处 6.39.5 未动；contract manifest/snapshot 未动；批 D 生产文件未动；批 A/B 已收口实现未动（audit_release_gate 仅在轮 2 新增的 check_series_binding 函数体内追加，批 B 第二层与其余函数零触碰）；**已 CLOSED 的一切实现未动**（camp_series_provenance/state_from_facts/figures_from_facts/两 producer 本轮零改动——三件套是 import 复用不是修改）；N-C5 未扩面（R10 台账）；未 git commit；未为绿改弱断言。

批C消化轮3施工完成
