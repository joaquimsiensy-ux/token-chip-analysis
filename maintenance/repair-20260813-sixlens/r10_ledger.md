# R10 台账（六视角修复工程 2026-08-13 建档；6.43.0 批 3 收官同步）

> 来源：plan.md 定案范围之外的存量/加深/评估项。下一轮修复工程（R10）开工时以本文件为完整候选清单。
> 引用纪律：每条的原始证据与最强反例在 `input_codex_review.md` / `input_gpt56_review.md` / 各批工单，动工前必读原文。

## 一、存量六条（plan 既定，用户 08-13 拍板留台账）

| # | 条目 | 一句话 | 修法线索 |
|---|---|---|---|
| R10-1 | F-09（=GPT-F-03）图 1 对未知阵营静默漏画【CLOSED 6.41.0】 | figures wrapper 接受任意阵营，绘图层只取 CAMP_ORDER 交集，未知阵营无警告无非零退出 | 已闭合——standard_charts.select_fig1_series 白名单外键 raise ValueError（commit c5f3458）；A5 图例绑定并入 R10-7 同批闭合。 |
| R10-2 | F-10 对抗复核可空壳【CLOSED 6.42.0】 | adversarial_review 的 reviews 只验角色名与 exit_code，内容可为空洞文本 | 批 2 工单 B 已落结构化 v3、受控 runner/finalize 与双消费重验；见 `maintenance/repair-20260814-batch2/workorder_B_done.md` 及三轮盲审 |
| R10-3 | F-11 replay gate fail-open 残留【CLOSED 6.41.0】 | 历史漏检家族（同族采集器已修，个别入口未等深） | 已闭合——replay_pass1/stream/duck gate false 全 exit 4、pass2 消费 gate_pass fail-closed（commit d78e210）。 |
| R10-4 | F-13 v2 采集器保留可选位置 api_token 且优先于环境变量/文件【CLOSED 6.41.0】 | 令牌可进 ps；F-07 回归只列三支 v1 脚本 | 已闭合——fetch_hypersync_v2 移除位置 api_token，唯一位置参数 from_block，token 走 --token-file/HYPERSYNC_TOKEN/默认文件（commit 253ac79）。 |
| R10-5 | GPT-F-07 deploy-sync 两条假绿（弱闸）【CLOSED 6.43.0】 | 部署目录缺失打 SKIP 但 return 0；MIGRATION_CHANGED 豁免无期限 | 已闭合——无界豁免删除+canonical fail-closed（消化轮 1 再收 HOME 环境缝隙改 getpwuid），三轮盲审+addendum PASS；见 `maintenance/repair-20260814-batch3/workorder_F04_done.md` 与 `blindreview_round3_addendum.md`。 |
| R10-6 | GPT-F-09 env_check 覆盖不足【CLOSED 6.43.0】 | 不查 Python 版本（pyproject 要求 >=3.14）、KEY_PKGS 手写 14 个漏 7 个直接依赖 | 已闭合——pyproject 机械派生三层闭合+requires-python，pre-commit 联动实证，三轮盲审+addendum PASS；见 `maintenance/repair-20260814-batch3/workorder_F05_done.md`。已知边界：平面 lock 判不了已删直接依赖残留。 |

## 二、GPT 交叉对账加深两条

| # | 条目 | 一句话 |
|---|---|---|
| R10-7 | A5 seal 增图例集合绑定（GPT-F-03 修法后半）【CLOSED 6.41.0】 | 已闭合——a5_report_seal 生成并重验 fig1_legend_receipt（commit e5c8043）。 |
| R10-8 | F-12 改名降权（GPT-F-10 修法） | `formal_ready` 静态声明可伪造属已接受边界；建议把字段名改为不承载"已验证"语义的中性名并在文档降权，消除"名字看起来像证明"的误导面 |

## 三、批 C 终验沉淀三条（batchD_ledger 二c 节转入）

| # | 条目 | 一句话 |
|---|---|---|
| R10-9（C-R1） | `target.as_of_block` 无真实对锚 | 6.44.0 案内观测缓解（MITIGATED，仍 OPEN 计现役）：EVM bundle 已把锚块、调用 transcript 与双收据内容绑定；但案内件仍可同步伪造，独立 RPC 复验/案外签署/git 上位登记未落。见 `maintenance/repair-20260814-evmobs/workorder_D_done.md`。 |
| R10-10（C-R2） | sol 侧 `solana-reconcile/v2` 收据 schema 无身份键【CLOSED 6.42.0】 | 已升 `solana-reconcile/v3`，绑定 chain/mint/window/producer/三输入；见 `maintenance/repair-20260814-batch2/workorder_C_f09.md` 与 `workorder_C_done.md` |
| R10-11（C-R3） | sol 分支发布期复算路径未经真实案端到端验证【CLOSED 6.42.0】 | 已完成同案夹具链与 PYTHIA 真实案纵向复验；见 `maintenance/repair-20260814-batch2/workorder_C_done.md`、`blindreview_C_round3.md` |

