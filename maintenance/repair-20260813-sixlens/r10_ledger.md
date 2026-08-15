# R10 台账（六视角修复工程 2026-08-13 建档；6.42.0 批 2 状态同步）

> 来源：plan.md 定案范围之外的存量/加深/评估项。下一轮修复工程（R10）开工时以本文件为完整候选清单。
> 引用纪律：每条的原始证据与最强反例在 `input_codex_review.md` / `input_gpt56_review.md` / 各批工单，动工前必读原文。

## 一、存量六条（plan 既定，用户 08-13 拍板留台账）

| # | 条目 | 一句话 | 修法线索 |
|---|---|---|---|
| R10-1 | F-09（=GPT-F-03）图 1 对未知阵营静默漏画 | figures wrapper 接受任意阵营，绘图层只取 CAMP_ORDER 交集，未知阵营无警告无非零退出 | 批 C 已在 compile_state 路径装白名单硬拒；**旧 state 直喂 fig1 的重绘路径不经 compile_state**，该路径仍开着——按 GPT-F-03 修法连 A5 图例集合绑定（R10-7）一起做 |
| R10-2 | F-10 对抗复核可空壳【CLOSED 6.42.0】 | adversarial_review 的 reviews 只验角色名与 exit_code，内容可为空洞文本 | 批 2 工单 B 已落结构化 v3、受控 runner/finalize 与双消费重验；见 `maintenance/repair-20260814-batch2/workorder_B_done.md` 及三轮盲审 |
| R10-3 | F-11 replay gate fail-open 残留 | 历史漏检家族（同族采集器已修，个别入口未等深） | 按 GPT-F-05 证据点逐入口收口 |
| R10-4 | F-13 v2 采集器保留可选位置 api_token 且优先于环境变量/文件 | 令牌可进 ps；F-07 回归只列三支 v1 脚本 | 移除位置参数或降级其优先序，回归补 v2 |
| R10-5 | GPT-F-07 deploy-sync 两条假绿（弱闸） | 部署目录缺失打 SKIP 但 return 0；MIGRATION_CHANGED 豁免无期限 | 豁免加期限＋缺目录 fail；**本轮旁证**：批 D 工单附三命令 staging/部署 SHA 实测全等记录（不引用该弱闸 rc=0 作证据） |
| R10-6 | GPT-F-09 env_check 覆盖不足 | 不查 Python 版本（pyproject 要求 >=3.14）、KEY_PKGS 手写 14 个漏 7 个直接依赖 | KEY_PKGS 从 pyproject 机械生成＋requires-python 检查；**本轮旁证**：批 D 工单附解释器版本与全部直接依赖 version/import 实测记录 |

## 二、GPT 交叉对账加深两条

| # | 条目 | 一句话 |
|---|---|---|
| R10-7 | A5 seal 增图例集合绑定（GPT-F-03 修法后半） | A5 只绑最终 PNG 哈希，不重验图例集合——与 R10-1 同一威胁面，修图 1 白名单时同批把"图例集合"纳入 A5 绑定 |
| R10-8 | F-12 改名降权（GPT-F-10 修法） | `formal_ready` 静态声明可伪造属已接受边界；建议把字段名改为不承载"已验证"语义的中性名并在文档降权，消除"名字看起来像证明"的误导面 |

## 三、批 C 终验沉淀三条（batchD_ledger 二c 节转入）

| # | 条目 | 一句话 |
|---|---|---|
| R10-9（C-R1） | `target.as_of_block` 无真实对锚【MITIGATED 6.43.0，案内观测缓解，外部真实性锚仍 OPEN】 | EVM bundle 已把锚块、调用 transcript 与双收据内容绑定；但案内件仍可同步伪造，独立 RPC 复验/案外签署/git 上位登记未落。见 `maintenance/repair-20260814-evmobs/workorder_D_done.md`。 |
| R10-10（C-R2） | sol 侧 `solana-reconcile/v2` 收据 schema 无身份键【CLOSED 6.42.0】 | 已升 `solana-reconcile/v3`，绑定 chain/mint/window/producer/三输入；见 `maintenance/repair-20260814-batch2/workorder_C_f09.md` 与 `workorder_C_done.md` |
| R10-11（C-R3） | sol 分支发布期复算路径未经真实案端到端验证【CLOSED 6.42.0】 | 已完成同案夹具链与 PYTHIA 真实案纵向复验；见 `maintenance/repair-20260814-batch2/workorder_C_done.md`、`blindreview_C_round3.md` |

## 四、批 D 评估留档两条（D-iv 评估产出，回传已报明）

| # | 条目 | 评估结论 |
|---|---|---|
| R10-12（A-2） | `approved_tolerance_bps` 硬顶＋`observed_diff_bps` 预先虚报【CLOSED 6.42.0】 | 用户已定三段政策；四值取最大值定区，>100bps 强制独立 `over-cap-approval/v1`，生产/消费双重验。见 `maintenance/repair-20260814-batch2/workorder_A_f10.md` 与 `workorder_A_fixround2_done.md`。 |
| R10-13（A-4） | EVM `onchain_total_supply` 链上观测件锚定【CLOSED 6.43.0】 | `evm-observation-bundle/v1` 已由正式 producer 落块头、EIP-1898 三笔供给调用与 transcript，并由 accounting v2/supply_truth v4/shared/handoff 双路线 N-2 重验；见 `maintenance/repair-20260814-evmobs/workorder_D_done.md`。CLOSED 仅指案内锚定建设完成，外部真实性锚见 R10-9（MITIGATED）。 |

## 四b、批 D 消化轮 1 追加

| # | 条目 | 一句话 |
|---|---|---|
| R10-14（F-D8 余项） | `entity_freeze.json` 自身完整性锚 | 单边改动已封（A5 ledger-sha 绑定＋发布闸 A5 重验的 final scan 绑定链）；"连 freeze 一起改写"在无分布链案上仍属自洽小件族。设计方向：freeze 落盘时向案外/上位（如 handoff manifest revision 或 git 对象）登记 sha——与 C-R1（as_of_block 对锚）同族，锚到案内件只是多一个可伪造件，需真实外锚设计 |
| R10-15（F-D7 余项） | `check_bound_file` 绝对路径绑定无案根强制 | trace 侧已限案根（新产 ledger 无此形态）；存量绝对路径 ledger 兼容面的收紧（freeze/check-unseal 消费点统一案根语义）留此 |

## 五、批 2 三线盲审新增登记（6.42.0）

| # | 条目 | 状态与出处 |
|---|---|---|
| R10-16 | B-09 blocker 存在性仍由输入自报、未与 artifact 语义联动 | 待用户裁；来源：`workorder_B_fixround1_done.md` §七、`blindreview_B.md` B-09 |
| R10-17 | any 语义“证据够不够”阈值 | 待策略定案；来源：`blindreview_B_round2.md` 残留观察、`workorder_B_fixround2_done.md` §发现未修 |
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
