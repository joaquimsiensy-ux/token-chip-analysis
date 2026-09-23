# 工单T1复核：退回

修复方向正确，但 v1 尚不能直接施工。需要修正整行锚、文件分支校验顺序、RED 与测试不一致、文档字节预算及“新增公开入口”的定位。未发现必须扩大生产代码白名单的第三处阻塞。

报告全文已打印到 stdout。基线为 HEAD `1cef258`，包含 `f4f80567c21f`；工作区状态为空，指定生产及文档路径相对基线的 diff 为空。全程离线，未修改或新建文件，未 commit；未读取 memories、`~/.codex/` 或其他禁读目录。Git 启动器和一次 shell heredoc 创建临时文件的尝试被沙箱拒绝，随后改用无临时文件的执行方式。

以下“工单 L…”均指 [workorder_T1.md](/Users/uravvv/.claude/skills/token-chip-analysis/maintenance/repair-20260923-t1-spotcheck-dir-input/workorder_T1.md) 当前行号。

**1. 目标与主要分歧**

支持修复的最强理由：目录计划、目录身份计算和时间抽查语义重放已经存在，缺口确实在收据封装与发布消费两端。绑定普通清单文件符合收据核现有要求。

反对意见的核心：消费者新增放行分支后，发布时验证的是清单及历史身份，并未验证目录当前全部内容。仅保持 schema、键名不变，不足以证明行为契约完全不变。

判断：可以按既有目录工作流的修复记 **9.0.3**，但须明确验证边界，并把辅助函数定位为内部实现。不应把目录重哈希搬进发布消费者。

**2. a）锚与行号：需改**

已执行整行 `grep -n -F -x`。核心源码位置与工单描述相符，包括：

- `receipt_kernel._resolved_input:53-78` 确实只收普通文件。
- `bound_case_ref:347-377` 确实要求案根内普通文件及 size/hash 一致。
- `anchor_plan.py:194-203` 确实写清单并绑定清单文件。
- `time_spotcheck.py:350-351` 的语义重放发生在收据封装之前。

不合格或有歧义的锚如下：

| 工单位置 | 核验结果 | 修正 |
|---|---|---|
| L53 | 起止文本实际在 418、420 | 锚区间写 418–420；调用范围仍是 417–421 |
| L99 | 519 是空行，`def main():` 在 521 | 直接锚 521 |
| L161 | 局部短语整行匹配为 0 | 换成 references:158 完整原文 |
| L166、L167 | CHANGELOG 锚省略行尾，整行匹配均为 0 | 换成 13、99 的完整原文 |
| shared:371、377、997 | 整行分别命中 2、4、2 处 | 注明非唯一事实引用，以所属函数定位 |
| time:416 | 命中 9 处 | 已注明非唯一并以 415 定位，合格 |

工单 **L99** 替换为：

> ### 2.3 `scripts/tests/test_anchor_plan_v3.py` —— 回归（在基线 `:521` 唯一整行锚 `def main():` 前插入，保持定义间两空行）

工单 **L16** 替换为：

> - 0.5 行号均指基线 f4f80567c21f；施工锚使用目标文件整行原文，以 `grep -n -F -x` 核验恰 1 处且行号一致，不符停工。`time_spotcheck.py:416` 非唯一，以 :415 定位；`shared_release_receipt.py:371、377、997` 为非唯一事实引用，分别按 `bound_case_ref`、`_validated_time_plan_authority` 定位。删除 > 修改 > 新增；新增代码只准放在 §2 指定位置。

**L166** 的旧版本整行锚应为：

