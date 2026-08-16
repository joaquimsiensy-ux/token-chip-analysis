# 六视角修复计划对抗性盲审

结论先说：**反对按现稿直接开工**。批次的大方向可以保留，但现稿至少有四个会让修复“看起来转绿、实际不闭合”的问题：F-04 只把自报数据换成自报文件，F-06 仍未机器证明报告真的并列披露，F-07 明确没有恢复“全有或全无”，以及 F-03/F-04 对 burn 的分母选错会卡死合法案。计划标出的四个卡死点不是穷尽清单。

## ① 逐条裁决表

| 审查项 | 裁决 | 理由与代码证据 |
|---|---|---|
| F-01：EVM tip/as-of 双时点 | **建议修正** | 把 `tip_block` 提前到第一次可能 `finish()` 之前是对的：当前代码先取得 tip 和写 `as_of_block`，却要到 `eth_getCode` 成功后才写 `tip_block`，所以“无代码”失败收据会缺 tip（`scripts/evm/accounting_gate.py:429-441`）。EVM-only 也对；Solana accounting 走 observation bundle，不是这套 tip 语义（`scripts/report/shared_release_receipt.py:278-294`）。但验收不能再要求原反例“被拒”：`as_of_block < tip_block` 在本修法里是合法双时点，shared validator 只应拒绝缺 tip、tip 小于 as-of、或语义字段不一致。当前 shared receipt 仍把 accounting 的 `as_of_block` 直接做统一 target（`scripts/report/shared_release_receipt.py:263-297`），所以计划还应明确：accounting 是“tip 上的模型探测”，不能被下游表述成“冻结块上的模型实测”。建议字段直接叫 `model_probe_block`，并补一条 `as_of=1, tip=100` 的合法绿例，而不是把它列入八条“全部被拒”。 |
| F-02：formal tolerance 钳制与 waiver | **建议修正** | formal 默认上限 10 bps、exploration 不钳、shared validator 调同一个 `decide()`，方向正确。当前 `--tolerance-bps` 无上下界（`scripts/lib/supply_truth_gate.py:175-181`），判定直接信该值（`scripts/lib/supply_truth_gate.py:268-269,310-320`），shared validator也只看自报 verdict/字段，没有重算 tolerance 政策（`scripts/report/shared_release_receipt.py:162-205`）。但新 waiver 仍可由运行者自己写：计划只要求理由、时间和“证据文件存在”。仓库里被计划引用的 precedent 也只检查 `evidence_refs` 非空且文件存在，不绑定内容哈希或裁决主体（`scripts/report/adjudication_validator.py:347-351`）。至少要补 `user_decided_at_utc/approved_by` 或等价的裁决主体、每个 evidence ref 的 sha/size，并限制 `0 <= tolerance_bps <= approved_tolerance_bps`。现有 distribution waiver 已经展示了更强的“用户决定时间＋当前 A4/scan/rounds 哈希”绑定（`scripts/report/holder_distribution_scan.py:803-817`），不该新造更弱收据。 |
| F-03 第一层：owner 快照双向闭合 | **反对** | 计划写成 `sum(balances) ≈ net_supply_raw` 会卡死合法 dead-sink 案。扫描器同时读 `total` 和 `net`（`scripts/report/holder_distribution_scan.py:207-219`），快照分桶明确包含 `burn_sentinel`（`scripts/report/holder_distribution_scan.py:51-62`），因此含 dead 地址的 owner 快照物理合计应闭合到 total，而不是扣过 burn 的 net。仓库已有合法纵切片：mint=100、burn/dead=20（`scripts/tests/test_batch3_evm_vertical_slice.py:129-136,273-292`）；这类案是 `snapshot sum=100, net=80`。照计划实现会误杀。正确修法应先冻结口径：owner 快照含 burn 地址时对 `total_supply_raw` 闭合；净供应只作分布百分比分母，并单独重算 burn 桶。全程用整数交叉乘法，不能把超大 raw 转 float。 |
| F-03 第二层：scan 快照与四查输入同件 | **反对** | EVM 比 sha、不比 path 是对的；但计划把 Solana 整支跳过，留下同值换仓绕过：攻击者可造一份“总和正确、owner 分配错误”的快照，第一层照样过。Solana 的正式 supply producer 已输出并哈希绑定 `holders_owners.json`（`scripts/solana/scan_token_accounts.py:257-268`），observation bundle 也带 `holder_outputs.owners`（`scripts/solana/scan_token_accounts.py:282-293`）。所以 Solana 不应跳过，而应把 distribution snapshot sha/size 对到 supply receipt 的 `holder_outputs.owners`；不需要拿 anchor sampler 当 balances producer。 |
| F-08：记录性 upstream receipts 三验 | **同意** | 计划正确区分了“只验证 scan 已记录项”与“扫描案目录现有项”。当前 producer 把找不到、越界、符号链接、损坏等所有 `ValueError` 都吞成“没记录”（`scripts/report/holder_distribution_scan.py:520-525`），validator 又只验 snapshot/data_map/supply/exclusion，完全没遍历 upstream receipts（`scripts/report/holder_distribution_scan.py:752-780`）。改成“普通缺件可不记录；一旦记录必须 path/sha/size 三验；非法路径和符号链接硬拒”能关闭证据外观问题，也不会重建 v6.39.5 已拆掉的目录在场死环。合法绿例“磁盘有 receipt、scan 未记录仍 PASS”与记录性语义一致。 |
| F-05：四族 addr2camp 互斥 | **同意** | 活跃生产实现确实是四族，没有查到第五个 addr→camp 覆盖器：EVM pass2 在 set 化后覆盖（`scripts/evm/replay_pass2.py:26-38`），Duck 版明确后项覆盖（`scripts/evm/replay_duck.py:371-383`），Solana replay_edges 覆盖（`scripts/solana/replay_edges.py:237-245`），Solana build_evolution 是 `{addr: camp}`（`scripts/solana/build_evolution.py:75-80`）。先按链规范化、再在 set 化/JSON 丢重复键之前拒绝，能打到原问题；entities 多归属确实是另一个有意契约，pass2 用 `setdefault(...).append(...)`（`scripts/evm/replay_pass2.py:35-38`），不应误修。建议四入口调用一个共享 validator，避免四份手抄条件以后再漂；`replay_edges` 缺 camps 的合法性必须在开工前定案，不能留到施工现场临时判断。 |
| 批 C 补漏一：地址规范化查重 | **同意** | EVM 当前两引擎都在映射时 `.lower()`，所以大小写地址本来就落到同一运行身份（`scripts/evm/replay_pass2.py:28-34`；`scripts/evm/replay_duck.py:377-381`）；修复若在 lower 之前查重，确会被 `0xAbC/0xabc` 绕过。Solana 地址大小写有意义，现役实现也原样匹配（`scripts/solana/replay_edges.py:241-255`），不能照抄 lowercase。build_evolution 必须用 `object_pairs_hook` 在 JSON 解析时抓同键；普通 `json.load()` 后重复键已经丢失（`scripts/solana/build_evolution.py:75-80`）。 |
| F-04：series 文件绑定、白名单、闭合、末点对账 | **反对** | 数值有限、0–100、日期严格递增、现代阵营白名单都应该加；当前 compiler 只验容器/长度就原样写入（`scripts/report/state_from_facts.py:85-107`）。但 `--series-source` 只证明“state 与另一个文件字节相同”，不证明该文件来自受控 replay。EVM pass2 只是直接写 JSON，没有 producer receipt（`scripts/evm/replay_pass2.py:110-116`）；Solana replay_edges 也是直接写文件（`scripts/solana/replay_edges.py:309-310`）；只有 build_evolution 另有 inputs manifest（`scripts/solana/build_evolution.py:180-199`）。调用者完全可以把一份数学上自洽的假序列同时放进 source 和 `--series-source`，新闸仍绿。必须绑定受控 producer＋输入清单/回执，或由 compiler 调共享 validator 从绑定 replay 输入重算，不能把“外置文件”当来源证明。另一个未定义点是“末点按 facts 逐实体聚合”：现有 facts 只给 entity 的 addresses/current_raw，state source 的 annotation 只有 type/status，没有 entity→camp 的机器映射（`scripts/report/state_from_facts.py:51-81`），所以现稿无法机械得到每个 camp 的 facts 真值；“实测不等就降级单向下界”会把根修退化成可绕检查。 |
| 批 C 补漏二：日期轴严格递增 | **同意** | 当前 compiler 只数 dates 长度，不验日期格式、顺序或重复（`scripts/report/state_from_facts.py:85-92`）；fig1 到出图时才逐项解析（`scripts/report/figures_from_facts.py:93-104`）。应在 compiler 里按同一 UTC 解析器转成时点后比较，不能直接比较日期字符串；覆盖等时区、乱序、重复和非法日期。 |
| F-04 计划外 burn 卡死 | **反对** | 除 F-03 外，F-04 的“所有阵营同点合计≈100%”也会误杀现役 Solana burn 序列。replay_edges 先用 `minted_cum-burned` 作分母，再把 owner 持仓按该净供应算到约 100%，随后又把 `锁仓/销毁=burned/net` 加进同一行（`scripts/solana/replay_edges.py:272-283`），有 burn 时总和必大于 100%。计划只豁免 `_meta/burn_cum_pct`，没有覆盖这个现役格式。必须先统一 schema：burn 是堆叠桶还是非堆叠旁注；不同 producer 不能各用一种口径后让 compiler 猜。 |
| F-06：flip 裁决收据＋披露门禁 | **反对** | flip fingerprint、entity file sha、handoff 重放同步、freeze 后 ledger sha 绑定，都是必要的；当前 freeze 已记录 provenance ledger sha（`scripts/report/handoff_manifest.py:992-1008`），handoff 也确实按旧字符串参数重装命令（`scripts/report/handoff_manifest.py:780-808`）。但现稿仍没闭合“用户裁决”和“报告并列披露”：新收据没有可信裁决主体，evidence refs 仍只验存在；A5 只要求出现 `flip-...` claim ID，也挡不住一条无关文本。A4 的通用 claim validator只要求 text 非空、report_locations 是字符串数组（`scripts/report/a4_gate.py:200-226`），不会检查报告位置真的含三策略明细；A5 当前也只检查 claims 非空（`scripts/report/a5_report_seal.py:109-128`）。必须让 flip claim 绑定 ledger/fingerprint，并结构化携带三策略 top/份额和报告中的可核位置；A5 要验证当前 Markdown 确实披露这些值，而不是只验 ID。裁决收据还应像 distribution waiver 一样绑定用户决定时间和当前证据哈希（`scripts/report/holder_distribution_scan.py:803-817`）。 |
| F-07：manifest 迁移写失败 | **反对** | 计划把原不变量从“全有或全无”偷换成“部分成功可重跑”。当前函数先验全部候选，然后仍逐文件提交，第二写失败时第一件已经落盘（`scripts/evm/fetch_hypersync_v2.py:277-309`）；计划中的“边写边记清单＋提示重跑”不会改变这个事实，原始 OSError 反例仍得到新旧 schema 混合状态。必须做真正事务：先把全部新文件写到各自临时件并 fsync，提交时保留原件备份；任一 replace/identity 写失败就逐文件回滚并验证回滚，回滚失败保留恢复件且 exit 1。若用户决定放弃事务保证，也必须把 finding 改判为“接受部分迁移”，不能声称 F-07 已修复。 |
| A→B→C→D 批序 | **建议修正** | F-05 先于 F-04、F-06 与 handoff 同批同步，依赖成立。F-02 先于 F-03 只在“F-03 读取 canonical 10 bps”时成立；不能把获批放大的 supply tolerance 直接复用为快照缺口容差，因为前者是“重放供给 vs 链上供给”，后者是“owner 清单是否完整”，是两个不变量（`scripts/lib/supply_truth_gate.py:76-83`；`scripts/report/holder_distribution_scan.py:195-219`）。另有跨批硬耦合：计划说 A/B/C 各自追加 contract manifest，却把存量注册和收口放 D；`test_contract_routes` 对 manifest 与 `contract_ids_snapshot.json` 做精确双向相等（`scripts/tests/test_contract_routes.py:142-152`），而它已经在 run_all（`scripts/tests/run_all.py:53-57`）。每批只改 manifest、不同时改 snapshot，会让该批必红。要么每批同步改 manifest＋snapshot＋权威文档，要么全部契约登记统一留 D，不能半套。 |
| 同族清单完整性 | **建议修正** | addr2camp 四族完整，见 F-05 行；但 tolerance 台账漏了真正的“判定翻转参数” `figures_from_facts.py check --tol-pp`。它由调用者任意给 float（`scripts/report/figures_from_facts.py:221-225`），直接决定图 2 末点与 facts 不同源时 PASS/FAIL（`scripts/report/figures_from_facts.py:179-197`）。这比计划列的 `--samples/--top-n` 更同族，必须纳入本轮钳制或 R10 明账，不能写“同族已列全”。`lp_positions --threshold` 只选要查的交易且代码明确不参与净额（`scripts/evm/lp_positions.py:37-39,86`），可继续归证据强度参数。 |
| 八条原始反例复跑 | **反对** | F-02/03/04/05/06/08 的原反例可构造并能打到目标；F-01 按新设计不应被拒，只应证明双时点被诚实记录；F-07 按现稿仍会留下部分迁移，不能转绿。F-04 还必须新增“伪序列同时写进 source 与 `--series-source`”反例，否则只会证明范围检查，不会证明来源。现有所谓真实 EVM/Solana vertical slice也覆盖不到这些卡死点：EVM slice 只跑 distribution→handoff→audit release（`scripts/tests/test_batch3_evm_vertical_slice.py:225-249`），Solana 同样止于 distribution/handoff/audit release（`scripts/tests/test_batch3_solana_vertical_slice.py:195-221`），都没跑 `state_from_facts.py`、fig1、A4 finalize、A5 seal/build_html。不能用这两条测试声称四个 A5/series 卡死点已绿。 |
| 破坏性注入方案 | **建议修正** | “先证明到达目标分支”原则正确，但需要每个 injection 写明命中标志，不能只看非零退出。尤其 F-07 的第二次 `atomic_write_json` 注入确实能命中逐项提交（`scripts/evm/fetch_hypersync_v2.py:304-309`）；验收应同时断言所有原 done 字节不变，不能只断言捕获 OSError 和打印完成清单。F-08 则要分别注入不存在、错 sha、错 size、越界、符号链接，确认不是被另一个前置路径闸提前拦掉（当前 `_verify_bound` 的实际目标分支在 `scripts/report/holder_distribution_scan.py:745-749`）。 |
| R10：GPT-F-06 audit_closed_accounts fail-open | **反对归台账不修；它阻断本轮解除 BLOCK** | 这是正式 Solana 销户覆盖审计，脚本自己定义“运行失败/样本无效=exit 1”（`scripts/solana/audit_closed_accounts.py:23-27`），但 getMultipleAccounts 失败只 warning+continue（`scripts/solana/audit_closed_accounts.py:257-267`），最后只按 `missing` 决定 0/2（`scripts/solana/audit_closed_accounts.py:322-345`）。它又没有进入 run_all 的 SUITE（`scripts/tests/run_all.py:10-79`），所以最终全绿看不见这个 P1。既然本轮目标是消化两份 BLOCK 报告，保留一个已复现的正式 P1 fail-open 就不能写“解除 BLOCK”。至少要同批改为显式 PASS/BLOCK/ERROR，并补 RPC 全失败、部分失败、checked=0、wall timeout 反例。 |
| R10：GPT-F-07 deploy sync 假绿 | **建议维持台账，但加验收旁证** | 技术问题属实：部署目录不存在打印 SKIP 却 return 0（`scripts/tests/test_commands_deploy_sync.py:35-38`）；两份命令 SHA 不同只要 staging 含 needles 就不记 failure（`scripts/tests/test_commands_deploy_sync.py:59-68`），最后仍打印 PASS（`scripts/tests/test_commands_deploy_sync.py:76-88`）。本轮计划不改 commands-staging，若最终验收在真实部署主机另存三对实际 SHA 全等证据，它不必阻断本批代码修复；但不能把该测试的 rc=0 当部署同步证据。若本轮任何文档改动触及命令契约，则此项立即升为阻断。 |
| R10：GPT-F-09 env_check 覆盖 | **建议维持台账，但不得拿现有 PASS 证明完整环境** | `pyproject.toml` 要求 Python >=3.14 并声明 21 个直接依赖（`pyproject.toml:13-47`），env gate 只手写检查 14 个包，且不查 Python 版本或 import（`scripts/tests/env_check.py:17-49`）。它已被 run_all 调用（`scripts/tests/run_all.py:37-38`），所以一行 PASS 只能证明这 14 个 metadata 版本，不能证明完整环境。此缺口不直接改变本轮八项业务修法；可留 R10，但最终工单必须另记解释器版本和全部直接依赖的 version/import 实测，或现在顺手把 env_check 机械生成化。 |

