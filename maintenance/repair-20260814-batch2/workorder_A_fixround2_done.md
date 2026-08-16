# 工单 A 消化轮 2 完工记录

施工分支：`repair-20260814-batch2`。开工 HEAD：
`58fdcfad3697c9d4556069c29b9b1dd39f0972ea`。开工时工作树干净。
全程未执行任何 git 写命令，未提交。

## 一、变更范围

- `scripts/lib/supply_truth_gate.py`：生产侧 R-01、R-03、R-04 收口。
- `scripts/report/shared_release_receipt.py`：消费侧独立实现同深收口；未改
  `validate_adversarial_review` 段。
- `scripts/tests/test_repair_batch_a.py`：R-01～R-05 定向回归、真实解析路径锚、
  内容身份与 evidence 内容夹具。
- 本文件：施工、双跑、边界与自审记录。

工单 C 文件、`invariant_manifest.json`、`staging-pythia/` 与 PYTHIA 历史案根均零改动。

## 二、逐项处置

### R-01：实义判定翻转为正向白名单

生产侧与消费侧各自保留独立同名 `_meaningful_text` 实现，不互相导入私有函数。
判定从 Unicode 类别黑名单翻转为“至少含一个明确批准的可渲染字符”。白名单覆盖：

- ASCII `U+0021–U+007E`；
- 拉丁补充/扩展 `U+00A1–U+024F`，排除软连字符 `U+00AD`；
- 通用标点 `U+2010–U+2027`；
- 已筛除组合/填充点的 CJK 标点段、平假名/片假名段；
- CJK 扩展 A、基本区；
- 韩文音节 `U+AC00–U+D7A3`；
- 全角可打印形式 `U+FF01–U+FF5E`。

白名单外字符可以与可见字符共存，但不能单独撑起实义性。原始盲审 13 码位已按
探测输出逐个入锚：`U+0301/U+0300/U+034F/U+3164/U+115F/U+1160/U+FFA0/`
`U+2800/U+17B4/U+17B5/U+E000/U+0378/U+2065`。每个码位均覆盖 approval
四字段、waiver 两字段、生产/消费两侧拒绝。混合串 `U+200B+U+3164`、双
`U+3164`、20 个 `U+2800`、三个 `U+200B` 均拒；`a+U+0301`、正常中英文、
纯中文及纯韩文音节“승인”均放行。

### R-02：四个 parse_constant 挂载点独立锚

新增四个独立测试，分别走生产 waiver、生产 approval、消费 waiver、消费 approval
的真实文件解析路径。每个原文只在未受后续 schema 约束的顶层 `parser_probe` 注入
`NaN`，因此摘掉对应 `parse_constant` 后不会被 `_finite_number` 等后置防线代拦；
对应专属锚必红。现有四个挂载点均为：

```text
json.loads(..., parse_constant=_reject_constant)
```

破坏性自证选择“生产侧 waiver”挂载点：临时摘除后只跑
`test_fixround_r02_producer_waiver_parse_constant_mount`，结果 `rc=1`，实测
NaN waiver 被错误放行并落 `PASS`；用 `apply_patch` 恢复挂载后同一专属锚 `rc=0`。
破坏性改动未留在工作树，未使用 git restore/checkout。

### R-03：evidence 独立性改为内容身份

两侧仍保留路径相等快捷检查，并在 path/size/sha256 三验后读取实物 SHA256：

- evidence SHA256 等于 replay_stats 实物 SHA256：拒绝；
- evidence SHA256 等于 over-cap approval 实物 SHA256：拒绝。

回归覆盖 evidence 硬链接到 approval、硬链接到 replay_stats、逐字节复制 approval
换名三种绕法，生产/消费均拒；正常内容不同的独立 evidence 两侧均放行。存量 F-E
的 replay_stats 独立性与 F-A9 approval 独立性在同一深度闭合。

### R-04：evidence 最低内容要求

两侧均在引用三验后执行：

- `size == 0` 硬拒；
- 实物可作 UTF-8 解码时，复用各侧独立 `_meaningful_text`，无实义字符则拒；
- UTF-8 解码失败时按二进制证据处理，只要求非空。

空文件、纯 `U+200B`、纯 `U+3164` 两侧均拒；正常中文文本与含 `0x00` 的
非 UTF-8 字节串两侧均放行。

### R-05：行为向量扩容

`test_fixround_fa10_two_side_behavior_vectors` 已扩入原始 13 码位、全部混合串族和
中文/英文/韩文/含可见拉丁字母组合串绿例。守卫逐向量比较生产、消费行为与明确期望，
不比较源码文本，也不破坏两侧独立纪律。

## 三、红 → 绿双跑证据

### 3.1 只改测试后的首红

生产代码未改时运行：

```text
python3 scripts/tests/test_repair_batch_a.py
rc=1
BATCH A FAIL 5/44
```

