# AI-3「采集通道与复核契约组」总完成报告（repair-20260815-g3）

- 日期：2026-08-15；基线 ddba187（v6.44.0）；分支 repair-20260815-g3
- 调度模式：Fable 调度与裁判验收 / codex 三工单纯施工（A 文档三件套→B 采集器主修→C 盲审消化）/ opus 4.8 独立盲审两轮（round1 BLOCK→消化→round2 PASS）
- 范围：v6.44.0 六视角 review 的 F-05 / F-06 / F-08 / F-13（三 AI 并行分工之第三组）

## 逐 finding 处置

| Finding | 处置 | 状态建议（r10 台账由融合方写） |
|---|---|---|
| F-08（P1）A0 命令断裂 | analyze-workflow A0 改 `--exploration`+探索文件名（`accounting_mode.exploration.json` 不占正式名，codex 复核采纳分文件设计）；A2 三步顺序 observe_supply→accounting `--bundle` formal 重跑→supply_truth，formal 为唯一 canonical；守卫测试整串断言+负向断言+顺序断言 | **FIXED_PENDING_REVIEW** |
| F-06（P1）备用采集器假完整 | SQD：解析纯函数（区间闭校验+number 类型收紧+log 逐字段 66 位 hex 校验+timestamp 安全化）、空响应/协议异常/前沿回退连续 5 次硬退、receipt 游标 provider 派生且 emitter 上下界恒等校验、`--receipt` 前置 lexists/realpath 双查、失败输出 `.partial` 隔离；Alchemy：正式资格除名（SUPPORTED/preflight/help/`--receipt` argparse 拒绝/FORMAL_CHANNEL_ELIGIBLE=False）+整页先验后写+逐字段 fullmatch 严校验（float 回退删除）。**用户拍板选型 B（除名）**；SQD 资格依三场景实测保留（哨兵=扫描前沿证据确凿，见 sqd_probe_notes.md） | **FIXED_PENDING_REVIEW** |
| F-05（P1）A4 N 路未机器化 | **用户裁决不加闸**；两文档补"机器化边界"段（六项已强制/四项未强制精确清单，盲审逐行对照 runner 代码全部属实）；runner 零改动 | **ACCEPTED_RISK（用户裁决豁免，保持现役，不得标 CLOSED）** |
| F-13（P3）runner 注入描述矛盾 | research-workflows 一句对齐现实（entrypoint 从环境变量读取逐字写入、runner 只校验不补入；盲审逐字对照吻合）；不选 runner 覆盖方向（会放宽检测面） | **FIXED_PENDING_REVIEW** |

## 验收与盲审证据链

- 先红后绿两轮：工单 B `evidence_B_red.txt`（基线上 6 红：`[COMPLETE] 0 rows` 假完成实锤）→ 8/8 绿；工单 C `evidence_C_red.txt`（消化前 R4/R5/R6 越界哨兵/混合/半残 log 全红）→ 13/13 绿
- 变异自证：M1-M4 四个文档变异 4/4 EXPECTED_RED（守卫强度实证）
- 盲审 round1（`blindreview_G3_round1.md`）：BLOCK，P0×1（SQD 完成证据缺上界）P1×1（log 级零校验）P2×2 P3×3——工单 C 消化六条（G3R1-04 边界外）
- 盲审 round2（`blindreview_G3_round2.md`）：**PASS**——round1 破防探针 7/7 重放失效、端到端断在第一环、13 条新攻击全拦、9 种合法形态零误杀
- 全量 SUITE：消化前后两次独立跑均 **101/101 全绿**（run_all @ 本机含 loopback 两项）
- 每工单 done 报告：workorder_A/B/C_done.md（改动清单+真实命令输出+边界自查）

## 交融合方清单（本组边界外/留账）

1. **G3R1-04（P2）**：SKILL.md:43 阶段路由表仍写 `accounting_mode.json`，与 A0 新产物名 `accounting_mode.exploration.json` 不一致——SKILL.md 属三方协调禁碰件，须融合方同步（建议改为"accounting_mode.exploration.json（A0 预检）/ accounting_mode.json（A2 formal）"）
2. **SUITE 注册**：两个新测试待融合方登记进 run_all.py——`scripts/tests/test_g3_docs_guards.py`、`scripts/tests/test_g3_alt_collectors.py`（各自独立可执行已验证）
3. **r10 台账登记**：上表四条状态建议（F-05 必须以非 CLOSED 载体计现役+正文注记用户裁决）
4. **G3R2-01（P3，设计取舍待裁决）**：SQD data 长度不设限（截断 data 静默改金额数量级）vs 钉死 64 位误伤非标 ERC20——二选一：收紧或 docstring 明写边界；顺带 header.hash 66 位断言+logIndex/timestamp 非负断言
5. **G3R2-02/03（P3）**：docs 守卫对"蓄意添加矛盾内容/诱饵段"形态的固有上限，改进方向在盲审报告
6. **G3R2-04（P3）**：data-pipeline-evm-channels.md"扫描前沿"措辞建议改口一句（本组域文档，下轮顺手）
7. **既有留账重申**：SQD receipt 无 chain 字段/dataset 任意名（错链空扫描面）；Alchemy 恢复正式资格候选=升分型收据

## 存量口径

- 改 fetcher 后脚本 sha 变化：旧 SQD native receipt 重验会因 collector 哈希不匹配被拒，须修复版重采重签；旧 Alchemy receipt 因除名一律被拒。备用通道按契约应零正式存量；未做任何旧 receipt 迁移或补签。
- 已交付案不重跑不受影响。

## 决策点存档

F-05 不加闸（用户 08-15）；F-06 选型 B 除名 Alchemy（用户 08-15，codex 复核给出两选型后拍板）；SQD 保留正式资格（三场景实测定案）；F-13 走文档方向；F-08 分文件两阶段（codex 复核设计）。