## ② 必须改计划的点

1. **重写 F-03 的闭合口径。** owner 快照包含 burn sentinel 时闭合到 total；net 只作分布百分比分母。补 dead-sink 20% 的正例。Solana 不能跳过等件绑定，改绑 observation bundle 的 `holder_outputs.owners`。
2. **把 F-04 从“外部文件一致”升级为“受控 producer 可重验”。** 必须规定 EVM pass2、EVM Duck、Solana replay_edges、Solana build_evolution 各自如何证明 producer、输入、算法和输出；若新增统一 receipt，就由共享 validator 消费。只给 `--series-source` 不算根修。
3. **先统一 burn schema 再做 100% 闭合。** 明确 `锁仓/销毁` 是堆叠桶还是非堆叠旁注，四个 producer 与 compiler 同一口径；禁止对现有 Solana `net 分母＋burn 叠加` 直接套 100% 闸。
4. **给“末点对 facts”补机器映射。** 新增并绑定 entity→camp 的单一映射，或从 camps spec 机械派生；不能靠 `entity_annotations.type/status` 猜，也不能用“实测不等就降级单向下界”代替来源闭合。
5. **补强两类裁决收据。** tolerance waiver 与 flip adjudication 都要有裁决主体/用户决定时间、目标与关键输入哈希、evidence ref 的 sha/size、过期条件；运行者自己写一份格式正确 JSON 不能解除硬闸。
6. **F-06 必须验证真实披露。** flip claim 结构化绑定三策略明细和 ledger fingerprint，A5 对当前 Markdown/结构化报告位置逐项核对；仅检查 claim ID 不够。
7. **F-07 要么真正事务化，要么承认风险接受。** 现稿的“部分写入＋重跑自愈”不能标 CLOSED，也不能让原反例转绿。
8. **把 `audit_closed_accounts.py` 纳入本轮。** 这是已复现 P1 fail-open，且 run_all 看不见；不修就不能宣称两份 BLOCK 报告已解除。
9. **修正逐批契约登记。** 每批新增契约时，同批更新 `contract_manifest.json`、`contract_ids_snapshot.json` 和权威文档；或统一留到 D。不能让 A/B/C 的 run_all 因 ID 快照必红。新 schema 还要在 `references/scan-schemas.md` 或明确的唯一权威页完整定义，不只是放一个 contract needle。
10. **重写最终验收矩阵。** F-01 改为双时点诚实绿例；F-07 只有真正全回滚才算绿；新增 F-04“同一伪文件双喂”反例、F-03 dead-sink 正例和 Solana 同值换仓负例。另建真正走完 state→A4→A5 seal→build_html 的 EVM/Solana 正例，现有 batch3 vertical slice 不能冒充这段覆盖。
11. **补 tolerance 同族。** `figures_from_facts.py check --tol-pp` 必须钳制、取消运行时覆盖，或进入 R10 明账并明确不作为正式发布闸。
12. **补齐调用面文档。** `state_from_facts.py` 新增必填 CLI 后，同批更新其模块用法和 `references/report-template.md` 的唯一生成命令；当前权威命令仍只有 facts/source/out（`scripts/report/state_from_facts.py:8-10,111-119`；`references/report-template.md:194-202`）。

