# 工单 U3：HyperSync CSV 同哈希续采闸（方案 B）

> 三单元收口工程第 3 单元。基线 `main=aadbe59`（6.47.1，单元1/2 及各自盲审消化已收口），动工前 `git rev-parse HEAD` 核对，不一致即停工留报告。
> fetch_hypersync.py 全部行号已由调度方在该基线亲核（该文件自 2d69373 后未被本工程改动）；发现不符按"不一致即停工"纪律办。
> 你（codex）只施工不 commit；报告写到 `workorder_U3_done.md`。

## 0. 边界

- **白名单**：
  ```
  scripts/evm/fetch_hypersync.py        scripts/evm/collector_history.py
  scripts/tests/test_csv_resume_collector_gate.py（新建）
  scripts/tests/test_collector_history.py
  scripts/tests/run_all.py（仅加注册行）
  references/data-pipeline-evm-channels.md（不得动 CT-SEMANTIC-33/34 needle 字符串）
  maintenance/closure-20260817-threeunit/workorder_U3_done.md（施工报告）
  ```
- **明确不改**：channels_preflight.py（`_csv_collector_provenance` 的历史哈希放行对消费场景是合法语义，收紧它会误伤 preflight 验旧 receipt）；csv_collector_receipt.py（结构断言写测试里，若须加注释在报告说明）。
- 不 commit；先红后绿。

## 1. 背景（一句话）

CSV 回执的采集者是顶层单值，`--resume-receipt` 跨版本续采会把旧段整体收进当前脚本署名的新回执（归属重写）——本单元加同哈希续采闸：脚本升级后必须另开新 CSV 作为新 channel 段接入（preflight 多 channel 拼接已支持，NES 39 份实件本就这么用）。

## 2. 施工内容（行号基准发放前核对；0ec6d1e 参考值）

1. **生产侧闸**：fetch_hypersync.py resume 分支（:90-106）在 `_csv_collector_provenance` 重验通过之后**独立加**校验——`prev["collector"]["sha256"] == <启动冻结哈希>`；不等 fail-closed，错误信息含指引："采集脚本已升级，禁止跨版本续采同一 CSV；请以前驱 receipt 覆盖终点为新起点另开 CSV/receipt，作为新 channel 段接入 channels.json"。prior 缺 collector/畸形同拒。
2. **TOCTOU 启动冻结**：进程启动算 `collector_start_hash`；resume 比对前驱用启动哈希；写 receipt 前（:196-219 附近）重算要求未漂移；receipt 的 collector.sha256（:207-208）用**启动哈希**（现行是写时即时算 `_sha256_file(Path(collector))`，改为启动哈希）。**等深延伸（U2b/R6 语义）**：启动冻结时查 collector_history 全表 hash-wide REVOKED，当前哈希在内即拒启动（"当前脚本版本已被吊销"同文案）。
3. **维护纪律**：被替换的 fetch_hypersync.py 现版本哈希 `cea82c7743f413555af0b913b1cb0662d52dbdd8e1686bc2443b2ca701266e84` 补登 collector_history（protocol="evm-collector-run/v2"，commit=`2d69373a2a2e0fdc08615e41c8a3dc9676cff22c`——调度方已考证：该 commit 树上此文件 sha256 与登记哈希逐字一致；40 位全哈希纪律）。⚠ U2b/B-02 纪律（maintenance-review-repair.md 已改写）：被替换版本按其生前签发过的**每个 protocol** 各补一条——本脚本生前只签发 evm-collector-run/v2 一线，故一条即可，报告确认此判断。
4. **语义声明**：data-pipeline-evm-channels.md 补段：自本版本起 v2 receipt 顶层 collector 保证覆盖全部 segments（同哈希续采闸）；此前多段 receipt（如存在）归属置信度=顶层自报，标 legacy confidence，**不声称修复历史**。不碰 CT needle 行。
5. **SQD 结构断言**：测试固化 csv_collector_receipt.py 的单 segment（:34-36）+fresh_output（:15-16）结构性保证。
6. **U1 盲审跨单元传染修复（三条）**：
   - **重复 JSON 键闸（V-31 同构）**：resume 读 prior receipt 是键判定（`prev["collector"]["sha256"]`）——重复 `collector` 键可人机分裂。fetch_hypersync.py 的 prior receipt 读入（**:95** `prev = json.loads(...)`）改用 `scripts/lib/anchor_point_contract.strict_json_loads`（引用勿复制）。范围仅本脚本的 receipt 读入；preflight 侧 CSV 读入点已由 U2b/R9 收口，勿重复改。红态：重复 collector 键的 prior receipt 修前按后值放行、修后读入层拒。
   - **分派禁 fail-open**：prior receipt schema 判定显式白名单（evm-collector-run/v2），未知值 ValueError 不落默认分支。
   - **枚举/结构判定前收类型**：collector 字段取用前 isinstance(dict)、sha256 取用前 isinstance(str)，统一 ValueError 错误面（畸形 prior 不得以 TypeError/KeyError 逃逸）。

## 3. 测试矩阵（新文件，注册 run_all.py）

照施工计划 §5.3 六条：同哈希续采 PASS／跨哈希拒+指引文案／prior 缺 collector 拒／SQD 恒单段+拒已存在输出／升级接续正例（旧 CSV 封盘新 CSV 起采 preflight 多 channel 全绿）／TOCTOU 漂移拒签。

## 4. 完成标准

run_all 除 loopback 外全绿；负测红实证；git diff 只含白名单；报告含 cea82c77 git 考证、改动摘要、未尽事项。
