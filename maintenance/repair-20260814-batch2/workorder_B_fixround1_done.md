# 工单 B 消化轮 1 完工记录

## 一、施工基线与边界

- 分支：`repair-20260814-batch2`
- 冻结 HEAD：`c9afcfe951589edd060a6da572685df3bd676571`
- 开工时工作树：干净。
- 施工前完整读取：`workorder_B_fixround1.md`、`blindreview_B.md`。
- 全程未执行任何 git 写命令；只使用 `git status/diff/show/branch/rev-parse` 做只读核验。
- `scripts/lib/supply_truth_gate.py` 仅由 runner import，文件本身未改。
- `shared_release_receipt.py` 仅改 `validate_adversarial_review` 定义行开始的函数体及其后的
  adversarial 读取点；waiver/approval 保护切片未动。
- `audit_release_gate.py` 仅改对抗复核相关的常量导入、严格 JSON loader、
  `check_adversarial` 与该 loader 的调用点。
- 工单 C 文件、`staging-pythia/` 与 PYTHIA 历史案根未触碰。

施工期间工作树另出现三份非本单未跟踪文件：`blindreview_C.md`、
`workorder_B_fixround1_amendment.md`、`workorder_C_fixround1.md`；本单未读取、未修改、未纳入施工。

## 二、逐项处置

### B-01/B-02/B-03：人工文本面升为实义判定

- `adversarial_review_runner.py` 删除 `_nonempty_string`，从
  `supply_truth_gate.py` 单源 import 正向白名单版 `_meaningful_text`。
- runner 的 registry claim id、artifact claim_id、evidence、alternative explanations、
  blocker id/resolution、critic findings/non_covered、role、target chain/token 均不再由
  `strip()` 决定实义性。
- critic 的 `findings[]`、`non_covered[]` 从“只验数组类型”升为逐元素实义校验；空数组仍按
  原协议允许。
- shared 在 `validate_adversarial_review` 内把消费侧已有 `_meaningful_text` 显式注入
  registry/artifact/receipt/blocker 深验；未调用生产侧实义判定。
- 端到端锚覆盖 U+200B/U+2060/U+3164/U+2800 evidence、resolution 与 critic 两数组；
  原全空白链不再能产 execution receipt 或 aggregate PASS。

### B-11：claim_id 与 A4 对账的零渲染规范化

- runner 新增零渲染剥除与 claim id 规范化：剥除 Unicode `Cf/Cc/Zs/Zl/Zp`，并显式覆盖
  A 消化轮 2 的 13 个探测点：U+3164/U+2800/U+115F/U+FFA0/U+0301/U+034F/U+E000/
  U+0378/U+0300/U+1160/U+17B4/U+17B5/U+2065。
- registry、artifact 的重复/越界/并集比较均使用规范化 id；`"C1"` 与
  `"C1\u200b"`/`"C1\u3164"` 视为同一 id。
- shared 保留消费侧本地规范化实现并注入深验，不依赖 runner 的字符剥除函数。
- `a4_gate.py check_audit_registry_alignment` 的 A4/audit/verdict id 与命题文本比较前使用
  同款剥除；正常命题对账保持通过。

### B-04：staging 与 receipt tmp 目录清理

- `run_review` 异常清理对精确 staging/tmp 路径分形态处理：普通文件/符号链接用
  `unlink`，真实目录用 `shutil.rmtree`。
- 反例 entrypoint 同时建立 staging 目录与 `.dir_execution.json.tmp.<runner-pid>` 目录，
  runner 返回 2，artifact/receipt 不落盘，两个目录均清零。

### B-05：N 路复核按内容身份去重

- finalize 在路径去重之后，再分别要求 `execution_receipt.sha256` 集合与
  `artifact.sha256` 集合无重复；任一重复即拒。
- shared 从案内实物三验后独立重建两个 SHA 集合并执行同款拒绝，聚合层自报路数不可信。
- 回归覆盖：receipt 换名副本重交、两份不同路径同字节 artifact、消费侧手抄 6 路 reviews。

### B-06：四处裸闸测试钉与临时削除自证

四个原有闸均保留，并新增负向锚。施工中逐项临时削除、运行完整 F-02、立即恢复；四次
均得到预期红态：

1. 删除 shared 的 `registry_ref != actual_registry_ref`：`rc=1`，仅
   `消费侧聚合 claim_registry 自报假 ref 必须拒绝` 失败。
2. 删除 runner 输出位 symlink 拒绝：`rc=1`，artifact/receipt 两锚失败，均实际写到
   case-root victim，证明锚咬中。
3. 删除 finalize 输出预存在拒绝：`rc=1`，仅 finalize 防覆盖锚失败且调用返回 0。
4. 删除 run_review artifact/receipt 正式位预存在拒绝：`rc=1`，两锚失败，sentinel 被
   实际覆盖，证明锚咬中。

