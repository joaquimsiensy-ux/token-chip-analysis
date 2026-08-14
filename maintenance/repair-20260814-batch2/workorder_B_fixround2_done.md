# 工单 B 消化轮 2 施工记录

> 基线：分支 `repair-20260814-batch2`，`HEAD=2806e90bc0d783a317694720163f2eed587f805b`。
> 状态：B-16/B-17/B-18 与 B-19 协议/fixture 子项已完成；B-19 的两份
> `_meaningful_text` docstring 裁决豁免（冻结优先），登记版本收口轮处理。
> 全程未执行 git 写命令，未触碰 `staging-pythia/` 或 PYTHIA 历史案根。

## 逐项处置

### B-16（P0）对账键改为黑名单安全方向

- `scripts/report/a4_gate.py:154-173` 的 `_norm_text` 先做 NFC，再移除
  `Cf/Cc/Zl/Zp/Mn/Me` 与 U+3164/U+115F/U+1160/U+FFA0/U+2800，Zs 折叠为普通
  空格，最后执行 `" ".join(split())`。箭头、数学符号、俄文及其他未点名实义字符
  原样保留。
- 注释明确区分两类安全方向：实义判定的未知字符若漏网会放行空壳，故用白名单；
  对账键的未知字符若保留只会触发人工复核，故用黑名单并 fail-closed。
- `claim_id` 的 all 语义未改；既有 U+200B/U+3164/U+0591 及正常 id 回归继续通过。
- 回归覆盖 `≥/≤`、`↑/↓`、`≈/≠`、俄文语义反转，五个显式零渲染点、Cf、
  NFC 后残留 Mn、NFC/NFD `á`、Zs 折叠，以及 `check_audit_registry_alignment`
  端到端 `≥/≤` 不一致拒绝。

### B-17（P1）路数增加语义锚

- 保留 execution receipt SHA 与 artifact SHA 两组既有字节去重。
- `adversarial_review_runner.py:373-398` 的 finalize 与
  `shared_release_receipt.py:697-730` 的消费侧各自新增 claim-review
  `(role, entrypoint 实物 sha256)` 集合；二元组重复立即拒绝。
- entrypoint SHA 不是聚合件自报值：两侧都先经 `validate_review_receipt` 对案内普通文件
  重算并核对，再取通过深验的 `execution["entrypoint"]["sha256"]`。
- 红例用同一 entrypoint 连跑两次，同一语义 artifact 仅 JSON 缩进不同；修后 finalize
  拒绝。消费侧另从合规聚合件注入重复二元组，修后独立拒绝。
- 绿例用两个实物 SHA 不同的 entrypoint 分别覆盖 C1/C2，仍正常通过。

### B-18（P1）特殊文件清理改 lexists 兜底

- `adversarial_review_runner.py:75-83` 新增统一 `remove_any`：
  `os.path.lexists(path)` 为真时，目录且非 symlink 才 `shutil.rmtree`，其余形态统一
  `unlink`。
- run_review 的 staging、receipt tmp 与 finalize tmp 失败清理均调用该函数。
- FIFO 红例同时制造 staging FIFO 与 receipt tmp FIFO：修前 `rc=2` 但两件残留；修后
  `rc=2` 且零残留。目录、symlink、正式位预存在与 socket 既有回归保持通过。

### B-19（P2）文档口径与 id 边界

- `references/analyze-workflow.md:158,162` 与
  `references/independent-audit-protocol.md:83,164` 均写明白名单覆盖 ASCII 可打印、
  拉丁补充与扩展、通用标点、CJK、假名、韩文音节、全角段；俄文、阿拉伯文等未覆盖
  语种与纯 emoji 文本会拒绝。外语原文应附中文说明，或保留 URL/数字等覆盖面内字符。
- 两份协议均明示 claim_id 不得含空格；存量 `A4 01` 形 id 重跑前必须先改两套
  registry 及其引用。
- 对 `scripts/tests/**/*.{py,json,jsonl}` 扫描内部空格 claim id，零命中。测试中的
  `" C1 "` 是验证外层 strip 后重复的故意负例，不属于内部空格 id。
