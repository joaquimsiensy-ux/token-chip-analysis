# 修复方案(plan)v2:溯源守恒改整数精确算术,撤销 7.0.3 尘埃豁免(7.0.3 → 7.1.0)

状态:**v2 = Fable 设计 + codex 只读复核融合,待用户审批**。未审批前不得施工。
基线:`main = 3b29e38`(7.0.3 + 平台件并入);逻辑基线按 **7.0.2 = 261d4e2**(见 §2 回退)。
复核记录:codex 复核原文 `cx_review_v1.txt`(本目录);融合裁决见 §10。标 **[CX]** 的条目来自 codex 复核并经 Fable 核实采纳;标 **[CX-驳]** 的是核实后不采纳或缩限的。

## 0. 一句话结论(大白话)

溯源脚本把每笔转账金额转成"浮点数"来记账,而这个币的总量是 4.2×10^29 这种天文数字,浮点数只能记住前 16 位,后面全是噪声。7.0.3 的做法是"库存小到没意义时就不检查了",这是治标。本单改成用 Python 的大整数记账,一个单位都不丢,守恒检查从"差不多等于 100%"变成"必须一个单位都不差",然后把 7.0.3 加的豁免和两个标记全部删掉。

codex 复核补了一句更准的目标 **[CX]**:"总量守恒、来源分配准确、输入数据完整"是三个不同的问题。本单**只承诺第一个**(总量守恒精确)并把第二个的偏差界定清楚(§3.2b),第三个(数据缺口)只保证"如实显现、不再被噪声冒充",不承诺归零。

## 1. 问题定性(为什么必须重修,不能在 7.0.3 上补)

同一根因,两个症状,7.0.3 只治了一个:

| 症状 | 表现(APU 0914 案实测) | 7.0.3 处理 |
|---|---|---|
| A. 尘埃现存锚点不闭合 | TE-02 现存 9.66e12 raw(占供应 2.3e-15%)构成为空 Σ=0%;TE-04 现存 7.67e9 raw 构成合计 4.45e12,Σ=57,980% | 豁免不拒,打两个标记 |
| B. 假"数据缺失" | 105 个实体里 91 个带 `data_gap_events>0`,构成里 105 条 `data_gap` 条目,raw 全部 ≤4.8e11,pct 全部 0.0;TE-02 一个实体记了 4,000 次 | 未处理 |

根因(`scripts/report/entity_source_trace.py`,行号按 7.0.2 内容):
- `simulate()` 第 455/457/459/463 行:`float(amt)`,把 1e29 量级整数塞进 float64(有效数字约 16 位,单步绝对误差约 1e13)。
- `VectorAccount.take` 第 262–276 行、`LayeredAccount` 第 286–326 行:按比例扣减全在 float 里做;层内构成归一化成 float 比例。
- `EPS = 1e-6`(第 89 行)是**绝对**阈值:`shortfall > EPS` 在 1e13 噪声面前必然触发 → 症状 B;`amt <= EPS` 截断 → 微小真实来源被吃掉。
- 闭合检查 `abs(s - 100.0) > 0.5`(第 806 行)与 freeze 端 `abs(s_raw - stock) > stock * 0.005`(`handoff_manifest.py` 第 1142、~1536 行)是为容忍浮点噪声而设的 0.5% 容差,容差本身就是根因的遮羞布。
- **[CX]** 顺带暴露的既有缺陷:`build_anchor` 第 608–610 行把 `stock <= 0` 一律输出成 `stock_raw="0"、composition=[]`,即使模拟快照非零;`combined_series`(第 511 行)按净流量算余额可为负。这意味着"零库存"锚点从未被检查过守恒,负库存(=数据缺失)被静默清零。本单一并关闭。

上游精度前提(Fable 核实):EVM `evm_v2` 路径由 `wave_scan.load_evm_v2` 把 hex 两段拼成 HUGEINT(第 222–230 行),**全程整数,精度完好**;APU 案 `logs.parquet` 的 `data` 列是十六进制字符串。`--duckdb` 分支(第 301 行)只 `CAST(amt AS HUGEINT)`,若上游已是 DOUBLE 则低位早已丢失 → §3.10 加类型闸 **[CX]**。

