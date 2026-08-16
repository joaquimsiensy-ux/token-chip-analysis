# 工单 A（F-10）：供给容差豁免分级硬顶＋over-cap-approval/v1

> 批 2 修复工程第一单。总计划见同目录 plan.md「一、F-10 落地」节（含用户政策定案原文与 @CX 融合记录）。
> 施工纪律：只改文件不执行任何 git 写操作（commit 由裁判代做）；边做边保存；完成后把完工摘要写到本目录 `workorder_A_done.md`（改动文件清单＋每条测试的红→绿证据＋自审结论）。

## 0. 背景一句话

`tolerance-waiver/v1` 的 `approved_tolerance_bps` 与 `observed_diff_bps` 均无上限，且 `json.loads` 接受 `NaN/Infinity`——豁免单现为万能通行证。用户已拍板三段分级制：≤10bps 自动过；10~100bps 普通豁免单；>100bps 必须"如实报告＋用户批准"的独立特批收据，不拦死但缺件即拒。

## 1. 不变量

人工豁免不得成为无界出口：waiver 只覆盖 ≤100bps；>100bps 必须由独立 `over-cap-approval/v1` 收据作保；所有数值字段必须有限（isfinite）；生产侧（supply_truth_gate）与消费侧（shared_release_receipt）任何一侧单独失守即整条失守——两侧必须等深。

## 2. 同族清单（施工首步复核，rg 全库确认无遗漏）

```
rg -l "approved_tolerance_bps|observed_diff_bps|tolerance-waiver" --glob '!maintenance/**' --glob '!archive/**' --glob '!blind-reviews/**'
```
已知命中：`scripts/lib/supply_truth_gate.py`（生产）、`scripts/report/shared_release_receipt.py`（消费）、`scripts/tests/test_repair_batch_a.py`（测试）、`scripts/tests/invariant_manifest.json:286,423`（登记）、`scripts/tests/contract_manifest.json:142`（CT-SEMANTIC-49 needle）、`references/analyze-workflow.md:66`（唯一正式文档面）、`CHANGELOG.md`。若 rg 出新命中，一并处理并在完工摘要说明。

另做 NaN 同族横扫：`rg "json.loads|json.load\(" scripts/lib/supply_truth_gate.py scripts/report/shared_release_receipt.py` 涉及 waiver/approval 的解析点全部收口；其他文件的 NaN 面**只登记不修**（写进完工摘要的"发现未修"节，留给裁判定夺，防本单范围蔓延）。

## 3. 修改内容

1. 新常量 `WAIVER_TOLERANCE_BPS_CAP = 100`，生产/消费两侧同源（消费侧 import 生产侧常量，沿用 `FORMAL_TOLERANCE_BPS_MAX` 同源模式，test_repair_batch_a.py:382 有同源断言先例可仿）。
2. `tolerance-waiver/v1` 语义收紧（生产侧 `load_tolerance_waiver`＋消费侧 `_validate_tolerance_policy` 等深）：
   - `approved_tolerance_bps > 100` 或 `observed_diff_bps > 100` 或本次申请 `tolerance_bps > 100` 或消费侧重算实际偏差 > 100 —— 四值取 max 判定是否属"超顶区"；
   - 超顶区必须存在 `over_cap_approval` 引用（waiver 新增可选字段：`{path,size,sha256}` 三验指向独立收据文件，路径约束与 evidence_refs 同款＝waiver 同目录内安全相对路径）；非超顶区出现该字段也照验（在场即验，防挂空引用）。
   - 缺引用/验不过 → `TolerancePolicyError`（exit 2，走既有 `policy_reject`＋`invalidate_stale_receipt` 归档路径）。
3. 新 schema `over-cap-approval/v1`（独立收据文件，参照 flip-adjudications/v1 独立裁决收据模式），必填：
   - `schema: "over-cap-approval/v1"`
   - `request` 块：`{target{chain,token,as_of_block}, observed_diff_bps, requested_tolerance_bps, replay_stats{path,size,sha256}, reason(非空详述)}`——与 waiver 主体逐项全等/绑定（target 全等、数值一致、replay_stats 指向同一实物）；
   - `request_sha256`：对 request 块规范化 JSON（sorted keys、紧凑分隔符）的 sha256，消费侧独立重算比对——防批复与本次运行脱钩、防复用旧批复；
   - `nonce`（非空唯一串）＋`expires_at_utc`（必填，Z 结尾 UTC，须晚于 `user_decided_at_utc` 且验收时未过期）；
   - `user_approval`（用户批复原文，非空）＋`reported_to_user`（如实报告的偏差原因原文，非空）＋`approved_by`（非空）＋`user_decided_at_utc`（Z 结尾 UTC，不得晚于 now+1d）。
