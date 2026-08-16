# 批 B 消化循环第 2 轮工单（N-B1～N-B4）

审查对象：`394ffbb`（消化轮 1 收口态）。盲审复核判轮 1 的 F-B1～F-B7 **全部 CLOSED**、锚点翻案独立复算成立，但在轮 1 新写的锚点代码里抓出 4 条新 finding（2×P2＋2×P3）。本轮只修这 4 条；已 CLOSED 的 7 条实现**一行未动**（末尾有逐条核对）。未提交 git。

## 一句话结论

锚点取值顺序倒置为"已绑定已验证链路优先"（案根裸件永不作锚点来源）、案根同名件在场非法 fail-closed、两条零覆盖防线补定向红线、denominators 语义写进 schema——N-B1 双向实测在 **9 个真案 × 2 种存放形态**上全过（正常 9/9、案根陈旧件干扰下仍 9/9），盲审存活的 N3/N7 两条变异现已双双变红。

---

## N-B1（P2，主项）锚点取值顺序倒置

### 根因确认（读真实收据，不靠推断）

真实 APU 收据 `supply_truth.json` 的绑定形态：

```
inputs.replay_stats.path = …/APU分析0801/data/replay_stats.json   ← 绑的是 data/，不是案根
mint_total = 420690000000000000000000000000
burn_total =  82800853653911207346039942180
replay_net = 337889146346088792653960057820   （== mint − burn，form2 语义）
```

而 `shared_release_receipt._bound_replay_totals` 对这份绑定实物已经做了：receipt 三验（存在＋size＋sha256）＋**必须落在案根内**（N-1 约束，resolve 后遏制，软链指案外一并拦）＋`mint − burn == replay_net` 交叉验。**已验证的链路一直在，轮 1 却把它排在案根硬编码文件名后面。**

存放形态全库扫描（比盲审的 9 案更广，22 个案目录）：**只有 APU 在案根**（且案根与 `data/` 两份并存），其余全在 `data/`、`data/replay/`、`out/`、`replay/`、`replay_out/` 等子目录。轮 1 恰好只在 APU 这唯一案根形态上验了主线。

### 修法

`mint_closure_anchor` 取值顺序改为（EVM）：

1. **`supply_truth` 收据 `inputs.replay_stats` 绑定的那份实物**（新增 `_bound_replay_stats`，与 `_bound_replay_totals` 同源同口径：路径遏制在案根内、拒符号链接/非普通文件），取出 mint/burn 后**再交叉验 `mint − burn == replay_net`**；
2. 收据的 `mint_total` 字段；
3. `onchain_total_supply`。

**案根裸 `replay_stats.json` 从取值链中彻底移除**，不再是任何一档的来源。

### 案根陈旧件的行为：**忽略**（裁判要求写清理由）

选"忽略"而非"报错"，三条理由：

1. **误伤面是真的且面很大**：22 个案目录里只有 1 个把 replay_stats 放案根，没有任何生产者契约要求它在案根。让一个"不该在那儿的文件"把合法案打成 `data_broken`，是拿非契约产物惩罚合规案子。
2. **未绑定的文件不是证据，就不该有一票否决权**。它既不能被采用（否则就是"自己报自己验"的攻击面），也不该能否决——否则任何人往案根丢一个同名文件就能瘫痪一个合法案，等于给攻击者一个免费的拒绝服务开关。
3. **真正的漂移由已验证链路兜底**：绑定实物一旦与收据不符，`_bound_replay_totals` 的三验和本闸新加的 `mint−burn==replay_net` 交叉验会当场炸；案根那份不参与任何计算，忽略它不放过任何真实风险。

例外：**在场却非法**（符号链接／非普通文件）仍 fail-closed 拒 —— 见 N-B2。

### 双向实测（裁判硬要求，a/b 缺一不可）

**a. 攻击面**：`test_nb1_anchor_prefers_bound_receipt` —— 收据绑 `data/` 真值 mint，案根丢一份与"抹平 5 个 owner 的快照"配套的伪造 `replay_stats.json` → **rc=2 被拒**（轮 1 此组合 rc=0 通过）。另加 `test_nb1_bound_stats_cross_check`：绑定件 `mint−burn ≠ replay_net` → 拒。

**b. 误伤面**：`test_nb1_stale_root_file_ignored`（合成）＋**9 个真案 × 2 形态实测**（用真案 `balances_final.json` + `replay_stats.json` 原始数字构案）：

| 案 | 存放形态 | 正常态 | 案根塞陈旧件（mint×2） | sum==mint |
|---|---|:-:|:-:|:-:|
| APU0801 | 案根+data 并存 | ✅ rc=0 | ✅ rc=0 | ✅ |
| IQ | data/ | ✅ | ✅ | ✅ |
| KOGE | data/replay/ | ✅ | ✅ | ✅ |
| QUQ | data/ | ✅ | ✅ | ✅ |
| SQD | data/ | ✅ | ✅ | ✅ |
| BUILD | data/ | ✅ | ✅ | ✅ |
| PING | data/ | ✅ | ✅ | ✅ |
| BANANAS31 | data/ | ✅ | ✅ | ✅ |
| SIREN | data/ | ✅ | ✅ | ✅ |

