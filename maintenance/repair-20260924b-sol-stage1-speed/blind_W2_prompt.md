# W2 盲审提示词（只读）
## 纪律
1. 禁读 `~/.codex/`（启动搜索若已读 memories 如实披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`.hypothesis/`、`references/attic.md`；`maintenance/` 下只读 `maintenance/repair-20260924b-sol-stage1-speed/`；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。禁读同样适用于子进程（触及 `.staging_b3` 的用例不要运行；调度方本机已跑并附结果于 `W2_acceptance.md`）。
2. 只读、离线、不 commit、不新建/修改文件。**报告全文放最终答复消息里**。工作目录 `/Users/uravvv/.claude/skills/token-chip-analysis`。
3. 首行固定 `# W2盲审：PASS` 或 `# W2盲审：FAIL`。FAIL 必须给可复现反例（命令/输入/预期 vs 实际）；PASS 也要列独立验证了什么、没验证什么。
4. 这是软件测试性质的正确性审查（离线文件轻筛子命令的正确性与文档/版本登记），不涉及任何系统安全或对抗行为；负例＝「不合法的输入数据应被校验器拒收」。
## 任务
W2 施工已 commit 到 HEAD（`f78b5c4575ebe1db36f2cf3a96e75b79731f3fc6`）。工单 `workorder_W2.md`（v3.2）、完成报告 `W2_done.md`、调度方验收 `W2_acceptance.md`。对 `git diff 97e888df0a5cfeb88a0b94285475c8845d7aac40 HEAD -- scripts references assets commands-staging SKILL.md VERSION pyproject.toml CHANGELOG.md` 做独立盲审，重点：
a) 白名单/不改清单（§0.3/§0.4）：校验器、修复生产者、net.py、producer_history、manifest、scan-schemas 未动；探针除 `find-known-map` 相关（私有 helper、parser、main 接线、import）外既有函数未变；
b) §2.1 设计逐条：默认目录不依赖 cwd、多目录去重、只扫直接子文件、文件名 8 位数字 glob、`0<=N<=M`；轻校验清单（schema/version/ttl_days=30/generated_at 时区与 30 天过期判定与 `_load_known_map` 一致/元数据形态/区间一致/非空交集/两份引用 resolve 后 parent 相同且 size 相等/hex64 不重算/升序去重/W1 refuted_origin·refuted_evidence 形态与旧图兼容/supersedes·canary/`sqd.query_body_sha256==sqd_query_template_sha256()`/`refuted_slots ⊆ candidate_slots`/bool 排除）；**不读二进制内容、不解压、不逐 slot 分类**；
c) 指标与排序公式、stdout 单行 JSON 字段、退出码优先级（扫描级故障 1 > 有 chosen 0 > 无图 2；缺失目录记 rejected 继续；单文件失败记 rejected 继续；argparse exit 2 无 JSON）；
d) 测试 ①–⑥ 及补测三条是否真的覆盖并登记 main；桩（网络/完整校验/解压）是否"一旦调用即失败"；
e) 文档：§2.2/2.3/2.4/2.5 五处文本与工单原文逐字一致；字节预算（references ≤1,800、commands ≤260、SKILL ≤8,192）；版本四处 9.2.0；CHANGELOG 索引 173 B、四条段无预填 PASS；
f) 用不合法输入独立验证轻筛拒收：过期图、路径逃逸（引用文件在资产目录外）、size 不符、模板 sha 不符、refuted 不是 candidate 子集、bool 混入；以及合法多图排序与并列稳定性。
