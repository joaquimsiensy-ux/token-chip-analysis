# R10 台账（六视角修复工程 2026-08-13 建档；6.43.0 批 3 施工状态同步）

> 来源：plan.md 定案范围之外的存量/加深/评估项。下一轮修复工程（R10）开工时以本文件为完整候选清单。
> 引用纪律：每条的原始证据与最强反例在 `input_codex_review.md` / `input_gpt56_review.md` / 各批工单，动工前必读原文。

## 一、存量六条（plan 既定，用户 08-13 拍板留台账）

| # | 条目 | 一句话 | 修法线索 |
|---|---|---|---|
| R10-1 | F-09（=GPT-F-03）图 1 对未知阵营静默漏画【CLOSED 6.41.0】 | figures wrapper 接受任意阵营，绘图层只取 CAMP_ORDER 交集，未知阵营无警告无非零退出 | 已闭合——standard_charts.select_fig1_series 白名单外键 raise ValueError（commit c5f3458）；A5 图例绑定并入 R10-7 同批闭合。 |
| R10-2 | F-10 对抗复核可空壳【CLOSED 6.42.0】 | adversarial_review 的 reviews 只验角色名与 exit_code，内容可为空洞文本 | 批 2 工单 B 已落结构化 v3、受控 runner/finalize 与双消费重验；见 `maintenance/repair-20260814-batch2/workorder_B_done.md` 及三轮盲审 |
| R10-3 | F-11 replay gate fail-open 残留【CLOSED 6.41.0】 | 历史漏检家族（同族采集器已修，个别入口未等深） | 已闭合——replay_pass1/stream/duck gate false 全 exit 4、pass2 消费 gate_pass fail-closed（commit d78e210）。 |
| R10-4 | F-13 v2 采集器保留可选位置 api_token 且优先于环境变量/文件【CLOSED 6.41.0】 | 令牌可进 ps；F-07 回归只列三支 v1 脚本 | 已闭合——fetch_hypersync_v2 移除位置 api_token，唯一位置参数 from_block，token 走 --token-file/HYPERSYNC_TOKEN/默认文件（commit 253ac79）。 |
| R10-5 | GPT-F-07 deploy-sync 两条假绿（弱闸）【FIXED_PENDING_REVIEW 6.43.0 批3】 | 部署目录缺失打 SKIP 但 return 0；MIGRATION_CHANGED 豁免无期限 | 工单 F04 已落地（无界豁免删除+canonical fail-closed），待批 3 盲审转 CLOSED；见 `maintenance/repair-20260814-batch3/workorder_F04_done.md`。 |
| R10-6 | GPT-F-09 env_check 覆盖不足【FIXED_PENDING_REVIEW 6.43.0 批3】 | 不查 Python 版本（pyproject 要求 >=3.14）、KEY_PKGS 手写 14 个漏 7 个直接依赖 | 工单 F05 已落地（pyproject 机械派生三层闭合+requires-python），待盲审转 CLOSED；见 `maintenance/repair-20260814-batch3/workorder_F05_done.md`。 |

## 二、GPT 交叉对账加深两条

| # | 条目 | 一句话 |
|---|---|---|
| R10-7 | A5 seal 增图例集合绑定（GPT-F-03 修法后半）【CLOSED 6.41.0】 | 已闭合——a5_report_seal 生成并重验 fig1_legend_receipt（commit e5c8043）。 |
| R10-8 | F-12 改名降权（GPT-F-10 修法） | `formal_ready` 静态声明可伪造属已接受边界；建议把字段名改为不承载"已验证"语义的中性名并在文档降权，消除"名字看起来像证明"的误导面 |

## 三、批 C 终验沉淀三条（batchD_ledger 二c 节转入）

| # | 条目 | 一句话 |
|---|---|---|
| R10-9（C-R1） | `target.as_of_block` 无真实对锚 | 改成任意正整数照过全部一致性校验；锚到案外链上证据属 F-12 地盘，锚到案内件只是多一个可伪造件——修法待设计 |
| R10-10（C-R2） | sol 侧 `solana-reconcile/v2` 收据 schema 无身份键【CLOSED 6.42.0】 | 已升 `solana-reconcile/v3`，绑定 chain/mint/window/producer/三输入；见 `maintenance/repair-20260814-batch2/workorder_C_f09.md` 与 `workorder_C_done.md` |
| R10-11（C-R3） | sol 分支发布期复算路径未经真实案端到端验证【CLOSED 6.42.0】 | 已完成同案夹具链与 PYTHIA 真实案纵向复验；见 `maintenance/repair-20260814-batch2/workorder_C_done.md`、`blindreview_C_round3.md` |