为什么 7.0.3 不能留:①它把"来源不可用"当成合法状态写进账本 schema,消费方以后都要学会认这个标记;②症状 B 仍在,复核人会把 4,000 次"数据缺失"当真;③闸门逻辑里多了一条"有条件不检查",与 skill"验自洽≠验真实、门禁必经"的原则相悖。

## 2. 回退策略

- `git revert f0036f8`(**不是** reset,历史保留),单独一个提交,提交信息注明"7.0.3 撤销,原因见本单 §1"。
- **[CX]** 验收条件改正:回退**前** `git diff 261d4e2 HEAD -- <五文件>` 须恰等于 f0036f8 的补丁(用 `git diff 261d4e2 f0036f8 -- <五文件>` 比对字节相同);回退**后**、整数化之前,五文件(`entity_source_trace.py`、`handoff_manifest.py`、`test_entity_source_trace.py`、`test_handoff_manifest.py`、`references/scan-schemas.md`)与 261d4e2 逐字一致(`git diff 261d4e2 HEAD -- <五文件>` 为空)。
- **[CX]** revert 会把 `CHANGELOG.md` 的 7.0.3 索引行一并删掉;在 7.1.0 提交里**重新写回**该行并追加"(已被 7.1.0 撤销,见 7.1.0 条目)"。`VERSION`/`SKILL.md`/`pyproject.toml` 随 revert 回 7.0.2 只是过渡态,不单独发布。
- 版本号定 **7.1.0**。理由 **[CX 修正措辞]**:这是一次算法数值域、账本 schema、守恒语义三项同时变化并带迁移义务的升级,值得独立版号便于运维识别;**版本号本身不作兼容性承诺**,不兼容面与迁移要求写在 CHANGELOG 与 §7。
- `agents/openai.yaml`(3b29e38 并入)不受影响。

## 3. 设计(施工方逐条实现,不得扩改)

### 3.1 数值域:整数贯穿
- `simulate()`:`float(amt)` 四处改 `int(amt)`;`comp`/`shortfall` 全部 int;`ORDER_AMBIGUOUS_KEY` 桶 int。
- 删除 `EPS` 常量及其全部引用;`top_entry`/`policy_detail`/`comp_to_list` 的 `> EPS`/`<= EPS` 改 `> 0`/`<= 0`。
- **[CX]** 逐一清除 `0.0` 累加种子,防止"整数加浮点又变回 float":第 260 行(`self.vec.get(k, 0.0)`)、第 306 行(`comp.get(k, 0.0)`)、第 325 行(`out.get(k, 0.0)`)、第 467 行(`comp.get(gap_key, 0.0)`)、第 635 行(`float(...)` → `int(...)`)。施工后 `grep -n "0\.0\|float(" entity_source_trace.py` 只允许出现在展示/百分比计算处,逐行说明。
- **[CX]** 输入契约:进入账户的金额必须是 `int` 且 `>= 0`;`take(0)` 返回 `({}, 0)`;负数请求 `raise ValueError`(实现缺陷,不得静默)。不得用 `int(float_value)` "纠正"输入。

### 3.2 确定性整数按比例分配(新增纯函数,两账户共用)
```
def split_proportional(vec: dict[TerminalKey, int], amt: int) -> dict[TerminalKey, int]
```
- 前置:`0 < amt < avail = Σvec`,所有 v ≥ 0(前置不满足 → 调用方分支处理,不进本函数)。
- 每键 `q_k, r_k = divmod(v_k * amt, avail)` **[CX]**;余数 `R = amt − Σq_k`(0 ≤ R < 非零键数)。
- 把 `+1` 分给 `r_k` 最大的前 R 个键,并列按 `str(key)` 升序。**[CX]** key 的类型契约收紧为现有终点键 `(kind:str, sub:str, via:str|None)` 三元组(字符串表示唯一),函数 docstring 明示,不宣称支持任意 key。
- **[CX]** 快路径:`R == 0`、单键、整取尽时直接返回,不排序。
- 后置(断言):`Σ结果 == amt`;每份 `0 ≤ part_k ≤ v_k`;仅当 `v_k > 0` 才可能 `part_k > 0`;同输入两次结果字节级相同。
- 分配后清理零值键(**[CX]** 但不得过滤负值来修饰异常,负值即断言失败)。
- 每个层/账户/快照的字典必须独立持有(**[CX]** 禁止多处共用可变字典)。

