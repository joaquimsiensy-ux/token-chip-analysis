# R9 最终验收台账

候选分支 `fix/r9-closure-20260807`,基线 main@`63cf715`。验收要素五项:全量 suite/静态守卫/49-49 SHA 回放/两轮 codex 全库盲审/版本收口。本文件由 Fable 逐项登记,完成一项记一项。

## 1. 全量 suite(PASS,2026-08-09)

- 命令:`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py`
- 结果:89 项全部通过(Fable 环境,含 codex/opus 沙箱跑不了的两项 loopback 纵切片)。
- 执行位置:批四降级收口 commit `b7a8537` 后复跑。

## 2. 静态守卫(PASS,2026-08-09)

- `invariant_scan.py`:PASS(receipt_producers=52, receipt_consumers=55, transport_calls=62, atomic_writes=42, formal_entrypoints=58, exceptions=0)。
- `test_sixlens_docs.py`:PASS(主表 49 行/详情零空栏/18 baseline-fixed/8 supplementary 复核门禁)。
- `docs_lint.py --all`:PASS(58 文档无断链)。
- `env_check.py`:PASS(pre-commit 三检within b7a8537)。
- 边界声明:批四 G2 formal E2E provenance 守卫按用户 2026-08-09 裁决降级接受——静态挡低级伪造,模块层/外层作用域重绑定伪造已知未闭合(rereview2.md N1~N20),无独立运行时兜底;详见 b4_progress.md 用户裁决节与 invariant_scan docstring。

## 3. 49/49 SHA 回放(PASS;2026-08-09 首跑于 b7a8537,Round B 指出登记缺口后修订)

- 工具:`maintenance/repair-20260806/sha_replay.py`(已入库,可复跑——Round B 盲审指出原登记只写 scratchpad 路径无法复现,本次整改)。
- **口径声明**(Round B 以宽口径实算 67 行/71 提及/41 unique 与原登记 62/37 不符——属口径差非数据错):本工具 A 检查只数「SHA 回填表」两列行(`| 组 | sha |`),不含主表 SHA 列与叙事段落里的裁决/基线 SHA;Round B 宽口径把后者也计入。**两口径下结论一致:missing=0、non-ancestor=0,全部 SHA 在 HEAD 祖先链上。**
- **时点声明**:首跑执行于批四降级收口 commit `b7a8537` 状态(当时 62 行/37 unique/82 改动文件);`45bf8f3` 提交本台账后文件数+1 属自指,Round B 实算 83 与此吻合。盲审消化 commit 后以入库工具在最终 tip 复跑为准(结果见第 4 节)。
- A. SHA 回填表全部 SHA 存在于仓库且为 HEAD 祖先;无空 SHA 行。
- B. ledger 主表恰 49 行、零空栏。
- C. 49 个详情节均含「最终结果」与「两轮盲审与 Fable 结论」。
- D. 全区间 63cf715..HEAD 改动文件除审查产物(map 通例明文豁免)外全部有 map owner 提及(final_acceptance/exemptions 等验收产物已入 BR-DIGEST owner 行)。

## 4. 两轮 codex 全库盲审(已完成,2026-08-09;基线 tip=45bf8f3,互盲)

### Round B 台账重放:43 CONSISTENT / 1 INCONSISTENT / 5 UNVERIFIABLE(分母 49)

- 报告 `blind-reviews/r9/45bf8f3/round-b-ledger-replay.md`。结构一致性 49↔49 全对齐;87/89 测试其环境 PASS(唯二 loopback EPERM 与预告一致)。
- **full-F-03 INCONSISTENT(属实,已整改)**:主表「豁免已登记」先行于事实——独立豁免台账/批准记录/防回流负测当时均不存在。整改:`exemptions.md` EX-01 四要素(调用图=生产零引用、formal registry 零引用、能力矩阵探索组、自动失效条件)+`test_exemption_guards.py` 防回流负测(挂 SUITE,含注入红)+ledger 主表与详情更新+Fable 批准记录。
- **final_acceptance 第 3 节数字/工具缺口(属实,已整改)**:见第 3 节口径与时点声明,工具已入库。
- **§7 批三 B3F_BLOCKED 旧标题与 R9-05 详情不一致(属实,已履约)**:裁判复跑(Fable 环境两纵切片+全量多次全绿、G3-0/PYTHIA mainnet smoke 完成)早已满足该节自设的改写条件,未回来登记;按原约定改写为 B3F_COMPLETE 并补裁判登记行。
- **5 UNVERIFIABLE=环境限制非缺陷**(loopback EPERM×3:full-F-01/six-F-03/R7-01;禁网 mainnet×2:R9-01/R9-05)。Fable 环境证据指针:全量 89 项含两纵切片多次全绿(批三收口 f4c40ea/批四各循环/降级收口 b7a8537 后);裁判 mainnet 证据哈希入档 `g3_preflight/smoke-20260808/`(GPA 82,218~82,223 账户、三方闭合 diff=0)。独立复核这两类需允许 loopback bind 的环境与联网裁判重放,属环境依赖如实登记。

