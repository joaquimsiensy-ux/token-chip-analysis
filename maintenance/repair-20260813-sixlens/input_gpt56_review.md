# token-chip-analysis v6.39.5 全量六视角 Review 报告

[已知] 审查对象：review 专用快照 `v6.39.5`，记录 HEAD `2ebd885d1a1364779338e02f8f30e991eec2302d`。
[计算得到] 上传归档 SHA256：`e9f8d5beb8490c519549e2732a302bfde656aee021ef9b5bf2ba75fe38fb48f5`。
[已知] 使用规范：`references/maintenance-review-repair.md` 第一节末尾“标准 review 指令模板”，六视角逐条执行；每项 finding 强制三选一归因，并写最强替代解释及排除理由。

## 一、裁决

[推理] **BLOCK。** 严重度为 **P0=2、P1=5、P2=3、P3=1**；P0/P1 仍存在，不能发布为“全量 review 通过”。置信度：**HIGH**。
[计算得到] 归因分布：历史漏检=5；老问题修复不全（半修残留）=4；修复中新引入（新引入）=2。
[推理] 最危险的不是普通测试缺口，而是三条“外观仍自洽”的错误接受链：自报阵营序列可直接进图、重复阵营地址后项覆盖仍加总 100%、失败 replay 仍可继续产正式序列。

### Finding 总表

| ID | 级别 | 结论 | 六视角 | 强制归因 | 置信度 |
|---|---:|---|---|---|---|
| F-01 | **P0** | [已知] 图 1 阵营时间序列仍是调用者自报，未绑定重放证据且不做数值闭合 | ①字段来源、⑤双向一致性、⑥闸可绕性 | **历史漏检** | **HIGH** |
| F-02 | **P0** | [已知] 阵营互斥只写在文档里，重复地址被后项静默覆盖 | ④同族调用面、⑤双向一致性、⑥闸可绕性 | **历史漏检** | **HIGH** |
| F-03 | **P1** | [已知] 未知阵营被图 1 静默漏画，A5 只封图片哈希不验图例集合 | ①字段来源、⑤双向一致性、⑥闸可绕性 | **历史漏检** | **HIGH** |
| F-04 | **P1** | [已知] 对抗复核门禁只证明“运行过并写了非空文件”，2 字节 `ok` 即可 PASS | ①字段来源、②失败分支、⑥闸可绕性 | **历史漏检** | **HIGH** |
| F-05 | **P1** | [已知] replay pass1 明知 `gate_pass=false` 仍退出 0，pass2 不检查便生成正式序列 | ②失败分支、④同族调用面、⑥闸可绕性 | **历史漏检** | **HIGH** |
| F-06 | **P1** | [已知] 销户账户覆盖审计在 RPC 批次失败、零事件可核验时仍退出 0 | ②失败分支、④同族调用面、⑤双向一致性、⑥闸可绕性 | **老问题修复不全（半修残留）** | **HIGH** |
| F-07 | **P1** | [已知] 命令部署同步守卫有两条假绿：部署目录缺失和两份迁移命令长期不一致 | ②失败分支、③存量迁移、⑤双向一致性、⑥闸可绕性 | **修复中新引入（新引入）** | **HIGH** |
| F-08 | **P2** | [已知] HyperSync v2 仍允许位置参数明文 token，且优先级最高 | ③存量迁移、④同族调用面、⑤双向一致性 | **老问题修复不全（半修残留）** | **HIGH** |
| F-09 | **P2** | [已知] 依赖锁守卫不校验 Python 版本，也漏掉 7 个直接依赖和 46 个锁包 | ④同族调用面、⑤双向一致性、⑥闸可绕性 | **老问题修复不全（半修残留）** | **HIGH** |
| F-10 | **P2** | [已知] `formal_ready` 的“可执行证据”仍可由静态调用字面伪造，且生产发布闸直接消费 | ①字段来源、④同族调用面、⑥闸可绕性 | **老问题修复不全（半修残留）** | **HIGH** |
| F-11 | **P3** | [已知] review 包说明写 353 文件，实际快照为 354 文件 | ⑤双向一致性 | **修复中新引入（新引入）** | **HIGH** |

## 二、全量覆盖证明：不是抽查

[计算得到] 归档共有 **354 个文件成员、28 个目录成员**；无危险路径、无重复成员、无符号链接。解压后逐文件读取并计算 SHA256：**354/354**；总字节数 **4,807,076**。
[计算得到] 文件类型：文本 **353**、PNG **1**；Python **235**、Markdown **84**、JSON **17**、CSV **7**、Shell **2**、TOML 1、lock 1。
[计算得到] 235 个 Python 文件共 **50,895** 行，全部 `compile()` 成功；17 个 JSON、7 个 CSV、1 个 TOML 全部解析成功，CSV 列宽一致，结构解析错误 **0**。
[已知] 唯一 PNG `references/examples/lifecycle-flow-sample.png` 已按图像实际检查：文字、节点、箭头、数值与脚注可辨识；未发现独立缺陷。
[已知] review 包说明明确剔除了六个大型标签 CSV、标签源数据、`.git/`、大部分 archive 和 blind-reviews；这些不在归档分母内，未被误报为缺失。
[推理] “全量”在本报告中的可复核含义是：归档内没有任何文件被省略；每个文件都进入哈希账本、结构检查、六视角适用性矩阵和全库双向检索。它不等于数学证明“绝无其他未知缺陷”。

### 六视角逐条执行与实际文件分母

| 视角 | 实际检查 | 跳过/特殊处理 | 产出 |
|---|---:|---|---|
| **①字段来源审计** | [计算得到] 346 文件；范围：关键字段、schema、事实源、producer/consumer、receipt 与自报值。 | [已知] 8 文件语义不适用；逐项路径与理由见附录 A。 | [已知] F-01、F-03、F-04、F-10 |
| **②失败分支审计** | [计算得到] 324 文件；范围：异常、warning、continue、退出码、失败产物、缺失输入与网络失败。 | [已知] 30 文件语义不适用；逐项路径与理由见附录 A。 | [已知] F-04、F-05、F-06、F-07 |
| **③存量迁移** | [计算得到] 240 文件；范围：legacy/schema/version/兼容入口、旧产物升级与迁移例外。 | [已知] 114 文件语义不适用；逐项路径与理由见附录 A。 | [已知] F-07、F-08 |
| **④同族调用面** | [计算得到] 326 文件；范围：正式入口、生产者/消费者、三 replay 引擎、采集器、门禁与测试同族。 | [已知] 28 文件语义不适用；逐项路径与理由见附录 A。 | [已知] F-02、F-05、F-06、F-08、F-09、F-10 |
| **⑤双向一致性** | [计算得到] 353 文本 + 1 图像实看；范围：文档↔代码、schema↔producer/consumer、CLI↔测试、包说明↔成员集合。 | [已知] 无文件跳过；PNG 采用视觉检查而非文本解析。 | [已知] F-01、F-02、F-03、F-06、F-07、F-08、F-09、F-11 |
| **⑥闸可绕性** | [计算得到] 338 文件；范围：发布闸、receipt、readiness、可选参数、skip/exception 和空壳证据。 | [已知] 16 文件语义不适用；逐项路径与理由见附录 A。 | [已知] F-01、F-02、F-03、F-04、F-05、F-06、F-07、F-09、F-10 |

[已知] 附录 A 逐一列出 354 个路径、字节数、行数、SHA256 前缀、六视角 Y/N/A/VISUAL、跳过理由和关联 finding；完整 64 位 SHA256 另附 CSV。

## 三、验证与门禁结果

| 检查 | 结果 | 裁决 |
|---|---|---|
| Python 源码编译 | [计算得到] 235/235，错误 0 | [已知] PASS |
| JSON/CSV/TOML 结构 | [计算得到] 25/25，错误 0 | [已知] PASS |
| `changelog_lint.py` | [已知] rc=0 | [已知] PASS |
| `docs_lint.py --all` | [已知] 48 文档、断链 0 | [已知] PASS |
| `casebook_lint.py` | [已知] 6 册 36 条，结构完整 | [已知] PASS |
| `fixtures_lint.py` | [已知] rc=0 | [已知] PASS |
| 版本一致性 | [已知] VERSION/SKILL/pyproject=6.39.5 | [已知] PASS |
| 契约路由双向闭合 | [已知] rc=0 | [已知] PASS |
| SUITE 分母 | [计算得到] 91 个唯一入口；83 个 `test_*.py` 全部挂载；缺路径 0 | [已知] PASS |
| 危险执行原语扫描 | [计算得到] 现役范围未发现 `shell=True`、`eval()`、`exec()`、`os.system()`、`mktemp()` | [已知] 无独立 finding |
| archive 防回流 | [计算得到] 命中均为边界说明、维护登记或测试；未发现现役生产脚本读取 archive 数据 | [已知] PASS |
| 当前容器全量 suite | [已知] Python 3.13.5，低于项目 >=3.14；缺 `msgspec/duckdb/pyarrow/hypersync` 等锁定依赖；`invariant_scan` 因 `msgspec` 缺失无法完整启动 | [已知] **环境不可作权威全量运行**；不把该失败计为产品 finding |
| 环境 gate 自身 | [计算得到] 通过猴补 14 个元数据版本可在错误 Python/缺 7 个直接依赖时 rc=0 | [已知] **F-09** |
| 11 个最小反例 | [计算得到] 11/11 成功复现 | [已知] 支撑本报告 finding |

[已知] 包内历史日志记录了原机环境的全绿运行，但它们不是 v6.39.5 当前快照在本容器中的独立重跑，因此只作为历史背景，不用于替代本轮反例。

## 四、Finding 详单

### F-01 · P0 · [已知] 图 1 阵营时间序列仍是调用者自报，未绑定重放证据且不做数值闭合