- 两份 `_meaningful_text` docstring 状态为**裁决豁免（冻结优先），登记版本收口轮处理**：
  生产侧位于被要求整文件冻结的
  `scripts/lib/supply_truth_gate.py`；消费侧位于 shared 文件头至
  `validate_adversarial_review` 定义行前的冻结切片。改任一处都会直接违反本工单
  “只 import 不改”或“保护切片 SHA 修前后一致”的铁律；没有用运行时改 `__doc__` 等
  规避手法伪装完成。裁判决定冻结铁律优先，故本轮豁免 docstring 子项；语种覆盖面与
  双写声明以 `references/analyze-workflow.md` 和
  `references/independent-audit-protocol.md` 两份权威协议文档为准。此项继续列入
  “发现未修”，待版本收口轮解除冻结后处理。

## 红到绿证据

### 先红

在只改测试、未改生产代码时运行：

```text
python3 scripts/tests/test_repair_batch2_f02.py
rc=1
FAIL workorder B F-02 regressions: 10
```

十个失败分别为：B-16 三组符号、俄文、NFC/NFD、端到端反转；B-17 finalize 与消费
侧重复 entrypoint；B-18 FIFO 残留；B-19 两份协议缺覆盖/边界文字。不同 entrypoint 真
两路绿例在红阶段已通过，证明 fixture 本身有效。

### 修后绿

```text
python3 scripts/tests/test_repair_batch2_f02.py
rc=0
PASS workorder B F-02 regressions

python3 scripts/tests/test_repair_batch_a.py
rc=0
PASS batch A F-01/F-02 regressions 44/44

python3 scripts/tests/test_a4_gate.py
rc=0
a4_gate 契约测试全部通过（23 项）

python3 scripts/tests/test_audit_release_gate.py
rc=0
PASS: audit_release_gate ... 十一类契约全过
```

收紧重排版同语义副本与五点名字符/Zs 测试后，`test_repair_batch2_f02.py` 再跑仍
`rc=0`。

### 裁决后收尾复验

```text
python3 scripts/tests/test_repair_batch2_f02.py
rc=0
PASS workorder B F-02 regressions

python3 scripts/tests/test_a4_gate.py
rc=0
a4_gate 契约测试全部通过（23 项）

git diff --check
rc=0
无输出
```

### 全量套件与环境复跑

沙箱内 `python3 scripts/tests/run_all.py`：`rc=1`，除以下两项外全部 PASS；两项均在
创建 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 时被沙箱以
`PermissionError: [Errno 1] Operation not permitted` 拒绝：

- `test_batch3_solana_vertical_slice.py`
- `test_batch3_evm_vertical_slice.py`

在获准 loopback 环境复跑原命令：

```text
python3 scripts/tests/test_batch3_solana_vertical_slice.py
rc=0
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release

python3 scripts/tests/test_batch3_evm_vertical_slice.py
rc=0
PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
```

因此业务测试失败为零；沙箱能力限制与获准环境通过证据分开记录，没有把沙箱
`run_all rc=1` 写成字面全绿。

## 六视角①②自审

### ① 字段来源审计

- B-16 的键只取实际正文字符并现场做 Unicode NFC/category 运算，不信 registry 自报的
  “已规范化”字段。
- B-17 的语义锚取 `validate_review_receipt` 深验后的 role 与案内 entrypoint 实物 SHA；
  path/size/SHA、普通文件 containment、receipt/artifact/registry 绑定先全部重验，不信
  aggregate 自报路数或自报 entrypoint 哈希。
- B-18 直接以 `os.path.lexists` 和实际文件类型分派，不信调用者声明的形态。
- B-19 fixture 结论来自仓库文本扫描零命中，不以文档声明代替磁盘实态。
- 结论：未发现新增关键字段依赖未重验自报值。

### ② 失败分支审计

- B-16 保留未知符号/语种会造成文本不一致并阻断，漏网方向为 fail-closed；点名零渲染
  字符才删除。