**汇总：正常形态 9/9 通过；案根陈旧件干扰下仍 9/9 通过；锚点来源全部记为 `bound_replay_mint`、raw 全部等于真值 mint。** 两种存放形态（案根并存 1 个＋子目录 8 个，含 KOGE 的三层 `data/replay/`）全覆盖，超过裁判要求的"data/ 系抽 2 个＋APU"。9 案 `sum(快照)==mint_total` 再次逐位成立，第三次独立印证锚点翻案。

---

## N-B2（P2）案根同名件在场非法 → fail-closed

轮 1 的 `except ValueError: stats_path = None` 把 `safe_file` 的报错一把吞掉，符号链接时无声换档继续算——与本批 F-08 刚立的"在场非法不得静默漂白"自相矛盾，同一文件两套标准。

**修法**：案根 `replay_stats.json` 在场性检查前置且独立于取值链——`is_symlink()` 或 `exists() and not is_file()` 即 raise，错误文本"案根 replay_stats.json 在场但非法（符号链接或非普通文件），拒绝静默换档"。它不参与取值，只当完整性闸：案目录被动过手脚是完整性信号，**不因该文件不参与计算而豁免**。

**红线用例**：`test_nb2_root_stats_symlink_failclosed` —— rc=2 且错误文本含"在场但非法"。

---

## N-B3（P3）两条零覆盖防线补测

### ① 跨轮 `snapshot_sha` 一致性（盲审 N3 变异存活）

`test_nb3_rounds_snapshot_sha_consistency`：造第 2 轮 `snapshot_sha` 与首轮不同的 rounds 台账（前向哈希链正确，只坏这一处）→ 断言 `validate_rounds_ledger` 报出含 `snapshot_sha` 的错误；**并配防误伤断言**：一致时不得误报。

### ② 影子键守卫（盲审 N7 变异存活）

盲审指出根因很具体：旧守卫只用正则扫**闭合比较那一行**，而分母是在 `mint_closure_anchor` 里选的，把影子键 fallback 加进那个函数正则完全看不见。

**修法**：守卫改为 `inspect.getsource(mint_closure_anchor) + getsource(_bound_replay_stats)` **扫函数体**，命中 `get("total_supply_raw"/"frozen_total_supply_raw")` 即红；另加功能反例——造"影子键恰等于快照和、且无任何合法锚点来源"的案子，断言锚点来源不得记为影子键。R5 变异（给锚点加影子键 fallback）实测立刻变红。

---

## N-B4（P3）denominators 语义——**未撞契约，走文档改写**

**撞不撞契约（裁判点名要核）**：核过 `contract_manifest.json` 与 `contract_ids_snapshot.json`，与 distribution 相关的只有 `CT-DISTRIBUTION-01`（authority=`references/scan-schemas.md`、needle=`distribution-scan/v1`）——**不含 `denominators`／`total_supply_raw` 任何字段名**。同时确认全库消费面：只有 `adjudication_validator.py` 读 `net_supply_raw`（语义未变），**没有任何代码读 distribution 的 `total_supply_raw`**；`handoff_manifest.py` 的 `denominators` 来自它自己的 CLI `--denominators`，与本产物无关。

**选文档改写而非改名**，理由＝改动面小、语义诚实、零契约风险：改名会改动落盘产物 schema（属 schema 升版，且要连 `distribution-scan/v1` 版本号一起走），按铁律留批 D；文档改写零代码改动、零产物变化、零契约触碰，当场把人读歧义消除。

**改法**（`scan-schemas.md`）：字段表行内注明 `total_supply_raw` ＝ mint_total 铸造总量（含已销毁）、`net_supply_raw` ＝ replay_net 链上流通量；正文补一段说明真 `_burn` 案两者可差三成以上（IQ 差 34.9%），引用"总量"必须按此口径，并注明改键名为 `mint_total_raw` 留批 D。

**红线用例**：`test_nb4_docs_denominator_semantics`。

---

## 施工中自己抓到的一处夹具语义错误（诚实记录）

新加的 `mint−burn == replay_net` 交叉验一上线就把**我自己轮 1 的夹具**打红了两条（form2 真实收据、合成 dead-sink）。查因：`make_case` 里 `burn = mint − onchain`，form2 下 `onchain == mint` 会让 `burn` 恒为 0，与收据 `replay_net` 自相矛盾。**正确定义是 `burn = mint − replay_net`（两形态通用）**，对真实 APU 收据验算：`420690e21 − 337889…820 = 82800853653911207346039942180` 逐位等于真实 `burn_total`。已修夹具（生产代码无误）。这条记下来是因为它说明新交叉验在干真活，不是摆设。