[已知] **六视角：** ①字段来源、⑤双向一致性、⑥闸可绕性。**归因：历史漏检。置信度：HIGH。**
[已知] **不变量：** 正式图 1 的每个时间点必须由受控重放产物机械导出；值必须为有限数且落在 0–100，阵营集合、同点合计、日期轴、终点持仓都必须可离线重验，并绑定当前 replay receipt。
[已知] **代码/文档证据：**
- [已知] `scripts/report/state_from_facts.py:85-92` 只验 `dates/series` 形状和长度；`101-107` 原样把 `camp_share_series` 写进正式 state。
- [已知] `scripts/report/figures_from_facts.py:93-124` 直接读取该字段并送入正式图 1；没有重放回执、值域、同点闭合或终点对账。
- [已知] `maintenance/repair-20260806/final_acceptance.md:39-61` 已把同一问题登记为 RA-01/P0/R10 候选；v6.39.5 现役代码未关闭。
[计算得到] **最小反例：** `compile_state()` 接受并原样输出 `项目方=150%`、`散户=-50%`：`{"dates": ["2026-01-01"], "series": {"项目方": [150.0], "散户": [-50.0]}}`。
[推理] **影响：** 报告可以生成视觉上正式、A5 可封口、但数值任意错误的核心筹码演变图；这是直接污染结论层的生产可达路径。
[推理] **最强替代解释：`camp_share_series` 由可信重放器生成，compiler 只需搬运。**
[推理] **不采纳理由：** 不采纳：schema 允许任意调用者提供 `state_source.json`；产物没有 replay receipt 引用或哈希绑定，消费者也不重算。所谓“可信上游”没有机器证据。
[推理] **根修要求：** 删除“裸序列输入”作为正式路径，改为由三套 replay 引擎共同产出统一 `camp-series-receipt/v2`；共享 validator 重验日期单调、有限数、值域、同点闭合、阵营集合、终点与余额/事实账一致；state/A5 只消费通过 validator 且绑定当前 replay run 的回执。
[推理] **必须新增的回归：** 至少覆盖 150%、负数、NaN/Inf、同点不闭合、日期乱序/重复、终点与 facts 不一致、旧回执/错 run、合法多阵营与 burn 非堆叠口径。

### F-02 · P0 · [已知] 阵营互斥只写在文档里，重复地址被后项静默覆盖

[已知] **六视角：** ④同族调用面、⑤双向一致性、⑥闸可绕性。**归因：历史漏检。置信度：HIGH。**
[已知] **不变量：** 一个规范化地址在同一 camp spec 中最多属于一个阵营；任何跨阵营重复必须在产生序列前 fail-closed。
[已知] **代码/文档证据：**
- [已知] `scripts/evm/replay_pass2.py:31-34` 用字典后写覆盖；模块说明 `:5-8` 却声明阵营互斥。
- [已知] 同族 `scripts/evm/replay_duck.py:371-380` 和 `scripts/solana/replay_edges.py:237-243` 保留同一覆盖语义。
- [已知] `maintenance/repair-20260806/final_acceptance.md:44-45,54-57` 将其登记为 RA-02/P0。
[计算得到] **最小反例：** 同一地址同时放入 A、B，进程退出 0；结果 `A=[0.0]`、`B=[100.0]`，加总仍为 100%，没有任何错误：`{"dates": ["2026-01-01"], "A": [0.0], "B": [100.0], "散户": [0], "_meta": {"denominator": "current_net_supply", "note": "分母=当期净供应(累计mint−累计burn)；burn_cum_pct 不参与堆叠"}, "burn_cum_pct": [0.0]}`。
[推理] **影响：** 同址冲突不会制造明显的总量异常，反而会生成外观自洽的错误归因；项目方、CEX、LP 等关键阵营可被键顺序悄悄改写。
[推理] **最强替代解释：JSON 键顺序就是显式优先级，后配置覆盖是设计。**
[推理] **不采纳理由：** 不采纳：文档明确写“阵营互斥”，没有优先级字段、冲突日志或可审计裁决；三个实现也没有共享的优先级契约。静默依赖键顺序不是正式规则。
[推理] **根修要求：** 建立单一 `validate_camp_spec()`，先统一大小写/链地址规范，再拒绝跨阵营重复；三引擎和图表入口全部调用同一实现。若确需优先级，必须显式字段化并把冲突裁决写入回执，不能靠字典覆盖。
[推理] **必须新增的回归：** 跨阵营同址、大小写变体、重复别名、同阵营重复、ZERO/dead 特例、三引擎等价性、键顺序置换不改变结果。

### F-03 · P1 · [已知] 未知阵营被图 1 静默漏画，A5 只封图片哈希不验图例集合

[已知] **六视角：** ①字段来源、⑤双向一致性、⑥闸可绕性。**归因：历史漏检。置信度：HIGH。**
[已知] **不变量：** 输入序列中的每个业务阵营必须被明确渲染，或在生成图片前被明确拒绝；不能无声丢弃。
[已知] **代码/文档证据：**
- [已知] `scripts/report/standard_charts.py:48-52` 固定 `CAMP_ORDER`；`:168-172` 只画输入与该列表的交集。
- [已知] `scripts/report/figures_from_facts.py:93-124` 接受任意阵营名，不校验标准集合。
- [已知] `scripts/report/a5_report_seal.py:120-128,149-156` 绑定图片文件哈希与图片集合，不解析/绑定图例或输入 series 集合。
[计算得到] **最小反例：** 输入 `项目方` 与 `未知阵营` 各 50%；图片成功生成，但实际 `stackplot` 标签只有 `["项目方"]`。
[推理] **影响：** 拼写错误、新增阵营或旧格式键会从正式图中消失；读者看到的堆叠面积可以不足 100%，却没有机器阻断。
[推理] **最强替代解释：固定词表是报告规范，非标准阵营本就不该画。**
[推理] **不采纳理由：** 不采纳：若非标准键不合法，入口必须拒绝；当前行为是“接受数据、丢弃呈现”，不是“执行规范”。
[推理] **根修要求：** 在 state/figure 边界校验阵营集合；未知键 fail-closed，或显式映射为“其他/未知”并在图例披露。A5 seal 增加输入阵营集合、实际图例集合和绘图 spec 哈希的双向绑定。
[推理] **必须新增的回归：** 未知键、近似拼写、废止 legacy 键、新增合法键未同步、输入集合与图例集合不等、合法缺省阵营。

### F-04 · P1 · [已知] 对抗复核门禁只证明“运行过并写了非空文件”，2 字节 `ok` 即可 PASS

[已知] **六视角：** ①字段来源、②失败分支、⑥闸可绕性。**归因：历史漏检。置信度：HIGH。**
[已知] **不变量：** 发布所依赖的对抗复核必须证明目标、覆盖面、反对命题、证据、未决项和裁决；不能用任意非空字节替代。
[已知] **代码/文档证据：**
- [已知] `scripts/report/adversarial_review_runner.py:67-75` 只要求子进程 rc=0 且 staging 文件非空；`:92-113` 只重验路径/大小/哈希。
- [已知] `scripts/report/shared_release_receipt.py:296-317` 只验角色、runner、执行回执、blocking/resolved 和 decision。
- [已知] `scripts/report/audit_release_gate.py:706-724` 同样只验角色名、blocker 状态和 release decision，不读复核正文。
[计算得到] **最小反例：** 受控 entrypoint 仅写入 `ok`；artifact 大小 2 字节，execution receipt 状态仍为 `PASS`，validator 接受。
[推理] **影响：** “对抗复核已完成”可被空壳满足，发布闸获得虚假的独立审查保证。
[推理] **最强替代解释：人的审查质量无法可靠机器评分，门禁只负责执行来源。**
[推理] **不采纳理由：** 不采纳：无需机器判断观点是否正确，也能要求结构化 schema、目标绑定、逐项命题、证据引用、覆盖清单和未决项；当前连这些最低可验证事实都没有。
[推理] **根修要求：** 把自由文本改为 `adversarial-review-artifact/v1` 结构化产物；强制目标哈希、实际检查文件、至少一个反例尝试/替代解释、finding 数、未决项、证据路径，并由独立 validator 消费。自由文本可作为附录，不能作为唯一门禁对象。
[推理] **必须新增的回归：** 空文件、`ok`、纯模板、角色互换、目标错绑、无实际文件清单、证据不存在、blocker 未决、两角色复制同一内容。

### F-05 · P1 · [已知] replay pass1 明知 `gate_pass=false` 仍退出 0，pass2 不检查便生成正式序列

[已知] **六视角：** ②失败分支、④同族调用面、⑥闸可绕性。**归因：历史漏检。置信度：HIGH。**
[已知] **不变量：** 任何重放账不闭合或出现负余额时，生产链必须非零退出、隔离失败产物，所有下游必须验证同一成功回执。
[已知] **代码/文档证据：**
- [已知] `scripts/evm/replay_pass1.py:136-155` 计算并写出 `gate_pass`；`:163-164` 顶层裸调 `main()`，函数没有根据 false 返回非零。
- [已知] `scripts/evm/replay_pass2.py:21-28` 只读 `mint_total_wei`，完全忽略 `gate_pass`；随后照常写 `camp_series.json`/`entity_series.json`。
- [已知] `maintenance/repair-20260806/final_acceptance.md:48,58-60` 已登记 RA-05/P1。
[计算得到] **最小反例：** 构造无 mint、A→B 转账导致负余额：pass1 返回 `None`（进程语义为 0），`replay_stats.gate_pass=false`；随后 pass2 返回 0 并写出正式命名序列。
[推理] **影响：** 坏账重放可以进入图表/报告链，且文件名与成功产物无区别。
[推理] **最强替代解释：pass1 是探索脚本，`gate_pass` 留给人工判断。**
[推理] **不采纳理由：** 不采纳：模块文档把“负余额=0 才过 gate”写成正式语义，pass2 是直接下游且不消费该字段；“人工会看”不是必经门禁。
[推理] **根修要求：** pass1 在 `gate_pass=false` 时返回 2，并把失败输出迁入 quarantine/ERROR receipt；pass2 必须接收并验证 pass1 receipt（目标、范围、输入哈希、status=PASS），不能只读 stats 中一个分母字段。三 replay 引擎共享同一 validator。
[推理] **必须新增的回归：** 负余额、供给不闭合、坏行放行边界、旧失败 stats、篡改 gate 字段、错 run receipt、成功链、失败后 canonical 文件不存在。

### F-06 · P1 · [已知] 销户账户覆盖审计在 RPC 批次失败、零事件可核验时仍退出 0