```text
- **9.0.2**（2026-09-19）口径漂移与文档-代码不符审计第二期闭环（针对 7.2.0→9.0.1 六版代码大改而文档零改动）：codex 两路盲审十三轮（a 路全范围术语表法 9→2→3→4→2→2→2→2→1→1→2→0→1，b 路 7.2.0 起代码变更区专审 0→0→2→1→1→0→1→2→2→0→0→0→0；用户裁决 R13 修完即收官），十二份工单皆先 codex 只读复核（退回 9 次全在派工前拦下）再 codex 施工，38 条/21 文件纯文本修复，零代码改动；references 930076→929092（净减 984 B）、SKILL.md 8021 不变、commands-staging 8798→8789；范围外残留一条登记（fetch_sqd_transfers_v2 帮助文字，改则变采集器 sha）。
```

**L167** 的旧版本整行锚应为：

```text
## [9.0.2] - 2026-09-19 — 口径漂移与文档-代码不符审计第二期闭环（零代码改动）
```

**3. b）来源与事实：核心成立，需收窄部分表述**

**① generate/verify 调用链成立。**

`handoff_manifest:349/483 → validate_reconciliation_report:1445 → validate_reconciliation_check:1391 → _validate_time_receipt:1069 → _validated_time_plan_authority`。

其他前置条件通过时，只修生产者仍会因目录身份进入 `_bound_case_ref` 被拒；READY generate 返回 2。verify 的该路径条件是非 legacy，或 wrapper 已存在。

**② 当前生产者生成的 manifest path 确实为绝对路径。**

`anchor_plan:107,153` 已归一输出目录；199–201 未传 `input_base`，`_file_ref:87-94` 保存解析后的绝对路径。但校验器没有保证任意外部 plan 的该字段都绝对。

工单 **L52 第一项**替换为：

> ①当前 `anchor_plan.py` 正常生成的 `plan["input_manifest"]["path"]` 为绝对路径：:107、153 归一输出目录，:199-201 调用收据核未传 input_base，`receipt_kernel._file_ref:87-94` 保存解析后的绝对路径。本修复沿用该生产者产物约定，不增加相对路径兜底；这不是对任意外部 plan 的格式保证。

**③ 目录身份确实重算。**

`validate_semantic_replay:203-210` 调用 `input_identity(raw_input)`，比较实际与声明的 SHA256。目录身份计算遍历全部普通文件，计算 size/hash，再对规范化清单计算哈希。随后还会重放并比较选点、统计。

准确说法是“SHA256 相等”，不是身份字典逐字段全等。

**④ 合成列名及整数秒正确。**

目录 SQL 所需 logs 列为 `block_number/transaction_hash/topic1/topic2/data`，blocks 列为 `number/timestamp`；工单全部提供。`block_hash/log_index` 在该解析器中未使用。整数秒乘 1000000 后传入 `make_timestamp` 正确。

**⑤ 24 行不会因最小覆盖被拒。**

默认 `per_cell=2`、`edge_max=5` 满足最低 2、3。代码只对非空格子抽样，没有九格齐全或最小总点数要求。

已用 DuckDB 1.5.4 在内存中代入相同数据并执行原目录 SQL、选点逻辑，结果为：

| 项目 | 结果 |
|---|---|
| 日期 | 2025-01-01～03 |
| cell_population | 中·大户 8；晚·大户 16 |
| 矩阵点 | 4 |
| 强制点 | 9 |
| 截止块校验 | 通过 |

该实验替换了 parquet 文件读取，没有落盘，不等同于完整 CLI 测试。

工单 **L157 最后一项**替换为：

> ③整数秒按 `make_timestamp((ts_i * 1000000)::BIGINT)` 正确解析。24 行与既有 `_produce_plan` 使用相同数据及参数，默认 per_cell=2、edge_max=5 满足覆盖参数下限；空格子不会触发拒收，不需增加行数或调整余额档。

**历史来源需订正。** 1a7e685 的日期确为 2026-08-07，但其父提交已有目录身份、目录读取和清单绑定，不能将其当作首次引入。

工单 **L3** 中相应短语替换为：

> 至少在 1a7e685（2026-08-07）的父提交中已接受目录输入；1a7e685 将相关逻辑收敛到共享核心