每次自证均用 `apply_patch` 恢复原闸；最终 F-02 与全量 suite 全绿。

### B-07：execution receipt ref 补 size

- shared 对 execution receipt 与 artifact 同深执行 path/size/sha256 三验。
- 聚合件把 execution receipt 的 `size` 手改为 `999999`、保持 sha 正确时，消费侧拒绝。

### B-08：schema 与迁移提示单源化

- shared、audit 均 import runner 的 `AGGREGATE_SCHEMA` 与 `V3_RERUN_HINT`；删除两处
  `adversarial-review/v3` 运行时字面量和 audit 的迁移提示副本。
- `invariant_scan.py` 的静态常量解析补充只认 imported `AGGREGATE_SCHEMA` 的窄适配；
  不把其他 importer 误扫为 schema producer。最终 invariant manifest 通过。

### B-12：对抗复核链统一拒绝非有限 JSON 数值

- runner 的正式 JSON 解析统一经 `_loads_json(..., parse_constant=...)`，默认使用从
  `supply_truth_gate` import 的 `_reject_constant`。挂载点包括 claim registry、受控 staging
  artifact、绑定 artifact、execution receipt、accounting target、blockers 与 finalize receipt
  预解析。
- runner 的深验接口允许显式注入 `reject_constant`；shared 注入自身 `_reject_constant`，
  因而 registry/artifact/receipt 深层仍保持消费侧独立。
- shared 的 aggregate 解析点（`validate_adversarial_review`、`validate_sources`）均使用本地
  `_reject_constant`；audit 的 adversarial 专用 loader 也委托 shared 本地实现。
- 循环/共享夹具锚覆盖各挂载点 NaN；另用 `consumer-side reject marker` 证明 shared 深层
  registry 解析实际调用消费侧回调，不是默认落回生产侧。

### 文档 B-10/B-13/B-14 与可执行性

- `independent-audit-protocol.md` 补：公开哈希非签名与威胁边界、finalize 非唯一物理路径、
  TOCTOU 后删除该角色 artifact＋execution receipt 的恢复动作、entrypoint 随案保留义务、
  critic 完整命令行、blockers 数组结构示例。
- `analyze-workflow.md` A4 §5 改为“证据含实义字符（不可见字符不算）”。

## 三、红到绿与验收证据

### 先红

- 修改测试前的存量基线：`python3 scripts/tests/test_repair_batch2_f02.py`，`rc=0`。
- 只修改/新增测试、不改生产代码后运行同命令：`rc=1`，共 26 项失败。失败族包括：
  零宽 evidence/resolution/critic、U+3164/U+2800、视觉同名 claim、A4 规范化、目录残留、
  receipt/artifact 注水、execution size、NaN 全挂载点、常量单源与文档契约。
- B-06 四闸另按上一节完成四次“摘掉即红”自证。

### 转绿

- `python3 scripts/tests/test_repair_batch2_f02.py`：`rc=0`，末行
  `PASS workorder B F-02 regressions`。
- `python3 scripts/tests/test_repair_batch_a.py`：`rc=0`，末行
  `PASS batch A F-01/F-02 regressions 44/44`。
- `python3 scripts/tests/test_a4_gate.py`：`rc=0`，23 项全过。
- `python3 scripts/tests/test_audit_release_gate.py`：`rc=0`。
- `python3 scripts/tests/invariant_scan.py`：`rc=0`；最终 census：
  `receipt_producers=55, receipt_consumers=73, transport_calls=62, atomic_writes=48,`
  `formal_entrypoints=58, exceptions=0`。
- 沙箱内首轮 `run_all.py` 如实得到 `rc=1`：本单 B-08 先触发 invariant 对 imported schema
  不识别的真实回归，另两项 vertical slice 因 `127.0.0.1 socket.bind` 被环境以 EPERM 阻断。
  invariant 扫描器窄修后单测 `rc=0`。
- 在允许 loopback 的获准环境运行 `python3 scripts/tests/run_all.py`：`rc=0`，Solana/EVM
  vertical slice 均 PASS，末行 `全部通过`。
- `git diff --check`：`rc=0`，无输出。

## 四、六视角自审 ①：字段来源与信任根

1. 人工文本：生产侧信任根是 `supply_truth_gate._meaningful_text` 的正向可渲染白名单；
   shared 使用自身独立白名单实现。`risk_flags` 的黑名单函数未被复用。
2. claim 身份：比较键来自当前 registry/artifact 实物经零渲染规范化后的 id，不信肉眼相似
   或聚合层自报；A4 净室表也以同一规则对账。