4. 数值有限性收口（现行新洞）：waiver 与 approval 的全部数值字段过 `math.isfinite()`；JSON 解析层用 `json.loads(text, parse_constant=_reject_constant)` 拒 `NaN/Infinity/-Infinity`——两侧全部 waiver/approval 解析点统一。
5. 砍两条伪防线：**不加** `approved_by` 长度下限、**不加** `user_decided_at_utc` 的 2026-01-01 下界（保留"不得晚于 now+1d"上界）。
6. 文档：`references/analyze-workflow.md` 供给真值闸段更新三段分级表＋over-cap-approval 流程（含"Fable 必须在会话内向用户如实报告偏差原因、取得批复后才可写此收据"的流程条款＋防伪边界声明："此设计防工作流走捷径/误操作，不防持同用户权限的恶意进程"）；确认 CT-SEMANTIC-49 needle `tolerance-waiver/v1` 仍在文档中（语义收紧不改名，needle 不破）。
7. 登记：invariant_manifest.json 两处 waiver 相关条目按新语义更新描述（如需）；若新增测试文件则挂 run_all.py SUITE（本单倾向扩展 test_repair_batch_a.py 不新增文件，减少挂载面）。

## 4. 三件套测试（先红后绿；全部挂 test_repair_batch_a.py 既有夹具族，仿 write_waiver(mutate=...) 模式）

a. 原反例（先确认红）：
- `approved_tolerance_bps=100000` 裸 waiver（无 approval 收据）→ 生产侧 exit 2、消费侧拒。当前代码此例通过——这是先红证据，完工摘要必须附"修前跑通过、修后拒绝"的双跑记录。
- `observed_diff_bps=100000` 预先虚报、无 approval → 同上。
- `observed_diff_bps=NaN`（JSON 原文 `NaN`）→ 当前代码静默通过全部比较（新洞先红），修后两侧均拒；`Infinity/-Infinity` 同族。

b. 同族变体：
- 边界三点：100（普通区最后一点，合法 waiver 应绿）／100.0001／101（超顶区，无 approval 拒）。
- 错位组合：approved=50 但 observed=5000；approved=5000 但 observed=50；申请 tolerance=200 但 approved=90。四值 max 判定下全部落超顶区。
- approval 收据变体：request_sha256 与重算不符（换 request 内容）／nonce 空／已过期／`user_decided_at_utc` 晚于 now+1d／`user_approval` 空串／replay_stats 指向另一份实物。
- 非超顶区挂了 approval 引用但引用 sha 错 → 拒（在场即验）。

c. 失败分支：
- approval 文件不存在→政策错 exit 2；approval 文件不可读（chmod 000）→通道故障 exit 1（与 waiver 的 F-D 两义拆分同款，test_fd_unreadable_files_all_land_on_exit_1 有先例）；approval JSON 损坏→exit 2。

d. 绿例防误伤：
- ≤100bps 现行九字段正常 waiver 照常放行（生产 rc=0＋消费放行）。
- >100bps 带完整合法 approval 收据 → 放行（用户政策：不拦死）。
- 存量夹具 FIXTURE_DIFF_BPS=9900 落在超顶区：全部旧绿例升级为带合法 approval 收据，逐条核对修后仍绿（防假绿假红，逐条列进完工摘要）。

e. 两侧独立直测：每条规则生产侧、消费侧各自直测命中（不允许"前一层先拒"造成假覆盖——消费侧用例沿用 consumer_case 的"重绑收据 inputs size/sha"手法让检查真正走到目标层）。

## 5. 新建代码六视角①②自审（完工摘要必填）

- ①字段来源：approval 每个字段的信任根是什么？request_sha256 重算是否消费侧独立完成（不信自报）？
- ②失败分支：每个新增校验的异常路径是否 fail-closed？归档失败是否升格 exit 1？staging/tmp 是否零残留？

## 6. 归因预判

F-10 原属"修复中新引入"（waiver 是批 A 新增批准面）；NaN 洞属"历史漏检"追加。本单完工后两者均闭合；若自审发现新的同族面，登记进完工摘要"发现未修"节。

## 7. 验收口径（裁判执行，施工方知悉）

裁判独立跑：`python3 scripts/tests/test_repair_batch_a.py`（rc=0）＋原反例三条手工复现（修后全拒）＋`python3 scripts/tests/run_all.py` 全绿＋git diff 逐文件审。
