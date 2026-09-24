# 工单W2复核r2：退回

v2 尚不能直接派工：**§2.4 文案超预算且有两处语义偏差；完整整行锚仍未提供；find 的部分扫描失败与退出码优先级尚未定形。** producer 登记拆到 WR 的基本路线成立，不必移回 W2。

本轮 HEAD 始终为 `60c88b88a024bf463e819d846b1ba3a9e06c7ecd`，工作树干净；包含 `cc6298b`，指定生产源码、文档、版本及资产相对该基线无差异。全程只读、离线，未新建或修改文件，未 commit；未读取任何禁读路径或 memories。未执行会写文件或读取禁区的测试、完整 lint。

**r1 的 11 条吸收情况**

| r1 条目 | r2 核对结果 | v2 对应位置 |
|---|---|---|
| 1．事实、TTL、资产现状 | 已吸收。加载条件、过期检查位置和资产数字吻合 | W2:6–7、26 |
| 2．producer 协议及登记 | 最终 producer 登记路线已吸收；原要求的 W1 过渡哈希未纳入，是否需要保留见下文第 6 项 | W2:11、18、48；WR:7–15 |
| 3．manifest 前置 | 已吸收。W1 将新增修复来源校验放入校验器，W2 检查扫描结果；没有要求拼接字符串逃避扫描 | W2:19；W1:22、54–56 |
| 4．find 契约 | 大部分吸收；目录故障与已有候选并存时的处理仍不明确，见第 3 项 | W2:34–37 |
| 5．排序 | 已吸收，明确交集 refuted 数及确定性排序 | W2:36 |
| 6．继承、resume、导出、W4 文档 | 大部分吸收；新文案的时效起点与“β 不变”需修正，见第 1 项 | W2:39–42 |
| 7．整行锚与预算 | 未完整吸收。事实③仍是前缀、省略号；扩写后超预算 | W2:8、20、27、41 |
| 8．CHANGELOG | 173 B 索引、实际日期和指标口径已吸收；lint 日期能力表述需澄清 | W2:9、43 |
| 9．禁读与测试纪律 | 已吸收。完整 docs/changelog lint 交调度方，白名单与 tempfile 纪律明确 | W2:17、21–22 |
| 10．find 测试 | 已吸收主要覆盖；应随第 3 项补充组合故障测试 | W2:38 |
| 11．commands 同步 | 已吸收；本轮再次逐字比较，当前两份文件一致 | W2:48 |

**1．【必改】W2:41／§2.4：预算不成立，时效起点和 β 范围需改准。**

从工单引号中提取原文，通过标准输入交给 `wc -c`，结果如下；不含外层引号、追加分隔空格或换行：

| 内容 | UTF-8 字节 |
|---|---:|
| §2.2 split-run 追加句 | 641 B |
| §2.3 commands 追加句 | 120 B |
| §2.4 生命周期替换段 | **1,039 B** |
| 被替换的原生命周期段 | 288 B |
| §2.4 压缩追加句 | 192 B |
| §2.4 W4 追加句 | 245 B |
| `references/` 合计净增 | **1,829 B** |

生命周期超过 900 B 上限 **139 B**；references 在尚未计入分隔符时已经超过 1,800 B 上限 **29 B**。不能同时要求逐字落下这些原文与遵守现有预算。

另有两处设计不一致：

- W1:35、47 将 `origin_generated_at` 定义为**首次直接 census 所属 coverage 的发布时间**，不是 census 执行或证明完成时间。W2 的“从其首次直接 census 证明算起”容易把时效向后移动。
- W4:25 明确：β 搜索保留，但 β 候选进入共用修复流程后也使用合并查询。W2 的“β 不变”范围过宽。这里应修正 r1 建议中的同样措辞，不能为了沿用上一轮意见而保留它。

将 W2:41 整行替换为下列三段施工要求：

> - 2.4 `references/data-pipeline-solana-capture.md:202` 整行替换为以下原文（890 B，不含行末换行）：
>
> **共享地图生命周期**：地图 TTL 为源 coverage 发布后 30 天；驳回时效从首次直接 census 所属 coverage 发布时间算，链式导出不续期。资产 refuted slot 仅在本案成功复用且非 unverified 区间，重查值＝资产值＝2 且证据未过期才记 `INHERITED_REFUTED`，不入候选、免修复 Helius getBlock；getBlocks 照常。重查只证块头在、零 AdvanceNonce，不证交易集合未变；须信任来源，导出不深验源案全量证据。值变整图回退，失败按规则重试。refuted 来自发布修复 census 或继承；refuted-only 无代，只能导出继承。有效发布且满足导出条件才回填：`sqd_coverage_probe.py export-shared-map --case-root <案目录> --probe-id <probe_id> --out <skill根>/assets/sqd-solana-coverage-map/ --repair-gid <gid>`；无代改用 `--no-repair`；调度方验收入库。
>
> `:107` 整行末尾追加以下原文（192 B）：
>
> （9.2.0 起 `scripts/lib/net.py::curl_json` 内置 `--compressed`，经该层的 Helius getBlock 与 SQD 请求自动协商压缩；ledger 字节/哈希按解码后内容计算不受影响）
>
> `:198` 第 2 条整行末尾追加以下原文（278 B）：
>
> 9.2.0 起共用修复流程将状态探针并入 census；无重试时每候选 slot 一次 SQD 请求（含 β 候选），β 搜索不变；新采 evidence 的 `coverage_probe_query_sha256/coverage_probe_response_sha256` 与 `query_body_sha256/response_sha256` 分别同值。

