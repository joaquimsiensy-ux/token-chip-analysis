# 【登记工单】F-03b 批 4:第二段——producer_history 登记 + 版本面 6.52.15

- 基线:main = `cdc4f87`(F-03b 主体段)。施工方 codex,只改文件、禁 git 写操作;裁判方验收后代 commit。
- 只做登记面与版本面,禁改任何代码/测试/契约/资产。

## 任务(全集)

### 1. `scripts/lib/producer_history.py` 增两条登记
紧跟现有 be415db3 两条之后,字段形态照抄:
- script: `scripts/solana/sqd_coverage_probe.py`
- sha256: `c4980c984b08d27f5a7e46db50f97c9c16e47ea491f37a459b3773f939218769`
- commit: `cdc4f876`(用完整 40 位:cdc4f87f8e3ee4d181760cb8455d688f23049f20)
- protocol: 一条 `sqd-solana-coverage/v1`、一条 `sqd-solana-coverage-pointer/v1`
- status: ACTIVE
- reason 一句(英文,风格照相邻条目):v6.52.15 F-03b 失败分级探针(限流段剔除转 full,mismatch 仍整体回退)/同一冻结探针的原子 CURRENT 指针生产者。
自检:`git show <完整commit>:scripts/solana/sqd_coverage_probe.py | shasum -a 256` 必须等于上述 sha,输出写 done 报告。

### 2. 版本三处 6.52.14 → 6.52.15
`VERSION`、`pyproject.toml`:15、`SKILL.md`:23。

### 3. `CHANGELOG.md` 增 6.52.15 条目(活跃索引一行+归档段一条,格式照 6.52.14)
大白话覆盖:出处=F-03 live 实测 1,182 限流失败零 mismatch 使复用必然回退;失败三分级(mismatch 整体回退不变/请求失败重试后仅剔除段转 full/canary 段失败整体回退);map-reuse 按验证子区间逐段声明+案外 recheck 撤销(有杀变异测试);unverified_ranges/recheck_stats 审计字段(重试 mismatch 不污染);盲审 R1 BLOCK 两项消化→R2 PASS;SUITE 139 不变(测试组 9→15 在既有文件内)。

## 白名单
`scripts/lib/producer_history.py`、`VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md`、`maintenance/repair-20260827-f03-sharedmap/batch4_done.md`。

## 完工标准
本机 run_all 全量原样贴报告(version/changelog/登记 git-可复算守卫必须绿);done 报告含 diff 摘要+准入自检+工单外发现。