[已知] **六视角：** ②失败分支、④同族调用面、⑤双向一致性、⑥闸可绕性。**归因：老问题修复不全（半修残留）。置信度：HIGH。**
[已知] **不变量：** 覆盖审计只有在样本有效、关键 RPC 完成且存在足够可核事件时才能宣称“零漏”；未知必须 ERROR/BLOCK，不能等价于 PASS。
[已知] **代码/文档证据：**
- [已知] `references/data-pipeline-solana-capture.md:95-97` 与脚本头 `scripts/solana/audit_closed_accounts.py:23-27` 明确：undetermined 不构成无漏证据，运行失败/样本无效应 exit 1。
- [已知] 现役代码 `:260-266` 在 `getMultipleAccounts` 失败时只 warning+continue；`:282-291` 深挖签名失败只计 `fetch_failed`；`:322-345` 即使 coverage=None、checked=0，仍仅按 `missing` 决定 exit 2/0。
- [已知] `CHANGELOG.md:141-148` 曾系统修复同族采集器 fail-open，但该正式审计入口没有等深闭合。
[计算得到] **最小反例：** 唯一账户批次的 `getMultipleAccounts` 返回失败；报告为 `events.checked=0`、`coverage_rate=null`、alive=0、closed=0，进程仍退出 0。
[推理] **影响：** 网络故障或限流能被报告成“抽样零漏边”，使通道完整性审计失去否决能力。
[推理] **最强替代解释：这是补充型抽查，0 只表示“未发现漏边”，不是强证明。**
[推理] **不采纳理由：** 不采纳：脚本自己的退出码契约明确把运行失败/样本无效定义为 1，并明确 undetermined 不能算无漏；实现与文档直接冲突。
[推理] **根修要求：** 输出显式 `status=PASS|BLOCK|ERROR`；任何账户状态批次失败、深挖 fetch_failed、零 closed、零 checked、墙钟截断或覆盖低于机器阈值均不得 PASS。把最小样本/最大 undetermined 比例参数写入回执并由消费者验证。
[推理] **必须新增的回归：** 全部状态 RPC 失败、部分批次失败、closed=0、checked=0、fetch_failed>0、过半 undetermined、墙钟截断、真实漏边、充分零漏正例。

### F-07 · P1 · [已知] 命令部署同步守卫有两条假绿：部署目录缺失和两份迁移命令长期不一致

[已知] **六视角：** ②失败分支、③存量迁移、⑤双向一致性、⑥闸可绕性。**归因：修复中新引入（新引入）。置信度：HIGH。**
[已知] **不变量：** 声称“部署同步”的门禁必须区分 PASS/SKIP，并在部署存在时要求所有现役命令逐字节一致；迁移窗口不能无限期改写为 PASS。
[已知] **代码/文档证据：**
- [已知] `scripts/tests/test_commands_deploy_sync.py:35-38` 部署目录不存在时打印 SKIP 但返回 0。
- [已知] `:59-68,76-88` 对 `token-analyze-1/2.md` 的 SHA 不一致只检查 staging 自身含几个 needle，随后打印 PASS 并返回 0；部署文件内容本身不受约束。
- [已知] `CHANGELOG.md:125` 曾声明命令已部署同步且 SHA 一致；当前迁移豁免在后续修复中重新制造了绿色接受面。
[计算得到] **最小反例：** 两份 deployed 文件故意写成 `STALE1/STALE2`，测试输出 `PASS: ...待 Fable 部署同步` 且 rc=0；把部署目录删掉，输出 `SKIP` 仍 rc=0。
[推理] **影响：** 全量 suite 可以在实际 slash command 仍运行旧契约时全绿；用户入口绕过新 schema/新闸的风险直接落到生产操作。
[推理] **最强替代解释：异机没有 `~/.claude/commands`，必须允许可移植测试；迁移期也必须容忍待部署。**
[推理] **不采纳理由：** 不采纳：可移植性需要的是“明确 SKIP、不能冒充 PASS”；迁移可由有期限/有回执的独立状态表达，不能让陈旧部署永久绿色。
[推理] **根修要求：** 删除 `MIGRATION_CHANGED` 绿色豁免；部署存在时三文件必须 SHA 全等。部署不存在时返回独立 skip 码或由 run_all 明确记录 `UNVERIFIABLE`，部署主机的发布门必须要求该项真 PASS。迁移使用一次性 receipt（源/目标 SHA、部署时间、操作者）并设置自动失效。
[推理] **必须新增的回归：** 目录缺失不得计 PASS、任一 stale 文件失败、stale 内容即使含 needles 也失败、退役文件在发布主机失败、三文件全等正例、迁移回执过期/错 SHA。

### F-08 · P2 · [已知] HyperSync v2 仍允许位置参数明文 token，且优先级最高

[已知] **六视角：** ③存量迁移、④同族调用面、⑤双向一致性。**归因：老问题修复不全（半修残留）。置信度：HIGH。**
[已知] **不变量：** 所有现役 HyperSync 入口都不得把秘密放入 argv；token 只能从受控文件或环境变量读取，测试必须覆盖全同族。
[已知] **代码/文档证据：**
- [已知] `scripts/evm/fetch_hypersync_v2.py:9-11,314-320,333-345` 明知 argv 会被 `ps` 看见，仍保留可选位置参数并置于最高优先级。
- [已知] `scripts/tests/test_token_no_positional.py` 只覆盖三支 v1 入口，没有 v2。
- [已知] `CHANGELOG.md:143-148` 的密钥修复只移除了三支 v1 的位置参数；同族主线 v2 漏修。
[计算得到] **最小反例：** 同时提供 argv=`argv-secret`、环境变量和 token 文件，`resolve_token()` 返回 `argv-secret`，只打印 warning。
[推理] **影响：** 使用旧命令或误复制示例时，秘密进入进程列表、shell 历史和诊断日志。
[推理] **最强替代解释：位置参数仅为旧用法兼容，warning 足以迁移用户。**
[推理] **不采纳理由：** 不采纳：安全不变量不能靠提醒；v1 已选择破坏兼容移除该通道，v2 作为现役首选入口没有合理例外。
[推理] **根修要求：** 删除 `api_token` 位置参数并对旧形态明确拒绝；统一优先级为显式 `--token-file` > 环境变量 > 默认文件，或只保留文件+环境。把所有 HyperSync 入口自动枚举进同族测试，禁止手写三文件白名单。
[推理] **必须新增的回归：** 全入口 argv secret 拒绝、文件/环境优先级、空文件、权限/缺文件、secret 不出现在 stdout/stderr/receipt/ps 形态的 argv。

### F-09 · P2 · [已知] 依赖锁守卫不校验 Python 版本，也漏掉 7 个直接依赖和 46 个锁包

[已知] **六视角：** ④同族调用面、⑤双向一致性、⑥闸可绕性。**归因：老问题修复不全（半修残留）。置信度：HIGH。**
[已知] **不变量：** 若文档把 requirements.lock 称为精确环境事实源，环境门禁至少必须验证 Python 版本、全部直接依赖的精确版本和可导入性；否则必须收窄声明。
[已知] **代码/文档证据：**
- [已知] `pyproject.toml:3-5` 把 lock 称为精确冻结事实源并把 `env_check.py` 称为一致性 gate；`:17-47` 要求 Python >=3.14 和 21 个直接依赖。
- [已知] `scripts/tests/env_check.py:17-49` 只检查手写的 14 个 `KEY_PKGS` 元数据版本，不看 Python、不导入模块、不检查其余直接依赖。
- [已知] `requirements.lock` 有 60 个包；当前 gate 覆盖 14 个。
[计算得到] **最小反例：** 在实际 Python 3.13.5（低于 >=3.14）环境中，仅伪造 14 个 metadata 版本匹配，gate 返回 0；未检查的直接依赖为 `certifi/google-cloud-bigquery/openpyxl/pydata-google-auth/pymupdf/pypdf/reportlab`。
[推理] **影响：** suite 的“环境一致”结论弱于 pyproject 声明；解释器或报告/BigQuery 依赖缺失可在后续正式路径才爆炸。
[推理] **最强替代解释：只查核心包是为了避免传递依赖噪音。**
[推理] **不采纳理由：** 不采纳：Python 版本和全部直接依赖不是传递噪音；而且当前输出明确说“环境与依赖锁一致”，语义过宽。
[推理] **根修要求：** 解析 pyproject 的全部 direct dependencies，按 lock 精确版本校验并做最小 import probe；单独校验 `requires-python`。若不准备验证 60 个传递包，输出与文档必须改成“核心直接依赖子集”，不能称完整环境一致。
[推理] **必须新增的回归：** 错误 Python、每个直接依赖逐一缺失/错版、metadata 存在但 import 失败、名称规范化（PyMuPDF/fitz）、合法锁环境。

### F-10 · P2 · [已知] `formal_ready` 的“可执行证据”仍可由静态调用字面伪造，且生产发布闸直接消费

[已知] **六视角：** ①字段来源、④同族调用面、⑥闸可绕性。**归因：老问题修复不全（半修残留）。置信度：HIGH。**
[已知] **不变量：** 正式链 readiness 若被发布闸消费，必须来自独立、不可由被测文件自证的运行证据；静态 AST 中出现脚本名不等于脚本执行成功。
[已知] **代码/文档证据：**
- [已知] `scripts/lib/formal_capability_probes.py:180-225` 只解析 callable、SUITE 挂载和 decorator 属性；没有执行纵切片。
- [已知] `scripts/lib/chain_registry.py:211-251` 据此导出 `formal_ready`；`scripts/report/audit_release_gate.py:60-73` 与 `handoff_manifest.py:443-446` 把它用于正式放行。
- [已知] `scripts/tests/invariant_scan.py:647-663,723-753` 明文承认模块级/外层重绑定可绕、无独立运行时兜底；`CHANGELOG.md:94-98` 与历史复审也登记为 KNOWN-OPEN。
[计算得到] **最小反例：** 武器化模块先 `import subprocess`，再在模块层把它替换为 `_Silent`；静态守卫 `errors=[]`，运行时 rc=0、打印 `VERTICAL SLICE GREEN calls=6`，实际启动 producer 数为 0。
[推理] **影响：** 该项不是隐藏风险，但名称和生产消费仍把“静态登记完整”提升成“正式可执行就绪”；恶意或误改纵切片可制造假 readiness。
[推理] **最强替代解释：这是已接受的低成本内部完整性守卫，真实数据正确性另由链上对账保证。**
[推理] **不采纳理由：** 部分采纳其风险登记，但不采纳“无需 finding”：生产 API 仍命名为 executable/formal readiness，并直接控制 release；静态完整性与运行证明是两种事实。诚实登记降低严重度到 P2，不会闭合不变量。
[推理] **根修要求：** 二选一：A）真正闭合——由独立 parent runner 生成 nonce，逐个启动登记 producer，收集 PID/argv hash/producer hash/exit/新鲜 receipt，并让 release consumer 验证该外部运行回执；B）诚实降权——把该字段改名为 `formal_registration_complete`，从发布许可中移除，正式 readiness 另由运行回执导出。
[推理] **必须新增的回归：** 模块级重绑定、外层闭包重绑定、wrapper stub、import alias 二次覆盖、零子进程绿色、旧 receipt 重放、错 producer hash、真实运行正例。

