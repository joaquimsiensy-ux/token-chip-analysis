# 包 3 fix 第四轮定点施工报告

日期：2026-08-15

施工目录：`/Users/uravvv/.claude/skills/tca-repair-g1`

状态：**COMPLETE**

本轮按裁决仅迁移 `scripts/tests/test_repair_batch_d.py` 中
`t_fd2_unseal_binds_flip_receipt()` 的 F-D2 存量 fixture，并新增本报告；
未改生产代码，未改 F-D2 断言逻辑、判据或 rc 预期，未执行任何 git 操作。

## 1. 迁移明细

手工生成的 `provenance_ledger.json` 在既有
`input_binding.algorithm_params.flip_adjudications` 绑定之外，补齐当前
`handoff_manifest.py freeze --check-unseal` 强制复验的
`input_binding.algorithm.files`：

| 对象键 | 绑定路径 | bytes | 完整 SHA256 |
|---|---|---:|---|
| `entity_source_trace.py` | `/Users/uravvv/.claude/skills/tca-repair-g1/scripts/report/entity_source_trace.py` | 42583 | `73f1cd6a8590eeecb2bddb18868f8d16b858dd4e913de508eb636e9a3763bcef` |
| `wave_scan.py` | `/Users/uravvv/.claude/skills/tca-repair-g1/scripts/report/wave_scan.py` | 40711 | `4d8f999406287c32258c9d834928b5b176ddb2c34b9461489d80550262f6638e` |

两项均由仓库当前普通文件实算，记录形状为绝对 `path`、`bytes`、完整
`sha256`，与 `handoff_manifest.py` 当前 `check_algorithm_file()` 复验口径一致。

F-D2 的变异/复原段无需同步修改：该段只改写、删除并按原始字节恢复
`flip_adjudications.json`；算法文件不参与变异。收据 `bytes`/SHA256、ledger
SHA256 及 freeze 绑定仍由原夹具在造件时动态实算。

## 2. F-D2 判据保持不变

以下四条原检查的断言表达式、判断条件和 rc 预期均未修改：

1. 收据原样时 `check-unseal` 放行，rc=0。
2. 冻结后改写收据时拒绝，rc=2。
3. 冻结后删除收据时拒绝，rc=2。
4. 按原字节复原收据后再次放行，rc=0。

本轮仅补存量造件缺失的算法实物绑定，没有放宽或改写 F-D2 不变量。

## 3. 验证结果

### 3.1 Batch D

命令：

```text
python3 scripts/tests/test_repair_batch_d.py
```

结果：**rc=0**，末行 `BATCH D 全部通过`。

F-D2 四条均为 `ok`：

```text
ok    F-D2 基线：收据原样 check-unseal 放行
ok    F-D2 原反例①：冻结后改写收据 → check-unseal rc=2
ok    F-D2 原反例②：冻结后删除收据 → check-unseal rc=2
ok    F-D2 复原后再放行（绑定即字节）
```

其余 Batch D 用例保持绿。

### 3.2 handoff manifest 回波

命令：

```text
python3 scripts/tests/test_handoff_manifest.py
```

结果：**rc=0**，`handoff_manifest 契约测试全部通过（68 项）`。

### 3.3 G1 handoff containment 回波

命令：

```text
python3 scripts/tests/test_repair_g1_handoff_containment.py
```

结果：**rc=0**，`PASS: 14/14 checks`。

## 4. 结论

F-D2 存量 fixture 已迁移到当前算法文件绑定不变量；两条原负例继续按原
rc=2 判据拦截，基线与复原两条按原 rc=0 判据放行。三项指定测试全部
rc=0，未出现回波。

**包 3 fix complete。**