---

## 变异验证（各"删掉即红"，备份 `/tmp/hds.r2_*`，逐条还原）

| 变异 | 结果 | 咬住的用例 |
|---|---|---|
| R1 锚点顺序倒回去（案根裸件优先） | 变红（2 条） | N-B1 攻击面 + N-B1 误伤面 |
| R2 N-B2 案根非法件检查删 | 变红 | N-B2 符号链接 fail-closed |
| **R3 跨轮 snapshot_sha 一致性删（盲审 N3 存活项）** | **变红** | N-B3 跨轮不一致必报 |
| R4 绑定件 mint−burn==replay_net 交叉验删 | 变红 | N-B1 绑定件不自洽被拒 |
| **R5 锚点允许回退影子键（盲审 N7 存活项）** | **变红** | N-B3 锚点函数体守卫 |

盲审在轮 1 里存活的 N3／N7 两条，本轮**双双变红**，回归覆盖缺口已补上。

---

## diff-finding-map（每 hunk 归属）

| 文件／hunk | finding | 归属 |
|---|---|---|
| `holder_distribution_scan.py` 新增 `_bound_replay_stats`＋`_mint_from_stats`（`@@ -246,0 +247,29`） | N-B1 | 读收据绑定实物，案根遏制＋拒符号链接 |
| `holder_distribution_scan.mint_closure_anchor` docstring 重写（`@@ -255/-258/-261`） | N-B1/N-B2 | 取值顺序与"忽略/拒"理由写进代码 |
| `holder_distribution_scan.mint_closure_anchor` 主体：案根件完整性闸＋绑定优先＋交叉验（`@@ -265,11 +303,13`） | N-B1/N-B2 | 顺序倒置、fail-closed |
| `holder_distribution_scan.mint_closure_anchor` 末档错误文本（`@@ -282 +322`） | N-B1 | 措辞对齐新取值链 |
| `references/scan-schemas.md` 锚点取值顺序段 | N-B1/N-B2 | 文档同批改口 |
| `references/scan-schemas.md` denominators 字段表行内注＋语义段 | N-B4 | 语义诚实 |
| `test_repair_batch_b.py` `make_case` 绑 `inputs.replay_stats`＋`burn=mint−net` 修正 | N-B1 | 夹具照真实收据形态 |
| `test_repair_batch_b.py` 新增 6 条用例 | N-B1/N-B2/N-B3/N-B4 | 攻击面、误伤面、交叉验、符号链接、跨轮、文档 |
| `test_repair_batch_b.py` 影子键守卫改扫函数体＋功能反例 | N-B3 | 补 N7 覆盖缺口 |

## 已 CLOSED 的 7 条：实现逐条核对未动

对比 `394ffbb` 的关键实现行，计数全等：

```
[同] final scan 快照与绑定的 initial scan 快照不一致    (F-B1 生产侧)
[同] UPSTREAM_RECEIPT_WHITELIST ×3                      (F-B3)
[同] 上游收据 path 不在白名单                            (F-B3)
[同] SNAPSHOT_CLOSURE_TOLERANCE_BPS = 0                 (F-B2)
[同] row.get("snapshot_sha") != first_snapshot_sha      (F-B1 第三道)
scripts/report/audit_release_gate.py                     未动（F-B1 第二道/F-B4/F-B6②/F-B7 全在其中）
```

本轮只动 `holder_distribution_scan.py` 的锚点取值区，**未重开任何已关闭的面**。

## 验证与最终退出码

| 命令 | 退出码 | 摘要 |
|---|---|---|
| `python3 -m py_compile scripts/report/holder_distribution_scan.py` | `0` | — |
| `python3 scripts/tests/test_repair_batch_b.py` | `0` | **41/41** |
| N-B1 真案双向实测（9 案 × 2 形态） | — | 正常 9/9、案根陈旧件 9/9 |
| **`python3 scripts/tests/run_all.py`** | **`0`** | **全部通过** |

## 边界

- 改动文件仅 4 个：`scripts/report/holder_distribution_scan.py`、`references/scan-schemas.md`、`scripts/tests/test_repair_batch_b.py`，以及盲审自己追加的 `batchB_adversarial.md`（**+175 行是盲审落盘的复核节，非本方改动**）。
- 版本三处（VERSION/SKILL.md/pyproject）、两份契约快照、批 C/D 十个生产文件——逐一 `git diff --quiet` 确认**全未动**。
- **N-B4 未撞契约**，无需上报冲突；改键名留批 D。
- 未 commit。**无越界。**

## 批 D 台账追加

- `denominators.total_supply_raw` → `mint_total_raw` 改名（schema 升版，连 `distribution-scan/v1` 版本号一起走）。
- （轮 1 遗留）Solana `holder_outputs.owners` 补文件级 validator 三验；Solana new-analysis 完整 `run()` 端到端夹具。

修复轮完成