## 四、批 D 评估留档两条（D-iv 评估产出，回传已报明）

| # | 条目 | 评估结论 |
|---|---|---|
| R10-12（A-2） | `approved_tolerance_bps` 硬顶＋`observed_diff_bps` 预先虚报【CLOSED 6.42.0】 | 用户已定三段政策；四值取最大值定区，>100bps 强制独立 `over-cap-approval/v1`，生产/消费双重验。见 `maintenance/repair-20260814-batch2/workorder_A_f10.md` 与 `workorder_A_fixround2_done.md`。 |
| R10-13（A-4） | EVM `onchain_total_supply` 链上观测件锚定【CLOSED 6.44.0】 | `evm-observation-bundle/v1` 已由正式 producer 落块头、EIP-1898 三笔供给调用与 transcript，并由 accounting v2/supply_truth v4/shared/handoff 双路线 N-2 重验；见 `maintenance/repair-20260814-evmobs/workorder_D_done.md`。CLOSED 仅指案内锚定建设完成，外部真实性锚见 R10-9（MITIGATED 仍计现役）。 |

## 四b、批 D 消化轮 1 追加

| # | 条目 | 一句话 |
|---|---|---|
| R10-14（F-D8 余项） | `entity_freeze.json` 自身完整性锚 | 单边改动已封（A5 ledger-sha 绑定＋发布闸 A5 重验的 final scan 绑定链）；"连 freeze 一起改写"在无分布链案上仍属自洽小件族。设计方向：freeze 落盘时向案外/上位（如 handoff manifest revision 或 git 对象）登记 sha——与 C-R1（as_of_block 对锚）同族，锚到案内件只是多一个可伪造件，需真实外锚设计 |
| R10-15（F-D7 余项） | `check_bound_file` 绝对路径绑定无案根强制【CLOSED 6.45.0】 | 已闭合——g1 组 F-01 工单：新建 `scripts/lib/case_paths.py::safe_case_file`（拒空段/`.`/`..`/abs＋逐段 symlink＋realpath containment），handoff generate/verify/data_map/`--include`/freeze 与 `resolve_bound_path` 全入口接入，adjudication_validator 同族收口（消化轮 D3）；含 abs/`../` 的旧案 check-unseal fail-closed 属期望行为。见 `maintenance/repair-20260815-g1/done_report.md` |

## 五、批 2 三线盲审新增登记（6.42.0）

| # | 条目 | 状态与出处 |
|---|---|---|
| R10-16 | B-09 blocker 存在性仍由输入自报、未与 artifact 语义联动 | 【CLOSED 6.43.0】用户 08-14 裁决方案 B（findings/non_covered/REFUTED 机械转 blocker 逐条处置），工单 F01 落地；盲审 R1 抓"省略整份 receipt"上层绕口，消化轮 1 补 execution ledger 哈希链+消化轮 2 补实物身份/基数闸，addendum PASS；见 `workorder_F01_done.md`、`workorder_digest_round1_done.md`。防伪边界：防事后省略，不防整册重造（无外锚定性同 R10-8）。 |
| R10-17 | any 语义“证据够不够”阈值 | 【CLOSED 6.43.0】用户裁决装 10 实义字符门槛，工单 F01 落地，addendum PASS。本批只关“空壳/极短 evidence”形式面（防呆不防伪）；“结构化 evidence（证据类型/引用对象/复算产物绑定）”不在本批，残余保留在案。 |
| R10-18 | `risk_flags.py::_strip_invisible_space` 黑名单版存量 | 【CLOSED 6.45.0】g1 组 F-12 工单已闭合：裁剪后 `fullmatch [a-z0-9-]+` 正向白名单否则 raise（内部不可见字符一并拒绝），resolver 四装载口 eager parse，label_lookup 及三写入侧稳定 `BLOCK: risk_flags 脏数据` 非零退出。见 `maintenance/repair-20260815-g1/done_report.md` |
| R10-19 | BC-O2 migration collector 身份无消费者 | 2026-08-16 用户裁决维持现状（consumer 不感知迁移身份）：实际工作流=老案一律重采重析、迁移路径几乎不走，且可迁数据已过同强度机械校验；转接受在案。来源：`workorder_C_fixround1_done.md` §七 BC-O2 |
| R10-20 | BC-O3 series binding 仅 new-analysis profile | 2026-08-16 用户裁决**批准立项 R11**（装上但不急）：`check_series_binding` 扩到 independent-audit profile，实现要点=缺新式绑定件的存量老案给明确迁移指引报错、不裸拒。来源：`workorder_C_fixround1_done.md` §七 BC-O3 |
| R10-21 | BC-O4 sidecar producer 字段无身份锚 | 接受“公开哈希不是签名”边界；来源：`workorder_C_fixround1_done.md` §七 BC-O4 |
| R10-22 | BC-O7 hard-link 替身 consumer 不可辨 | 接受在案，系 importer 允许 hard link 的设计依赖；来源：`workorder_C_fixround1_done.md` §七 BC-O7 |
| R10-23 | B 三轮 R-1：Mn/Me 全类移除会碰撞依赖组合符承载语义的文字 | 文档边界已补，技术窄口留账；来源：`blindreview_B_round3.md` R-1 |
| R10-24 | C 三轮 O-1：目录级 symlink 的全库逐段 realpath 口径 | 跨工单统一面；来源：`blindreview_C_round3.md` O-1 |
| R10-25 | C 三轮 O-3：symlink 拒绝退出码存在 CLI rc=1/直调 rc=2 两路 | 待统一；来源：`blindreview_C_round3.md` O-3 |
| R10-26 | C 三轮 O-4：a4_gate/a5_report_seal 裸 `json.loads` 同族面 | 待等深；来源：`blindreview_C_round3.md` O-4 |
| R10-27 | emoji 实义白名单扩容候选 | 候选、非当前承诺；来源：A 线第三轮 CLOSED 消息的误伤评估，由 `workorder_final_closure.md` §1 入档（无独立报告文件） |

