# R9 批四 · 批内修复循环 2 · 只读复审报告（rereview2）

- 复审对象：`6b93e9d..919266e`（`f6523ef` = 循环 2 主体修复，`919266e` = SHA 回填）
- 复审性质：防御性质量核验（只读），验证 F-B4-01「G2 formal E2E 执行证据守卫可被伪造」是否真闭合
- 实测环境：最小镜像 `/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmp.9luCcHaDwn`（只含 `scripts/` + `VERSION` + 后补的 `references/` 文档件），原 worktree 全程只读
- 复审日期：2026-08-09

---

## 一、总裁决

**BLOCK。F-B4-01 第三次 STILL-OPEN。**

新 finding 计数：**P0 = 0，P1 = 0，P2 = 1，P3 = 1**

| 编号 | 级别 | 结论 |
|---|---|---|
| F-B4-01（第三次） | **P2** | 遮蔽检测只看「调用所在的那一层函数」，**模块作用域重绑定**与**外层函数作用域重绑定**两条路全线可穿；已用武器化样本证明「静态守卫零报错 + 运行时 exit=0 + 一个进程都没起」 |
| F-B4-01-B（新） | **P3** | 新写的诚实文档把兜底责任推给「SUITE 的 loopback E2E harness」，但那个 harness 就是被本守卫校验的纵切片测试文件本身——兜底与被验证对象是同一个东西，逻辑上是循环，不构成独立防线 |

### 一句话说清这次为什么没闭合

上一轮抓到的 M10 是「函数里写一行 `subprocess = None`」。这轮修完之后，只要把**同一行代码往左顶格挪到模块层**（`import subprocess` 之后写 `subprocess = None`），守卫就又瞎了。攻击代码字数没变、缩进少了四个空格，**这正是"换语法就穿"的第三次复现**。

### 根因（读码 + 实测双证）

`scripts/tests/invariant_scan.py`

1. `_execution_call_bindings.visit_Call` 只记 `stack[-1]`——即**紧邻的那一层函数**的绑定集，外层函数、模块层一概不看。
2. `_execution_imports(tree)` 只扫 `tree.body` 的 `Import/ImportFrom` 建立 `imports` 映射，**全程没有任何一处检查这个名字后来在模块层是否被重新绑定过**（`subprocess = None` / `def subprocess()` / `import json as subprocess` 都不影响 `imports`）。
3. `call_bindings.get(id(node), frozenset())` 的兜底值是**空集 = 判定为"没被遮蔽"**，属于 fail-open。凡是 `_execution_call_bindings` 没走到的节点（嵌套 def 体内、class 体内），一律默认"干净"。这三条叠加，构成下面整个 BYPASSED 家族。

---

## 二、任务一：循环 1 四变体复跑（全部 CAUGHT ✅）

调用形式：`formal_e2e_provenance_errors(targets={"sol": (样本路径, "test_fake_vertical_slice")})`，样本内含 runner + 五个 sol producer 路径字面量。

| 变体 | 构造 | 期望 | 实测 | 判定 |
|---|---|---|---|---|
| M6 | 无 import，裸 `subprocess.run(['python3','scripts/...'])` | errors 非空 | errors 2 条 | **CAUGHT** ✅ |
| M7 | 无 import，裸 `os.execv('python3', [...])` | errors 非空 | errors 2 条 | **CAUGHT** ✅ |
| M8 | 无 import，裸 `formal_ready_test_harness.run_formal_script(...)` | errors 非空 | errors 2 条 | **CAUGHT** ✅ |
| M10 | 顶层 `import subprocess`，函数体内 `subprocess = None` 后调用 | errors 非空 | errors 2 条 | **CAUGHT** ✅ |

四条实测输出一致，均为：

```
formal E2E target lacks real reconciliation runner for sol
formal E2E target lacks registered producer execution for sol: ['scripts/lib/supply_truth_gate.py', 'scripts/solana/accounting_gate_sol.py', 'scripts/solana/anchor_sampler.py', 'scripts/solana/scan_token_accounts.py', 'scripts/solana/window_fetch.py']
```

