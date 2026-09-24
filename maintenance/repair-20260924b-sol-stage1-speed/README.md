# 工程 repair-20260924b：Solana −1 机械段提速（共享地图驳回继承 / 强制用地图 / Helius 压缩 / 修复阶段单次 SQD 探针）→ 版本 9.2.0

出处：用户 2026-09-24 裁决（原话摘要）：「1.驳回过的 slot 记进共享地图,后案只做一次便宜的 SQD 状态确认就继承 2.让codex/opus跑-1阶段时使用共享地图 3.Helius 下载也开压缩 4.同一个候选 slot 被 SQD 探两次，看看怎么修复。1-4 现在就改 skill」。流程＝每单：写工单→codex 只读复核→融合→codex 施工→codex 盲审（连败三次换 opus）→全部完成后 codex 收官 review。调度方（Fable）只写工单/验收/commit，不写代码。

调度方实证（PYTHIA 0919 案，案卷在调度方本机，本仓库不含）：−1 纯机器时间 ≈85 h＝转账采集 22.5 h＋覆盖普查 20 h＋α 修复 37 h＋其余 ≈5 h。α 修复 157,700 候选中 155,642（98.7%）与 TROLL 0905 共享地图候选相同；修复 census refuted 150,133 / confirmed 7,567；补边 0 条；Helius getBlock 下载 366.7 GB（均 2.33 MB/块，未压缩，带宽瓶颈 92 slot/min）；普查未带 `--known-map`（开工失误，中途不可换图）。

| 单 | 内容 | 生产文件 | 顺序 |
|---|---|---|---|
| W1 | 共享地图 `refuted_slots` 由修复 census 填充；探针复用地图时对重查未变的 refuted slot 记 `INHERITED_REFUTED`，不再进候选；校验器同步重算 | `scripts/solana/sqd_coverage_probe.py`、`scripts/lib/solana_exact_validate.py` | 1 |
| W4 | 修复阶段每候选 slot 的 SQD 请求由 2 次（探针＋census）合并为 1 次 | `scripts/solana/sqd_gap_repair.py` | 2 |
| W3 | `net.py::curl_json` 加 `--compressed` | `scripts/lib/net.py` | 3 |
| W2 | `find-known-map` 子命令；split-run/命令/分册/README 文档硬性；版本 9.2.0；源码提交后由 WR-b 登记 probe | 文档＋`sqd_coverage_probe.py`＋版本四处；producer_history 仅由 WR 修改 | 4 |

上表顺序列为原计划；实际施工顺序以下方「顺序调整」为准。施工严格串行（同一工作树），复核/盲审只读可并行。`cc6298b` 是工程原始基线；各单实际派工基线取前序施工及必要登记完成后的 commit，由调度方更新工单基线、差异检查、事实与行号。


## 顺序调整（2026-09-24，r2 复核后）

实际施工顺序：**W3（先行）→ W1 → W4 源码提交 → WR-a 登记提交及真实注册表入口验收 → W4 最终收官 → W2 源码提交 → WR-b 登记提交及最终 probe 注册核验 → 工程最终验收与 codex 收官 review**。W3 与 W1/W4 无文件交集。各单经只读复核通过后施工，由调度方验收、commit，再经只读盲审；盲审连败三次换 opus。W4 与工程最终收官分别以完成 WR-a、WR-b 的对应验收为前置，具体按 `workorder_WR.md` §0.6–0.8 执行。施工者不 commit。

## 收官（2026-09-24）
- **结局**：六单＋一返修＋一文档修正全部收官，版本 9.1.1→**9.2.0**。W3（`net.py --compressed`，6b36dcd）；W1（驳回继承 `INHERITED_REFUTED`＋副本见证＋fail-closed 校验，2c3b17d/65132ab；返修 W1F cfe2f41 后盲审 r3 PASS）；W4（α/β 候选状态探针并入 census 单次 SQD 请求，59f88b8）；WR-a（repair sha `15822564…` 四协议登记 70e14a8，真实入口验收 `WR-a_formal_entry.md` PASS）；W2（`find-known-map` 子命令＋−1 开工硬性文档＋版本，f78b5c4，盲审一次 PASS）；WR-b（probe sha `d4adc0c8…` 两协议登记 8ba3de9，`WR-b_formal_entry.md` PASS，登记守卫 0 FAIL）；收官 review `review_final_reply_r1.md` PASS（P0/P1 空）；P2/P3 由 W5 文档修正关闭（64f4d1a，盲审 PASS）。
- **本机终验**：docs_lint/changelog_lint PASS；run_all 150/151（唯一红＝reseal 验收 worktree 缺失环境项）；`~/.claude/commands/token-analyze-1.md` 已与 commands-staging 逐字同步（备份 `.bak_20260924_081152`）。
- **过程数字**：codex 复核退回 W1 3 轮／W4 2 轮／W3 1 轮／W2 2 轮／W1F 1 轮／WR-a 1 轮／W5 2 轮；盲审 FAIL 3 次（W1 r2＝真缺陷→W1F；W4 r1/r2 与 WR-a r1＝非代码：正式入口待登记／只读沙箱无 tempfile，改派写模式验收任务），未触发换 opus。
- **残余与未做（如实）**：继承重查只证「块头在、零 AdvanceNonce」，不证交易集合未变（用户裁决接受）；完整生产链路吞吐收益未证明（仅单 slot gzip 6.1× 与查询内容对照）；仓库唯一共享地图 `20260827.json` 已于 09-24 03:17 UTC 过期，`find-known-map` 对其返回 exit 2；**案卷侧待做**：PYTHIA 修复代发布后用 `export-shared-map --repair-gid` 导出新图入库（PYTHIA 按用户指令等 QUQ 跑完再跑）。
- **教训**（详见记忆）：派工前树必须干净；zsh `"${C}:path"`；整行锚以 `-` 开头须 `grep -e`；codex 只读沙箱无 tempfile 时改派写权限极窄的验收任务；盲审提示词避免"篡改/绕过"措辞。