## 六、状态

- 建档：2026-08-13（批 D 收口时）。6.42.0 清账 R10-2/R10-10/R10-11/R10-12；原 15 条余 11 条，新增 12 条，现役保留/接受项合计 23 条。
- 弱闸旁证（R10-5/6 相关）：见 `batchD_workorder.md` §旁证——三命令 staging/部署 SHA 实测全等记录＋解释器与直接依赖 version/import 实测记录，均为实测输出，不引用弱闸 rc=0。
- 2026-08-14 批 3 收官：批 1 补账 CLOSED 4 条（R10-1/3/4/7，v6.41.0 已修当时未记，F-07 集成漂移修正）；批 3 修复 4 条（R10-5/6/16/17）经三轮盲审（R1 BLOCK 1P1+3P2 → R2 CONDITIONAL 2P2 → R3 CONDITIONAL 1P2）+三轮消化+addendum PASS 转 CLOSED；批 3 收官时现役 15。盲审全程证据见 `maintenance/repair-20260814-batch3/blindreview_round{1,2,3}.md` 与 `blindreview_round3_addendum.md`。
- 2026-08-15 EVM 观测锚工程（6.44.0）收官：R10-13 转 CLOSED、R10-9 案内观测 MITIGATED 仍计现役；收官时现役计 14。独立盲审（opus 线程）31 伪造向量全拒 PASS，证据见 `maintenance/repair-20260814-evmobs/blindreview_OBS_round1.md`。
- 2026-08-15 三 AI 并行修复工程（6.45.0，v6.44.0 review 14 findings 全处置）收官：g1 清账 R10-15/R10-18；当前现役 = 27 − 15 = **12**。14 findings 逐条处置与状态见三组 done 报告（`maintenance/repair-20260815-g{1,2,3}/`）；其中 review F-05 经用户 08-15 裁决不加闸（ACCEPTED_RISK，机器化边界如实写入 analyze/research 两分册，本台账 R10-17 残余定性不变仍在案）；review F-07 关至 transcript/实物绑定深度，远端真执行证明仍属 R10-9/14 外锚族；g2 盲审 PARTIAL-1（抽查覆盖面无下限＋去重计数要点）与 g3 的 SQD data 长度取舍（G3R2-01）列 R11 候选。
- 2026-08-16 用户四项裁决落账（现役计数不变）：① F-01 hard link 盲区**不加检测**——合法硬链接误伤面真实（PYTHIA 案 nlink=3 正常件先例），威胁模型下攻击者另有更短路径，与 R10-22 同族定性，接受为已记录边界；② `a5_report_seal.safe_file` 允许绝对路径**正式豁免**——build_html resolve 后传入的合法调用形态，案根围栏由 relative_to 强制，现场注释已标（`scripts/report/a5_report_seal.py:32`）；③ g2 PARTIAL-1 抽查覆盖面下限**批准立项 R11**（修但不急；实现要点=去重计数＋小盘币取 min(下限, 实际总数)）；④ G3R2-01 SQD data 长度**裁决不设限**——兼容非标 ERC20 优先，截断风险边界已注释入采集器现场（`scripts/evm/fetch_sqd_evm.py`），撤出 R11 候选；捆绑小收紧（header.hash 66 位/logIndex·timestamp 非负）随 R11 顺手；⑤ 同日追加 R10-19 **裁决维持现状**、R10-20 **批准立项 R11**（均详见第五节条目行）。R11 实改项就此定局两件：抽查覆盖面下限（③）＋series binding 扩复核档（R10-20），捆绑 SQD 小收紧与小卫生活顺手。
