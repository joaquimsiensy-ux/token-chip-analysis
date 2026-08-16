# g2 工程 done 报告（AI-2「对账与观测证据链组」）

- 工程：三 AI 并行修复 v6.44.0 六视角 review 14 findings 之 g2 组（F-04/F-07/F-09/F-10）
- 分支：`repair-20260815-g2`（worktree `~/.claude/tca-repair-g2`），基线 `ddba1871`（v6.44.0）
- 终态：**六 commit 全收口，本机全量 suite 105/105 全绿，独立盲审 209 向量 BREACH 0，总判定 CONDITIONAL——可交付融合**
- 调度模式：Fable 只调度/验收/代 commit；codex 纯施工（8 轮，含 3 次主动停工请示全部正确）；opus 子代理攻击型验收（两轮+复验）

## 一、commit 链（六刀）

| commit | 内容 | 关闭 |
|---|---|---|
| `4577106` | F-04 观测件拒空 runtime code＋66 字符 ABI word＋getCode 对齐 EIP-1898 同分叉（producer/transcript/validator 三层等深） | F-04 |
| `9d2f97c` | F-10 先钉正式消费面（四分支 mode+formal_ready 双断言）再放宽四 CLI（executable helper＋resolve_execution_mode 唯一策略＋--exploration） | F-10 |
| `4a43234` | F-07 schema 升 v3＋consumer 五路深重验（supply 实物重算/balance top-N 有序＋transcript 逐笔/time plan multiset/anchor output 逐行/gmgn Decimal） | F-07 主体 |
| `daaed16` | F-09 黄灯制（PASS+warnings）＋gmgn-divergence-note/v1（三 cause 无 self_error）＋双写验证器＋互锁（用户裁决语义） | F-09 |
| `861a234` | 末刀中心登记（run_all 挂 4 测试→SUITE 105＋契约 CT-RECON-01/02/03） | 中心件 |
| `55f2c44` | 消化轮 1：盲审 time 查 7 BREACH 全关（plan 权威链 12 项绑定消费侧独立实现＋H 向量固化回归负测）＋盲审报告入库 | 盲审 BREACH |

每刀先红后绿证据：`f04|f10|f07|f09|digest1_red|green.log`（消化轮日志带 SHA256）。

## 二、独立盲审终态（`blindreview_g2_round1.md`，opus 红队）

- 累计 **209 向量**：F-04 28＋F-10 18＋F-07 43＋F-09 45＋time 攻击轮 50＋round2 复验 25。
- **BREACH 终态 0**：time 轮抓出的 7 条（plan 权威链消费侧缺失）经消化轮修复后逐条重放关闭，边界外 17 个新向量也全拦。
- 盲审两条方法论教训已在报告边界节：①"读代码判断同构同严"被夹具推翻（time 面）；②中间口头汇报不可信，只认落盘报告＋可复现探针（F-10 首轮口头报数未实测事件）。
- **PARTIAL 留档（不阻断融合）**：
  1. **抽查覆盖面无下限（P2，唯一建议排期）**——`requested_top_n` 可合法缩到 1、time plan 点位规模无外部事实约束；round2 前瞻：将来加下限必须**去重计数**（防重复点填充）。
  2. 说明件语义充数（P3）——explanation 30 实义字符防呆不防伪，R10-17 已知边界同族。
  3. 双写分叉两处（P3）——绝对路径 evidence_ref、截止块 `or` vs `is None`。
  4. R2A：`repo_ref_ok` 验 producer 声明非签名，"全套离线自造签发链"仍可行——整个 receipt 体系无收据签名的全局已知边界（R10-8/9/14 外锚族），本工程已把门槛从"拿任一真实签发件混搭"提到"伪造整条链"。

## 三、留融合方事项

1. **不 push 不 merge**：等三组融合，融合顺序建议 g1→g2→g3；本分支六 commit 线性无冲突。
2. **跨组文件交叠**：①`references/analyze-workflow.md` 一行 time-spotcheck v3 串级联（AI-3 的 F-08 改 A0 段，不同章节，预期自动合并）；②`test_a4_gate.py` 本地夹具 helper 两轮适配（AI-3 若改其 A4 断言区属不同函数）；③AI-1 披露曾为 Solana 小写化 bug 破例动 shared 一处——与本组 shared 对账区改动需对一次冲突面。
3. **末刀（`861a234`）与消化轮的中心件**：run_all 追加块/契约 CT-RECON 条目/invariant 登记（consumers 85→86、floor 52→54）按 union 合并，CT-RECON 前缀不撞号。
4. **R10 台账建议**（台账在本组禁碰清单，由融合方落笔）：review F-04/F-07/F-09/F-10 四条转 CLOSED（本工程关闭定性以各工单 done 报告"如实定性"节为准——F-07 关至 transcript/实物绑定深度，远端真执行证明仍属 R10-9/14）；PARTIAL-1（覆盖面下限＋去重计数要点）建议新挂 R11 候选。
5. **存量案影响**：EVM 案重发布须以 verify_recon v3/time_spotcheck v3 重跑对账（v2 收据消费面拒收，迁移文案已内置）；已交付案不重跑不受影响。

## 四、工艺沉淀（供维护方法论参考）

- codex"宁停不越界"三次全正确：存量夹具产旧协议、名单外 batch_a 红、工单白名单自相矛盾（调度方失误，codex 拒绝执行矛盾指令并给出两个可选修法）。
- 盲审"自报缺口必须补轮"实证：round1 CONDITIONAL 自报 time 未实测→补轮抓出 7 BREACH→若当时收官即带洞交付。**子代理的覆盖自报与判定结论要分开审**。
- 三 AI 并行的 worktree 勿放 `~/.claude/skills/` 下（会被扫成 skill 干扰路由）。
