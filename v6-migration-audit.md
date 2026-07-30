# v6.0.0 冻结-核销双向审计表（2026-07-30）

> 冻结面：v5.0.0（commit 087ccec）的 SKILL.md（180 行/37KB）＋ 4 个现役 commands（~/.claude/commands/，git 外）＋ retrospective.md ＋各 gate exit 语义。审计方向：**正向**＝每条旧义务→新权威位置；**反向**＝每条新义务→旧来源或批准例外。结论：**零丢失、零静默取舍；存疑清单经逐项验证后清零**。

## 一、正向核销（旧 SKILL.md 义务 → 新位置）

| 旧段落 | 义务要点 | 新位置 | 处理 |
|---|---|---|---|
| frontmatter | description 触发面 | SKILL.md 原样保留 | 零变更 |
| 头部 | 三问框架＋门槛提要＋开放条款＋监控包规则＋核心信条 | SKILL.md 使命段；门槛细则 analyze-workflow A3.4→playbook §6a | 压缩，语义全保 |
| 头部 | 问 4 删除＋解锁情报保留＋背调路线退役 | SKILL.md（三问）＋A1 尾句 | 迁移（初稿漏"其余路线按需"半句，审计中补回） |
| 头部 | "报告骨架最小集/特有章节自由插入" | report-template L29/L52 已有（验证过） | 权威源覆盖，指针 |
| 铁律 1 | 结论独立性＋白名单/黑名单＋零外部代币名＋一币一会话 | SKILL.md 铁律 1 | 白名单枚举＝references 目录结构本身（pipeline=端点/scripts=脚本/environment=坑/workflow=模板/§11=措辞/address-book=标签）；"标签用前抽查核验"义务在 address-book.md 纪律区①（验证过） |
| 铁律 2–7 | 对账/证据强度/复核/取数/成本/交付边界 | SKILL.md 铁律 2–7 | 铁律 2 三查→四查（例外①）；铁律 4 履历数字剥除（CHANGELOG 可考古）；铁律 7 SPX 案例名剥除规则全保 |
| 工作流总览 | 七阶段图＋计划落盘＋用户决策点前置 | SKILL.md 路由表＋A0 首段 | "决策点前置"初稿漏，审计中补回 A0 |
| 阶段 0 | 四核定/多链硬关卡/vesting/版本自查/链路由表/通道探路/记账 gate | analyze-workflow A0 | 记账 gate 原理压缩（脚本头注为权威）；VIRTUAL 履历留一行来源 |
| 阶段 1 | 三路并行/长任务运维/预采集衔接 | A1 | 全保 |
| 阶段 2 | 三查＋anchor_plan 分层计划制 | A2（升四查） | 真值闸=例外①；QUQ 实测数字剥除 |
| 阶段 3 | 盲化/方法序列/G8 硬闸/判级门槛/大户双闸/演变重放/状态评估 | A3.1–A3.7 | 判级门槛一行摘要＋权威指针 §6a（消双写）；Alpha 集齐率同责句保留（指 casebook C-01） |
| 阶段 4 | 执行序全要素（扰动/揭盲/反例/N 路/完整性/外部异构/三档/修订序/附录） | A4 | 全保；casebook 三册作备择弹药为新挂载 |
| 阶段 5 | 三图/流转图/build_html/附录四件套/analysis-state/监控包/checklist | A5 | 全保；阵营名白名单+图例目检自坑表迁入 |
| 阶段 6 | 复盘指针 | A6 | 全保 |
| 断点恢复 | 五步固定序 | context-discipline.md 末节 | 全保 |
| update 段 | 两条核心纪律＋scripts/update 通用件 | SKILL.md 一行路由＋commands-staging/token-update＋update-workflow（原有） | 全保 |
| easy 段 | 同强度/两件套/绝不自动转正/跨币汇总禁令 | SKILL.md 一行路由＋commands-staging/token-easy-analysis＋easy-workflow（原有） | 全保 |
| 成本纪律 | 三刀 13 条＋预算数字＋两档制唯一权威源声明 | context-discipline.md（逐条对过 1–13） | 全保；定位改"质量机制"，规则零变更 |
| 深入阅读 | 26 个文件索引 | SKILL.md 清单（docs_lint 反向检查 PASS＝齐全） | 新增 4 行（analyze-workflow/context-discipline/casebook/collect-workflow） |

## 二、坑表 18 条分流核销

