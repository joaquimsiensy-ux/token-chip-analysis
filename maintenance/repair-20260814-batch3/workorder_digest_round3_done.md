# 消化轮 3 完工记录（BR3-01）

## 结论

BR3-01 已按裁判定案闭合：R10 条目行中的全角括号载体统一由
`【[^】]*】` 提取；载体仅在所在节的合法状态列、且完整匹配严格枚举时才可作为状态。
合法状态列没有任何载体时才归 OPEN。未知关键字、不可见字符插词、HTML 实体、
全角空格等非枚举载体均 fail-closed，并以 `repr` 形式附载体原文；嵌套、缺左括号、
缺右括号均报“状态载体括号不配对”。既有 statusish、裸词、列结构与现役计数守卫保留。

本轮生产改动仅涉及 `scripts/tests/test_repair_batch3_gates.py`，另新增本完工记录。
未执行任何 git 写命令。

## 先红证据

反例在无 `.git` 的 `/tmp/tca-digest-round3.ZwjeoE/repo-head` 临时副本运行；
临时复现脚本为 `/tmp/digest_round3_red.py`，SHA-256：
`0bd304eda9deaf9a2e1fdd35620e58a9e3586ed454d7f84f74953d9cbc321a7d`。

生产实现未修改时，裁判三例与未闭合括号例均被静默放行：

```text
ZWSP: []
UNKNOWN: []
HTML_ENTITY: []
UNCLOSED: []
```

随后只在该临时副本追加正式回归、仍不改实现，执行
`python3 scripts/tests/test_repair_batch3_gates.py` 得到 rc=1；新增四项断言全部红，
既有测试项全部通过：

```text
FAIL  F07 BR3-01 零宽字符插词状态载体必须 FAIL  []
FAIL  F07 BR3-01 未知状态关键字状态载体必须 FAIL  []
FAIL  F07 BR3-01 HTML 实体状态载体必须 FAIL  []
FAIL  F07 BR3-01 未闭合状态载体括号必须 FAIL  []
```

## 修后反例重放

最终实现与临时绿副本逐字节一致时，同一独立复现脚本返回：

```text
ZWSP: ["R10-1 状态载体无法识别为枚举：'【CLO\\u200bSED 6.41.0】'"]
UNKNOWN: ["R10-1 状态载体无法识别为枚举：'【CLOSED_PENDING 6.41.0】'"]
HTML_ENTITY: ["R10-1 状态载体无法识别为枚举：'【CLO&#83;ED 6.41.0】'"]
UNCLOSED: ['R10-1 状态载体括号不配对']
```

另补嵌套载体 `【CLO【SED 6.41.0】】` 正式回归，固定报“状态载体括号不配对”。

## diff → finding 映射

| 文件 / hunk | finding / 根不变量 | 测试 owner |
|---|---|---|
| `scripts/tests/test_repair_batch3_gates.py` 的 `R10_STATUS_CARRIER_RE`、逐 cell 载体提取与括号状态机 | BR3-01：载体存在但无法识别时不得静默归 OPEN；嵌套/不配对必须 FAIL | F07 三项裁判反例、未闭合与嵌套回归 |
| 同文件由载体 fullmatch 生成 `status_markers` 的分支 | BR3-01：严格枚举与合法列同时成立才是状态；无载体才是 OPEN | 真实 27 条绿例、Round 1/2 存量反例 |
| 同文件 F07 小节新增五项断言 | BR3-01 反例所有权与错误文本契约 | `test_repair_batch3_gates.py`、`run_all.py` |
| `maintenance/repair-20260814-batch3/workorder_digest_round3_done.md` | 本工单证据、范围与验收记录 | 完工门禁 |

未映射业务 hunk：0。

## 验收结果

最终精确 diff 的验收结果：

```text
python3 scripts/tests/test_repair_batch3_gates.py  rc=0
python3 scripts/tests/invariant_scan.py             rc=0
git diff --check                                    rc=0
```

invariant 输出：

```text
receipt_producers=58, receipt_consumers=78, transport_calls=62,
atomic_writes=51, formal_entrypoints=58, exceptions=0
```

`run_all.py` 在 workspace-write 沙箱内先得到 97/99 PASS；仅 Solana/EVM 两条
vertical slice 在业务断言前被 `socket.bind(127.0.0.1, 0)` 以
`PermissionError: [Errno 1] Operation not permitted` 拒绝。随后在允许 loopback 的环境
对最终精确 diff 按原命令完整重跑，99/99 全部通过、rc=0，其中：

```text
PASS B3-SOL-E2E: real producer->runner->aggregator->READY->release
PASS B3-EVM-E2E: eth/bsc/base slices + nonzero dead vertical closure
```

## 六视角自审

### ① 输入与载体范围

- 仅对已识别的 R10 条目行工作；先按真实 section 表取得合法状态列，再对全行各 cell
  提取全部 `【...】` 载体，不再把“正则没命中”直接等同 OPEN。
- 提取使用非贪婪边界等价式 `【[^】]*】`；每个载体均逐个校验，没有 first-match-wins。

### ② 列身份与枚举

- 第五节合法状态列保持 cell 3，其余受控节保持 cell 2；合法枚举落正文列仍由既有
  “正文列出现状态样式标记”守卫拒绝。
- 状态载体必须 `fullmatch` 既有严格枚举：`CLOSED x.y.z` 或
  `FIXED_PENDING_REVIEW x.y.z 批N`，只接受 ASCII 空格。

### ③ 隐形与编码变体

- U+200B、未知关键字、HTML entity 均进入“状态载体无法识别为枚举”分支。
- 错误消息使用 `{carrier!r}`，不可见字符显示为转义形式，便于定位原始字节而不做
  Unicode/HTML 规范化后误收。

### ④ 括号、失败分支与 OPEN

- 单遍括号状态机拒绝嵌套、孤立右括号与未闭合左括号；对应错误文本固定为
  “状态载体括号不配对”。
- 合法状态列没有任何载体时才记 OPEN；存在非法载体时即使现役数同步，也保留 failure，
  关死 BR3-01 的假绿路径。

### ⑤ 存量语义与回归

- 既有 statusish、裸词、重复状态、列数、转义/原始竖线、结构空白、重复现役声明与
  27 条集合/计数守卫未删除、未放宽。
- 真实 R10 台账全绿；Round 1 三反例、Round 2 组合/竖线/全角结构反例继续按原语义
  FAIL。新增五例进入正式 gates owner，并由全量 suite 覆盖。

### ⑥ 范围、版本与禁触

- tracked 业务 diff 只有 `scripts/tests/test_repair_batch3_gates.py`；工单与盲审输入文件
  未改写，新增文件仅本 done。
- `VERSION`、`pyproject.toml`、`SKILL.md` 版本锚仍为 6.43.0；未改 CHANGELOG，未转
  R10-5/6/16/17 为 CLOSED，未执行批 3 closure。
- `maintenance/repair-20260814-evmobs/`、`scripts/tests/test_evm_observation.py`、
  `archive/**`、`blind-reviews/**`、两份 `_meaningful_text` 本体、两处 schema 探测锚、
  `baseline_run_all*.log` 均未触碰。
- `sync-from-cc.sh` 可能执行 `git merge`，与本工单“禁一切 git 写命令”冲突，故未运行。

## 未修事项

- BR3-01 范围内未修事项：无。
- R10-5/6/16/17 的 CLOSED 转换、批 3 closure、版本发布与 CHANGELOG 记账均不属于本单，
  本轮刻意不做。

WORKORDER_DIGEST_ROUND3_COMPLETE
