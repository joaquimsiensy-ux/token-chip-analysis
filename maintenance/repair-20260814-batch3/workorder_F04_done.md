# 工单 F04 完工记录

## 结论

F-04（R10-5）已按工单落地：deploy-sync 删除无界迁移豁免，所有 staging/deployed 命令恢复逐文件 SHA-256 等值严判；缺失部署目录时，仅非规范 checkout 输出 `SKIP_NON_CANONICAL_CHECKOUT` 并返回 0，规范安装路径 fail-closed 返回 1。校验主体已拆为只读纯接口 `check_deploy_sync(root, deployed) -> list[str]`，canonical 判定可参数化直测。

未运行任何 git 写命令，未改版本件，未触碰 evmobs 文件或目录。`scripts/tests/run_all.py` 仅在当时 SUITE 末尾追加本批共享测试挂载；并行 evmobs 会话后续撤掉其自身挂载，不属于本工单改动。

## 先红清单

生产代码尚未修改时，先新增 `scripts/tests/test_repair_batch3_gates.py` 并执行：

```text
python3 scripts/tests/test_repair_batch3_gates.py
exit code: 1
```

真实先红共 4 项：

1. 原迁移豁免文件 `token-analyze-1.md` 的 deployed 内容改为 `STALE` 后仍返回 PASS，未报 SHA-256 不一致。
2. 非 canonical checkout 缺部署目录仍输出旧 `SKIP: 部署目录不存在（异机允许）`，缺少 `SKIP_NON_CANONICAL_CHECKOUT` 明确语义。
3. 缺少可参数化的精确 canonical 判定纯函数。
4. canonical 部署机缺部署目录仍错误返回 0，而非 fail-closed rc1。

其中第 1 项直接复现 review F-04 的无界迁移豁免假绿。

## 修后绿证据

```text
python3 scripts/tests/test_repair_batch3_gates.py
exit code: 0
末行: PASS: 批3 deploy-sync/env-check gates 回归全部通过

python3 scripts/tests/test_commands_deploy_sync.py
exit code: 0
末行: PASS: 3 份 staging/部署命令 SHA-256 逐文件一致
```

`rg -n "MIGRATION_CHANGED|MIGRATION_NEEDLES" scripts/tests/test_commands_deploy_sync.py scripts` 零匹配；该命令按 `rg` 语义返回 1，表示目标引用已全部删除。

完整 suite 首次在 workspace-write 沙箱内执行，F04 与其余业务测试通过；两个 vertical-slice 测试仅因沙箱拒绝 loopback bind 失败，同时并行 evmobs 会话的临时测试文件在运行期间被其会话撤掉，导致当次旧挂载失败。未将该轮记作全绿，也未修改测试绕过。

随后在允许 loopback bind 的环境完整重跑：

```text
python3 scripts/tests/run_all.py
exit code: 0
末行: 全部通过
```

两个 vertical slice 均真实 PASS；F04 共享回归和真实 deploy-sync 入口均在全量 suite 中 PASS。`git diff --check` exit 0。

## 改动文件清单

- `scripts/tests/test_commands_deploy_sync.py`
- `scripts/tests/test_repair_batch3_gates.py`（新增，F04/F05 共享）
- `scripts/tests/run_all.py`（只追加共享测试挂载）
- `maintenance/repair-20260814-batch3/workorder_F04_done.md`（本文件）

## diff → finding 逐 hunk 映射

| 文件 / hunk | finding 映射与作用 |
|---|---|
| `test_commands_deploy_sync.py` 常量区 | F-04 / R10-5：删除 `MIGRATION_CHANGED`、`MIGRATION_NEEDLES` 及 staging 全局路径依赖。 |
| `test_commands_deploy_sync.py` `is_canonical_checkout` | F-04 / R10-5：精确比较规范安装路径，并允许测试传入临时 home。 |
| `test_commands_deploy_sync.py` `check_deploy_sync` | F-04 / R10-5：聚合缺目录、清单、缺文件与逐文件 SHA-256 失败，无迁移旁路。 |
| `test_commands_deploy_sync.py` `main` | F-04 / R10-5：非 canonical 缺目录明确 SKIP；canonical 缺目录进入 failures 并 rc1；结论保持最后一行。 |
| `test_repair_batch3_gates.py` F04 小节 | F-04 / R10-5：缺文件、普通字节漂移、原豁免文件 STALE、全等、两类缺目录与 canonical 精确判定先红后绿。 |
| `run_all.py` 末尾追加项 | F-04 / R10-5：共享回归进入全量 suite；未重排或删除既有内容。 |

未映射 hunk 为 0。

## 新建代码自审

1. `check_deploy_sync` 只有只读文件访问，所有失败均追加到同一 `failures` 列表；不存在中途 `return 0` 旁路。
2. `main` 唯一 rc0 SKIP 分支同时要求部署目录缺失且 checkout 非 canonical；canonical 缺目录必进入聚合失败。
3. 三份命令无论文件名是否曾列入迁移集合，都走同一 SHA-256 比较分支。
4. RETIRED 精确名单提示保留；`.bak_*` 不会被误识别为退役文件。

## 发现未修事项

F04 范围内未发现未修事项。

WORKORDER_F04_COMPLETE