上述替换原文已重新用 `wc -c` 核算：references 净增为 **1,713 B**；三处行末追加各加一个 ASCII 空格后为 **1,716 B**。commands 为 120 B，加分隔空格后 121 B。均满足现有上限，无须提高预算或删除无关内容。

**2．【必改】W2:5、8、20：事实快照与派工基线混写，所谓“完整整行锚”仍是缩写。**

本轮对六处文档目标原文实际执行 `grep -n -F -x`，均恰好命中一次，行号正确。但 W2:8 仍用“以……开头”和 `…` 代替整行，与 W2:20 自己的要求冲突。

此外，W2:5 将事实基线写成将来的 W3 收官 commit；W2:11 却列的是当前 `cc6298b` 同源脚本哈希。W1、W4 施工后，这两个哈希不能继续被称作 W2 开工时的“现役”。

将 W2:5 替换为：

> > 事实快照＝`60c88b88a024bf463e819d846b1ba3a9e06c7ecd`；下列源码、文档行号及现役 producer 哈希均对应此快照，生产文件相对 `cc6298b` 无差异。W2 派工基线另为 W3 收官 commit `<W2_BASE>`；派工时须更新已变化的事实、行号和锚，不能只改基线名称而沿用旧现役哈希。

将 W2:8 的锚说明替换为以下内容，保留其末尾 commands 同步责任说明：

> > ③ 六处施工目标的完整整行锚如下；本快照均经 `grep -n -F -x` 确认恰命中一次。派工时按 `<W2_BASE>` 重核；不以省略号或前缀充当整行参数。

`references/split-run.md:41`：

```text
- **A2 全部**：EVM 四查；Solana 五查＝四查＋精确重放 `exact_reconcile`。所有家族一律由 `scripts/report/reconciliation_report.py` 接收 job spec 后受控启动，并原子生成 `reconciliation-report/v3` wrapper；runner 校验新鲜 receipt、target、生产者和输入/receipt 哈希，禁止手拼 wrapper。Solana A2 FAIL 先跑 coverage 探针归因，再按 α/β 止损线运行修复生产者，禁止逐账户 BFS 补账。时间抽查跑 `scripts/lib/time_spotcheck.py`（EVM 案 `time_spotcheck.json` 为 READY 必备件＋AUTO_GATES，6.7.0）——**默认锚点级直查即闭环，全史第二源重拉是例外动作**（触发条件与 pilot 报 ETA 纪律见 evm-recon §13；APU 案照旧模板全史重拉 103 分钟纯冗余教训）。
```

`commands-staging/token-analyze-1.md:12`：

```text
3. **范围**＝A0–A2 全部＋A3 机械子层（split-run §1.3）；Solana 案 A2＝五查（四查＋`exact_reconcile`）。其中第 9 项必须运行 initial 持仓分布扫描并产 `distribution_scan.json`；CEX 黑箱关卡维持点名制——仅当我在命令里附加"CEX 黑箱 ≤N% 才继续"类要求时执行。
```

`references/data-pipeline-solana-capture.md:202`：

```text
**共享地图生命周期**：已知缺陷地图只省重复探测，不替代本案证据。地图 TTL（有效期）为 30 天；已知缺陷 slot 仍逐个复核；每次运行抽 canary（哨兵 slot）验证健康区和已知缺陷区，任一不符就停止复用并重建地图。
```

同文件 `:107`：

```text
- **gzip 压缩 = 21 倍**：同段对照实测明文 4.65 slots/s vs `--compressed` 98 slots/s（wSOL 高密度压测,压缩比 ~40x；普通 mint 预计 5-15x）。requests.Session 默认协商 gzip——**新脚本一律 requests,遗留 curl 件必须补 `--compressed`**。
```

同文件 `:198`：