结论：**上一轮点名的四条确已堵住**，`import` 真绑定硬门（`_resolved_call_name` head 不在 imports 返回 None + `_is_execution_primitive` 三重拒绝）对这四种形态有效。但这只是把攻击面往外推了一格，见任务二。

---

## 三、任务二：边界外一步——第三代绕过变体

共实测 20 条。**BYPASSED 9 条、CAUGHT 11 条**（其中 1 条 CAUGHT 属"控制组本该放行却放行"，另计）。

### 3.1 命题清单

| 编号 | 变体 | 构造要点 | 实测 | 说明 |
|---|---|---|---|---|
| **N1** | **模块级遮蔽**（Fable 读码点名，必测） | 顶层 `import subprocess` + 顶层 `subprocess = None`，函数内 `subprocess.run('scripts/..')` | **BYPASSED** ❌ | `errors == []`。**核心洞**，与 M10 同一招只差一层缩进 |
| N2 | 函数内局部 import | 函数体内 `import subprocess` 后同函数调用 | CAUGHT ✅ | 被 `_function_local_bindings.visit_Import` 收进遮蔽集而拒绝（过严但安全，见 3.3） |
| N3 | `del` 后调用 | 顶层真 import，函数内 `del subprocess` | CAUGHT ✅ | `visit_Name` 收 Store/Del 两种 ctx，符合预期 |
| N4 | `global` 声明 | 函数内 `global subprocess; subprocess = None` | CAUGHT ✅ | 靠的是那句赋值（Name Store），不是 `global` 语句本身 |
| N5 | 别名遮蔽 | 顶层 `import subprocess as sp`，函数内 `sp = None` 后 `sp.run` | CAUGHT ✅ | |
| N6 | 嵌套函数递归链 | target → outer → middle → deepest，最深层用未 import 的裸 `subprocess.run` | CAUGHT ✅ | 递归链上绑定集传递正确 |
| **N7** | **嵌套 def + 外层遮蔽**（自拟） | 目标函数内 `subprocess = None`，内部 `def _inner(): subprocess.run(...)`，然后 `_inner()` | **BYPASSED** ❌ | `_inner` 自己的绑定集不含 `subprocess`，而外层的绑定集不会向内传递；运行时 `_inner` 通过闭包拿到的是 `None` |
| **N8** | **模块级属性猴补**（自拟） | 顶层 `import subprocess` + 顶层 `subprocess.run = lambda *a, **k: None` | **BYPASSED** ❌ | 属文档已声明的 monkeypatching 边界，但见 F-B4-01-B |
| N9 | lambda 体内调用且被立即调用 | `(lambda: subprocess.run([...]))()` | CAUGHT ✅ | `_reachable_calls.visit_Lambda` 直接 return，lambda 体不采证 |
| N10 | 顶层 `if True: import subprocess` | 模块层导入藏进 If 块 | CAUGHT（过严） ⚠ | `_execution_imports` 只扫 `tree.body` 直接子节点；对合法写法会误拒，见 3.3 |
| N11 | 顶层 `try: import subprocess except ImportError:` | 同上 | CAUGHT（过严） ⚠ | 同上 |
| **N12** | **模块层同名 def 遮蔽**（自拟） | 顶层 `import subprocess` 后再 `def subprocess(): ...` | **BYPASSED** ❌ | 运行时 `subprocess` 是函数对象，`.run` 直接 AttributeError |
| N13 | `getattr` 间接 | `getattr(subprocess, 'run')([...])` | CAUGHT ✅ | `_call_name` 对 Call 节点返回空串，head 为空被拒 |
| **N14** | **同名二次导入**（自拟） | 顶层 `import subprocess` 后 `import json as subprocess` | **BYPASSED** ❌ | 运行时 `subprocess` 是 json 模块 |
| **N15** | **生产同形攻击**（自拟，杀伤力最大） | `from formal_ready_test_harness import run_formal_script` + 顶层 `run_formal_script = _stub` | **BYPASSED** ❌ | **这就是现役四链纵切片文件的真实 import 形态**，四行代码即可整体伪造 |
| **N16** | 遮蔽写在文件末尾（自拟） | `subprocess = None` 放在所有 def 之后 | **BYPASSED** ❌ | 位置无关，模块层任何位置都能穿 |
| N17 | 先赋值后 import（控制组） | `subprocess = None` 然后 `import subprocess` | BYPASSED（**判定正确**） ✅ | 运行时 import 后绑定生效、确实会真跑进程，放行是**对的**，记为 REFUTED-CANDIDATE |
| **N18** | 嵌套 class 方法 + 外层遮蔽（自拟） | 目标函数内 `subprocess = None` + 嵌套 class 的方法体调用 | **BYPASSED** ❌ | `_execution_call_bindings.visit_ClassDef` 直接 return，方法体内调用拿到 fail-open 空集 |
| **N19** | 两级嵌套 def（自拟） | 遮蔽只写在最外层，`lvl1 → lvl2` 两级内调用 | **BYPASSED** ❌ | 证明不是"差一层"，是**整条外层作用域链**都不看 |
| **N20** | 顶层 wrapper + 模块遮蔽（自拟） | 模块层遮蔽 + 顶层 `def runner(): subprocess.run(...)`，target 调 `runner` | **BYPASSED** ❌ | 走 `_local_function_executes` 递归路径同样穿透 |