3. 路数：finalize/shared 均从实际绑定 ref 取得当前 SHA256，分别对 execution 与 artifact
   内容去重；路径数量、文件名、inode 不再充当独立路数证明。
4. ref：registry、artifact、execution receipt 均闭合到案内 regular file 的 path/size/sha256；
   producer/runner 继续绑定当前仓库脚本路径与 SHA。
5. schema/迁移提示：唯一运行时定义来自 runner；shared/audit 只 import，不再各自维护副本。
6. JSON 数值：生产链所有解析点由 supply truth 拒绝器兜底；消费链由 shared 自身拒绝器
   兜底，测试对两侧回调来源做了可区分验证。

结论：本轮新增判断均从当前案内字节、当前仓库 producer 或明确的两侧校验实现派生；没有
把聚合层自报、路径换名或不可见 Unicode 当成可信证据。

## 五、六视角自审 ②：失败路径、清理与边界

1. 无实义文本、视觉重复 claim、重复内容路数、ref size/sha 撕裂、NaN 均 fail-closed；
   runner CLI 返回 2，shared/audit 抛错或记录发布阻断。
2. staging/tmp 失败清理覆盖文件、symlink、目录三形态；只删除本次计算出的精确随机路径，
   未扩大到案根或 glob。
3. artifact/receipt/final aggregate 正式位预存在一律拒绝；B-06 临时削除证明每个保护都有
   独立负向测试，不是形式覆盖。
4. finalize 仍用同目录独占 tmp、flush＋fsync、`os.replace`；异常清理精确 tmp，不留半件。
5. shared/audit 仍从当前实物重建，不把 finalize 当不可绕过的执行证明；文档已明确该边界。
6. 所有攻击夹具只在 `TemporaryDirectory`；四次削除后均立即恢复并由最终全量绿确认。

结论：失败出口保持 fail-closed，目录型残留已闭合；临时破坏自证未遗留弱化代码或案根污染。

## 六、保护面自证

- shared waiver/approval 切片定义：文件头至
  `validate_adversarial_review` 定义行前（当前定义行 657）。修前与修后 SHA256 均为
  `e4174f14b220989ffa546d088b25f8c598e0c9119e2991c55b21a3d414854f93`。
- `supply_truth_gate.py` 当前/HEAD SHA256 均为
  `2da44c487273ba7671a5b443ab28d7e9d46a58fc6e5282e501deb5e784506ba4`。
- 工单 C 四文件当前/HEAD SHA256 逐一相等：
  - `camp_series_provenance.py`：`f43b91a4f52cfe6e14469c34173c9a60a7880a6383cf64e399a4c5d1687e59e9`
  - `replay_edges.py`：`a9979f4c878440920033270c51868219066f74577b94b500d57143e47922f35f`
  - `state_from_facts.py`：`0fddc19f835eecfbbe10ee1319a568c195437a1e47019741774c777fd172274c`
  - `test_repair_batch_c.py`：`cb19424f10de1d2b3f49d4fd2a1f76170f3f0bae0a40ad27c156fa24b3f2e530`
- `git diff --name-only` 对上述五文件与 `staging-pythia/` 无输出。
- `audit_release_gate.py` 本单相关行：22（runner 常量 import）、822–851（adversarial
  严格 loader＋`check_adversarial`）、1114–1115（仅 adversarial 文件转用严格 loader）。

## 七、发现未修

- B-09：blocker 是否存在仍由 blockers 输入自报，未与 artifact 语义联动；超出 F-02
  “客观结构”边界，留 R10 台账待用户裁决。
- B-15：runner subprocess 仍无 timeout；属存量问题，非本单引入。
- `risk_flags.py` `_strip_invisible_space` 仍是挡不住 U+3164/U+2800 的黑名单版；本单未动，
  留批 4 守卫收尾轮统一处理。
- 除上述登记项外，本工单声明范围内无已知未修缺口；最终闭合仍以盲审员 B 第二轮为准。

WORKORDER_B_FIXROUND1_COMPLETE

## 八、裁决修正：claim_id all 语义

### 修正范围与实现

- 冻结基线仍为 `c9afcfe951589edd060a6da572685df3bd676571`；在 B 消化轮 1 未提交改动上
  原位修正，全程未执行任何 git 写命令。
- `adversarial_review_runner.py` 删除 `Cf/Cc/Zs/Zl/Zp` 类别黑名单、13 码位枚举、
  `_strip_zero_rendering` 与 `_normalize_claim_id`。新增标识符合法性判定：先 `strip()`
  外层空白，再要求非空且 `all(_meaningful_text(char) for char in stripped)`；生产侧继续
  直接复用已 import 的 `supply_truth_gate._meaningful_text`。