### 3.2b 取整偏差的界与它对"翻转"判定的影响 **[CX 反例成立,Fable 给出界与处置]**
- codex 反例(已复算成立):账户 A=4、B=2,连续三次各支出 1,整数 pro-rata 得 A=1/B=2,而 FIFO/LIFO 得 A=2/B=1 → 第一大来源翻转,纯粹由逐次取整造成。
- 界:`split_proportional` 每次每键偏离理想值 <1 raw,n 次分配后任一键累计偏差 < n raw;n ≤ 该实体子图边数。APU 最大子图 576,315 边,偏差 < 5.8e5 raw/键;而非尘埃锚点库存 ≥ 0.01% 供应(APU 为 4.2e25 raw)。要让 top-1/top-2 因此互换,二者真实份额差须 < 1e-19 相对,这本质是并列。
- 处置:**不引入** Fraction/余数结转/浮点 EPS(**[CX-驳]** codex 提到的"误差界、余数结转"机制不做,复杂度与确定性代价不值);**接受**尘埃锚点上的这类翻转作为"保守阻断"——但尘埃锚点本来就在稳定性判定中豁免(`negligible`,第 622 行),所以对结论零影响;非尘埃锚点由上面的界保证不受影响。
- 落地:①`entity_source_trace.py` 在 `sens` 段注释写明此界;②测试 T3b 把 codex 反例作为固定用例:总供应设大(反例锚点为尘埃)→ `exit 0` 且 `negligible_stock=true`;总供应设 6(非尘埃)→ 三策略 top 不一致 → `stable=false`、`exit 2`,文案含"整数分配模型差异或真实策略翻转";③文档 scan-schemas.md 追加一句"整数分配偏差 <n raw/键,尘埃锚点不承载翻转结论"。

### 3.3 `VectorAccount`(pro-rata)整数化
- `add`:`v > 0` 的 int 累加。
- `take(amt)`:`amt == 0` → `({}, 0)`;`avail = Σvec`;`avail == 0` → `({}, amt)`;`amt >= avail` → 取全部,shortfall `amt − avail`;否则 `part = split_proportional(vec, amt)`,`vec[k] −= part[k]`,shortfall 0。
- 不变量(测试断言,**[CX]** 用独立维护的参考余额比,不与同路径更新的量互证):任意时刻 `Σvec == 参考余额`。

### 3.4 `LayeredAccount`(FIFO/LIFO)整数化
- 层 = `(amount:int, comp:dict[key,int])`,**`Σcomp == amount`,不再归一化为 float 比例**。
- `add(comp)`:`s = Σ(v>0)`,`s == 0` 不建层;comp 拷贝后持有。
- `take(need)`:`need == 0` → 空;按端序取层;`use = min(la, need)`;`use == la` 整层取走;否则 `taken = split_proportional(comp, use)`,层更新为 `(la − use, comp − taken)`(逐键相减,断言结果 ≥0 且 Σ == la − use)。
- `snapshot`:逐层 comp 累加(全 int),返回新字典。
- **[CX]** "每次误差 ≤1 raw/键"只对**当次分配**成立,不得在文档里扩写成"整段历史来源误差 ≤1 raw";历史累计界见 §3.2b。

### 3.5 `comp_to_list` / `policy_detail` / `top_entry`
- 过滤条件 `amt <= 0` 才跳过;`raw = str(amt)`(已 int);`pct_of_anchor = round(amt * 100.0 / stock, 4)` 仅展示。
- 排序键统一 `(-amt, str(key))`。
- **[CX]** 显示百分比逐项四舍五入后合计可能是 99.9999%,这是展示舍入;**数量门禁一律以 raw 判定**,`*_sum_pct` 不再参与任何拒收判断。