### 3.2 武器化实证（决定性证据）

只测"守卫报不报错"还不够——必须证明这个伪造件**既骗过守卫、又能在 SUITE 里跑绿、且真的一个进程都没起**。构造如下（`mutants/N1W_weaponized_module_shadow.py`）：

```python
import subprocess

class _Silent:
    @staticmethod
    def run(*args, **kwargs):
        return None

subprocess = _Silent          # ← 全部攻击就这一行

def test_fake_vertical_slice():
    subprocess.run(['python3', 'scripts/report/reconciliation_report.py'], check=True)
    ...（五个 producer 同形）
    return True

def main():
    test_fake_vertical_slice()
    print('VERTICAL SLICE GREEN')
```

实测三连：

```
STATIC GUARD errors = []
STATIC GUARD verdict = BYPASSED
RUNTIME exit=0
RUNTIME stdout='VERTICAL SLICE GREEN'
RUNTIME stderr=''
```

三件事同时成立：**守卫零报错、测试退出码 0、六个 producer 一个都没被执行**。这正是 F-B4-01 的原始威胁模型（伪造 E2E 执行证据），未闭合。

### 3.3 过严边界（不是洞，但要记账）

N2 / N10 / N11 三条属**误拒**方向：

- N2：函数内 `import subprocess` 后调用——这是完全合法的写法，却被当成"遮蔽"拒了。
- N10 / N11：模块层导入写在 `if` 块或 `try/except` 里（`try: import subprocess except ImportError:` 是极常见的兼容写法）——`_execution_imports` 只扫 `tree.body` 直接子节点，扫不到就判"没 import"。

这三条方向是安全的（宁可错杀不放过），不构成 finding，但会限制纵切片测试今后的写法自由度。若将来有人给纵切片加个条件导入，守卫会红得莫名其妙。建议在修 P2 时顺手把 `_execution_imports` 改成走 `ast.walk` 收模块层（非函数体内）的导入。

### 3.4 修复方向（供施工方参考，非本报告结论）

三处一起改，缺一仍可穿：

