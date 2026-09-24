# 收官review：PASS

审查范围：`cc6298b → ef20dd825a0f3698bee79b6adfae59befcf6285d`，限定的 19 个变更文件及允许读取的工程记录。**未发现 P0/P1；发现 1 项 P2、1 项 P3。** 四项裁决的核心实现成立，W2 异常分支的执行文档仍需补齐。

全程只读、离线，无文件新增或修改、无 commit；未读取 `~/.codex/`、memories 或其他禁区，未运行触及 `.staging_b3` 的用例。结束时工作树干净。

**分级发现**

- **P0：无。**
- **P1：无。**
- **P2：W2 执行文档未限定“只有 exit 0 才能采用 chosen”。**  
  [split-run.md:41](/Users/uravvv/.claude/skills/token-chip-analysis/references/split-run.md:41)、commands 和资产 README 均写“chosen 非空必用”。但 `_find_known_map` 在扫描级故障时会返回 **exit 1，同时保留非空 chosen**；工单明确禁止使用这种部分结果。  
  **独立复现：**内存固定 `utc_now=2026-09-01T00:00:00+00:00`，对真实旧资产区间运行 find，并追加 `--search-dir VERSION`。得到 `rc=1`、chosen 指向 `20260827.json`、rejected 为 `directory scan failed: Not a directory`。照现行执行文档仍可能继续使用 chosen。  
  **影响：**错误分支的操作指令与程序契约不一致；完整地图加载仍会校验，所以不列 P1。应明确：exit 0 才采用 chosen；exit 2 且合法 JSON 的 chosen=null 才全扫；其余先处理错误。

- **P3：9.2.0 CHANGELOG 停留在施工期状态，未归并最终验收。**  
  [CHANGELOG.md:108](/Users/uravvv/.claude/skills/token-chip-analysis/CHANGELOG.md:108) 仍称 WR-b 待登记、lint/run_all 待验收、W3 联网验收与 W4 线上实测未记录。实际已有 WR-b 两条登记、formal_entry 和最终验收追记。  
  **可复现依据：**对照 `WR-b_acceptance.md`、`WR-b_formal_entry.md`、`W2_acceptance.md`，以及 [fable_probes_20260924.md:41](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/fable_probes_20260924.md:41)。P5 已记录 W3 gzip：传输字节 `4,516,539 → 736,729`，规范化结果摘要相同；P3 已记录 W4 合并查询内容对照。  
  四条 CHANGELOG 的实现描述及施工数字基本对应各 done 报告，但作为最终版本记录，待办状态已经过时。**提示词中的“W3 线上收益未记录”也应据此修正**；完整生产链路吞吐收益仍未证明。

**四项裁决与跨单一致性**

| 裁决 | 实现与判断 |
|---|---|
| **① W1 驳回继承** | [export_shared_map:840](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:840) 从已验证 coverage 和当前 formal/live repair 来源导出；重算原始候选，处理 confirmed 冲突、继承过期和证据重新编号。`_load_known_map:681` 仅继承实际复用区间内、非 unverified、重查值与资产值均为 2、原始证据未过期的 slot。问题在约定的可信来源边界内解决。 |
| **继承证明与拒收** | [校验器:589](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/solana_exact_validate.py:589) 核来源副本大小/摘要、完整成员映射、完整 evidence、实际 map-reuse 台账及重查响应；失败记录 reasons，并清空继承重新分类。副本在 probe_id 计算前发布，纳入同代比较；不是仅相信 `INHERITED_REFUTED` 标签。 |
| **② W2 强制查图** | `find-known-map:1560/1644` 实现离线轻筛、确定性排序和扫描故障优先退出；split-run 与命令入口规定非 resume 开工先查图、有图必用、发布后回填。**正常路径已解决；异常采纳纪律存在上述 P2。**这是执行者纪律，不是 CLI 禁止直接全扫的机器门禁。 |
| **③ W3 压缩** | [net.py:105](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/net.py:105) 在共用 curl 参数中加入 `--compressed`；Helius getBlock 与 SQD 调用确实经过该层。curl 透明解压后再解析，账本字节及摘要口径保持不变。实现成立。 |
| **④ W4 单次 census** | [_fetch_live_slot:1007](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1007) 先取一次合并 census，从同一响应计算块头、nonce 数和交易集合；状态不符或重复目标块在 Helius 前拒绝。旧 `_state_probe` 已删除。无重试时，每候选为一次 SQD census、一次 Helius；β 搜索请求不计入该承诺。 |

跨单核对结果：