### 3.6 trace 端闭合与库存符号门禁(第 ~800–815 行 + `build_anchor` 第 604–612 行)
- **[CX]** 负库存:`combined_series` 任一锚点 `stock < 0` → `exit 2`,文案"实体历史负余额=期初余额缺失或数据缺口,禁止清零";**不再**把负数输出成 0。
- **[CX]** 零库存:`stock == 0` 时仍须检查三策略快照 `Σvec == 0`,否则 `exit 2`(模拟残留非零而余额为零=实现或数据不一致);输出保持 `stock_raw="0"、composition=[]`。
- 正库存:`closure_check` 新增 `current_sum_raw` / `peak_sum_raw`(str int);判据 **`Σraw == stock_raw` 精确相等**;**[CX]** 三策略都查(`policy_details` 每策略 Σraw == stock),不只查序列化的 pro-rata;任一不等即 `exit 2`,文案"守恒被破坏(实现缺陷或数据缺口)"。
- 删除 7.0.3 的 `dust_current`/`current_negligible_skipped`/`composition_usable`/`continue`(revert 后自然不存在,施工方**禁止**重新引入任何"有条件跳过闭合"的分支)。
- 尘埃锚点在 `sens` 稳定性判定里的 `negligible` 豁免**保留不动**(那是"构成排序不承载结论",与守恒无关;见 §3.2b)。

### 3.7 freeze 端(`handoff_manifest.py`,7.0.2 内容为基线)
- 第 ~1536 行 `abs(s_raw − stock) > stock * 0.005` → `s_raw != stock`;文案去掉"0.5%"。
- **[CX]** 第 1120–1143 行**调整顺序**:现在是"零库存跳过 → 尘埃跳过 → 才查三策略明细齐全与闭合",导致尘埃锚点的明细守恒从未被查。改为:①结构与整数合法性(raw 为非负整数字符串)→ ②三策略明细 `Σraw == stock` 精确(**所有** `stock > 0` 的锚点,含尘埃)→ ③零库存要求三策略明细为空或 Σ==0 → ④之后才对尘埃锚点跳过**稳定性裁决**(第 1123 行的 `continue` 只跳 top 比较,不跳守恒)。
- 不新增任何供应量分母解析、不新增任何豁免路径(7.0.3 的 `den`/`dust_current` 段随 revert 消失,禁止重写)。
- `validate_and_replay_provenance` 用当前代码真实重放并比语义 sha 的机制不动;第 1176–1182 行算法哈希检查不动(它已保证旧账本必重跑,v3 是把契约写明,不是唯一重跑机制 **[CX]**)。

### 3.8 schema 升版与消费方(**[CX]** 清单经 Fable grep 核实)
- `SCHEMA = "provenance-ledger/v3"`(trace 第 79 行、docstring 第 2 行)、`PROVENANCE_SCHEMA = "provenance-ledger/v3"`(freeze 第 65 行),注释写明"v1 = pro-rata 数学错误版,v2 = 浮点账户版(尘埃锚点不守恒、假 data_gap),v3 = 整数精确守恒;v1/v2 一律拒"。
- 消费方逐项(**不是**"只改常量"——每处须确认其校验逻辑在 v3 下仍成立 **[CX]**):
  - `scripts/report/a5_report_seal.py:203` 硬编码只收 v2 → 改 v3(不改则 A5 拒收所有新账本)。
  - `scripts/tests/test_handoff_manifest.py:238` fixture 默认 schema → v3;第 261 行覆盖真实生成结果的路径核对。
  - `scripts/tests/test_repair_batch_d.py:1290` 手工 fixture → v3。
  - `scripts/tests/contract_manifest.json:52` `CT-WAVE-26` needle → `provenance-ledger/v3`(**[CX]** 若文档保留 v2 历史说明,旧 needle 会继续命中却没验新契约,所以 needle 必须改)。
  - `scripts/tests/invariant_manifest.json:173/430/496` 生产者/消费方登记同步。
  - `references/split-run.md:95`、`references/scan-schemas.md:5/217/246` 文案。