1. **模块层重绑定要摘牌**：全模块扫一遍「不在任何函数体内」的 `Store/Del` Name、`FunctionDef`/`ClassDef` 定义名、以及后续 `Import as` 的同名覆盖；命中就把该名字**从 `imports` 里直接删掉**。N1/N12/N14/N15/N16/N20 一次性全关。
2. **绑定集要取整条作用域链的并集**，不是 `stack[-1]`；并且 `visit_ClassDef` 不能直接 return——class 体内的函数也要带着外层栈继续走。N7/N18/N19 一次性全关。
3. **兜底值从 fail-open 改 fail-closed**：`call_bindings` 里查不到 `id(node)` 的调用节点，应当判为"来源不明 → 不算执行证据"，而不是现在的"空遮蔽集 → 算"。这是防第四代变体的关键，否则下一个没被 visitor 走到的语法结构又是一个洞。

---

## 四、任务三 + 任务四：不误伤与新洞检查

### 4.1 不误伤（全 PASS ✅）

镜像内实测（`sys.path` 已加 `scripts/lib` 与仓库根）：

| 检查项 | 期望 | 实测 | 判定 |
|---|---|---|---|
| `formal_e2e_provenance_errors()`（默认四链） | `[]` | `[]` | **PASS** ✅ |
| `chain_registry.formal_ready_chains()` | `{'eth','bsc','base','sol'}` | `{'base','bsc','eth','sol'}` | **PASS** ✅ |
| M4 多层 wrapper（`run → _r2 → subprocess.run`，顶层真 import） | `[]` | `[]` | **PASS** ✅ |
| M5 别名（`import subprocess as sp; sp.run`） | `[]` | `[]` | **PASS** ✅ |
| `from subprocess import run` 直用 | `[]` | `[]` | **PASS** ✅ |
| `from formal_ready_test_harness import run_formal_script` 直用（**四链真 target 形态**） | `[]` | `[]` | **PASS** ✅ |
| `from os import execv` 直用 | `[]` | `[]` | **PASS** ✅ |

### 4.2 批四注入测试全绿（EXIT=0 ✅）

镜像内 `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_batch4_invariant_guards.py` → **EXIT=0**，22 条用例输出行齐全，F-B4-02/03/04/05 对应行全部在位：

```
INJECT B4-RPC-01 bare RpcPool -> RED
INJECT B4-LABEL-01/02 + B4F-LABEL-03 extra/missing/eighth surface -> RED
INJECT B4F-FORMAL-01 empty ACCOUNTING_PRODUCERS -> RED with diagnostic
INJECT B4-VS-01/02 missing SUITE + missing file -> RED
INJECT B4-INV17-01/02 urllib + variable curl + denominator shrink -> RED
INJECT B4-RH-COUNT-01 documented 15/14 vs disk 16/15 -> RED
INJECT R9-B4-MAIN-01 bare integer main() -> RED
INJECT B4F2-MAIN-02 top-level bare integer main() -> RED
INJECT R9-B4-E2E-01 hand-written observation bundle -> RED
INJECT B4F2-E2E-02 local no-op run wrapper -> RED
INJECT B4F2-E2E-03 dead subprocess primitive -> RED
INJECT B4F2C2-E2E-04 unimported subprocess.run -> RED
INJECT B4F2C2-E2E-05 unimported os.execv -> RED
INJECT B4F2C2-E2E-06 unimported harness primitive -> RED
INJECT B4F2C2-E2E-07 locally shadowed subprocess -> RED
PASS B4F2C2 M4/M5 import bindings + four live ready chains
PASS B4F2C2 local binding forms + nested scope boundary
INJECT R9-B4-STALE-01 failed producer leaves old canonical -> RED
INJECT B4F2-STALE-03 dead quarantine/error calls -> RED
INJECT B4F2-STALE-03B constant-false contract calls -> RED
INJECT R9-B4-STALE-02 remove formal producer artifact registration -> RED
INJECT B4F2-STALE-04 newly added standalone producer -> RED
PASS B4-G1: bare pool / labels / vertical slice / denominator injections
```

注：首跑因镜像缺 `references/` 报 `FileNotFoundError: references/data-pipeline-robinhood.md`（`robinhood_inventory_errors()` 要读文档）；补齐 `references/*.md` + `casebook/` + `labels/` 小件后即 EXIT=0，与守卫逻辑无关，是镜像裁剪的副作用。

