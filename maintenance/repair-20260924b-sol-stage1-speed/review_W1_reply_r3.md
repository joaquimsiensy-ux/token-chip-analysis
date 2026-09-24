# 工单W1复核r3：退回

v3 已吸收 r2 的主要技术意见；指定的修复来源字段、副本发布协议、`--no-repair` 冲突路径和链式 evidence 规则均可施工。**唯一确定的派工阻断是基线门禁未随 W3 先行更新**：照工单执行必然停工，完成报告也会把 W3 误算为 W1 越界修改。

本次按用户指定的 HEAD 复核，没有把工单中的旧门禁当作本轮停止条件。

支持方案的核心理由是：复用已完成的 census 结论，可以减少重复整块下载，且 v3 已补齐来源绑定和冲突剔除。反对立即派工的理由是：工单必须能在当前仓库状态下通过自己的开工与验收规则。零 nonce 重查的残余风险已明确接受，本轮不再据此扩大需求。

**r2 的 8 条吸收核对**

以下工单行号均指 [workorder_W1.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260924b-sol-stage1-speed/workorder_W1.md)。

| r2 条目 | v3 位置 | 复核结果 |
|---|---|---|
| 1．修复来源字段与绑定 | 12、55–59 行 | 已吸收。bundle 使用 `coverage.map` 文件引用；resolution 使用 `coverage.map_sha256`；producer 取 bundle；指针调用改为 keyword-only；保留 β 并集及真实分类检查。 |
| 2．副本 evidence 绑定、counts 边界 | 69、79、82 行 | 已吸收。明确 evidence 全等、逐 slot 索引绑定、按副本完整映射核计数；不再声称 JSON 副本包含源 counts。 |
| 3．`--no-repair` confirmed 冲突 | 63–64、99 行 | 已吸收。CURRENT 存在时仍调用同一 helper；失败报错；仅清空 own，保留 confirmed 冲突剔除。 |
| 4．链式 evidence 转换 | 48、62、64、100 行 | 已吸收。新建 inherited 项，清空四个修复字段，切换 producer 归属，过滤后重排索引和计数。 |
| 5．副本发布协议定形 | 70 行 | 已吸收，可复用现有发布机制，不必修改 receipt kernel 或 pointer 键集。 |
| 6．recheck 专用检查与负例 | 81、98 行 | 主体已吸收。完整返回、跨边界记录及结果绑定要求明确；部分继承测试的措辞建议澄清，见下文。 |
| 7．范围精度与唯一锚 | 8–9、24 行 | 已吸收。实际写入范围及函数所属文件正确；事实范围与施工唯一锚已区分。 |
| 8．`origin_asset_sha256` | 36、48、62、100 行 | 已吸收。首次直接导出 null，首次链式填来源资产摘要，以后保留；不刷新原始时效。 |

**指定源码与协议亲核**

- [sqd_gap_repair.py:1336](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1336) 的 census 字段与 v3 对应，`state_in_map` 确实硬编码；真实分类来自 `coverage_state`。[resolution:1483](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1483) 无 producer；[bundle:1587](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_gap_repair.py:1587) 的 map 确实是文件引用。原 r2 字段错误已消除。
- [RawBytes:41](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/lib/receipt_kernel.py:41) 支持原字节发布；底层写入执行文件 fsync。副本在计算 probe_id 前落盘、使用代内相对路径，可以避免路径与 probe_id 的循环依赖。
- [_same_generation:1007](/Users/uravvv/.claude/skills/token-chip-analysis/scripts/solana/sqd_coverage_probe.py:1007) 已支持文件可选存在。纯内存给其清单增加副本后，双方缺失／副本相同均返回 True，单方缺失／副本不同均返回 False。`_clear_pending` 加入副本名称也符合现有逐文件清理方式。
- `repair-census → inherited → inherited` 的字段契约现在一致：若最初资产为 A，第一次链式导出填 `origin_asset_sha256=sha(A)`，第二次继续保留该值；`asset_sha256` 则更新为各自直接来源资产的摘要。两者职责没有冲突。

上述属于源码和纯内存核验，不代表尚未施工的新实现已通过测试。

**1．必改：更新 W1 基线，排除已提交的 W3 差异**

定位：工单 **20、39–40、105 行**；锚分别为 `0.1`、`1.10`、`1.11`、完成报告正文。

本轮实测：

```text
HEAD = 6b36dcdd043d0b2b51c03de9ab0bb555b25f436a
git status --short：空
cc6298b 是 HEAD 祖先：exit 0
§0.1 原 git diff --quiet 命令：exit 1

差异文件：
scripts/lib/net.py
scripts/tests/test_net_result.py
```

三个 W1 生产文件相对 `cc6298b` 均无差异，因此源码行号可以保留；需要调整的是施工差异基线。

第 20 行可直接替换为：

