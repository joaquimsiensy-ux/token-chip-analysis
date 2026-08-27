# 【登记工单】F-03 批 2:第二段——producer_history 登记 + 版本面 6.52.14

- 基线:main = `f0469a376c0101759f260dafb1678c00ff785d65`(第一段修复主体,已含批 1+1b 全部代码/测试/文档/契约)。
- 施工方:codex,**只改文件,不执行任何 git 写操作**;裁判方验收后代 commit。
- 本批是两段提交协议的第二段:只做登记面与版本面,**禁改任何代码/测试逻辑/契约/资产**。

## 任务(全集,不得增减)

### 1. `scripts/lib/producer_history.py` 增两条登记

被替换的探针版本是 `bccf1802…`(已在册,勿动)。新现役探针按准入纪律登记,**两协议各一条**,插入位置紧跟现有两条 bccf1802 条目之后,字段形态照抄现有条目:

- `script`: `scripts/solana/sqd_coverage_probe.py`
- `sha256`: `be415db3552588532ff195126ddd53aefe9d3c14785da64c2be4cf23804f7bea`
- `commit`: `f0469a376c0101759f260dafb1678c00ff785d65`
- `protocol`: 一条 `sqd-solana-coverage/v1`、一条 `sqd-solana-coverage-pointer/v1`
- `status`: `ACTIVE`
- `reason`(大白话,一句):v6.52.14 F-03 修复——共享地图复用闸身份三分类+历史锚+并发重验版探针(coverage 条);同一冻结探针的原子 CURRENT 指针生产者(pointer 条)。英文表述参照相邻条目风格即可。

准入自检(结果写 done 报告):`git show f0469a376c0101759f260dafb1678c00ff785d65:scripts/solana/sqd_coverage_probe.py | shasum -a 256` 必须逐字节等于上述 sha256。

### 2. 版本面 6.52.13 → 6.52.14(三处)

- `VERSION`(整文件单行)
- `pyproject.toml` :15 `version = "6.52.14"`
- `SKILL.md` :23 版本注释行(`skill-version: 6.52.14`)

### 3. `CHANGELOG.md` 增 6.52.14 条目

两处结构照现有惯例(顶部活跃列表一条 + 正文归档段一条,格式抄 6.52.13 条目)。内容大白话覆盖:F-03 出处(codex 六视角 review 2026-08-27 P1,修复中新引入 b005a468);身份三分类+历史锚+head 单调+模板绑定;重验仅连续合并+并发+失败整体回退+失败时撤销本轮 recheck 覆盖声明;validate_shared_map 扩全;validate_coverage 接 producer_history(D1 用户裁决);CT-SQDGAP-35;20260827 资产零字节改动即刻可复用;盲审两轮(1 轮 BLOCK 三项消化→2 轮 PASS);SUITE 138→139。

## 白名单(全集,越界停工)

`scripts/lib/producer_history.py`、`VERSION`、`pyproject.toml`、`SKILL.md`、`CHANGELOG.md`、`maintenance/repair-20260827-f03-sharedmap/batch2_done.md`(done 报告自身)。

## 完工标准

1. 本机 `python3 scripts/tests/run_all.py` 全量原样贴报告(重点:test_version_consistency、test_collector_history/producer 登记 git-可复算类守卫、changelog_lint 必须绿;沙箱环境性失败如实标注);
2. `batch2_done.md`:diff 摘要+准入自检输出+工单外发现清单;
3. 工作树只含白名单内改动。