QUQ 行数、7.6 GB、原案运行结果及前案输入形态，本次没有访问原案独立验证。工单 **L6 开头**替换为：

> 调度方提供的案情记录（本次源码复核未访问原案独立验证）：

**4. c）修法定形：保留正文检查，恢复文件分支顺序**

**不能删掉清单正文核验。** 引用三验只能证明“这是绑定的文件”，不能证明正文 `input` 等于 `plan.input/input_identity`。只复用 manifest 引用不满足 §1.2，也无法发现哈希绑定自洽、但正文身份不一致的清单。

**不重哈希的安全边界必须写清。** 发布期重哈希能发现目录生产后的变化，但增加全目录读取成本，并改变工单已经选定的边界。保留现方案意味着：存在性检查不能证明目录内容自生产后未变。

工单 **L24** 替换为：

> - 1.2 发布消费者不重算目录哈希。目录内容身份由时间生产者在 :350-351 的语义重放中重算并核对；发布期只验证时间收据 inputs.input 三验、该文件与 plan receipt 清单绑定相同、清单正文 input＝input_identity＝plan.input，并检查目录路径为案根内普通目录且末级非 symlink。该发布检查不证明目录内容自生产完成后未改变。

**文件分支不是“逐字节不变”。** 提前显式校验 manifest，会改变部分同时有错输入的首个异常。工单举的“identity 非文件＋manifest 缺失”并不准确，因为前面的 `validate_receipt` 已验证清单实物；准确例子是 identity 无效，同时 `plan.input_manifest` 与 receipt 引用不一致。

对 `scripts/tests` 搜索以下三类原文，均为零命中：

- `time plan input identity`
- `time plan input manifest`
- `signed input identity`

因此“既有测试只匹配各自 needle”没有依据。

工单 **L70–94** 建议替换为：

```python
        identity = plan_receipt.get("input_identity")
        _require(isinstance(identity, dict) and plan.get("input") == identity,
                 "plan input identity differs from signed receipt")
        if identity.get("kind") != "directory":
            identity_path = _bound_case_ref(root, identity, "time plan input identity")
            _require(identity_path == input_path,
                     "signed input identity is not the time receipt input object")

        manifest = (plan_receipt.get("inputs") or {}).get("input_manifest")
        manifest_path = _bound_case_ref(root, manifest, "time plan input manifest")
        _require(isinstance(manifest, dict) and plan.get("input_manifest") == manifest,
                 "plan input manifest differs from signed receipt binding")
        if identity.get("kind") == "directory":
            _require(input_path == manifest_path,
                     "directory input identity is not bound through the signed input manifest")
            manifest_doc = strict_json_loads(
                manifest_path.read_text(encoding="utf-8"),
                parse_constant=_reject_constant)
            _require(isinstance(manifest_doc, dict) and manifest_doc.get("input") == identity,
                     "input manifest identity differs from signed identity")
            directory = Path(str(identity.get("path") or ""))
            _require(directory.is_absolute() and not directory.is_symlink()
                     and directory.resolve().is_dir()
                     and directory.resolve().is_relative_to(Path(root).resolve()),
                     "signed directory identity is not a directory inside the case root")
```

工单 **L97 第一项**替换为：

> ①文件分支保留 identity 校验→同一实物校验→manifest 校验的原有顺序。现有测试未直接匹配上述三类错误文本，不以其通过代替顺序核验。

**macOS alias 不会误拒。** 目录和案根都 resolve，`/var` 与 `/private/var` 能归一；末级 symlink 被拒，中间别名解析后仍在案根内即可，与 `bound_case_ref:355-369` 一致。“非 symlink”并非禁止所有祖先别名，也不是重新扫描目录子项。

**生产者可减少新增代码。** 不必新增第二个 try/except，直接复用现有封装异常处理。

工单 **L27** 替换为：

> - 1.5 生产代码至多新增一个私有辅助函数 `time_spotcheck._bound_input_ref`，不新增公开接口；消费者不新增函数。