## ③ 建议改的点

1. F-05 四入口调用一个共享 `validate_camp_spec()`；否则这轮虽修齐四份，下轮仍可能深度漂移。
2. 所有 raw 闭合用整数交叉乘法，例如 `abs(sum-total)*10000 <= total*tol_bps`；不要用 float 处理 18 位 decimals 的大整数。
3. F-02 的 waiver 只放大 supply truth 判断，不自动放大 distribution snapshot 完整性容差；两个阈值分开命名和登记。
4. F-08 文档明确写“upstream_receipts 是非穷尽记录，不构成执行证明；记录项在场即三验”。这样 scan 记录为空时 PASS 不会再产生“已绑定全部上游”的误解。
5. deploy sync 与 env check 可以暂留 R10，但最终验收报告要分别给真实部署 SHA 和完整解释器/直接依赖实测，不能引用两个弱 gate 的 PASS 文案代替。
6. 批 C 的日期测试至少含：相同瞬间不同 offset、闰日、重复时点、倒序、非法日期、naive/aware 混用；统一转 UTC 后再比较。

## ④ 无异议确认清单

- 同意继续以 `main@2ebd885`、v6.39.5 为冻结基线，按 A→B→C→D 管理施工；但须先按上节修订批内内容。
- 同意 F-01 只改 EVM tip 语义，不把同一字段要求套到 Solana。
- 同意 F-02 formal 默认 10 bps、exploration 分开，以及 shared validator 直接复用 `supply_truth_gate.decide()`，不手抄第二份公式。
- 同意 F-08 只三验 scan 实际记录的 upstream receipt，案目录后来多出的未记录 receipt 不反向污染旧 scan。
- 同意 addr2camp 活跃同族为四族；同意 camps 与 entities 的多归属边界分账，entities 不随 F-05 改成互斥。
- 同意批 C 内先 F-05 后 F-04；先消灭重复归属，后做序列闭合。
- 同意 CAMP_ORDER 拆现代/legacy 两段并保持合并顺序不变；新分析 compiler 只接受现代段，legacy 仅用于明确的旧报告非正式重绘。
- 同意 F-06 的 flip fingerprint、entity-file sha、handoff 重放同步和 freeze→ledger sha 绑定方向。
- 同意最终快照独立验收、每个新校验做破坏性注入、注入先证明到达目标分支、测试必须显式挂入 run_all。
- 同意 F-12 继续作为已接受边界保留，不把风险登记写成 CLOSED。

盲审完成