- `references/scan-schemas.md` §4:删 7.0.3 段(随 revert);"v2 算法冻结"段改"v3 算法冻结",追加:整数精确守恒、`closure_check.*_sum_raw` 精确等于 `stock_raw`、无容差、负库存拒、零库存验快照、整数分配偏差界(§3.2b)。
- **[CX]** 单搜 schema 字符串会漏掉的隐式依赖(不改代码,但 §7 迁移必须覆盖):翻转裁决收据指纹(`flip_fingerprint` 第 858–864 行对三策略明细取哈希,raw 变即失效)、A4 封口文件哈希(`a4_gate.py` 第 386–401 行)、final distribution 绑 freeze(`holder_distribution_scan.py` 第 672–695 行)、A5 绑 ledger/freeze(`a5_report_seal.py` 第 194–207 行)。

### 3.9 性能预算
- **[CX 更正]** 10^29 ≈ 2^97,Python 整数按 30 位肢需 4 肢(不是 2),乘积更大;成本还包括每次部分取出的 divmod、字典分配、排序,乘三策略、乘实体数;账本终点 ≤57 不代表中间账户也 ≤57。
- 施工方须在 APU 0914 案(隔离副本,见 T6)上分别记录 7.0.2 与 7.1.0 的 trace **加载、模拟、总墙钟与内存峰值**;7.0.2 若因尘埃闭合 `exit 2` 提前结束须注明,不得拿提前结束的运行直接比。
- 目标 **≤2×**(验收目标,不是已证明的预期);超出先上报不得自行优化。允许的既定优化仅 §3.2 快路径与零值清理。

### 3.10 输入类型闸 **[CX]**
- `wave_scan.py` `--duckdb` 分支(第 274–301 行)`CAST(amt AS HUGEINT)` 之前,`DESCRIBE` 检查 `amt` 列类型必须是整数族(`HUGEINT/UHUGEINT/BIGINT/UBIGINT/INTEGER/DECIMAL(*,0)`),否则 `exit 2` 文案"amt 列为 {type},非精确整数,拒绝转换后宣称精确";`evm_v2` 路径(hex→HUGEINT)已精确,只加一行注释。
- HUGEINT 上限 ≈1.7e38,APU 量级 1e29 安全;超限由 DuckDB 抛错即可,不另加逻辑。

## 4. 测试计划(先红后绿;RED 证据按既有格式)

删除 7.0.3 的 8 组 dust 测试(随 revert),替换为:

- **T1 精度用例**:沿 7.0.3 的 2^90 边表(H 进、H−1 出两跳,可选再进 1):7.1.0 须 `exit 0`,`current_sum_raw == stock_raw`(1 或 2)精确,构成 raw 精确 `["1"]`/`["2"]`,无 `data_gap` 条目,无 `current_negligible_skipped`/`composition_usable` 字段。
- **T2 缺口与负余额(**[CX]** 拆三例)**:
  - T2a 上游缺库存:X 空账户 → X→实体 100 → 实体 `data_gap` raw 精确 == 100,两锚点精确闭合,`exit 0`。
  - T2b 实体自身先支出后收款(先出 100 再入 50,净 −50):`exit 2`,文案含"负余额";**不**输出零库存账本。
  - T2c 实体先出 100 后入 150(净 +50 但来源账户 150):`exit 2`(Σraw 150 ≠ stock 50),证明整数化不掩盖此类不一致。