- **α/β 一致：**生产者禁止 `INHERITED_REFUTED` 进入 α；β 可独立纳入，但必须有块头且 nonce=0。深验由重算 coverage 候选和独立 β trace 限定计划集合，再核同一状态语义。
- **TTL 一致：**地图从源 coverage `published_at` 起算；驳回继承保留首次来源的 `origin_generated_at`，链式导出不续期；历史离线复验按记录的 `verified_at` 判断。
- **resume 一致：**不调用地图加载、不保留继承，恢复普通分类。
- **摘要一致：**新采证据的两组请求/响应摘要分别同值；旧证据仍允许双查询摘要不同，没有把新规则强加给历史产物。
- **W1F 成立：**空响应映射为请求区间全 1；完整响应内缺失 slot 补 1，使冲突检查能够看到“无块头”，而非遗漏该 slot。

**登记与正式入口**

本轮亲跑 `test_producer_registry_current.py`：**53 项 ok，0 FAIL**。AST 对照确认注册表从 34 条增至 40 条，原 34 条未变。

| 新增登记 | Git 源码提交 | 复算 SHA-256 |
|---|---|---|
| repair 四协议 | `59f88b84c9ab9eeb95c92a15e342d8cbe09925db` | `15822564046e654b46300edcc26aeb51b397217ecce0fb555df0e891d98a1a33` |
| probe 两协议 | `f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6` | `d4adc0c88f87bc03b3d847db7df9c9f7e588cb503734dfd977b818b581d998d8` |

两者均与当前源码相等，旧 repair `3f89aab1…` 仍为 ACTIVE。

- **WR-a：**核对了 formal_entry、保存的 runner/results 与 [真实入口源码](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_cache_identity.py:124)。全旧、全新、混合证据的深验及 CURRENT resolver 验收与源码路径一致；移除四条登记后的拒收原因也对应真实入口。历史认领仍验证前代登记、前缀及前代 plan digest。
- **WR-b：**报告正确区分了“注册查询有效”与“当前源码产物兼容”。coverage 校验允许当前源码 SHA，因此不能把移除登记后仍能校验当前产物误判成登记失效；报告用真实查询的正负对照证明登记，表述准确。
- 本轮**没有重新生成三类发布产物或重跑正式入口动态验收**；上述部分属于源码与现存验收证据交叉核查。

**本轮独立验证与预算**

- `invariant_scan.py`：**PASS**，`exceptions=0`。
- `test_net_result.py`：**PASS**；限定 diff 的 `git diff --check` 通过。
- 32 组无继承输入：现行分类结果与 `cc6298b` 分类器逐项相同。
- 64 组状态/αβ/块头/nonce 组合：W1/W4 规则一致；拒绝向量无 Helius 调用，接受向量仅一次 census，新增摘要同值。
- W1F 重查重算：2 个正例、7 个错误字段拒收向量通过。
- β 搜索相关五个函数与基线 AST 相同。
- **真实旧资产完整校验通过：**新 `validate_shared_map` 读取两份二进制并重算，`ok=True, reasons=[]`；空 refuted 且缺新增证据字段兼容。
- **旧资产当前不可复用：**到期时点为 `2026-09-24T03:17:11.217739Z`。真实 find 返回 exit 2、chosen=null、`shared map expired`；精确到期边界可接受，超过 1 微秒拒绝。

字节数独立复算：

| 项目 | 结果 |
|---|---:|
| SKILL | **8,021 B ≤ 8,192 B** |
| W2 references 净增 | **1,716 B ≤ 1,800 B** |
| commands 净增 | **121 B ≤ 260 B** |
| 全工程 references 净增 | 3,831 B |
| 全工程资产 README 净增 | 3,840 B |

W1 文档原 1,200 B 已由工单改为报告指标，其超量有说明，不构成预算违约。`VERSION`、`pyproject.toml`、`SKILL.md`、CHANGELOG 四处均为 **9.2.0**。

**边界与未完成项**

- 继承只重新证明“块头存在、零 AdvanceNonce”；不能证明非 nonce 交易集合未变化。文档已明确这一限制，导出也不重放来源全量修复证据。
- PYTHIA 案卷侧导出按本次交接仍待做，本轮未验证；默认仓库目前只有已过期、refuted 为空的旧图，**不能把代码就绪写成实际继承收益已兑现**。
- W3 已有单 slot 联网对照；W4 已有查询内容对照，但完整生产吞吐收益、线上无目标块头样本仍未证明。
- 未重跑需写临时产物的完整回归、禁区用例及读取 archive 的 lint。最终本机验收记录为 **150 PASS、1 项 reseal 验收 worktree 缺失**，不是全绿；本轮未独立复验该环境项。

按约定的“P0/P1 为空才 PASS”判据，本次结论为 **PASS，保留上述 P2/P3 文档修正项**。