L36 函数名及对应调用统一改为 `_bound_input_ref`。工单 **L53–61** 替换为：

> 在现有 `:416` try 内、`:417` build_envelope 前插入 `bound_input = _bound_input_ref(a.input, plan)`；把 `:420` 的 `"input": a.input` 改为 `"input": bound_input`。复用 `:422-424` 异常处理，不新增 try/except。

也可以内联而做到零新增函数；保留私有 helper 的理由仅是方便独立测试。

**5. d）回归面：白名单足够，测试不足**

其他文件要求如下：

| 消费点 | 结论 |
|---|---|
| `receipt_validate:56-78,124-144` | inputs 仍须普通文件；清单满足要求 |
| shared witness `1964-1974` | 记录全部 inputs 文件指纹，清单可正常进入 |
| runner `snapshot_inputs:78-94` | 显式列入 spec 的 inputs 只收文件，但不自动收录时间 CLI 目录参数 |
| handoff、audit、new-analysis、stage2 | 复用深验链，未发现必须为 merged 数据文件的额外约束 |
| data_map/artifacts | 全 inputs 专门登记规则属于 Solana exact |
| freeze `1264-1277` | 要求登记 provenance source.files，不是所有 EVM 时间收据 inputs |

若真实案卷 spec 把目录直接登记为文件输入，runner 仍会拒收。本次未读原案，不能宣称已经排除该配置问题；没有证据要求为此扩大生产代码修改范围。

**invariant_manifest 无需因 helper 新增而登记。** 扫描器登记 schema、生产消费点、transport、atomic 等，不登记所有公开函数。已在内存代入两份拟改源码，其扫描结果与基线相同；未运行完整 invariant suite。

**producer_history 无需登记 time_spotcheck。** 它不在 PRODUCER_HISTORY 或 CURRENT_PRODUCERS 中；默认验证当前生产者文件哈希。修改脚本后旧时间收据可能需要重跑，这是现有机制，不应顺便扩大历史哈希允许集。

测试存在三处缺口：

1. L18 要求消费者篡改拒收，L153–154 实际只测生产者。
2. 篡改清单后，沿 `_shared_authority` 会先在 shared:1009–1012 的 plan receipt envelope 校验失败，并非先到 `_bound_case_ref(manifest)`。
3. helper 返回正确不能证明 main 已将其接入 `build_envelope`。

工单 **L18** 替换为：

> - 0.7 基线独立记录：生产者 main 向 build_envelope 传入目录而非清单的失败、目录计划消费者放行失败，以及消费者篡改拒收结果。前两项是修复前失败、修复后通过的 RED；篡改拒收属于保持通过的负例，不要求所有负例在基线变红。各项隔离求值，不因首个异常跳过后项；不得仅用新增 helper 不存在的 AttributeError 证明原缺陷。

工单 **L139 后**新增：

> 调用 `validate_semantic_replay(plan, source)` 验证目录 fixture 的完整重放。另调用真实 main，用 mock 在 build_envelope 入口记录参数并以受控异常终止，断言 `inputs["input"]` 为清单路径；必须在任何 RPC 前终止，不发网络请求。基线应捕获到目录路径，从而让该断言失败。

工单 **L152 后**插入：

```python
        _expect_reject(
            lambda: _shared_authority(root, manifest_path, plan_path, receipt_path),
            "plan receipt envelope invalid")
```

工单 **L157 第一项**替换为：

> ①消费者清单实物篡改先由 plan receipt envelope 校验拒绝；显式断言该拒绝。另在独立子场景同步更新清单引用与 plan 输出哈希、保持 plan.input/input_identity 不变，断言消费者报 `input manifest identity differs from signed identity`，以覆盖清单正文身份检查；不得只靠外层哈希拒收替代该断言。

新用例会被 `test_anchor_plan_v3.py:522-525` 自动发现，无需登记。

**6. e）上下文与精简：存在 0 B 等价改法**