| # | 坑 | 归宿 |
|---|---|---|
| 1/2/3 | SSL / reportlab / PDF 质检假通过 | environment.md 已有（A5、通用纪律指针） |
| 4/9 | 免费层限流 / 长跑预估跳票 | analyze-workflow 通用纪律＋A1 |
| 5 | Etherscan 免费 key 仅 ETH | data-pipeline-evm-channels 死亡名单 L68 已有 |
| 6 | 口径混淆 | casebook S 册＋playbook-supply-recon §1 |
| 7 | CEX 黑箱越界表述 | A5 指针→playbook-evidence-wording §11 |
| 8 | 聚类服务地址污染 | casebook E-02＋playbook §6 服务枢纽剔除 |
| 10 | 关键字符串从落盘文件取 | analyze-workflow 通用纪律 |
| 11/12 | EIP-7702 / 循环论证 948 倍 | casebook E-01 / E-03 |
| 13 | 浮点阈值漏整数枚 | A3 尾（含橱窗仓指纹提示） |
| 14 | 前台 sleep/until 10 分钟上限 | environment.md Shell 坑节（本次 append，唯一缺口） |
| 15 | zsh 通配符 | environment.md 已有 |
| 16 | 阵营名静默过滤＋图例目检 | A5 出图纪律 |
| 17 | DuckDB wei DOUBLE | data-pipeline-evm-recon L15 已有 |
| 18 | 0 抽查点报 PASS | casebook S-03 检验④（fail-closed 通则） |

## 三、commands 核销（旧 4 入口 → commands-staging/）

- **token-analyze**：旧文"五问框架/官推侦查/JSON 附录"为 v2 时代废止口径（现行漂移实证），新版对齐三问/监控包买入后补/analysis-state.json；其余义务（地址核定 AskUserQuestion/工作目录/独立性）全保。
- **token-easy-analysis**：全部义务保留；"P0P1 判级"→"标签判级"、"三查"→"四查"、"砍背调"条款随 v5.0 框架删除而移除（不再是差异点）。
- **token-update**：7 条义务全保；"P0/P1 阈值"→"判级门槛"；U2 提及供给真值闸（例外①）。
- **collect-data**：操作细节（清单解析/plan/run_guarded/泳道/锁/夜间/巡检/汇报）**全量迁入 references/collect-workflow.md**（新建——原细节只活在 git 外的 command 文件里，是"权威源不受保护"的实证）；command 瘦身为入口。逐条对照原文第 2–9 条：零丢失。

## 四、反向核销（新义务 → 来源）

| 新义务 | 来源 |
|---|---|
| 供给真值闸（scripts/lib/supply_truth_gate.py；A2 第 3 查/easy E2/update U2.4 必跑；exit 0/2/1） | **批准代码例外①**（GNT replay-silent-burn-trap 2026-07-28，机制成立直接转正） |
| casebook_lint.py 挂 run_all | **批准代码例外②** |
| casebook 3 册 11 条＋A3.2 判例过闸＋A4 备择弹药挂载 | 计划第 2 步；判例内容全部来自已终裁翻案（PYTHIA/TROLL/IQ/QUQ/LPT/PENGUIN/GNT/GMX），零新判定规则 |
| evals 8 题＋README | 计划第 1 步；不进分析流程（目录在 references 外），零分析义务 |
| retrospective 2c 分流决策树＋整编触发线 2 条＋evals 候选登记 | 计划第 5 步；元规则（v4.1.0）从身份类推广到达标教训 |
| A3.6 阵营恒等自检 assert＝100%/反向断言 | IQ 案 2026-07-26 复盘教训（原记 memory"待写入 skill"未落地——本次借 casebook S-03 收编＋workflow 挂载，正是四案复发病灶的治法） |
| A3.6 历史清零层检测（全期 max 仓位） | v4.2 已固化于复核 prompt（evidence-wording §10 完整性批评）；A3 明写＝把拦截点从复核前移到分析，非新规则 |
| references/collect-workflow.md | collect-data 命令细节迁入（见三） |
| environment.md sleep/until 条 | 旧坑表第 14 条迁入 |

## 五、gate exit 语义逐字比对

- accounting_gate 0=放行/2=BLOCK 硬停/1=检测失败禁当放行 → A0 逐字保留 ✓
- entity_identity_gate 三类 flag→build_html G8 物理拦截 → A3.3 逐字保留 ✓
- build_html 退出码 0、WARN 拒交付 → A5 ✓；easy WARN=0 → command ✓
- supply_truth_gate 0/2/1（新）→ A2/E2/U2 三处一致 ✓
- collect 队列锁 exit 3/skipped_locked → collect-workflow.md ✓

## 六、存疑清单（计划要求"提交用户裁决，不静默取舍"）

逐项验证后**清零**。两条"非丢失的语义微增"透明申报（见表四后两行注）：恒等自检与历史清零层均为已终裁教训的挂载，未改任何判定阈值/流程顺序/交付规格。