五个失败分别命中：R-01 端到端、R-01 正负向控件、R-03 内容身份、R-04 空证据、
R-05 行为向量。首个 R-01 反例为 approval `nonce=U+3164`，生产侧 `rc=0` 并落
`PASS`；R-03 硬链接 approval 生产侧 `rc=0/PASS`；R-04 空 evidence 生产侧
`rc=0/PASS`。四个 R-02 真实解析路径在挂载尚完整的基线上均通过，其独立摘挂红证据
见第二节。

### 3.2 修后定向绿跑

```text
python3 scripts/tests/test_repair_batch_a.py
rc=0
PASS batch A F-01/F-02 regressions 44/44
```

原始 13 码位纠正为盲审探测输出的精确集合后再次运行，结果仍为 `rc=0, 44/44`。

### 3.3 全量与获准环境复跑

受限沙箱内运行：

```text
python3 scripts/tests/run_all.py
rc=1
2 项失败
```

唯一失败为：

- `test_batch3_solana_vertical_slice.py`：绑定 `127.0.0.1` 时
  `PermissionError: [Errno 1] Operation not permitted`；
- `test_batch3_evm_vertical_slice.py`：同一 loopback bind `EPERM`。

其余全部 PASS，含 `test_repair_batch_a.py = 44/44`、batch B、batch C、工单 B
`test_repair_batch2_f02.py`、invariant scan、docs lint 与所有业务测试。

按工单惯例在获准环境复跑上述两项：

```text
python3 scripts/tests/test_batch3_solana_vertical_slice.py
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release

python3 scripts/tests/test_batch3_evm_vertical_slice.py
PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure

combined rc=0
```

最终在获准环境对含完工记录与精确 13 码位向量的工作树运行完整套件：

```text
python3 scripts/tests/run_all.py
rc=0
test_batch3_solana_vertical_slice.py PASS
test_batch3_evm_vertical_slice.py PASS
test_repair_batch_a.py PASS batch A F-01/F-02 regressions 44/44
全部通过
```

格式检查：`git diff --check`，`rc=0`。

## 四、六视角自审 ①：字段来源与信任根

- 文本实义性的信任根是两侧代码中明确列出的正向可渲染区间，不再依赖会随 Unicode
  版本变化且跨类别含不可见点的黑名单判断。
- waiver/approval 原文分别由四条真实解析路径读取；`NaN` 的拒绝发生在 JSON 解析层，
  不依赖后置数值字段恰好被消费。
- evidence/replay_stats/approval 的身份均先由安全路径与 path/size/sha256 三验绑定到
  案内实物；独立性再以各侧从实物字节重算的 SHA256 比较，不信路径名或 inode 表象。
- evidence 文本内容来自被绑定实物本身；UTF-8 解码成功后才走各侧自己的实义判定，
  解码失败只证明它属于机器无法按文本检查的二进制面，不据此声称内容真实。
- 生产侧与消费侧的 `_meaningful_text`、evidence 内容检查和内容身份比较均各自实现；
  测试只比较行为与期望，消费侧没有调用生产侧私有校验函数。

结论：关键字段均闭合到本次读取的案内实物；路径身份、Unicode 类别与生产侧自报值
均不再单独充当独立性或实义性的信任根。

## 五、六视角自审 ②：失败路径、清理与边界

- 生产侧空/无实义文本 evidence、内容撞 replay_stats/approval、NaN JSON 均抛
  `TolerancePolicyError`，经既有政策拒绝出口返回 exit 2，不发布 PASS；消费侧抛
  `ValueError`，fail-closed。
- evidence 读取 `OSError` 仍沿既有通道故障语义走生产 exit 1；没有把权限/介质故障
  错报成政策内容错误。
- UTF-8 解码失败只在 `size > 0` 后放行二进制面；空二进制仍拒，未形成空文件旁路。
- 新测试全部使用 `TemporaryDirectory`；硬链接与副本只存在于临时案根，自动清理，
  未污染真实 references/data/maintenance 历史资产。
- `shared_release_receipt.py` 的 `validate_adversarial_review` 受保护段按“从该函数定义到
  下一顶层函数/EOF”的精确字节切片计算：修前、修后均为 3345 字节，SHA256 均为
  `dd032fde074cb0b60a481ca27d18d1cc27491c697c9003cd282023bad5d0f8a9`。
- 最终只读差异盘点仅命中本单三份代码/测试文件及本完工记录；未执行 add/commit/
  checkout/reset/restore/stash 等 git 写命令。

结论：新增拒绝均 fail-closed，政策错误与通道故障分层未漂移；临时破坏性自证已恢复，
工单 B/C 与 PYTHIA 边界保持不变。

## 六、发现未修

更深的“evidence 内容是否在语义上真实、是否真的由独立人工复核产生”超出本轮机器可验
范围。本轮只证明证据非空、文本可见、内容不与 replay_stats/approval 相同，并不把这些
结构事实冒充语义真实性；按工单登记留 R10 台账待裁。

工单 A 消化轮 2 施工完成，等待盲审员第三轮复核。