- registry id、artifact `claim_id`、blocker id 均按上述 all 语义校验；含任一非白名单字符
  直接报 `id is invalid`。合法 id 的集合、越界、覆盖与重复判断均回到 `strip()` 后精确值，
  不再剥除字符后比较。
- `shared_release_receipt.py` 删除函数内消费侧枚举与 `normalize_claim_id`，只把本文件已有的
  `_meaningful_text` 注入 runner 深验，因此消费侧独立执行同一 all 语义；waiver/approval
  保护切片未动。
- `a4_gate.py check_audit_registry_alignment` 的 A4/净室/verdict id 同样先 strip 后逐字符
  all 校验。claim 正文仍属自由文本：比较键逐字符只保留 `_meaningful_text(char)` 为真者
  与普通空格，删除其余字符后再执行 `" ".join(split())`；U+0591 不再进入比较键。
- `test_repair_batch2_f02.py` 新增 U+200B/U+3164/U+0591 的 runner/shared claim id、
  blocker id 与 A4 id 拒绝锚；新增 `C1`＋`C1\u0591` 非法而非重复、`C1`＋` C1 `
  strip 后精确重复、C1-C99/连字符/下划线正常 id、A4 正文 U+0591 等价锚。
- `test_repair_batch_a.py` 将旧 13 码位十六进制枚举改为测试字符串向量并加入 U+0591，
  保留 A 轮行为覆盖，同时清除 `scripts/` 下 `0x3164` 文本命中。

### 红→绿证据

- 只改测试、未改本次生产代码时运行
  `python3 scripts/tests/test_repair_batch2_f02.py`：`rc=1`，末行
  `FAIL workorder B F-02 regressions: 11`。真实失败包括 runner/shared 的三种非法 id，
  `C1`＋`C1\u0591` registry、A4 正文 U+0591 与 A4 三种非法 id；其中 U+0591 在旧
  黑名单下确实放行或仅报集合不一致，证明第 14 码位可重演。
- 完成生产修正与补强锚后：
  - `python3 scripts/tests/test_repair_batch2_f02.py`：`rc=0`，末行
    `PASS workorder B F-02 regressions`；
  - `python3 scripts/tests/test_repair_batch_a.py`：`rc=0`，末行
    `PASS batch A F-01/F-02 regressions 44/44`；
  - `python3 scripts/tests/test_a4_gate.py`：`rc=0`，23 项全过；
  - `python3 scripts/tests/test_audit_release_gate.py`：`rc=0`；
  - `python3 scripts/tests/invariant_scan.py`：`rc=0`，census 为
    `receipt_producers=55, receipt_consumers=73, transport_calls=62, atomic_writes=48,`
    `formal_entrypoints=58, exceptions=0`。
- 沙箱内首次 `python3 scripts/tests/run_all.py`：`rc=1`，仅
  `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 因
  `127.0.0.1 socket.bind` 返回 `PermissionError: [Errno 1] Operation not permitted`；其余
  全部 PASS。随后在允许 loopback 的获准环境复跑完整同命令：`rc=0`，两项 vertical
  slice 均 PASS，末行 `全部通过`。
- `git diff --check`：`rc=0`，无输出。

### 枚举清零与保护面自证

- `rg -n 'zero_rendering_extras|0x3164' scripts/`：`rc=1`，无输出，机械清零成立。
- shared waiver/approval 保护切片仍定义为文件头至 `validate_adversarial_review` 定义行前；
  定义行仍为 657，修正前后 SHA256 均为
  `e4174f14b220989ffa546d088b25f8c598e0c9119e2991c55b21a3d414854f93`。
- `scripts/lib/supply_truth_gate.py` 当前/HEAD SHA256 均为
  `2da44c487273ba7671a5b443ab28d7e9d46a58fc6e5282e501deb5e784506ba4`。
- 工单 C 四文件当前/HEAD SHA256 逐一相等：
  - `scripts/lib/camp_series_provenance.py`：
    `f43b91a4f52cfe6e14469c34173c9a60a7880a6383cf64e399a4c5d1687e59e9`
  - `scripts/solana/replay_edges.py`：
    `a9979f4c878440920033270c51868219066f74577b94b500d57143e47922f35f`
  - `scripts/report/state_from_facts.py`：
    `0fddc19f835eecfbbe10ee1319a568c195437a1e47019741774c777fd172274c`
  - `scripts/tests/test_repair_batch_c.py`：
    `cb19424f10de1d2b3f49d4fd2a1f76170f3f0bae0a40ad27c156fa24b3f2e530`
- `git diff --name-only` 对上述五个受保护文件与 `staging-pythia/` 无输出；
  `git status --short -- staging-pythia PYTHIA pythia` 无输出。

WORKORDER_B_AMEND_COMPLETE
