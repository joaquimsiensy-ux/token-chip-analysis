# PYTHIA 判定题 v5/v6 对照双跑记录（2026-07-30，验收产物）

> 同一冻结题面（evals/cases/01 A 节），两个互相隔离的子会话：v5 侧只读 main（v5.0.0＝087ccec），v6 侧只读 rebuild/v6。均禁止读 evals/、对方目录、memory。以下为两版原始产出的并排对照与逐字要点，供用户挑错终裁。

## 一、结论对照（最重要的一行）

| | v5 基线 | v6 新版 |
|---|---|---|
| 9Z 身份判定 | 币安 Alpha 场内托管库存仓（接近确证），非私人庄家、非做市商 | 同 |
| 当年确证错误（判"小庄#1"）| **拦住** | **拦住** |
| 处置 | 不入私人实体表，单列 CEX 托管黑箱 16.72% | 同（16.7%，G8 语义核对过） |
| 措辞纪律 | 强度封顶"接近确证"（无官方公示/PoR 不写实锤）；黑箱只写份额上限 | 同；另明确"减仓不得写成庄家出货" |

两版证据链同构且互相印证：address-book L121 标签命中（批量 CSV 层 miss、并源层命中）＋ed25519 off-curve（无私钥）＋Alpha 集齐率 94.3%（66/70 当场实测）＋BN111 程序与 feePayer 轮换代付（decode 抽验复现）＋双向吞吐净沉淀形态（504 变动日）。

## 二、判定路径差异（v6 的增量在哪）

| 维度 | v5 基线 | v6 新版 |
|---|---|---|
| 起步阅读 | SKILL.md 全文 37KB → 从阶段 3 长段落里找到硬闸与 E0b④"完整版同责"句 | SKILL.md 8.6KB 路由表 → A3 行直接点名"casebook C/E 册全过一遍＋identity gate" |
| 排除其他解释 | 直接奔托管验证去（结论对，但"为什么不是别的"未显式走查） | **判例过闸显式化**：C-01 逐字命中锁定三项必做检验；C-02/03/04/05 逐条登记"不适用"（把 TROLL 型反向过判、跨链迁移型、质押产品型、escrow 型四种错法照单排除）；E-03 循环论证自查、C-02 正向证据自查 |
| 拦截层数 | 硬闸（v4.1/4.2 装的三闸，v5 继承） | 判例过闸（新增强制步骤）＋同一套硬闸——双层 |
| 依赖"读到关键句"的程度 | E0b④"完整版同责"藏在阶段 3 段落中部 | 该义务已成 A3 路由行＋casebook C-01 必做检验③，双处显式 |

## 三、诚实声明（不粉饰）

1. **v5 此题也判对是意料之中**：v4.1.0/v4.2.0（2026-07-30 早些时候）已装 address-book 并源＋entity_identity_gate＋G8 三闸，当年犯错的是 v4.1 之前的版本。本题对 v5 的意义是"三闸仍然有效"，对 v6 的意义是"重构没有弄丢三闸，且判例层多拦一手"。
2. **单题成本几乎持平**（v5：107k tokens/21 次调用；v6：104k/29 次）——两边大头都在读案目录＋链上实测，SKILL.md 37KB→8.6KB 的上下文优势要在完整分析（几百轮工具调用、每轮重读历史）里才会放大，本题测不出来。
3. v6 独有而 v5 零覆盖的能力（本题未涉及）：供给真值闸（GNT 型静默改账，v5 全部自检静默放行）——见 evals/cases/06 与契约测试。

## 四、原始产出存档

### v5 侧完整产出

**步骤**：①读 SKILL.md 全文路由至阶段 3 硬闸＋E0b④＋solana-scan §2/§2a/§3＋cluster-methods §3 ②replay_balances.json 取 9Z 全值（167,404,065.5 枚）③标签双源：CSV miss＋address-book L121 命中「币安 Alpha 托管库存仓（接近确证）」，配套 6ZaWyb（执行仓）/BN111（批量程序）在册 ④ed25519 本地自算 off-curve ⑤accounting_mode.json standard PASS 核对（总供应 998,158,041.8，authority 已弃）⑥日级形态：504 变动日、净增 275/净减 227＝双向吞吐净沉淀，现 166.92M＝16.72%，峰 188.07M@2026-03-04 ⑦Helius 只读实测：324 token account、SOL 0.257 ⑧ATA 最近 15 笔 decode：11/15 走 BN111、feePayer 7 址轮换 ⑨集齐率现场重跑 66/70＝94.3%，与 PENGUIN 实测逐币一致 ⑩identity_gate.json 45/45 flag 已解决核对，e_alpha 单址单列。

**结论**：托管库存仓接近确证；off-curve＋BN111 流水＋代付结构为链上铁证级，集齐率一票否决做市商假设；"高频对手方极多"正是零售充提特征（私人庄家对手方反而集中）；不入实体表、份额只作单一实体上限表述。

**出处**：SKILL.md 阶段 3 硬闸/铁律 1/铁律 3；easy-workflow E0b②③④；solana-scan §3 集齐率四档/§2 两跳判别/§3a 坑 1/2；cluster-methods §3；entity_identity_gate.py 头注"托管判定反向闸"；address-book Solana 节三条目。

### v6 侧完整产出

**步骤**：①读 SKILL.md 定位 A3 两道必做 ②读 analyze-workflow A3 步骤 2/3 明确判例过闸＋硬闸＋集齐率同责 ③cex-custody 全册：C-01 逐字命中锁三项检验，C-02 正向证据要求入自查，C-03/04/05 登记不适用 ④entity-clustering 全册：E-02 设施先验、E-03 循环论证入自查 ⑤solana-scan §2/§2a/§3 取操作定义 ⑥labels_top300.jsonl 取全值（批量层 hit:false＝C-01 说的"零命中≠没记录"情形）⑦label_lookup 正式过闸：[EXCLUDE] cex，merge:no_merge，来源 address-book 并源层 ⑧redo/verify_oncurve.py＋oncurve_result.json：off-curve ⑨daily_9ZPsRWGk.json：07-28 余额 16.72%、峰 17.23%@07-25，双向小幅净流 ⑩RPC 实测：SOL 0.257、324 币种（299 非零）、现持 16.65% ⑪集齐率当场实测 66/70＝94.3%，PYTHIA 在 Alpha 表内（在架前提复核）⑫代付指纹：最近 10 签跨 4.1h，decode 4/4 feePayer 非本尊（两代付方轮换）、4/4 含 BN111 ⑬entity_identity_gate.py 判定段核对：tier=exclude 入私人实体即 INFRA_IN_ENTITY→G8 ⑭E-03 自查（两侧集合外生非循环）＋C-02 自查（标签＋四重专属指纹，非单一通用特征）。

**结论**：托管库存仓（接近确证）；不得写入私人实体（写入即 G8 物理拦截）；16.7% 单列 CEX 托管、场内黑箱不可穿透；日度增减＝场内用户买卖净流，减仓不得措辞"庄家出货"。五项独立证据同向收敛。

**出处**：SKILL.md 铁律 2/3/4＋A3 路由行；analyze-workflow A3 步骤 2/3；cex-custody C-01/C-02；entity-clustering E-02/E-03；solana-scan §2/§3；tiering §6a；address-book L121；entity_identity_gate.py 三 flag 语义。