+21 B 算术正确，但没有必要增长。将 `merged input `，含末尾空格的 **13 B**，替换为 `文件/清单`，也是 **13 B**，整行维持 **326 B**。

工单 **L161** 替换为：

> - 基线 `references/data-pipeline-evm-recon.md:158` 以整行原文为锚，仅将 `merged input `（含末尾空格）替换为 `文件/清单`；该行 UTF-8 为 326→326 B。

替换后整行原文：

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`，target 绑定 chain/token/final-block，并绑定 plan、plan receipt、文件/清单与逐笔 RPC transcript；verdict/exit_code 为 0 PASS/2 FAIL/1 检测自身失败禁当 PASS）；split-run 案是 READY 必备件＋AUTO_GATES（handoff_manifest 重读防手报）。
```

旧整行锚即将其中 `文件/清单` 还原为 `merged input `。

工单 **L25** 的“净增 ≤ +21 B”替换为“净增 0 B”。

原拟 CHANGELOG 索引为 **439 B**，既有 13–25 行为 **192–1373 B**，量级相当，不能单凭长度判不合格。可选精简文本，替换 **L166 新条目**：

```text
- **9.0.3**（2026-09-23）修复 v2 目录输入的时间抽查收据绑定：生产者绑定 anchor_plan 输入清单，发布消费者验证清单身份；文件分支校验顺序保留。schema/键不变，references/SKILL/commands 字节不增；新增目录回归。
```

测试可以共用原 `_produce_plan` 的 CLI 调用。工单 **L102–132** 可替换为：

> 将现有 `_produce_plan(root)` 改为 `_produce_plan(root, *, directory=False)`：保留原 CSV 默认路径，在 directory=True 分支构造本工单的 logs/blocks parquet；两分支共用原 :108-128 的 anchor_plan 调用和返回。新用例调用 `_produce_plan(root, directory=True)`，不新增 `_produce_directory_plan`。

**7. f）范围与版本：9.0.3 可保留**

修复限于两个生产文件、同一测试文件、单行文档及版本登记，范围合理。

CHANGELOG:4 确实把“新公开接口或持久化契约扩展”归为次版本。因此“schema/键没变”不是充分理由。支持修版本的关键证据是：既有 CLI、计划生产者和语义重放已经承诺目录输入，此次修通的是失效路径。

采用私有 helper 后，**9.0.3 恰当**。若坚持把 helper 作为新增对外接口，就应按仓库规则记次版本。

工单 **L167 成本指标**替换为：

> 生产逻辑文件 2、新公开入口 0、私有辅助函数至多 1、新增产物输出键 0、外部网络 0、不运行真实案卷判断链。

另有验收证据错误：**L172** 的 `git diff --stat f4f80567c21f HEAD` 不包含未提交的施工修改。替换为：

> `git diff --stat f4f80567c21f -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 全文，并附 `git status --short` 标明本工单目录下的新增报告与证据文件。

| 审查项 | 结论 | 必须处理 |
|---|---|---|
| a 锚与行号 | 退回 | 完整行锚、418–420、521、重复事实行说明 |
| b 来源与事实 | 核心通过，文字订正 | 历史引入时间、绝对路径保证范围、案情来源限定 |
| c 修法 | 方向通过，方案修改 | 保留文件校验顺序及清单正文核验 |
| d 回归面 | 白名单足够，测试不足 | main 接线、消费者篡改及自洽重绑负例 |
| e 上下文 | 退回 +21 B 方案 | 采用 0 B 替换；复用测试运行部分 |
| f 范围与版本 | 9.0.3 可保留 | helper 私有化，不宣称新增公开入口 |
| 验证记录 | 只读复核完成 | 完整 CLI、定向套件由施工阶段执行 |

本次完成了源码与整行锚核验、内存目录 SQL 和覆盖验证、拟改源码 invariant 扫描项对比；未运行会创建案卷或临时文件的完整测试套件，不能登记为 §0.8 全部 PASS。