### Round A 六视角全库:BLOCK(P0=2/P1=3/P2=2/P3=0)——Fable 逐条读码核实全部属实

- 报告 `blind-reviews/r9/45bf8f3/round-a-sixlens.md`。其环境基线与 Round B 一致(87/89+2 EPERM;invariant_scan 全绿)。报告质量高:每条带复现、git blame 归因、最强替代解释与不采纳理由。
- **关键定性:RA-01~05、RA-07 六条 git blame 全部早于 R9 基线(63cf715),属存量历史漏检,不在 R9-01~05 五 finding 范围;所在子系统(replay→state→figures 结果计算/呈现层、adversarial review 内容深度、v2 采集器 key 纪律)R9 四批均未触及。** RA-06 即 F-B4-01,已经用户 2026-08-09 裁决降级接受(盲审独立复现印证诚实登记成立,其自评「不夸大为 P0/P1」)。
- 逐条 Fable 读码核实(均属实):
  - RA-01(P0)`state_from_facts.py:85-95` camp_share_series 只验结构长度,不验值域[0,100]/同点闭合/末点对 facts/不绑定 replay 收据——正式图 1 序列可自报,组装错误(含 AI 手滑)不被机器拦截。
  - RA-02(P0)`replay_pass2.py:31-34`(同族 replay_duck/replay_edges)阵营互斥宣称无 validator,重复地址后项静默覆盖,加总仍 100% 外观正常。
  - RA-03(P1)fig1 全收阵营但绘图层只画 CAMP_ORDER 交集,未知阵营静默漏画,A5 只封 PNG 哈希不验图例集合。
  - RA-04(P1)对抗复核 runner 只验 exit 0+产物非空,发布闸只验角色名/blocker resolved/decision,产物内容零校验——2 字节「ok」可满足「对抗复核必做」。
  - RA-05(P1)旧小样本 replay pass1 gate_pass=false 仍 exit 0,pass2 不查 gate 照常产正式命名序列。
  - RA-07(P2)F-07 回归只锁三支 v1,现役首选 fetch_hypersync_v2 保留位置明文 token 且优先级最高——同族没关到同一深度。
- **处置:六条存量 finding 登记为 R10 候选清单(见下),不并入 R9 收敛范围;是否随 R9 先修或立 R10,交用户裁决。**

### R10 候选清单(存量,按风险排序)

| 候选 | 级 | 一句话 | 风险窗口 |
|---|---|---|---|
| RA-01 | P0 | 图 1 阵营序列自报无校验无绑定 | 每次生成新报告的图 1 |
| RA-02 | P0 | 阵营重复地址静默后项覆盖 | 每次 camps.json 组装 |
| RA-05 | P1 | 旧 replay gate 失败仍出正式序列 | 走旧引擎的小样本分析 |
| RA-03 | P1 | 未知阵营静默漏画 | 图 1 呈现 |
| RA-04 | P1 | 对抗复核可被空壳满足 | 发布闸把关深度 |
| RA-07 | P2 | v2 采集器位置明文 token 漏回归 | 采集操作 key 纪律 |

## 5. 版本收口(完成,2026-08-09)

- 用户裁决(AskUserQuestion):R9 先收尾,R10 候选六条下轮修。
- VERSION 6.36.0→6.37.0;CHANGELOG 版本索引+详情节已写(changelog_lint PASS,活跃 18 条)。
- 待用户授权:--ff-only 合并 main+push(Fable 不自行 push)。

## 5. 版本收口(待盲审后)

- 升 VERSION 6.36.0→6.37.0 + CHANGELOG;请用户授权 --ff-only 合并 main+push(Fable 不自行 push)。