### F-11 · P3 · [已知] review 包说明写 353 文件，实际快照为 354 文件

[已知] **六视角：** ⑤双向一致性。**归因：修复中新引入（新引入）。置信度：HIGH。**
[已知] **不变量：** review 快照的文件计数必须由打包 manifest 机械生成，与归档实际成员完全一致。
[已知] **代码/文档证据：**
- [已知] `REVIEW_PACKAGE_README.md:8` 声明“353 文件”；zip 中有 354 个文件成员、28 个目录成员，无重复、无危险路径、无符号链接。
[计算得到] **最小反例：** 归档枚举结果：declared=353，actual=354。
[推理] **影响：** 不影响运行逻辑，但削弱“全量包”覆盖证明和后续审查分母。
[推理] **最强替代解释：353 不含 README 自身。**
[推理] **不采纳理由：** 不采纳：说明未定义这种口径，且归档分母应由 manifest 明确列举，不能靠隐含自排除。
[推理] **根修要求：** 打包时生成 `REVIEW_PACKAGE_MANIFEST.json`（path/size/SHA256/type），README 从 manifest 取计数；验收测试比对 zip 实际成员。
[推理] **必须新增的回归：** 成员增删、README 自身、目录项、重复成员、符号链接、路径穿越、manifest 与 zip 双向集合。

## 五、归因汇总与流程病根

[已知] **历史漏检 5 项：F-01～F-05。** 包内 R9 最终台账已用早于基线的 blame 证据定性，且这些子系统当轮未触及；本轮在 v6.39.5 重新读码并独立复现，不是照抄旧报告。
[推理] **半修残留 4 项：F-06、F-08、F-09、F-10。** 共同模式是“主入口修了、兄弟入口或证据深度没到同一层”：fail-closed 漏 audit、密钥修复漏 v2、锁环境只验子集、可执行 readiness 最终仍是静态字面。
[推理] **新引入 2 项：F-07、F-11。** 前者是在后续迁移修复中重新放开的部署漂移接受面；后者是本次 review 打包流程的计数漂移。
[推理] 最主要的流程失守不是测试数量不足，而是门禁语义被降成“文件存在/字段存在/脚本名存在/返回码为 0”。这些条件证明了形式，不证明了目标不变量。

## 六、修复顺序与解除 BLOCK 条件

[推理] **Batch 1（P0，禁止夹带功能）：** F-01+F-02 同批根修。先建立 camp spec/series 单一 validator 与 replay receipt，再迁三个 replay 引擎、state、figures、A5；旧反例必须先红。
[推理] **Batch 2（P1 数据链）：** F-05+F-06。统一失败回执、退出码和下游必验；失败产物不得占 canonical 名。
[推理] **Batch 3（P1 发布/操作链）：** F-03+F-04+F-07。图例集合绑定、结构化对抗复核、部署同步真 PASS/SKIP 分离。
[推理] **Batch 4（P2）：** F-08+F-09；密钥入口自动枚举，环境 gate 与声明对齐。
[推理] **Batch 5（已知降级项）：** F-10 只能选择“独立运行回执闭合”或“从 release readiness 降权”，禁止继续加 AST 语法补丁。F-11 随打包器修。
[已知] **解除 BLOCK 的最低条件：** P0=0、P1=0；每项原反例、同族变体、失败分支三件套全绿；三 replay 引擎和两条正式发布入口做真实故障注入；最终合并快照重新执行本报告同一 354 文件分母的六视角全量审查。

## 七、被排除的候选与非 finding

[已知] 六个大型标签 CSV 和 `scripts/labels/sources/` 是 review 包明确剔除项；未把它们报成断链。
[已知] 当前容器缺锁定依赖、Python 版本不足导致的测试失败是环境事实；没有把“本容器跑不动”伪装成代码故障。F-09 针对的是 gate 可以错误放行，证据独立于环境缺包。
[已知] `archive/` 字样命中来自防回流说明、复盘登记和守卫测试；现役生产代码未读取考古资产。
[已知] `scripts/lib/net.py` 的 curl argv 可能携带 header/body，但现役调用面未找到把秘密传给该后端的生产路径；缺少生产可达反例，未立 finding。
[推理] `handoff_manifest.py` 对超大文件的稀疏哈希候选未能证明可绕过正式 freeze 输入的全哈希绑定，证据不足，未立 finding。

## 附录 A：354/354 全文件六视角覆盖账本

[已知] 标记：`Y`=该视角实际适用并检查；`N/A`=仍读取/哈希/结构检查，但该文件不承载该视角语义；`VISUAL`=按图像实看。