- **T3 守恒模糊测试**(单元级,直接 import 两账户类 + `split_proportional`):固定 seed,1,000 次随机 add/take,金额混合 1、1e29、随机;每步断言 `Σvec == 独立参考余额`(Vector)与 `Σ各层comp == Σamount == 参考余额`(Layered);`split_proportional` 断言 Σ==amt、每份∈[0,v_k]、**[CX]** 与实数比例的偏差用整数交叉相乘验证 `|part_k·avail − v_k·amt| < avail`(oracle 不用 float)、同输入两次字节级相同、键插入顺序打乱后结果相同、零请求、负数请求抛错、快照与层字典无别名(修改快照不影响账户)。
- **T3b 取整偏差与翻转(§3.2b)**:codex 反例两态(尘埃 → `exit 0`/`negligible_stock=true`;非尘埃 → `exit 2`);另一例:非尘埃锚点、两来源份额差 > 边数 raw → 三策略 top 一致(界成立)。
- **T4 尘埃现存(TE-02 型)**:周转 1e29 进出后残留 1e12 级 → 精确闭合、`exit 0`、反向断言 7.0.3 字段不存在。
- **T5 freeze 精确性**:精确闭合放行;账本某条 raw ±1 → 拒,**[CX]** 且断言 stderr 命中"闭合重算失败"文案(而非重放摘要不符);policy_details ±1 → 拒且文案命中"明细不闭合";尘埃锚点明细 ±1 → 拒(证明 §3.7 顺序改对);零库存但明细非空 → 拒;schema 写 v2 → 拒。
- **T6 APU 真实回归**(离线、本机数据、只记数字不记结论):**[CX]** 在保持案根布局(manifest、data_map、`data/v2`、收据)的**隔离副本**里跑 7.1.0 trace(trace 用 `--out` 父目录当案根,第 728 行;直接写临时目录会丢冻结边界),核对生效 cutoff/block/边数与 7.0.3 运行一致;对比 7.0.3 账本:按终点键对齐,分别比较 raw、未舍入比例、显示值;记录 105 实体 top 是否一致与 `data_gap` 条目变化——**两者都是待验证结果而非预设的通过条件** **[CX]**;若 data_gap 非 0,逐条列 raw 与来源实体,判定属 T2a 型真缺口还是异常。结果表落本目录 `apu_regression.md`。
- **T7 版本一致性**:`VERSION`、`pyproject.toml`、`SKILL.md` 版本注释、`CHANGELOG.md` 索引行**和详细段**五处 7.1.0;`test_version_consistency.py` 绿(7.0.3 就是漏了 pyproject 与详细段才红的)。
- **T8 输入类型闸**:`--duckdb` 表 amt 为 DOUBLE → `exit 2`;为 HUGEINT → 通过。
- **T9 全套**:`run_all.py` 全绿,SUITE 数按实际登记(测试文件增删须同步 run_all 与 `invariant_manifest.json`)。

## 5. 文档与登记面
- `CHANGELOG.md`:7.1.0 六栏(出处与根因/设计与实现/消费面与防回流/测试/盲审与验收/成本-质量指标);出处只写"APU 案触发的工具故障",禁写任何代币结论;7.0.3 索引行写回并加撤销注(§2)。
- `entity_source_trace.py` 模块 docstring 与 `handoff_manifest.py` 第 65 行注释同步 v3。
- `references/scan-schemas.md`、`references/split-run.md` 见 §3.8。
- 白名单(超出即违规):`scripts/report/entity_source_trace.py`、`scripts/report/handoff_manifest.py`、`scripts/report/a5_report_seal.py`(仅 :203 常量)、`scripts/report/wave_scan.py`(仅 §3.10 类型闸)、`scripts/tests/test_entity_source_trace.py`、`scripts/tests/test_handoff_manifest.py`、`scripts/tests/test_repair_batch_d.py`(仅 :1290 常量)、`scripts/tests/test_wave_scan.py`(仅 T8)、`scripts/tests/run_all.py`(仅 SUITE)、`scripts/tests/invariant_manifest.json`、`scripts/tests/contract_manifest.json`(仅 CT-WAVE-26 needle)、`references/scan-schemas.md`、`references/split-run.md`、`CHANGELOG.md`、`VERSION`、`pyproject.toml`、`SKILL.md`(仅版本注释)、本目录产物。

## 6. 施工纪律
- **独立工单、独立会话**:禁止在任何代币分析会话里"顺手"做;施工 = codex `--write --fresh`;验收 = Fable;盲审 = opus 攻击型(目标:构造让整数账户仍不守恒、让 `split_proportional` 不确定、或让零/负库存路径绕过门禁的输入)。
- 禁止读取 `~/.codex/skills/_archive/` 与 tag `codex-frozen-20260915` 下的实现(codex 侧缓存层对闭合另有假设,不得混入)。
- 先 RED 后 GREEN;`run_all.py` 用 nohup 落盘;完工不 commit,Fable 验收后代 commit。

