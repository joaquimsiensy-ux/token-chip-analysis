# 工单 F05 完工记录

## 结论

F-05（R10-6）已按工单落地：`env_check.py` 不再维护手写包清单，受检集合唯一来源为 pyproject.toml `[project].dependencies`；每个直接依赖必须满足 direct→唯一 lock pin→installed 三层闭合，lock pin 还必须满足 pyproject 下限；解释器必须满足 `requires-python`。依赖名在三侧统一按 PEP 503 规范化，未知说明符与重复 pin 全部 fail-closed。

未运行任何 git 写命令，未改版本件，未改 `.git/hooks/pre-commit`，未触碰 evmobs 文件或目录。三处文档现有描述仍准确，无需修改。

## 先红清单

生产代码尚未修改时，先向 `scripts/tests/test_repair_batch3_gates.py` 追加 F05 注入假件并执行：

```text
python3 scripts/tests/test_repair_batch3_gates.py
exit code: 1
```

真实先红共 8 项：

1. pyproject 新增 `fakepkg>=1.0`、lock 缺包仍 PASS，复现手写 `KEY_PKGS` 漏直接依赖。
2. `duckdb>=2.0`、lock/installed 均为 1.0 仍 PASS，复现缺少 pyproject→lock 下限校验。
3. `X==1.0` 与 `x==2.0` 规范化重名仍 PASS，复现重复 pin 覆盖。
4. `pkg~=1.0` 未 fail-closed。
5. `pkg[extra]>=1.0` 未 fail-closed。
6. `pkg>=1.0; python_version<"4"` 未 fail-closed。
7. 注入 Python 3.13.0 对 `requires-python >=3.14` 仍 PASS。
8. `requires-python ~=3.14` 未 fail-closed。

同轮确认旧实现对 `installed 1.1 ≠ lock 1.0` 已能拒绝；该既有能力在重写后保留。规范化配对与 lock 多出传递依赖两个绿例在改前、改后均为 PASS。

## 修后绿证据

```text
python3 scripts/tests/test_repair_batch3_gates.py
exit code: 0
末行: PASS: 批3 deploy-sync/env-check gates 回归全部通过

python3 scripts/tests/env_check.py
exit code: 0
末行: PASS: 21 个直接依赖逐项满足 pyproject→lock→installed；Python 3.14.6 满足 requires-python >=3.14

python3 scripts/tests/run_all.py
执行环境: 允许 loopback bind
exit code: 0
末行: 全部通过
```

直接执行第二活挂载点脚本（未提交）：

```text
sh .git/hooks/pre-commit
exit code: 0
末行: [pre-commit] 三检全过
```

其中 hook 内 env_check 同样输出 21 个直接依赖与 Python 3.14.6 全绿。真实 `git commit` 由裁判执行；施工方受“禁止一切 git 写命令”约束未自行提交。`git diff --check` exit 0。

## 改动文件清单

- `scripts/tests/env_check.py`
- `scripts/tests/test_repair_batch3_gates.py`（共享文件追加 F05 小节）
- `scripts/tests/run_all.py`（F04 时已追加共享测试挂载，F05 复用）
- `maintenance/repair-20260814-batch3/workorder_F05_done.md`（本文件）

## diff → finding 逐 hunk 映射

| 文件 / hunk | finding 映射与作用 |
|---|---|
| `env_check.py` docstring、路径与受控正则 | F-05 / R10-6：明确 pyproject 为受检集合源，声明依赖/解释器/lock 的受控语法。 |
| `env_check.py` `normalize_name`、数字版本函数 | F-05 / R10-6：PEP 503 三侧统一；不同长度数字元组右补零比较。 |
| `env_check.py` `_parse_project` | F-05 / R10-6：tomllib 读取全部直接依赖与 requires-python；extras、marker、多说明符及其他运算符 fail-closed。 |
| `env_check.py` `_parse_lock` | F-05 / R10-6：只接受 name==version 行，规范化同名重复 pin 机械拒绝。 |
| `env_check.py` `check_environment` | F-05 / R10-6：direct→lock 全覆盖、lock 满足下限、installed 严格等于 pin、Python 下限四项聚合校验；metadata 后端异常也 fail-closed。 |
| `env_check.py` `main` | F-05 / R10-6：失败逐项列明且最后输出 FAIL 结论；绿例报告直接依赖计数与解释器版本。 |
| `test_repair_batch3_gates.py` F05 小节 | F-05 / R10-6：漏包、漂移、低 pin、重复 pin、非法说明符、规范化、传递依赖、低 Python 与非法 requires-python 注入回归。 |
| `run_all.py` 共享挂载 | F-05 / R10-6：F05 回归复用已追加在 SUITE 末尾的共享测试入口。 |

未映射 hunk为 0。

## 新建代码自审

1. 字段源头：生产代码中已无 `KEY_PKGS`；直接依赖集合只由 tomllib 解析 `[project].dependencies` 得到。
2. 失败分支：pyproject/lock 读取或解析异常、依赖与 Python 非白名单说明符、重复 pin、缺 pin、pin 低于下限、未安装、metadata 查询异常、installed 漂移均进入同一 failures 列表，无静默跳过。
3. 对账方向：只要求 direct→lock 全覆盖；lock 多出的传递依赖合法，不会因系统环境中的无关包产生噪音。
4. 输出纪律：FAIL 明细在前，最终结论在最后一行；PASS 同一行同时给出 21 包计数和解释器检查。

## 已知边界

平面 `requirements.lock` 无法判断某个多余 pin 是仍被其他包引用的传递依赖，还是已删除直接依赖的残留，因此不反向要求 lock⊆direct，也不把“残留 lock 已清零”冒充为可证明结论。

## 发现未修事项

F05 范围内未发现未修事项。

WORKORDER_F05_COMPLETE