```text
2. `sqd_gap_repair.py/v1` 只修已确认缺陷，产 `sqd-solana-coverage-resolution/v1`、repaired `sqd-solana-cache/v4`、`sqd-solana-repair-bundle/v1` 与 `sqd-solana-repair-pointer/v1`。交易按签名取参考源真值，并统一成 `reference-nonvote-ordinal/v1`。producer 升版后同案旧 pending 可经 `--resume --adopt-pending <旧目录>` 认领（前代 sha 须在 producer_history 登记、台账 header 记 `adopted`、深验重算前代 digest；来源可信是输入前提）；Solana 请求的交易版本上限统一取 `endpoint_identity.SOLANA_MAX_SUPPORTED_TX_VERSION`，升版本或改修复请求模板须同步换代 producer。
```

`assets/sqd-solana-coverage-map/README.md:3`：

```text
本目录存放由 `scripts/solana/sqd_coverage_probe.py --full` 在可联网主机完成全史扫描后发布的、可复算的 SQD 覆盖资产。批 2 只交付生产程序与协议说明，不放首版数据；首版由 Fable 本机完成 ARC 全扫并验收后入库。
```

其余关键事实已亲核：加载条件在 probe:1223，TTL 判断在 :697–700，入口锚在 :1430；版本位置、8,021 B 的 SKILL 大小、manifest 消费关系及 producer 协议集合均吻合。资产到期时间精确为 `2026-09-24T03:17:11.217739+00:00`，复核时已过期。

**3．【必改】W2:35–38／§2.1：补齐部分扫描故障的确定行为。**

目前同时规定“有 chosen 返回 0”“运行故障返回 1”“chosen＝accepted[0]”。如果一个目录有合格地图，另一个目录不可读，三条规则如何组合尚未明确。r1 明确要求调用方同时检查退出码和完整 JSON，这句话在 v2 中也没有完整落下。

另外，轻筛应直接沿用已确定的廉价形态约束。例如正式校验器 `solana_exact_validate.py:797–799` 要求二进制引用文件与 JSON **位于同一目录**，不只是位于其后代目录；无需读取二进制就能判定。

在 W2:35 后追加：

> 轻校验的整数均排除 bool；两份二进制引用 resolve 后必须满足 `resolved.parent == asset_json.resolve().parent`，与正式校验器保持一致。JSON 层检查 `refuted_slots ⊆ candidate_slots`，并检查 W1 §2.1 规定的 origin 索引、等长关系及逐证据计数；需要二进制内容才能证明的条件留给正式加载。accepted 中的 `generated_at` 与 `expires_at` 均统一输出 UTC ISO-8601。

将 W2:37 的退出码及目录错误说明替换为：

> 退出码按以下优先级决定：发生目录枚举、目录权限等扫描级故障 → 1；否则有 chosen → 0；否则 → 2。缺失目录记入 rejected 后继续，视为正常扫描；空目录允许。单个候选文件的读取或校验失败记入 rejected 后继续，不升级为扫描级故障。扫描级故障也记录目录绝对路径与 reason；已得到的 accepted 仍排序输出，chosen 仍等于 accepted[0] 或 null，但调用方不得使用 exit 1 的部分结果。除 argparse 参数错误沿用 exit 2＋stderr 外，受控退出均输出一行固定结构 JSON。调用方必须同时检查退出码与完整 JSON：仅 exit 0 可采用 chosen，仅 exit 2 且合法 JSON 中 chosen=null 才可按无图执行 `--full`；其他结果先处理错误。

在 W2:38 测试清单末尾追加：

> 补测「一目录有合格地图＋另一目录不可读」仍返回 1、保留部分 accepted 且调用方不采用；另测缺失目录＋合格地图返回 0，以及 argparse exit 2 无合法结果 JSON 时不得误判为无图。

**4．【建议】WR:1、16–17：登记纪律成立，但把“源码提交”和“最终收官”拆开写清。**

已复算当前 probe、repair 文件哈希，均与各自登记 commit 的 `git show` 内容一致。WR 的三方哈希比对、只追加 ACTIVE、保留历史条目、不新增 shared-map 协议，均成立；源码提交后再登记也不存在 commit 自引用问题。

正确顺序已经在 W4:52 写明。WR 标题却写“W4 收官后”，容易与“登记是 W4 收官前置”混淆。建议同步明确：

将 WR:1 替换为：

> # 登记单 WR（模板）：追加 9.2.0 生产者 ACTIVE 条目——WR-a 在 W4 源码提交后、最终收官前登记 repair；WR-b 在 W2 源码提交后、工程最终收官前登记 probe

在 WR:17 后追加：