## 7. 案卷影响与迁移交接(**[CX]** 按依赖哈希逐项判断,不按"数字进没进报告")
- 依赖链:`provenance_ledger.json`(sha、`input_binding.algorithm`)→ `entity_freeze.json`(记录 ledger sha)→ `final_distribution`(绑 freeze 文件与 revision)→ `a4_seal`(封所选文件与 claim 引用文件哈希)→ `a5_assembly_workorder` / A5 seal(绑 ledger/freeze)。ledger 一重跑,链上每一环都要按各自校验逐项判断失效,而不是看报告数字。
- 翻转裁决收据:`flip_fingerprint` 对三策略明细取哈希,raw 变即失效,须重新裁决(即使 top 与显示百分比不变)。
- APU 0914 案交接义务(执行交 −2 主线,本单只列义务):①用 7.1.0 重跑 trace;②freeze revision **按现有历史递增**(不硬编码 5);③按依赖链逐项复验/重封;④若有翻转收据,重新裁决。
- 其他案:凡再次跑 trace/freeze 的案子自动升 v3;已封存文件保留原样,但**不保证**新版工具复验通过(**[CX]** 措辞)。

## 8. 明确不做
不改顺序敏感性口径(`ORDER_MATERIAL_PCT`)、不改尘埃锚点的稳定性豁免、不改 BFS 深度/预算、不重构 `wave_scan` 加载(只加类型闸)、不引入 `Fraction`/`Decimal`/余数结转、不重构缓存或 producer 登记、不改 A4/A5 校验逻辑(只改 A5 的 schema 常量)。

## 9. 留给盲审方的问题(施工后 opus 攻击型盲审请逐条给证据)
- 是否存在让 `split_proportional` 后置断言不成立的输入(极端:avail 巨大、amt=1、键数上千)?
- `LayeredAccount` 部分消耗路径是否可能产生负键或 Σ 漂移(T3 之外的构造)?
- 零/负库存门禁是否可被"先负后正回到零"的序列绕过?
- freeze §3.7 新顺序下,尘埃锚点明细 ±1 是否确实被拒?
- 性能基准是否在同输入、同 scope、同参数、同环境下对比?

## 10. 复核融合记录(codex 意见 → Fable 裁决)
| codex 意见 | 核实 | 裁决 |
|---|---|---|
| Q1 整数分配造成三策略伪翻转 | 反例复算成立 | 采纳事实;不采纳"余数结转/误差界机制";以偏差界 + 尘埃豁免 + T3b 处置(§3.2b) |
| Q2 层式账户守恒成立但需边界条件 | 成立 | 采纳五条实现要求(§3.1/3.2/3.4) |
| Q3 消费方清单与隐式依赖 | grep 核实 8 处 + 4 处隐式依赖 | 采纳,进白名单与 §7 |
| Q4 肢数错误、性能不能预设 | 10^29≈2^97 属实 | 采纳更正,≤2× 改为验收目标 |
| Q5 精确闭合不误伤合法场景但不等于放行 | 成立 | 采纳,写入 §0 三问题分离 |
| T2 与零库存隐藏异常 | 第 608–610 行属实 | 采纳,负库存拒、零库存验快照、三策略全查 |
| freeze 第 1123 行顺序 | 属实 | 采纳,§3.7 重排 |
| T6 临时目录丢案根 | 第 728 行属实 | 采纳,隔离副本 |
| 迁移按哈希链 | 属实 | 采纳,§7 |
| 0.0 种子与上游精度 | 种子属实;evm_v2 路径核实为 hex→HUGEINT 精确 | 种子采纳;上游精度担忧**缩限**到 `--duckdb` 分支加类型闸 |
| T3/T5/T6 断言修正 | 合理 | 采纳 |
| 回退验收写反、CHANGELOG 行被 revert 删除 | 属实 | 采纳 |
| 7.1.0 与 v3 | 赞成 | 保留,措辞按 codex 修正 |