### 4.3 循环 2 改动面核对（符合声明 ✅）

`git diff --stat 6b93e9d..919266e`：

```
 maintenance/repair-20260806/b4_progress.md      |  13 +++
 maintenance/repair-20260806/diff-finding-map.md |   8 ++
 scripts/tests/invariant_scan.py                 | 118 ++++++++++++++--
 scripts/tests/test_batch4_invariant_guards.py   | 147 ++++++++++++++++++++++
 4 files changed, 274 insertions(+), 12 deletions(-)
```

只动了 invariant_scan.py、test_batch4_invariant_guards.py 与两份台账，**与声明一致，未动件保持闭合**。

### 4.4 两个新函数本身的正确性

| 检查点 | 结论 |
|---|---|
| `_function_local_bindings` 递归终止 | ✅ 只遍历 `function.body`，遇 FunctionDef/AsyncFunctionDef/Lambda/ClassDef 立即 return，AST 无环，必然终止 |
| `_function_local_bindings` 形参/各类绑定收全 | ✅ posonly/args/kwonly/vararg/kwarg + Assign/AugAssign/AnnAssign/For/With/except-as/walrus/Import/ImportFrom 均覆盖（施工方自带的 `test_execution_local_binding_scope_contract` 已断言，我复跑通过） |
| `_execution_call_bindings` 递归终止 | ✅ `stack.append` / `finally: stack.pop()` 配对，树遍历必然终止 |
| `id(node)` 映射在递归链中是否一致 | ✅ `formal_e2e_provenance_errors` 里 `tree` 只 parse 一次，`_execution_call_bindings(tree)` 与 `_reachable_calls(functions[...])` 取到的是同一棵树的同一批节点对象；`tree` 在整个循环体内保持强引用，不存在 id 复用。`_local_function_executes` 递归时把同一个 `call_bindings` 一路透传，一致性成立 |
| 但：`id()` 查不到时的默认值 | ❌ **fail-open**（`frozenset()` = 判"无遮蔽"）。这是 N7/N18/N19 能穿的直接原因，也是今后新增语法结构必然复发的结构性隐患，已计入 F-B4-01 根因第 3 条 |
| 装饰器 / 默认参数里的调用 | ✅ 两个 visitor 都只走 `node.body`，装饰器与默认值里的调用既不进绑定表也不进 `_reachable_calls`，采不到证 → 不构成新洞 |

### 4.5 F-B4-01-B（P3）：诚实文档指向的兜底是循环论证

`_reachable_execution_evidence` 新写的 docstring：

> ……dynamic exec dispatch、`importlib.import_module`/`getattr` 间接、模块加载期 monkeypatching 不在本 AST 守卫范围内，**由 SUITE 的 loopback E2E harness 兜底**。

问题在于：这里说的 loopback E2E harness，查 `formal_capability_probes.VERTICAL_SLICE_EVIDENCE_TARGETS` 可知就是
`scripts/tests/test_batch3_evm_vertical_slice.py`（文件头自述 "eth/bsc/base real CLIs with loopback transport only"）与 `test_batch3_solana_vertical_slice.py`——**正是 G2 这个守卫要去校验真伪的那两个文件本身**。

也就是说：守卫说"我管不了的部分由 X 兜着"，而 X 就是守卫要验的那个东西。伪造者把 X 改成假的，兜底自然一起假掉。这不是独立防线，是循环。

定级 P3 而非 P2 的理由：这条本身不新增可利用面（可利用面已被 P2 的 N1/N15 覆盖），但它会让下一轮读者误以为"有兜底所以可以放着"，属于**会误导后续判断的表述问题**，必须改口——要么写明"该部分目前无独立兜底"，要么补一个真正独立于纵切片文件的运行时校验（例如由 runner 自己产出的、带进程指纹的收据）。

---

## 五、REFUTED-CANDIDATE（试过但被驳回的攻击思路）