## 四、批 D 评估留档两条（D-iv 评估产出，回传已报明）

| # | 条目 | 评估结论 |
|---|---|---|
| R10-12（A-2） | `approved_tolerance_bps` 硬顶＋`observed_diff_bps` 预先虚报【CLOSED 6.42.0】 | 用户已定三段政策；四值取最大值定区，>100bps 强制独立 `over-cap-approval/v1`，生产/消费双重验。见 `maintenance/repair-20260814-batch2/workorder_A_f10.md` 与 `workorder_A_fixround2_done.md`。 |
| R10-13（A-4） | EVM `onchain_total_supply` 链上观测件锚定 | **属新功能面设计活，与 A-3（路径语义改造）不顺手，本轮不做**；批 A 已有"明示局限"写入 `independent-audit-protocol.md` 兜底。设计要点留档：①对标 Solana observation bundle，造 EVM 链上观测收据 producer（attested eth_call totalSupply@as_of_block，经 net.attested_rpc_pool 出 attestation）；②supply_truth 额外落该观测件并入 inputs 绑定；③消费侧（shared_release_receipt supply_truth 分支）比对收据自报 onchain 与观测件数值——对齐 Solana 侧 N-2 修复的强度；④观测件须绑定端点指纹与 genesis/chainId 证明，防"观测件也自报"。 |

## 四b、批 D 消化轮 1 追加

| # | 条目 | 一句话 |
|---|---|---|
| R10-14（F-D8 余项） | `entity_freeze.json` 自身完整性锚 | 单边改动已封（A5 ledger-sha 绑定＋发布闸 A5 重验的 final scan 绑定链）；"连 freeze 一起改写"在无分布链案上仍属自洽小件族。设计方向：freeze 落盘时向案外/上位（如 handoff manifest revision 或 git 对象）登记 sha——与 C-R1（as_of_block 对锚）同族，锚到案内件只是多一个可伪造件，需真实外锚设计 |
| R10-15（F-D7 余项） | `check_bound_file` 绝对路径绑定无案根强制 | trace 侧已限案根（新产 ledger 无此形态）；存量绝对路径 ledger 兼容面的收紧（freeze/check-unseal 消费点统一案根语义）留此 |

## 五、批 2 三线盲审新增登记（6.42.0）

| # | 条目 | 状态与出处 |
|---|---|---|
| R10-16 | B-09 blocker 存在性仍由输入自报、未与 artifact 语义联动 | 【FIXED_PENDING_REVIEW 6.43.0 批3】用户 08-14 裁决方案 B（findings/non_covered/REFUTED 机械转 blocker 逐条处置），工单 F01 已落地；见 `maintenance/repair-20260814-batch3/workorder_F01_done.md`。 |
| R10-17 | any 语义“证据够不够”阈值 | 【FIXED_PENDING_REVIEW 6.43.0 批3】用户裁决装 10 实义字符门槛，工单 F01 已落地。本批只关“空壳/极短 evidence”形式面（防呆不防伪）；“结构化 evidence（证据类型/引用对象/复算产物绑定）”不在本批，残余保留在案。 |
| R10-18 | `risk_flags.py::_strip_invisible_space` 黑名单版存量 | 留批 4 守卫收尾轮；来源：`workorder_B_fixround1.md` §10、`workorder_B_fixround1_done.md` §七 |
| R10-19 | BC-O2 migration collector 身份无消费者 | 待产品语义裁决；来源：`workorder_C_fixround1_done.md` §七 BC-O2 |
| R10-20 | BC-O3 series binding 仅 new-analysis profile | 待存量复核影响裁决；来源：`workorder_C_fixround1_done.md` §七 BC-O3 |
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
- 2026-08-14 批 3 状态：批 1 补账 CLOSED 4 条（R10-1/3/4/7，v6.41.0 已修当时未记，F-07 集成漂移修正）；批 3 施工 FIXED_PENDING_REVIEW 4 条（R10-5/6/16/17）；当前现役 = 23 − 4 = **19**（其中 4 条待盲审转 CLOSED 后 → 15）。