> - 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。固定施工基线 `W1_BASE=6b36dcdd043d0b2b51c03de9ab0bb555b25f436a`（已含 W3）；开工先设置该变量，再跑并贴进 `W1_done.md`：`git status --short`（须为空）、`git rev-parse --short HEAD`、`git merge-base --is-ancestor "$W1_BASE" HEAD`（须 exit 0）、`git diff --quiet "$W1_BASE" HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets`（须 exit 0）。任一不符停工。源码事实行号仍沿用 `cc6298b`，三个 W1 生产文件在两基线间无差异。

第 39 行可直接替换为：

> - 1.10 生产改动量列入报告（`git diff --numstat "$W1_BASE" -- <文件>` 逐文件）；原 ≤140/≤120 上限改为审查指标：超过须逐项说明新增职责与复用情况；不得为压行数省略校验或压缩可读性。优先复用现有 helper（`_check_file_ref`、`_success_ranges`、`checked_slots`、`validate_repair_pointer`、`_repair_state_matches` 等）。

第 40 行可直接替换为：

> - 1.11 `git diff --stat "$W1_BASE" -- . ':!maintenance'` 只含 0.3 白名单；W3 已提交差异不计入 W1。

第 105 行可直接替换为：

> 首行 `# W1 完成：<一句话>` 或 `# W1 停工：<原因>`。含：固定 `W1_BASE` 值及 §0.1 四项输出；每处施工实际 diff 行号与 `git diff --numstat "$W1_BASE"` 逐文件行数（超出原 140/120 指标的逐项说明）；§0.7 测试尾行与未运行清单；1.1 兼容证据（具体用例名）；2.3 resume 限制与副本发布协议处理说明；`invariant_scan.py` 结果（探针无新增消费者）；文档字节数；`git diff --stat "$W1_BASE" -- . ':!maintenance'` 只含白名单；末尾披露是否读过禁读路径。

**2．建议：把部分继承的合法正例与计数篡改负例分开**

定位：工单 **98 行**；锚「部分继承导致 evidence 计数不同」。

第 79 行已正确要求按副本完整映射核计数。若资产证据对应 R1、R2，而本案只继承 R1，原 evidence 的 `refuted_count=2` 应保留并通过。第 98 行把“部分继承导致 evidence 计数不同”放在“均拒”清单中，容易产生相反断言。

**这处措辞沿用了 r2 第 156 行的不精确建议，本轮明确修正。** 按上下文可以理解为计数篡改，因此列为建议，不另判技术阻断。

第 98 行中的对应短句可直接替换为：

> 部分继承时，把 coverage 中 evidence 的 `refuted_count` 错误改成本案继承子集计数，而副本保持原样 → 拒绝且 reasons 含 `inherited refuted`。另加正例：副本同一证据对应 R1、R2，本案仅继承 R1；coverage 保留与副本全等的完整 evidence，`refuted_count` 仍为 2，`slots/count/origin` 仅描述实际继承的 R1，校验必须通过。

**3．建议：让 helper 示例签名完整列出已要求的输入**

定位：工单 **55、57、59 行**；锚「校验器新增 helper」。

第 59 行已要求调用方传入起始 slot、counts、states，第 57 行还要求绑定实际 coverage 路径；第 55 行的示例签名没有列出这些参数。正文足以指导施工，但统一签名能减少遗漏。

第 55 行的签名部分可直接替换为：

> `validate_repair_export_source(case_root, mint, gid, *, expected_probe_id, coverage_map_sha256, effective_candidates, coverage_path, coverage_from_slot, coverage_counts, coverage_states)`；后四项由调用方从本次已验证的源 coverage 取得，供路径绑定、范围检查和状态核验使用，不在 helper 内重复执行整套 coverage 校验。

**执行纪律与证据范围**

全程离线，未读取 `~/.codex/`、memories 或所列禁读目录；未新建、修改文件或 commit，复核前后工作树均干净。未运行会落盘的测试套件。一次 here-document 命令因 shell 试图创建临时文件而被沙箱拒绝，随后改用 `python3 -B -c` 完成纯内存检查。

| 条目 | 等级 | 工单位置 | 处理要求 |
|---|---|---|---|
| W3 先行后，开工及差异验收基线仍为 cc6298b | **必改** | 20、39–40、105 行 | 固定含 W3 的 W1_BASE，统一开工、统计和验收命令 |
| 部分继承与 evidence 计数篡改混写 | 建议 | 98 行 | 拆为合法部分继承正例和篡改计数负例 |
| helper 示例签名未列全已要求输入 | 建议 | 55、57、59 行 | 补齐 coverage 路径、起始 slot、counts、states |
| r2 的来源字段、副本绑定、CLI 冲突及链式转换 | 已核通过 | 36、48、55–82、99–100 行 | 无新增阻断项 |