以下是我提出并实测、但**证据不支持**、不予记为 finding 的思路，列出以防幻觉与重复劳动：

1. **`getattr(subprocess, 'run')(...)` 间接调用**（N13）——想绕过名字白名单。实测 CAUGHT：`_call_name` 对 Call 类型节点返回空串，`head` 为空被第一重拒绝挡下。**驳回**。
2. **lambda 体内藏执行原语并立即调用**（N9）——想利用 `_execution_call_bindings.visit_Lambda` 的 return 拿 fail-open 空集。实测 CAUGHT：`_reachable_calls` 同样对 Lambda 直接 return，调用根本进不了采证列表，两个 visitor 的口子恰好对齐。**驳回**。
3. **先 `subprocess = None` 再 `import subprocess`**（N17）——想说"模块层出现过赋值就该拒"。实测 BYPASSED，但这是**正确行为**：运行时 import 在后、绑定生效，进程真的会起。若把它也拒了才是误伤。**驳回**（同时提醒：3.4 的修复方案 1 若不考虑先后顺序会误杀这一形态，实现时需注意，或接受这一保守误杀）。
4. **顶层裸 `subprocess.run` 写在模块层（不在函数里）** ——想绕开 `_execution_call_bindings` 的 `if stack:` 判据。未构成攻击：`_reachable_execution_evidence` 只遍历函数体内的调用，模块层调用根本不采证，采不到证 = 拒。**驳回**。
5. **在 `scripts/tests/` 下放一个假的 `subprocess.py` 顶掉标准库** ——理论上可行且守卫看不见，但需要**新增一个文件**、且该文件本身会被目录级审查与 import 路径顺序约束限制，超出"单文件伪造纵切片测试"的威胁模型。**不记为本轮 finding**，仅提示：真要修 P2 时，模块层重绑定检测顺带能覆盖"同目录同名模块"的一部分风险，但不能全覆盖。

---

## 六、工作区自查

| 项 | 情况 |
|---|---|
| 原 worktree 写入 | 仅本报告一个文件 `r9-reviews/b4/rereview2.md`；无 `git` 写操作、无分支/HEAD 变更（HEAD 保持 `919266e`） |
| 最小镜像路径 | `/var/folders/z6/mlppyd097493blf6v8_h29dw0000gp/T/tmp.9luCcHaDwn`（`scripts/` + `VERSION`，后补 `references/*.md`、`references/casebook/`、`references/labels/` 小件、`CHANGELOG.md`/`SKILL.md`/`pyproject.toml`/`requirements.lock`；**未拷任何链上数据**） |
| 所有 mutant 实验位置 | 全部在镜像的 `mutants/` 子目录，未落进原 worktree |
| 禁用命令遵守 | 全程**未用 `du`**、未用 `find` 全盘扫、未用 `ls -R`、未做整树 `wc`；目录体量只用单层 `ls -l` 查看 |
| 出网 | 无 |
| 工具无响应 | 未发生（0 次） |
| 报告落盘确认 | 见文末 `ls -la` 证据 |

---

## 三行摘要

- **总裁决：BLOCK**（新 finding：P0=0 / P1=0 / **P2=1** / **P3=1**）
- **F-B4-01 终态：第三次 STILL-OPEN（P2）**——遮蔽检测只覆盖调用所在的那一层函数；模块作用域重绑定（N1/N12/N14/N15/N16/N20）与外层作用域重绑定（N7/N18/N19）九条变体全部 BYPASSED，武器化样本已实证"静态零报错 + 运行时 exit=0 + 零进程启动"
- **不误伤全 PASS**：默认四链 `[]`、`formal_ready_chains()=={'eth','bsc','base','sol'}`、M4/M5/三种 `from X import Y` 直用形态全放行，`test_batch4_invariant_guards.py` EXIT=0 且 F-B4-02/03/04/05 注入行全在位；循环 2 改动面与声明一致，未动件保持闭合