- B-17 任一重复二元组在 finalize 或消费侧均抛 `ValueError`；不会 warning 后继续生成
  或接受 PASS 聚合件。两个不同 entrypoint 的正例不误伤。
- B-18 staging/tmp 的普通文件、目录、symlink、FIFO 等都进入兜底删除；删除自身若失败
  会继续抛异常，不会把失败运行包装为成功。
- `audit_release_gate.py:836-851` 未改；`check_adversarial` 在 schema 预检后转调 shared
  深验，shared 的 B-17 拒绝会被转成 release errors，不存在另一路裸放行。
- 结论：未发现新增 warning-as-success 或失败半成品放行面。

## 保护面与越界自证

- shared 保护切片为文件头至 `validate_adversarial_review` 定义行前（当前定义行 657，
  保护区 1-656）：修前、修后 SHA-256 均为
  `e4174f14b220989ffa546d088b25f8c598e0c9119e2991c55b21a3d414854f93`。
- `scripts/lib/supply_truth_gate.py` 当前与 HEAD 相同：
  `2da44c487273ba7671a5b443ab28d7e9d46a58fc6e5282e501deb5e784506ba4`。
- 工单 C 已收口文件当前与 HEAD 相同：
  - `scripts/lib/camp_series_provenance.py`：
    `b6a8da352b99eb8014cd2b7c951488b7cbd22460420310becf3b332a2f352a7c`
  - `scripts/solana/replay_edges.py`：
    `80c69bdedac9fd6d513c4e6b631fe7ecf4ef53a58bca55e1d342f1d58aa4c93a`
  - `scripts/report/state_from_facts.py`：
    `919604f3997f36487744f1c6f37aecfbcbb769c576e5facc1a04540dcfb0e9a9`
  - `scripts/tests/test_repair_batch_c.py`：
    `f2f9697e1d958d572dfaec72da1fb55c58b200eaf43924ccb61f332da2790fea`
  - `scripts/tests/test_review_resume_integrity.py`：
    `3f0dfbc9767e9777fa88805ea9aca2d99d30f9a00f79c8c7d6f27c2c9aaa2e98`
  - `maintenance/repair-20260814-batch2/import_pythia_legacy.py`：
    `ce13ee2afbc40d27193060f40220bcc21a040e35cce1e9f7403fa54467c7e597`
- `scripts/report/audit_release_gate.py` 当前与 HEAD 相同，SHA-256
  `f58a48e8e11ade54c5d4d562486ff1807d98cab2309b687e7155a6f7a2e6b6c1`；本轮零 hunk，
  因而没有超出“只动 check_adversarial 相关行”的边界。
- `git diff --check`：`rc=0`，无输出。

## 发现未修

1. **B-19 docstring 裁决豁免（冻结优先），登记版本收口轮处理**：两份 docstring 都位于
   明确禁止改动的文件/切片；裁判决定冻结铁律优先，本轮不放宽
   `supply_truth_gate.py` 整文件冻结与 shared 保护切片 SHA。语种覆盖面与双写声明以
   `references/analyze-workflow.md` 和 `references/independent-audit-protocol.md` 两份
   权威协议文档为准；当前实现行为、两侧行为向量及协议文档均已闭合，但不能声称源码
   docstring 已补，待版本收口轮解除冻结后处理。
2. **any 语义固有边界**：`零宽×2000＋单可见字符` 仍会放行；这是“证据够不够”的
   策略阈值，与 `evidence=["-"]` 同口径，留 R10 台账。
3. **B-09/B-15/risk_flags**：维持消化轮 1 登记，本轮未扩 scope、未改变行为。

## 变更范围

- `scripts/report/a4_gate.py`
- `scripts/report/adversarial_review_runner.py`
- `scripts/report/shared_release_receipt.py`（仅 `validate_adversarial_review` 段）
- `scripts/tests/test_repair_batch2_f02.py`
- `references/analyze-workflow.md`
- `references/independent-audit-protocol.md`
- 本记录

除上述文件外无工作树改动；无 git commit、add、checkout、reset、stash 或其他 git 写操作。