> - 0.6 调度顺序：W4 源码 commit → WR-a 复算并追加四协议 → 调度方登记 commit → 真实注册表入口验收 → W4 收官；W2 源码 commit → WR-b 复算并追加两协议 → 调度方登记 commit → 工程最终验收。施工者不 commit。
> - 0.7 WR-a 正式验收沿用 W4 §3：自包含夹具通过未替换 `historical_producer_hashes` 的 `validate_repair_bundle(deep=True)` 与 `resolve_formal_cache`。仅测试尾行或直接调用深验 helper 不替代这项验收。WR-b 核对最终 probe sha 同时进入 coverage/v1 与 coverage-pointer/v1 的真实 ACTIVE 查询结果。完成报告记录源码 commit、登记 commit、sha 和实际验收结果；缺项写待验收。

依据是 `test_sqd_gap_repair.py:322–330` 的既有用例会替换历史注册查询，其通过不能独自证明登记有效；WR:16 已排除禁读夹具用例，这项纪律应保留。

背景 README:12 仍写 W2 修改 `producer_history.py`，建议同步替换该表格行：

> | W2 | `find-known-map` 子命令；流程文档硬性；版本 9.2.0；源码提交后由 WR-b 登记 probe | 文档＋`sqd_coverage_probe.py`＋版本四处；producer_history 仅由 WR 修改 | 4 |

**5．【建议】W2:9、43：173 B 索引正确，日期“合法”不应归功于 changelog_lint。**

索引确为 **173 B**，含末尾 LF 为 174 B。9.2.0 档位与 `CHANGELOG.md:4` 相符；新增标题格式也匹配当前解析器。

但 `changelog_lint.py:21–33` 只用正则检查日期外形。亲核该正则：

- `2026-09-24`：匹配；
- `2026-09-2X`：不匹配；
- `2026-99-99`：仍匹配。

将 W2:9 中相关短句替换为：

> `changelog_lint.py:21-33` 只检查版本标题及 `YYYY-MM-DD` 日期格式，不验证日历日期真实性；实际发布日期由调度方人工核定，`2026-09-2X` 不通过。

在 W2:43 末尾追加：

> 索引原文为 173 B（不含 LF），长度由人工字节核算验收。changelog_lint 检查活跃与归档合并后的版本唯一性、活跃降序、归档降序及两者边界；不检查索引字节数、四条详细段内容或日期真实性。原版完整检查读取 archive，仍由调度方执行并记录。

本轮未读归档，故不声称已经验证新增版本在活跃与归档合并范围内唯一。

**6．【存疑】WR-b 仅登记 W2 最终 probe，r1 要求的 W1 过渡 probe 是否需要保留尚无证据。**

把最终 probe 登记放在 W2 源码提交后是正确的。但 r1:61 原本还要求登记 W1 已提交 probe 的两协议；WR-b 当前只登记最终 W2 sha。

若 W1 仅产临时测试夹具，此缩减可以成立。若 W1 版本产过需要长期重验的正式 coverage，W2 改动 probe 后，W1 sha 既不再是当前文件 sha，也未进入历史集合，`solana_exact_validate.py:499–506` 将无法凭这两条路径接受它。本轮可读资料不能确定是否存在这种产物。

在 WR 的派工填写项后追加：

> 调度方在 WR-b 派工前核查 W1 过渡 probe 是否产生需保留、继续重验的正式 coverage/pointer。若无，在 WR-b_done 明记「W1 过渡版本仅作施工测试，无需保留的正式产物」；若有，另列其源码 commit、可复算 sha 与产物范围，补独立登记单追加 coverage/v1、coverage-pointer/v1。WR-b 的两条最终 probe 登记不得被表述为已经覆盖 W1 过渡哈希。

| 条目 | 等级 | 依据文件:行 |
|---|---|---|
| §2.4 超预算、时效起点及 β 范围 | **必改** | `workorder_W2.md:27/:41`；`workorder_W1.md:35/:47`；`workorder_W4.md:25` |
| 事实快照、派工基线与完整整行锚 | **必改** | `workorder_W2.md:5/:8/:11/:20`；`split-run.md:41`；`token-analyze-1.md:12`；`data-pipeline-solana-capture.md:107/:198/:202`；资产 `README.md:3` |
| find 部分故障、退出码及廉价校验边界 | **必改** | `workorder_W2.md:35/:37/:38`；`solana_exact_validate.py:797`；`workorder_W1.md:45–48` |
| WR 时序、真实注册表验收与 README 同步 | 建议 | `workorder_WR.md:1/:13–17`；`workorder_W4.md:52`；`test_sqd_gap_repair.py:322`；工程 `README.md:12` |
| CHANGELOG 日期与检查器能力说明 | 建议 | `workorder_W2.md:9/:43`；`changelog_lint.py:21/:41/:48/:57/:63/:67` |
| W1 过渡 probe 历史兼容范围 | 存疑 | `review_W2_reply_r1.md:61`；`workorder_WR.md:15`；`solana_exact_validate.py:499–506` |