| # | 路径 | 字节 | 行 | SHA256 前16 | ① | ② | ③ | ④ | ⑤ | ⑥ | 关联/跳过理由 |
|---:|---|---:|---:|---|:--:|:--:|:--:|:--:|:--:|:--:|---|
| 1 | `.gitignore` | 686 | 21 | `94911ceb418c504d` | Y | N/A | N/A | Y | Y | N/A | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 2 | `CHANGELOG.md` | 71,752 | 362 | `1aedd14721bd6e72` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-06,F-07,F-08,F-10 |
| 3 | `REVIEW_PACKAGE_README.md` | 4,482 | 72 | `6b7f2cc7d853fc18` | Y | N/A | Y | Y | Y | Y | [已知] 支撑 F-11；[已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。 |
| 4 | `SKILL.md` | 7,737 | 88 | `d40d6c569d79005b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 5 | `VERSION` | 6 | 1 | `8d72971a556ac193` | N/A | N/A | N/A | N/A | Y | N/A | [已知] 1：不承载关键字段、schema、来源或回执语义；仍做字节/结构/双向检查。；2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 6 | `archive/README.md` | 274 | 5 | `edca1f6b81f539cb` | N/A | N/A | Y | N/A | Y | Y | [已知] 1：不承载关键字段、schema、来源或回执语义；仍做字节/结构/双向检查。；2：不包含执行失败分支或状态转换；仍检查内容与引用。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 7 | `commands-staging/token-analyze-1.md` | 2,112 | 17 | `9832eace6960bb66` | Y | Y | N/A | Y | Y | Y | [已知] 支撑 F-07；[已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 8 | `commands-staging/token-analyze-2.md` | 2,449 | 20 | `510152a8a40efcc3` | N/A | Y | Y | Y | Y | Y | [已知] 支撑 F-07；[已知] 1：不承载关键字段、schema、来源或回执语义；仍做字节/结构/双向检查。 |
| 9 | `commands-staging/token-analyze.md` | 828 | 13 | `f227da3bddcee26b` | N/A | Y | N/A | Y | Y | N/A | [已知] 1：不承载关键字段、schema、来源或回执语义；仍做字节/结构/双向检查。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 10 | `maintenance/repair-20260806/b1_progress.md` | 38,142 | 328 | `7d22ea2c5c0462ca` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 11 | `maintenance/repair-20260806/b2_progress.md` | 10,336 | 218 | `2af40e3f4f66ad7b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 12 | `maintenance/repair-20260806/b3_progress.md` | 48,195 | 383 | `9f83020a45788603` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 13 | `maintenance/repair-20260806/b4_progress.md` | 32,565 | 163 | `9168f4bfea50007f` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 14 | `maintenance/repair-20260806/batch1-report.md` | 14,319 | 215 | `ff760f160609f611` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 15 | `maintenance/repair-20260806/batch2-report.md` | 22,926 | 377 | `01a547f744c20c0d` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 16 | `maintenance/repair-20260806/batch3-report.md` | 17,234 | 290 | `2607c8d922645072` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 17 | `maintenance/repair-20260806/batch4-report.md` | 13,271 | 238 | `870f9072cd0767bd` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 18 | `maintenance/repair-20260806/diff-finding-map.md` | 48,126 | 233 | `8f8a220cb6587013` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 19 | `maintenance/repair-20260806/exemptions.md` | 2,343 | 19 | `b4f8c4f83837adb3` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 20 | `maintenance/repair-20260806/final_acceptance.md` | 7,132 | 72 | `26d7e229cda8f92c` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-01,F-02,F-03,F-04,F-05,F-08,F-10 |
| 21 | `maintenance/repair-20260806/g3_preflight/g3_0a_usdc_activity.json` | 2,415 | 73 | `c89ec1d635dcddc3` | Y | Y | Y | N/A | Y | Y | [已知] 4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 22 | `maintenance/repair-20260806/g3_preflight/g3_0a_usdc_activity.py` | 4,315 | 108 | `a8ea85ceea8e6f33` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 23 | `maintenance/repair-20260806/g3_preflight/g3_0b_pythia_gpa.json` | 5,120 | 131 | `faf8d902ee1aa1d5` | Y | Y | Y | N/A | Y | Y | [已知] 4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 24 | `maintenance/repair-20260806/g3_preflight/g3_0b_pythia_gpa.py` | 2,713 | 65 | `5b14d52917a15f44` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 25 | `maintenance/repair-20260806/g3_preflight/smoke-20260808/accounting_mode.json` | 1,216 | 41 | `5fa831ceac129b92` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 26 | `maintenance/repair-20260806/g3_preflight/smoke-20260808/solana_observation_bundle.json` | 4,903 | 143 | `1d606ec406a8eb31` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 27 | `maintenance/repair-20260806/g3_preflight/smoke-20260808/supply_truth.json` | 1,770 | 46 | `67767aa1b3f4c2f0` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 28 | `maintenance/repair-20260806/invariant-merge.md` | 9,007 | 97 | `dff02931fb4e900c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 29 | `maintenance/repair-20260806/ledger.md` | 90,675 | 687 | `c2de86a3c4195c24` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 30 | `maintenance/repair-20260806/reviews/batch1-review.md` | 23,495 | 240 | `f5edff2e2f9653d8` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 31 | `maintenance/repair-20260806/reviews/batch2-rereview.md` | 27,888 | 408 | `b94a58a77837d041` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 32 | `maintenance/repair-20260806/reviews/batch2-review.md` | 33,511 | 485 | `18f42de7db2dd987` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 33 | `maintenance/repair-20260806/reviews/batch2-review3.md` | 12,002 | 188 | `ebfe42c5e9582fae` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 34 | `maintenance/repair-20260806/reviews/batch3-rereview.md` | 18,609 | 282 | `9912422e4197e3f5` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 35 | `maintenance/repair-20260806/reviews/batch3-review.md` | 31,947 | 450 | `25cd22ffb712de5f` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 36 | `maintenance/repair-20260806/reviews/batch4-rereview.md` | 9,199 | 147 | `1275f9d0e43a68e5` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 37 | `maintenance/repair-20260806/reviews/batch4-review.md` | 22,632 | 307 | `3ce4eeeb3aeb04dc` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 38 | `maintenance/repair-20260806/reviews/r9-batch1-rereview.md` | 35,048 | 382 | `03957f5f0295e34a` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 39 | `maintenance/repair-20260806/reviews/r9-batch1-rereview2.md` | 24,340 | 213 | `5d92a798a34feb8b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 40 | `maintenance/repair-20260806/reviews/r9-batch1-review.md` | 36,607 | 367 | `da81e146e8c73cc8` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 41 | `maintenance/repair-20260806/reviews/r9-batch3-rereview-partial.md` | 4,703 | 54 | `b2ea0db2a57ff7ff` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 42 | `maintenance/repair-20260806/reviews/r9-batch3-rereview3-mutants.md` | 3,478 | 32 | `fce4c1257e741e96` | Y | Y | N/A | N/A | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 43 | `maintenance/repair-20260806/reviews/r9-batch3-review.md` | 23,524 | 274 | `933a55b19b382a6a` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 44 | `maintenance/repair-20260806/reviews/r9-batch4-rereview.md` | 9,678 | 85 | `c23039dc04e346c7` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 45 | `maintenance/repair-20260806/reviews/r9-batch4-rereview2.md` | 20,360 | 260 | `9cc177025bdb7f1b` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-10 |
| 46 | `maintenance/repair-20260806/reviews/r9-batch4-review.md` | 6,322 | 60 | `c2225937680cff73` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 47 | `maintenance/repair-20260806/robinhood-impact.md` | 8,328 | 115 | `dbf462b93b2ee9ab` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 48 | `maintenance/repair-20260806/sha_replay.py` | 5,050 | 114 | `00faea5effe16aeb` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 49 | `maintenance/repair-20260806/transport-injections.json` | 10,423 | 142 | `b72500565d5e8505` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 50 | `maintenance/repair-20260809-apu-legacy/WORKORDER_apu_legacy_gaps.md` | 7,519 | 99 | `80f8dd7254f3e79c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 51 | `maintenance/repair-20260809-apu-legacy/run_all_final.txt` | 9,734 | 95 | `885598887d3df09b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 52 | `maintenance/repair-20260809-supplytruth/WORKLOG_codex.md` | 2,341 | 13 | `f99c81146f39e337` | Y | Y | Y | N/A | Y | Y | [已知] 4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 53 | `maintenance/repair-20260809-supplytruth/WORKORDER_supplytruth.md` | 11,918 | 116 | `5783105c0b40426e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 54 | `maintenance/repair-20260809-supplytruth/acceptance_rerun_fable.txt` | 9,650 | 94 | `8af4fbcc8d103b91` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 55 | `maintenance/repair-20260809-supplytruth/red_phase.txt` | 6,671 | 131 | `932c6d1a57f98747` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 56 | `maintenance/repair-20260809-supplytruth/run_all_final.txt` | 9,650 | 94 | `8af4fbcc8d103b91` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 57 | `pyproject.toml` | 1,784 | 48 | `69041f2f2de037a9` | Y | N/A | Y | Y | Y | Y | [已知] 支撑 F-09；[已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。 |
| 58 | `references/address-book.md` | 72,734 | 238 | `2ceb66def647ce7c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 59 | `references/analysis-playbook.md` | 6,031 | 54 | `0ee07ee636347e65` | Y | Y | Y | N/A | Y | Y | [已知] 4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 60 | `references/analyze-workflow.md` | 24,674 | 168 | `088b355247e58bf4` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 61 | `references/attic.md` | 6,335 | 43 | `db42c08871f690c7` | Y | Y | Y | N/A | Y | Y | [已知] 4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 62 | `references/casebook/README.md` | 3,175 | 44 | `43c1135db8671aa7` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 63 | `references/casebook/cex-custody-methods.md` | 5,573 | 28 | `32b74409a6ac8bd9` | Y | Y | N/A | N/A | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 64 | `references/casebook/cex-custody.md` | 8,612 | 49 | `8f02ace907df71ac` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 65 | `references/casebook/entity-clustering-methods.md` | 20,728 | 88 | `d3cead0cb0c58e32` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 66 | `references/casebook/entity-clustering.md` | 13,935 | 112 | `2dff82ea4ea37e51` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 67 | `references/casebook/supply-accounting-methods.md` | 1,891 | 15 | `8e0e8921b6175a9d` | N/A | Y | N/A | N/A | Y | Y | [已知] 1：不承载关键字段、schema、来源或回执语义；仍做字节/结构/双向检查。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 68 | `references/casebook/supply-accounting.md` | 17,356 | 95 | `78661b47ddd7cbdc` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 69 | `references/context-discipline.md` | 6,661 | 45 | `753e254a51ccaac1` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 70 | `references/data-pipeline-evm-channels.md` | 45,445 | 301 | `b549440692bf1f49` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 71 | `references/data-pipeline-evm-recon.md` | 28,012 | 173 | `5468a62805416f37` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 72 | `references/data-pipeline-evm-sources.md` | 29,983 | 131 | `18594513328f2424` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 73 | `references/data-pipeline-evm.md` | 2,747 | 32 | `4f90e2b23622db2b` | Y | N/A | Y | N/A | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 74 | `references/data-pipeline-robinhood-channels.md` | 10,465 | 44 | `03d2ea615c7764e4` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 75 | `references/data-pipeline-robinhood-methods.md` | 8,420 | 27 | `2021dc72a2d9f116` | Y | N/A | Y | Y | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。 |
| 76 | `references/data-pipeline-robinhood-traps.md` | 20,580 | 63 | `53b13bf779a7af64` | Y | N/A | Y | N/A | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 77 | `references/data-pipeline-robinhood.md` | 3,023 | 26 | `2482fcbd2b02db6b` | N/A | N/A | N/A | Y | Y | Y | [已知] 1：不承载关键字段、schema、来源或回执语义；仍做字节/结构/双向检查。；2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 78 | `references/data-pipeline-solana-capture.md` | 30,160 | 204 | `f4e36791680093f4` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-06 |
| 79 | `references/data-pipeline-solana-scan.md` | 34,039 | 193 | `222a047a808f791f` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 80 | `references/data-pipeline-solana.md` | 3,136 | 34 | `c69e0c8e73662cee` | Y | N/A | N/A | N/A | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 81 | `references/economic-control-accounting.md` | 6,715 | 96 | `46eda5de8bb39892` | N/A | N/A | N/A | N/A | Y | N/A | [已知] 1：不承载关键字段、schema、来源或回执语义；仍做字节/结构/双向检查。；2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 82 | `references/environment.md` | 6,803 | 81 | `49e7b4c54a1c47ab` | Y | Y | Y | Y | Y | N/A | [已知] 6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 83 | `references/examples/lifecycle-flow-sample.png` | 234,681 | 0 | `31c2d5e1f2c0177e` | N/A | N/A | N/A | N/A | VISUAL | N/A | [已知] 1：不承载关键字段、schema、来源或回执语义；仍做字节/结构/双向检查。；2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；⑤：PNG 已视觉检查；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 84 | `references/independent-audit-protocol.md` | 13,126 | 166 | `e568700d3389a762` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 85 | `references/labels/MAINTENANCE.md` | 14,676 | 117 | `8d21f35701f04a03` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 86 | `references/labels/README.md` | 14,040 | 90 | `168608aced12067e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 87 | `references/labels/benchmark/goldset.csv` | 107,783 | 894 | `9237a17b7cc793e0` | Y | N/A | Y | Y | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。 |
| 88 | `references/labels/benchmark/result-2026-07-16.json` | 1,058 | 53 | `2b5be5b496a10563` | Y | N/A | N/A | N/A | Y | N/A | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 89 | `references/labels/benchmark/result-2026-07-17.json` | 1,496 | 73 | `afde6351eafe70c0` | Y | N/A | N/A | N/A | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 90 | `references/labels/benchmark/result-2026-07-18.json` | 1,496 | 73 | `9c9b88457f893f6e` | Y | N/A | N/A | N/A | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 91 | `references/labels/codehash-robinhood.csv` | 1,040 | 5 | `ff4f3c16974fed72` | Y | Y | Y | Y | Y | N/A | [已知] 6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 92 | `references/labels/labels-robinhood.csv` | 104,551 | 400 | `edd33770b8787642` | Y | N/A | Y | Y | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。 |
| 93 | `references/labels/manifest.json` | 1,251 | 45 | `6c05dd9146966a06` | Y | N/A | N/A | N/A | Y | N/A | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 94 | `references/labels/miss-queue/base.csv` | 16,214 | 111 | `bc1777748e50b953` | Y | N/A | N/A | N/A | Y | N/A | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 95 | `references/labels/miss-queue/bsc.csv` | 97,931 | 658 | `e1aa09c9406c16aa` | Y | N/A | N/A | N/A | Y | N/A | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 96 | `references/labels/miss-queue/eth.csv` | 72,240 | 462 | `936afefc7c827c0f` | Y | N/A | N/A | N/A | Y | N/A | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 97 | `references/labels/miss-queue/sol.csv` | 4,645 | 42 | `63c34624eb446d90` | Y | N/A | N/A | N/A | Y | N/A | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 98 | `references/lp-fee-accounting.md` | 8,143 | 154 | `eba4288905a6842c` | Y | N/A | Y | Y | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。 |
| 99 | `references/maintenance-review-repair.md` | 16,478 | 170 | `ca8ab56d40609ba8` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 100 | `references/monitoring-package.md` | 15,075 | 131 | `90891428b989bc0e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 101 | `references/playbook-entity-cluster-cost.md` | 6,696 | 33 | `73b30d013b1cca36` | Y | N/A | Y | N/A | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 102 | `references/playbook-entity-cluster-methods.md` | 48,026 | 260 | `1bf26a57a067ff00` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 103 | `references/playbook-entity-cluster-tiering.md` | 29,028 | 151 | `b863e3eb039ae5d9` | Y | N/A | Y | Y | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。 |
| 104 | `references/playbook-evidence-wording.md` | 20,158 | 125 | `ca8eeb75ed5012ea` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 105 | `references/playbook-state-anomaly.md` | 44,921 | 254 | `7993754db4fb127e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 106 | `references/playbook-supply-recon.md` | 19,691 | 136 | `d9ac11183a0b83da` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 107 | `references/report-template.md` | 38,921 | 295 | `a8d815dc5b5e670e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 108 | `references/research-workflows.md` | 23,276 | 185 | `236e2d7016d6c198` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 109 | `references/retrospective.md` | 18,114 | 142 | `69ba3b7448f40b9b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 110 | `references/scan-schemas.md` | 35,327 | 490 | `9371c9c9c36d413a` | Y | Y | Y | N/A | Y | Y | [已知] 4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 111 | `references/split-run.md` | 18,775 | 142 | `7334a0e7e8f9b9c3` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 112 | `requirements.lock` | 1,119 | 61 | `b098a367e4496226` | Y | N/A | N/A | N/A | Y | N/A | [已知] 支撑 F-09；[已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 113 | `scripts/bench/golden_baseline.py` | 5,457 | 134 | `edb7e5ff29f1bf5b` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 114 | `scripts/bench/scan_script_forks.py` | 7,156 | 147 | `bde941b7965e268a` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 115 | `scripts/evm/accounting_gate.py` | 25,483 | 527 | `38914a1ccc872f23` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 116 | `scripts/evm/analyze_holdings.py` | 13,711 | 256 | `62d4c5fc1c12affd` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 117 | `scripts/evm/cadence_fingerprint.py` | 13,995 | 263 | `212b9036b563a739` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 118 | `scripts/evm/cadence_rank.py` | 10,102 | 189 | `1c59f83e1ef44d90` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 119 | `scripts/evm/channels_preflight.py` | 22,922 | 429 | `992d9bc2201c672e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 120 | `scripts/evm/cluster.py` | 14,586 | 253 | `56bad823a8181f37` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 121 | `scripts/evm/cluster_prep_duck.py` | 10,979 | 190 | `20156d2a5b0d9a16` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 122 | `scripts/evm/cluster_sensitivity.py` | 29,309 | 574 | `e825b108bd959d1e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 123 | `scripts/evm/config.example.json` | 4,407 | 78 | `e92e65ac33c9f7b8` | Y | N/A | N/A | Y | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 124 | `scripts/evm/csv_collector_receipt.py` | 2,499 | 42 | `2cca90ee43a52394` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 125 | `scripts/evm/fetch_alchemy.py` | 7,130 | 137 | `bf8fa1f2e47e3d54` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 126 | `scripts/evm/fetch_bigquery.py` | 5,429 | 114 | `20bbc52479c5877e` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 127 | `scripts/evm/fetch_etherscan.py` | 3,540 | 78 | `c9042e30cb14c1d3` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 128 | `scripts/evm/fetch_gmgn.sh` | 2,641 | 64 | `7793c1cca67c9b41` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 129 | `scripts/evm/fetch_hypersync.py` | 12,333 | 239 | `d8113c590fe78e49` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 130 | `scripts/evm/fetch_hypersync_logs.py` | 6,394 | 140 | `629d183a7826c2ac` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 131 | `scripts/evm/fetch_hypersync_v2.py` | 20,791 | 436 | `d229a1c200554708` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-08 |
| 132 | `scripts/evm/fetch_pool_swaps.py` | 8,074 | 174 | `ff98d0465dc2cf8b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 133 | `scripts/evm/fetch_sqd_evm.py` | 5,732 | 129 | `042fe44eb1f8aea7` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 134 | `scripts/evm/lp_positions.py` | 10,493 | 209 | `534afc66a074e75e` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 135 | `scripts/evm/make_channel_receipt.py` | 4,426 | 120 | `d7aa3301b4e8f321` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 136 | `scripts/evm/multicall_balances.py` | 5,268 | 130 | `9a7a05785b347899` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 137 | `scripts/evm/peaks_daily.py` | 11,876 | 221 | `0a8ceb05548684a5` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 138 | `scripts/evm/pierce_stake.py` | 7,750 | 175 | `79aa51519c72e1f4` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 139 | `scripts/evm/prep_cluster_inputs.py` | 1,408 | 36 | `6aaeb53ce2c8dcce` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 140 | `scripts/evm/replay_duck.py` | 32,271 | 567 | `50def969eac162c1` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-02 |
| 141 | `scripts/evm/replay_pass1.py` | 8,471 | 165 | `2d4e3f2b51c15a6e` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-05 |
| 142 | `scripts/evm/replay_pass2.py` | 5,578 | 124 | `6928aadb794c558c` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-02,F-05 |
| 143 | `scripts/evm/replay_stream.py` | 13,363 | 257 | `70f42cb9e01d12bf` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 144 | `scripts/evm/scan_bloxroute_seg.py` | 5,115 | 114 | `8f32b95a055dc2cb` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 145 | `scripts/evm/scan_transfers.py` | 8,689 | 195 | `0b08dc4d130c6e99` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 146 | `scripts/evm/staged_capture.sh` | 2,614 | 55 | `2723504d7b9008eb` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 147 | `scripts/evm/transfers_lib.py` | 18,144 | 409 | `d130fe4be5f6eb2c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 148 | `scripts/evm/verify_recon.py` | 8,510 | 173 | `ca99e0181af104e1` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 149 | `scripts/hooks/guard_file_ops.py` | 3,068 | 79 | `830ee92d5ff1b5ea` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 150 | `scripts/labels/accumulate_offenders.py` | 19,664 | 335 | `9001e8e36cf636cd` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 151 | `scripts/labels/add_labels.py` | 10,531 | 232 | `a6f230bb92265a64` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 152 | `scripts/labels/benchmark_labels.py` | 7,052 | 145 | `8d0dc7d17acadf4a` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 153 | `scripts/labels/build_goldset.py` | 12,905 | 255 | `17466b7fc52421e5` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 154 | `scripts/labels/build_labels.py` | 39,265 | 653 | `4980a49a3969e821` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 155 | `scripts/labels/check_manual_sync.py` | 1,988 | 58 | `4d24ec59055bcc23` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 156 | `scripts/labels/dune_fetch_results.py` | 1,111 | 29 | `a4541963bae1aa12` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 157 | `scripts/labels/fingerprint_check.py` | 6,063 | 124 | `0fe510de21d1ef7f` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 158 | `scripts/labels/gatekeeper.py` | 7,630 | 173 | `5f7460e6550b6e36` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 159 | `scripts/labels/gen_manual_from_addressbook.py` | 4,882 | 125 | `bba7af2f679e008b` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 160 | `scripts/labels/goplus_check.py` | 4,777 | 107 | `50718264bfe61ef6` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 161 | `scripts/labels/label_lookup.py` | 11,546 | 218 | `99cbe81ef0975c53` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 162 | `scripts/labels/labels_resolver.py` | 22,187 | 440 | `c15d2a15ad81e4b0` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 163 | `scripts/labels/probe_codetype.py` | 3,698 | 86 | `cd15c01f498bfa5e` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 164 | `scripts/labels/pull_verified_contracts.py` | 4,341 | 111 | `20d13acbe5929244` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 165 | `scripts/labels/risk_flags.py` | 1,416 | 44 | `b5330dd275fb80ca` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 166 | `scripts/labels/roundtrip_check.py` | 8,743 | 181 | `671f5e1573644a19` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 167 | `scripts/labels/sourcify_check.py` | 4,951 | 124 | `75756faa0d7f1f68` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 168 | `scripts/labels/validate_labels.py` | 8,035 | 157 | `f66558b7dfc9d30b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 169 | `scripts/lib/anchor_plan.py` | 12,186 | 234 | `e5168a455d53bb51` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 170 | `scripts/lib/anchor_selection.py` | 15,428 | 324 | `fdc7af62143a4174` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 171 | `scripts/lib/artifact_quarantine.py` | 968 | 28 | `3d2ef1e4f03a49d6` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 172 | `scripts/lib/attestation_adapters.py` | 1,723 | 46 | `4c5af4b9f5e03c59` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 173 | `scripts/lib/chain_registry.py` | 11,691 | 326 | `8266ab2dbd75e144` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-10 |
| 174 | `scripts/lib/endpoint_identity.py` | 3,142 | 89 | `732958d865a67822` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 175 | `scripts/lib/formal_capability_probes.py` | 10,370 | 263 | `d22b1550ec999ec6` | Y | Y | N/A | Y | Y | Y | [已知] 支撑 F-10；[已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 176 | `scripts/lib/net.py` | 18,552 | 414 | `af9d7a94304282ef` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 177 | `scripts/lib/receipt_kernel.py` | 20,783 | 512 | `2b4b039c3610463c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 178 | `scripts/lib/receipt_validate.py` | 4,554 | 130 | `2fbe31e3facabc24` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 179 | `scripts/lib/rpc_batch.py` | 5,434 | 130 | `f993c16ea846945e` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 180 | `scripts/lib/solana_attested_session.py` | 5,574 | 150 | `59e24d67d90f2dba` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 181 | `scripts/lib/solana_observation.py` | 28,074 | 598 | `c0f38c0ef12c5c17` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 182 | `scripts/lib/solana_sqd_dataset.py` | 2,766 | 63 | `51bca2c79e1b5dea` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 183 | `scripts/lib/supply_semantics.py` | 819 | 18 | `dfef0925ae7d8bc1` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 184 | `scripts/lib/supply_truth_gate.py` | 17,609 | 347 | `24713f19e13d33f6` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 185 | `scripts/lib/time_spotcheck.py` | 21,687 | 415 | `23cf87e23f8c1856` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 186 | `scripts/prices/llama_price.py` | 5,918 | 153 | `a0f50dd5adb666f2` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 187 | `scripts/prices/price_check.py` | 9,768 | 199 | `45f7fb2c53350d41` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 188 | `scripts/proclock.py` | 6,788 | 156 | `c7b9b8e69215bc87` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 189 | `scripts/report/a4_gate.py` | 22,796 | 466 | `af6cb83a3692785b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 190 | `scripts/report/a5_report_seal.py` | 9,143 | 168 | `c6a2ff31d54b3e70` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-03 |
| 191 | `scripts/report/adjudication_validator.py` | 31,244 | 586 | `6d340b50ec84d3bd` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 192 | `scripts/report/adversarial_review_runner.py` | 5,311 | 133 | `c423e62a93922d4b` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-04 |
| 193 | `scripts/report/audit_release_gate.py` | 39,936 | 834 | `34bec1945c27e08e` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-04,F-10 |
| 194 | `scripts/report/build_html.py` | 29,237 | 554 | `87cd8e238592ca14` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 195 | `scripts/report/chart_style.py` | 2,250 | 45 | `b2ed3effc720e762` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 196 | `scripts/report/distribution_explanation_check.py` | 9,318 | 200 | `9f28d91275cd1e88` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 197 | `scripts/report/entity_identity_gate.py` | 19,499 | 398 | `fa864d0d78aa0f2e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 198 | `scripts/report/entity_source_trace.py` | 41,000 | 837 | `ee4243eaf597dc67` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 199 | `scripts/report/facts_gate.py` | 13,963 | 282 | `f58093f042d0f8fe` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 200 | `scripts/report/figures_from_facts.py` | 10,404 | 232 | `1e21d6b57dd929e3` | Y | Y | N/A | Y | Y | Y | [已知] 支撑 F-01,F-03；[已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 201 | `scripts/report/flow_anomaly_scan.py` | 23,833 | 418 | `7f13c4fd4cb027ee` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 202 | `scripts/report/handoff_manifest.py` | 59,109 | 1087 | `e24d4123cef0b955` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-10 |
| 203 | `scripts/report/holder_distribution_scan.py` | 45,689 | 923 | `a4d810f0411154d5` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 204 | `scripts/report/identity_snapshot_receipt.py` | 11,482 | 191 | `4a636a88811ad90b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 205 | `scripts/report/lifecycle_flow.py` | 12,276 | 228 | `493ae70caa6bb861` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 206 | `scripts/report/md2pdf.py` | 9,961 | 199 | `6f78e957383c23d5` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 207 | `scripts/report/migrate_legacy_case.py` | 7,848 | 193 | `01d73a0b1c06f8a4` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 208 | `scripts/report/reconciliation_report.py` | 12,650 | 301 | `c8b0b429252624c2` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 209 | `scripts/report/reproduce_receipt.py` | 6,057 | 146 | `753f3afac9324d9e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 210 | `scripts/report/retro_draft.py` | 5,895 | 114 | `ca1caa7b1b508b90` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 211 | `scripts/report/shared_release_receipt.py` | 18,480 | 374 | `f7031d3d9f715fe3` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-04,F-10 |
| 212 | `scripts/report/standard_charts.py` | 19,970 | 354 | `c8ffa96da8919d61` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-03 |
| 213 | `scripts/report/state_from_facts.py` | 5,893 | 133 | `e8a0667207ab4776` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-01 |
| 214 | `scripts/report/wave_scan.py` | 40,711 | 774 | `4d8f999406287c32` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 215 | `scripts/robinhood/amounts.py` | 670 | 18 | `c9c6d10b39affa23` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 216 | `scripts/robinhood/build_price.py` | 3,844 | 92 | `d93bf0f5a7f9e8fb` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 217 | `scripts/robinhood/config.example.json` | 3,074 | 46 | `1aa84661c4b7daa7` | Y | N/A | N/A | Y | Y | N/A | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 218 | `scripts/robinhood/cost_engine.py` | 4,794 | 95 | `7ad85a1baf9e38dd` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 219 | `scripts/robinhood/gas_trace.py` | 5,250 | 125 | `60859545aa234b4f` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 220 | `scripts/robinhood/gas_trace_bs.py` | 5,792 | 139 | `49c6b2628e533e1a` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 221 | `scripts/robinhood/merge_hs_rpc.py` | 3,881 | 110 | `6a3950c44ae4fc2f` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 222 | `scripts/robinhood/pull_block_ts_anchors.py` | 1,285 | 25 | `c13b15cb386c4368` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 223 | `scripts/robinhood/pull_lp_events.py` | 5,675 | 118 | `f82c4ffbcd0bf014` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 224 | `scripts/robinhood/pull_ohlcv.py` | 2,909 | 75 | `66fa6e950942eba6` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 225 | `scripts/robinhood/pull_swaps.py` | 4,840 | 120 | `5ecc0fc16ba30f6b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 226 | `scripts/robinhood/pull_swaps_v4.py` | 6,161 | 140 | `407133bca3c598a4` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 227 | `scripts/robinhood/pull_transfers.py` | 5,368 | 118 | `95fb216c98293ba0` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 228 | `scripts/robinhood/pull_transfers_rpc.py` | 3,103 | 63 | `51ca6fd4848bb970` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 229 | `scripts/robinhood/pull_weth_pool.py` | 3,122 | 67 | `8f9dddd926bdeff1` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 230 | `scripts/robinhood/resume_guard.py` | 2,238 | 58 | `2375138e386ebc33` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 231 | `scripts/run_guarded.py` | 9,080 | 181 | `a407b2344a677517` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 232 | `scripts/solana/README.md` | 2,855 | 32 | `06d896fed39207e7` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 233 | `scripts/solana/accounting_gate_sol.py` | 13,544 | 264 | `b84b6f7666823a58` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 234 | `scripts/solana/anchor_sampler.py` | 13,606 | 301 | `bde20f22ca190f24` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 235 | `scripts/solana/audit_closed_accounts.py` | 17,159 | 350 | `a438fc12213811c2` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-06 |
| 236 | `scripts/solana/build_evolution.py` | 10,248 | 211 | `700202fa87c239f0` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 237 | `scripts/solana/curve_cost.py` | 5,965 | 129 | `3749ad8458b7cbbb` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 238 | `scripts/solana/decode_txs.py` | 3,462 | 93 | `d15227be85193b43` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 239 | `scripts/solana/decode_txs_v2.py` | 16,962 | 412 | `fa5b3ef0e59a5769` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 240 | `scripts/solana/fast_probe_tops.py` | 6,089 | 145 | `8f426097d87b1b62` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 241 | `scripts/solana/fetch_pool_sigs.py` | 3,039 | 78 | `e79252dabd974aa3` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 242 | `scripts/solana/fetch_sqd_transfers_v2.py` | 59,442 | 1195 | `ee78b746a1c61048` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 243 | `scripts/solana/gas_origin.py` | 5,626 | 144 | `a862ec5b5139765f` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 244 | `scripts/solana/hypersync_recon.py` | 7,928 | 166 | `c045bf8bcb31aeb1` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 245 | `scripts/solana/probe_escrows.py` | 6,700 | 174 | `d781ac10efa62f0f` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 246 | `scripts/solana/probe_window_moves.py` | 7,615 | 167 | `9ffd167bde956e62` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 247 | `scripts/solana/replay_edges.py` | 16,491 | 376 | `244fb7d665c2d41a` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-02 |
| 248 | `scripts/solana/scan_sharded.py` | 6,074 | 150 | `37a2eb6fbc9295e6` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 249 | `scripts/solana/scan_token_accounts.py` | 15,442 | 316 | `8405225cf71cb952` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 250 | `scripts/solana/snapshot_diff.py` | 3,938 | 85 | `394801e25b2cab1a` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 251 | `scripts/solana/squads_members.py` | 6,631 | 153 | `90128bde1e325bb1` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 252 | `scripts/solana/stake_decode.py` | 7,328 | 177 | `737721f55843d70f` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 253 | `scripts/solana/trace_wallet.py` | 5,953 | 133 | `ed176d36c76598d6` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 254 | `scripts/solana/whale_deep.py` | 8,301 | 194 | `d428addd0d17c569` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 255 | `scripts/solana/window_fetch.py` | 10,846 | 256 | `fe3d767545227833` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 256 | `scripts/tests/casebook_lint.py` | 3,541 | 88 | `4d3fa8e54764bb08` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 257 | `scripts/tests/changelog_lint.py` | 3,485 | 79 | `ff426ca0beef2af9` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 258 | `scripts/tests/contract_ids_snapshot.json` | 2,488 | 141 | `c02cc10bc97327ac` | Y | N/A | N/A | N/A | Y | N/A | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。；3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。；4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。；6：不实现或声明门禁、发布、验证、回执或 readiness；无可绕闸对象。 |
| 259 | `scripts/tests/contract_manifest.json` | 20,631 | 144 | `6645b0b1c8426456` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 260 | `scripts/tests/docs_lint.py` | 22,703 | 443 | `39be88edfd067712` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 261 | `scripts/tests/env_check.py` | 2,138 | 55 | `88ee0954433ed7c1` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-09 |
| 262 | `scripts/tests/evm_channel_fixture.py` | 1,859 | 44 | `978119b5e4aaf865` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 263 | `scripts/tests/fixtures/pythia_anchors.json` | 7,291 | 78 | `55055a93269f5c79` | Y | Y | Y | N/A | Y | Y | [已知] 4：不属于生产调用、入口、路由或同族实现面；仍纳入全量账本。 |
| 264 | `scripts/tests/fixtures_lint.py` | 4,886 | 105 | `6ea338e9f0299465` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 265 | `scripts/tests/formal_ready_test_harness.py` | 2,749 | 72 | `27a1588937c07c73` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 266 | `scripts/tests/identity_gate_fixture.py` | 2,996 | 64 | `6dd5cf4d1cd13379` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 267 | `scripts/tests/invariant_manifest.json` | 23,116 | 944 | `e5edc66f8e214d5a` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 268 | `scripts/tests/invariant_scan.py` | 58,006 | 1378 | `48f075c29ad1b306` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-10 |
| 269 | `scripts/tests/labels_manifest.py` | 3,111 | 63 | `e476feb099a1cf7e` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 270 | `scripts/tests/run_all.py` | 5,009 | 113 | `5870d69b41327a7d` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 271 | `scripts/tests/runtime_docs_manifest.json` | 4,113 | 55 | `4d2b22d49fe24141` | Y | N/A | Y | Y | Y | Y | [已知] 2：不包含执行失败分支或状态转换；仍检查内容与引用。 |
| 272 | `scripts/tests/test_a4_gate.py` | 24,065 | 427 | `335dca133bb52340` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 273 | `scripts/tests/test_add_labels_rollback.py` | 6,580 | 130 | `9838064d41a601b7` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 274 | `scripts/tests/test_adjudication_validator.py` | 16,840 | 350 | `a0e4cb13c14ca65e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 275 | `scripts/tests/test_apu_legacy_gaps.py` | 20,263 | 400 | `9e092dae9db42d08` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 276 | `scripts/tests/test_audit_release_gate.py` | 31,990 | 617 | `69c4b657e56bdc42` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 277 | `scripts/tests/test_batch1_receipt_paths.py` | 5,345 | 148 | `404e332a04e0a99e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 278 | `scripts/tests/test_batch1_risk_flags.py` | 4,298 | 107 | `3075ebc169009758` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 279 | `scripts/tests/test_batch1_rpc_attestation.py` | 13,653 | 327 | `e93180407f80eeda` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 280 | `scripts/tests/test_batch2_capability_matrix.py` | 3,904 | 96 | `ebcd3d6342ad8492` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 281 | `scripts/tests/test_batch2_legacy_hardening.py` | 7,752 | 187 | `cdb6ed90d63e92c1` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 282 | `scripts/tests/test_batch2_p3_hardening.py` | 2,346 | 67 | `8761459b77831a61` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 283 | `scripts/tests/test_batch2_ready_reconciliation.py` | 903 | 27 | `4f74abc8cae2dc52` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 284 | `scripts/tests/test_batch2_registry_harness_hardening.py` | 4,741 | 128 | `4960a10fc1dab392` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 285 | `scripts/tests/test_batch2_robinhood_exploration.py` | 5,892 | 132 | `8ea28527a7efcb6d` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 286 | `scripts/tests/test_batch3_evm_vertical_slice.py` | 15,083 | 326 | `e8851480f8880a3a` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 287 | `scripts/tests/test_batch3_solana_producers.py` | 14,473 | 328 | `4e2536455c809d92` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 288 | `scripts/tests/test_batch3_solana_vertical_slice.py` | 11,888 | 246 | `fc4d3726390f342f` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 289 | `scripts/tests/test_batch4_invariant_guards.py` | 23,650 | 541 | `70b05c4329c0d7ef` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 290 | `scripts/tests/test_benchmark_labels.py` | 3,090 | 77 | `62a57ac93167cc01` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 291 | `scripts/tests/test_build_html.py` | 5,577 | 103 | `e2a52366b6db56ec` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 292 | `scripts/tests/test_chain_registry.py` | 5,831 | 121 | `eb8da61d2cc981a9` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 293 | `scripts/tests/test_chain_support_matrix.py` | 4,456 | 114 | `4eb359d766468dde` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 294 | `scripts/tests/test_cluster_quality.py` | 11,320 | 215 | `8fe4ba92e220fb1f` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 295 | `scripts/tests/test_commands_deploy_sync.py` | 3,212 | 93 | `d6cb6e405d2ba975` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-07 |
| 296 | `scripts/tests/test_contract_routes.py` | 8,458 | 186 | `a0697ac1db0afcb4` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 297 | `scripts/tests/test_distribution_gate.py` | 26,863 | 425 | `9c74d226d5b62592` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 298 | `scripts/tests/test_engine_equivalence.py` | 5,812 | 123 | `a2bc29c22bf88ad6` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 299 | `scripts/tests/test_entity_identity_gate.py` | 2,763 | 73 | `49502e8359dc3e3c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 300 | `scripts/tests/test_entity_source_trace.py` | 12,763 | 248 | `e10901b052b856d2` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 301 | `scripts/tests/test_exemption_guards.py` | 3,974 | 100 | `2ad6c3a571f23835` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 302 | `scripts/tests/test_fault_injection.py` | 11,929 | 242 | `27427aeaecf7df90` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 303 | `scripts/tests/test_fetch_failclosed.py` | 9,320 | 216 | `bf96ed91ec989359` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 304 | `scripts/tests/test_fetch_gmgn_sh.py` | 3,104 | 77 | `2268e8a47abb6320` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 305 | `scripts/tests/test_figures_from_facts.py` | 5,180 | 116 | `aa1a8c904328adb5` | Y | Y | N/A | Y | Y | Y | [已知] 支撑 F-01,F-03；[已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 306 | `scripts/tests/test_flow_anomaly.py` | 15,334 | 291 | `b32c9648a1dc07fd` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 307 | `scripts/tests/test_formal_chain_support.py` | 4,116 | 97 | `2538901ca35c9771` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 308 | `scripts/tests/test_handoff_manifest.py` | 38,649 | 669 | `ea0562c6bf6776fa` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 309 | `scripts/tests/test_labels_resolver_guards.py` | 1,099 | 38 | `6db978c59ffefe88` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 310 | `scripts/tests/test_net_result.py` | 1,862 | 55 | `1ab20226acbac238` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 311 | `scripts/tests/test_param_scripts.py` | 3,697 | 95 | `9a405c05020bff02` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 312 | `scripts/tests/test_peaks_daily.py` | 6,172 | 149 | `d7a5cbe905f3a339` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 313 | `scripts/tests/test_r7_findings.py` | 23,378 | 508 | `1526aaf807a6c529` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 314 | `scripts/tests/test_r9_batch1_boundaries.py` | 15,159 | 373 | `068de96919b873ee` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 315 | `scripts/tests/test_r9_batch2_attestation_adapters.py` | 3,573 | 100 | `38fc8c3648a9b8cf` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 316 | `scripts/tests/test_r9_batch2_executable_capabilities.py` | 5,684 | 142 | `0021524a8133fbf0` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 317 | `scripts/tests/test_r9_batch2_solana_sqd_adapter.py` | 4,122 | 122 | `cee06bcfff5d39d8` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 318 | `scripts/tests/test_r9_batch3_dynamic_runner.py` | 3,560 | 88 | `6e65f08260dace69` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 319 | `scripts/tests/test_r9_batch3_preflight.py` | 2,945 | 77 | `f407c1d10713c678` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 320 | `scripts/tests/test_r9_batch3_release_guards.py` | 7,468 | 195 | `d02311021242878f` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 321 | `scripts/tests/test_r9_batch3_solana_observation.py` | 25,036 | 617 | `b167e8df3e586530` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 322 | `scripts/tests/test_r9_solana_attested_session.py` | 9,508 | 263 | `fad8d94c0d028c34` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 323 | `scripts/tests/test_receipt_kernel.py` | 10,177 | 239 | `9fb6a7296c73f027` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 324 | `scripts/tests/test_reconciliation_runner.py` | 6,695 | 187 | `05ccbfe9a1c1499c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 325 | `scripts/tests/test_report_facts.py` | 5,555 | 122 | `e1bbced3f321b9ec` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 326 | `scripts/tests/test_review_20260804_p0.py` | 8,393 | 207 | `096c0f9292703096` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 327 | `scripts/tests/test_review_20260804_p101.py` | 3,171 | 88 | `de63967ff91fa054` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 328 | `scripts/tests/test_review_20260804_p104.py` | 2,649 | 66 | `21b8a6e1d0040467` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 329 | `scripts/tests/test_review_20260804_p105.py` | 4,688 | 99 | `66d65afddebabf2c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 330 | `scripts/tests/test_review_20260804_p106.py` | 3,079 | 82 | `72e11ce33b8f2501` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 331 | `scripts/tests/test_review_20260804_p201.py` | 2,748 | 72 | `157c2af6aac46777` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 332 | `scripts/tests/test_review_20260804_p202.py` | 2,194 | 58 | `adafcbae70abfe88` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 333 | `scripts/tests/test_review_chain_collectors.py` | 1,392 | 48 | `d7e32c337c2432d7` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 334 | `scripts/tests/test_review_evm_integrity.py` | 4,273 | 107 | `63c85101f6625041` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 335 | `scripts/tests/test_review_labels.py` | 1,475 | 37 | `34f7ea46e49e4bb9` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 336 | `scripts/tests/test_review_resume_integrity.py` | 11,035 | 263 | `12778d9395524f3c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 337 | `scripts/tests/test_review_robinhood_integrity.py` | 1,794 | 53 | `75674e1fdf39845e` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 338 | `scripts/tests/test_review_scale_guards.py` | 3,438 | 92 | `6f107ee2e183d454` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 339 | `scripts/tests/test_review_solana_integrity.py` | 6,580 | 151 | `4ea9ac3355195f42` | Y | Y | N/A | Y | Y | Y | [已知] 3：不定义版本/schema/旧产物兼容或迁移；无可迁移对象。 |
| 340 | `scripts/tests/test_round4_a5_seal.py` | 2,424 | 57 | `ed936bf02f885c55` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 341 | `scripts/tests/test_round4_csv_adapters.py` | 1,518 | 32 | `68a81d853137aa04` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 342 | `scripts/tests/test_round4_identity_emitter.py` | 4,000 | 61 | `88c1674787c23fb9` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 343 | `scripts/tests/test_round4b_provenance.py` | 5,848 | 132 | `d1e12282f8cf6cf9` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 344 | `scripts/tests/test_round4c_solana_provenance.py` | 6,703 | 150 | `750d440545f1463b` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 345 | `scripts/tests/test_roundtrip_check.py` | 5,468 | 128 | `d954f2ab93229426` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 346 | `scripts/tests/test_sixlens_docs.py` | 5,399 | 103 | `749bd1fd7311d076` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 347 | `scripts/tests/test_sixlens_receipts.py` | 13,337 | 282 | `1eb60ca8b7a14ee4` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 348 | `scripts/tests/test_sqd_merge_equiv.py` | 10,548 | 243 | `88c949006ccde7fc` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 349 | `scripts/tests/test_state_from_facts.py` | 1,893 | 51 | `e762225438369ecb` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-01 |
| 350 | `scripts/tests/test_supply_truth_gate.py` | 11,539 | 272 | `c0818b3a98423798` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 351 | `scripts/tests/test_time_spotcheck.py` | 16,728 | 335 | `7986ca7bdbbc341a` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 352 | `scripts/tests/test_token_no_positional.py` | 2,581 | 62 | `4e548d9d77a9e89d` | Y | Y | Y | Y | Y | Y | [已知] 支撑 F-08 |
| 353 | `scripts/tests/test_version_consistency.py` | 1,217 | 30 | `ab7c81c054a2c6a4` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |
| 354 | `scripts/tests/test_wave_scan.py` | 10,448 | 203 | `7b1ca665bf1cc67c` | Y | Y | Y | Y | Y | Y | [计算得到] 已读/已查，无独立 finding |

## 附录 B：可复现证据文件

[已知] 证据包包含：完整报告、354 文件 SHA 账本、归档安全检查、结构/门禁验证日志、11 项反例源码与输出、inventory 和 package SHA。

[RULES I BROKE]: 无
