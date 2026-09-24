# 工单W1复核r4：通过

v4 已吸收 r3 的必改 1 和建议 2、3，可派工。本轮无新增必改、建议或存疑项，无需替换条文；未重复审查 r2/r3 已通过的其他事项。

当前 `HEAD=90579db4ad1ee69bc4f44010cb6d7264c2e62a5e`，已包含固定的 `W1_BASE=6b36dcdd043d0b2b51c03de9ab0bb555b25f436a`。实际执行用户指定命令：

```sh
git diff --quiet 6b36dcdd043d0b2b51c03de9ab0bb555b25f436a HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md assets
```

**退出码为 0。** 开工与报告基线已统一，W3 已提交差异不会计入 W1。

§2.6(c) 已明确区分两种情况：仅继承 R1 时，完整 evidence 保留 `refuted_count=2` 应通过；将 coverage 中该计数改为子集计数、而副本不变，应拒绝。此要求与第 80 行按副本完整映射核计数、evidence 全等的规定一致。

§2.2 helper 签名已列全 `coverage_path`、`coverage_from_slot`、`coverage_counts`、`coverage_states`，并明确由调用方传入已验证的数据，与路径绑定和状态核验要求一致。

全程只读、离线；未读取 `~/.codex/`、memories 或所列禁读路径，未新建、修改文件或 commit。复核前后工作树均干净。未运行施工测试，本次结论为工单可派工。

| 核对项 | v4 行号／锚 | 实测或核对结果 |
|---|---|---|
| 开工门禁 | 21／§0.1 | 通过：status 空；短 HEAD 为 `90579db`；祖先检查及指定 diff 均 exit 0 |
| 生产改动统计基线 | 40／§1.10 | 通过：三个生产文件相对 W1_BASE 的 numstat 为空；相对 cc6298b 的 diff 亦 exit 0 |
| 白名单差异基线 | 41／§1.11 | 通过：指定 stat 输出为空，未计入 W3 |
| 完成报告基线 | 106／§3 | 通过：门禁、numstat、stat 均统一使用 W1_BASE |
| 部分继承正例／篡改负例 | 99／§2.6(c) | 通过：合法部分继承与计数篡改已明确分开 |
| helper 完整签名 | 56、58、60／§2.2 | 通过：所需输入齐全，调用方责任明确 |
