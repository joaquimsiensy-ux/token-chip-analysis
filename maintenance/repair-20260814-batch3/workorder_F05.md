# 【修复工单 F05】bug：env_check 手写 14 包漏 7 个直接依赖、不查 Python 版本、不查 lock 是否满足 pyproject（codex review F-05，P2；R10-6）

> 施工方：codex。**禁一切 git 写命令**；只改文件。完成后写 `maintenance/repair-20260814-batch3/workorder_F05_done.md`。
> 禁触清单同 plan.md。注意本文件另挂 `.git/hooks/pre-commit:8`（第二活挂载点）——收紧即收紧每次 commit，此联动为有意接受。

## 1. 不变量

1. env_check 的受检包集合 = pyproject.toml `[project].dependencies` 的全部直接依赖（机械派生，今后 pyproject 加包无需记得改 env_check）。
2. 三层关系逐包成立，缺一层即 FAIL（@CX 补齐，防"pyproject 升下限而 lock 没跟"假绿）：
   - 每个直接依赖在 requirements.lock 恰有一个 pin（0 个或重复行都拒）；
   - lock pin 满足 pyproject 说明符；
   - installed 版本严格等于 lock pin。
3. 解释器满足 requires-python（">=3.14" vs sys.version_info）。
4. 说明符解析 fail-closed：只支持受控语法，遇不认识的形态直接 FAIL，绝不静默跳过。

## 2. 同族清单

- 改动文件：`scripts/tests/env_check.py`（重写）。挂载点：run_all.py:37、.git/hooks/pre-commit:8（未跟踪，不改）。
- 文档双向面（改完顺检描述是否仍准确）：pyproject.toml:5 注释、references/split-run.md:28、references/data-pipeline-evm-recon.md:78。
- tomllib house style 先例：scripts/tests/test_version_consistency.py。
- 实测基线：本机 Python 3.14.6，21/21 包 installed==lock 且 lock 满足说明符——重写后本机必绿，先红全靠注入反例。

## 3. 施工内容

- tomllib 读 pyproject.toml：`[project].dependencies`（21 条）+ `requires-python`。
- 说明符解析（**不用 packaging 库**——它是未声明的传递依赖，守卫依赖未声明包=循环）：受控语法白名单，当前全部形如 `name>=X.Y[.Z…]`；解析器识别 `>=` 单说明符+纯数字点分版本；遇 extras（`pkg[x]`）、环境 marker（`;`）、`~=`、`!=`、`<`、多说明符逗号等 → FAIL 并报"说明符语法超出受控白名单"。版本比较用数字元组（不同长度右补零，如 1.27.2.3 vs 1.27.2）。
- 名称规范化 PEP503：`re.sub(r"[-_.]+", "-", name).lower()`，pyproject/lock/installed 三侧统一后对账。
- lock 解析：沿用 `name==version` 行式；同名（规范化后）出现两行 → FAIL。
- 对账方向（@CX 重定义）：direct→lock 全覆盖必查；lock 多出的传递依赖**合法**（不反向要求）；"已删直接依赖残留 lock"平面文件判不了——在 done 文件记为已知边界，不冒充。
- requires-python：解析 `>=X.Y` 与 `sys.version_info` 比较；其他形态 fail-closed。
- 输出保持一行结论风格；FAIL 时逐项列出（包名: 哪一层断了）。
- docstring 更新（顺检三处文档引用描述）。

## 4. 三件套测试（新文件 test_repair_batch3_gates.py 与 F04 共用，挂 run_all SUITE）

核心函数参数化（接收 pyproject_path/lock_path/metadata 查询函数），注入假件测：

- 漏包：pyproject 有 fakepkg、lock 没有 → FAIL。
- 版本漂移：installed ≠ lock pin → FAIL。
- **lock pin 低于 pyproject 下限**（pyproject `x>=2.0`、lock `x==1.0`、installed 1.0）→ FAIL（先红点：HEAD 版 env_check 三层缺第二层，且 KEY_PKGS 硬编码根本看不见 7 个包——HEAD 上 reportlab 从 lock 删掉也绿）。
- 重复 lock 行（`X==1.0` 与 `x==2.0` 规范化同名）→ FAIL。
- 非法说明符（`pkg~=1.0`、`pkg[extra]>=1.0`、`pkg>=1.0; python_version<"4"`）→ FAIL（fail-closed 而非跳过）。
- 规范化重名对账：`PyMuPDF` vs `pymupdf` 正确配对 → PASS 分支。
- 传递依赖多出：lock 含 pyproject 没有的包 → 不影响 PASS。
- 低版本 Python：monkeypatch sys.version_info=(3,13,0) → FAIL；requires-python 非受控形态 → FAIL。
- 真环境绿例：`python3 scripts/tests/env_check.py` rc=0 且输出含 21 包计数。

## 5. 新建代码自审

字段源头（受检集合唯一来源=pyproject 解析结果，无手写清单残留）；失败分支（任何解析异常→FAIL 而非跳过；输出列全断层明细）。

## 6. 归因预判

历史漏检+半修复（ff47763 建 11 包、637df73 扩 14 包均手写；pyproject 后续加 7 包/加 requires-python 时无人同步——手维护清单的结构性根因，机械派生根治）。

## 7. 验收标准（裁判执行）

- 新测试 rc=0；`python3 scripts/tests/env_check.py` rc=0 且受检 21 包+解释器检查；run_all 全绿；随后一次真实 git commit 过 pre-commit 钩子（联动实证）。
- codex 报告 F-05 反例复跑：机械对比确认 UNCHECKED_DIRECT_DEPENDENCIES 清零、ENV_CHECK_HAS_VERSION_INFO=True。
