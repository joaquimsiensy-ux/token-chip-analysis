# 工单 T1（v4，融合 codex 复核 r1/r2 全部意见＋施工 attempt1 停工勘误）：time_spotcheck 与发布校验器对「v2 目录输入」的收据绑定对齐 —— repair-20260923-t1-spotcheck-dir-input

> 出处：QUQ 0922 案 −1 阻塞点 ANOM-008（调度方本机复现）。`anchor_plan.py` 至少在 1a7e685（2026-08-07）的父提交中已接受目录输入（1a7e685 将相关逻辑收敛到共享核心 `anchor_selection`：`input_identity` 对目录产 `kind=directory`＋文件清单哈希；`_detect_input` 读 `run_*/logs.parquet`），并把清单写成 `anchor_plan.input.json`、以该**清单文件**绑进 `anchor_plan.receipt.json`（`anchor_plan.py:194-203`）。但下游两处仍假定输入是普通文件：
> ① 生产者 `scripts/lib/time_spotcheck.py:417-421` 把 CLI `--input`（目录）原样交给 `receipt_kernel.build_envelope`，`_resolved_input`（`receipt_kernel.py:53-78`，`:77` 判 `is_file`）拒 `input is not a regular file: data/v2` → exit 1，`time_spotcheck.json` 不产；语义重放（`:350-351`，对目录已跑通）在其之前，故退出码是 1 不是 2。
> ② 消费者 `scripts/report/shared_release_receipt.py:_validated_time_plan_authority`（`:987-`；`:998-999`、`:1033-1038`）对 `plan_receipt.input_identity` 走 `_bound_case_ref`（＝`bound_case_ref:347-377`，要求案根内普通文件＋size/sha 全等）并要求它与时间收据的 `inputs.input` 同一实物——目录身份必拒。调用链 `handoff_manifest.py:349`（generate READY）/`:483`（verify）→ `validate_reconciliation_report:1445` → `validate_reconciliation_check:1391` → `_validate_time_receipt:1069` → `_validated_time_plan_authority`，故只修①、−1 交接 READY 仍会被自己的 generate 拒（返回 2）。
> 复现：`build_envelope(..., inputs={"input": "data/v2"})` → `ReceiptKernelError: input is not a regular file: data/v2`；换 `anchor_plan.input.json` 通过。调度方提供的案情记录（本次源码复核未访问原案独立验证）：前案 OPN/BITCOIN/APU 输入均为单文件 `merged.parquet` 故未暴露；QUQ 1.097 亿行按手册 §12/§12b 走不物化的 `replay_stream`，目录是正式输入形态。
> 用户 2026-09-22 裁决：走方案 A 改 skill；原则＝skill 上下文不增、能删不增、能改不增；codex 施工、codex 常规盲审（三次 FAIL 才换 opus）、收官 codex review 确认问题真正消失；版本 9.0.3（修：既有 CLI、计划生产者与语义重放已承诺目录输入，本次修通失效路径；收据 schema/键不变；不新增公开接口）。
> v2 变更（`review_T1_reply_r1.md`）：整行锚订正（418–420、521、references:158 与 CHANGELOG 13/99 全文）；文件分支保持原校验顺序、清单正文核验保留；helper 改私有 `_bound_input_ref` 并复用既有 try/except；文档改 0 B 等价替换；RED 三项改为"main 接线/消费者放行/篡改拒收"并要求 main 级 mock 接线断言；测试改造 `_produce_plan(root, *, directory=False)` 不新增第二个生产函数；补消费者篡改与自洽重绑负例；验收 diff 命令改为对工作树；历史引入时间、绝对路径保证范围、案情来源限定三处措辞订正。
> v3 变更（`review_T1_reply_r2.md`，仅工单文本）：§0.5 补列非唯一事实行 time:422/424、shared:369；§2.4 文档锚改为代码围栏（去掉误入的字面反斜杠）；§2.5 CHANGELOG:13 给出完整整行原文；§2.3 说明④确定为绝对路径形态（`receipt_validate._input_file:67-78` 接受案根内绝对路径）；§3 去掉"取哪一形态"。修法、测试、白名单、版本档位与 v2 相同。
> v4 变更（`T1_done_attempt1_stopped.md`，仅测试夹具一行）：§2.3 新用例 `root = Path(td).resolve()`——macOS `tempfile` 目录经 `/var`→`/private/var` symlink，`time_spotcheck.py:409` 的 `assert_distinct_paths` 经 `receipt_kernel._secure_target`（`:248-249`）拒父级 symlink 输出路径，mock 接线前即返回 1；归一后无 symlink 父级（调度方本机实证）。§0.7 RED 第①项夹具同此写法。其余与 v3 相同；本条为施工方停工报告已考证结论，调度方亲核采纳。
> 内容基线：`f4f80567c21f`（v9.0.2 + labels miss-queue 追加），行号按此核。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `T1_done.md`：`git status --short`（须为空）；`git diff --stat f4f80567c21f HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `T1_done_attempt<N>_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。豁免：§0.8 指定测试自身以子进程访问历史目录属测试依赖，允许原样运行。
- 0.3 **白名单**：生产 `scripts/lib/time_spotcheck.py`、`scripts/report/shared_release_receipt.py`；测试 `scripts/tests/test_anchor_plan_v3.py`；文档 `references/data-pipeline-evm-recon.md`（仅 §2.4 一行）；版本登记 `VERSION`、`pyproject.toml`、`SKILL.md`（仅 `:23` 版本注释行）、`CHANGELOG.md`；本目录新建 `T1_done.md`、`T1_red_evidence.txt`，停工时 `T1_done_attempt<N>_stopped.md`。
- 0.4 **不改**：`scripts/lib/receipt_kernel.py`（`_resolved_input` 只收普通文件是收据核契约，不放宽）、`scripts/lib/anchor_selection.py`、`scripts/lib/anchor_plan.py`、`scripts/lib/receipt_validate.py`、`scripts/lib/producer_history.py`（time_spotcheck 不在 `PRODUCER_HISTORY`/`CURRENT_PRODUCERS`，不登记、不扩历史哈希集）、`scripts/report/handoff_manifest.py`、`scripts/report/reconciliation_report.py`、`scripts/tests/test_time_spotcheck.py`（dry-run 不经收据封装，不在此加用例）、`invariant_manifest.json`/`contract_manifest.json`（开工与完工各跑一次 `python3 -B scripts/tests/invariant_scan.py` 证实无需登记）、`commands-staging/`、其余 references。
- 0.5 行号均指基线 f4f80567c21f；施工锚使用目标文件**整行原文**，以 `grep -n -F -x` 核验恰 1 处且行号一致，不符**停工**。`time_spotcheck.py:416、422、424` 为非唯一事实引用，以 `:415` 的唯一整行及其后收据封装 try/except 定位；`shared_release_receipt.py:369、371、377、997` 为非唯一事实引用，前三项按 `bound_case_ref`、末项按 `_validated_time_plan_authority` 定位。删除 > 修改 > 新增；新增代码只准放在 §2 指定位置。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset。
- 0.7 先红后绿，基线独立记录三项写 `T1_red_evidence.txt`（attempt1 已取得第②③项证据，可沿用其结果并注明来源）：①生产者 main 向 `build_envelope` 传入目录而非清单（按 §2.3 的 mock 接线法在基线上求值，夹具根目录须 `Path(td).resolve()`，基线应捕获到目录路径）；②目录计划的消费者放行（基线 `_validated_time_plan_authority` 抛 `time plan input identity is not a regular file`）；③消费者篡改拒收结果。前两项是修复前失败、修复后通过的 RED；篡改拒收属于保持通过的负例，不要求在基线变红。各项隔离求值，不因首个异常跳过后项；不得仅用新增 helper 不存在的 AttributeError 证明原缺陷。临时脚本不得留在仓库。
- 0.8 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_anchor_plan_v3.py`、`test_time_spotcheck.py`、`test_recon_deep_reverify.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch3_evm_vertical_slice.py`、`python3 -B scripts/tests/invariant_scan.py`、`python3 -B scripts/tests/changelog_lint.py`。沙箱临时目录不可写报 `No usable temporary directory found` 的记 `SANDBOX-BLOCKED`（贴错误行）不计 FAIL，由调度方本机补验。

## 1. 硬约束

- 1.1 `time-spotcheck/v3` 收据 schema、`inputs` 四个键名（`plan`/`plan_receipt`/`input`/`transcript`）、verdict/exit 契约不变；**文件输入路径**：生产者 `inputs.input` 仍绑 merged 文件本身，消费者保留 identity 校验→同一实物校验→manifest 校验的原有顺序。目录输入时 `inputs.input` 绑 `anchor_plan.input.json` 清单文件（即 `plan["input_manifest"]` 所指、已由 `load_validated_plan` `:113-117` 与 plan receipt 对账过的那份实物）。
- 1.2 发布消费者不重算目录哈希。目录内容身份由时间生产者在 `:350-351` 的语义重放中重算（`validate_semantic_replay:203-210` 调 `input_identity(raw_input)` 比对 SHA256）并核对；发布期只验证时间收据 `inputs.input` 三验、该文件与 plan receipt 清单绑定相同、清单正文 `input`＝`input_identity`＝`plan.input`，并检查目录路径为案根内普通目录且末级非 symlink。**该发布检查不证明目录内容自生产完成后未改变**（与文件输入的三验不同，这是本修复明示的验证边界）。
- 1.3 文档三处字节：`SKILL.md` 8021→仅 `:23` 版本号 `9.0.2`→`9.0.3`（字节不变）；`commands-staging/*.md` 8789 不变；`references/**/*.md` 929092 → **只允许 §2.4 一行等长替换，净增 0 B**，完成报告贴替换前后该行字节（326→326）与总字节。
- 1.4 `git diff --stat` 只含 0.3 白名单。
- 1.5 生产代码至多新增一个**私有**辅助函数 `time_spotcheck._bound_input_ref`，不新增公开接口；消费者不新增函数、不新增 import。

## 2. 逐条施工

### 2.1 `scripts/lib/time_spotcheck.py` —— 生产者

- `:180`（整行锚 `def validate_semantic_replay(plan, raw_input, *, mem_limit="6GB", threads=4):`，唯一）之前插入（保持定义间两空行）：

```python
def _bound_input_ref(raw_input, plan):
    """收据 inputs.input 绑定对象：文件输入绑文件本身；v2 目录输入绑 anchor_plan 已签名的清单
    anchor_plan.input.json（receipt_kernel 只收普通文件；目录身份已由 validate_semantic_replay
    重算哈希核过）。清单正文 input 须与 plan.input 全等，否则 fail-closed。"""
    if not Path(raw_input).expanduser().is_dir():
        return raw_input
    manifest_path = Path(str((plan.get("input_manifest") or {}).get("path") or ""))
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if not isinstance(manifest, dict) or manifest.get("input") != plan.get("input"):
        raise ValueError("anchor_plan.input.json input identity differs from plan.input")
    return str(manifest_path)
```

  说明：①当前 `anchor_plan.py` 正常生成的 `plan["input_manifest"]["path"]` 为绝对路径：`:107`、`:153` 归一输出目录，`:199-201` 调用收据核未传 input_base，`receipt_kernel._file_ref:87-94` 保存解析后的绝对路径。本修复沿用该生产者产物约定，不增加相对路径兜底；这不是对任意外部 plan 的格式保证。②`json`（`:38`）、`Path`（`:42`）已导入，不新增 import。
- 在现有 `:416` try 内、`:417` `build_envelope` 前插入一行 `        bound_input = _bound_input_ref(a.input, plan)`；把 `:420`（整行锚 `                                          "input": a.input},`，唯一）改为 `                                          "input": bound_input},`。复用 `:422-424` 既有异常处理（`[fatal] receipt envelope 构建失败`、return 1），不新增 try/except。调用范围 `:417-421` 其余不动。

### 2.2 `scripts/report/shared_release_receipt.py` —— 消费者

- `:1033-1043`（整行锚 `        identity = plan_receipt.get("input_identity")` 起、`                 "plan input manifest differs from signed receipt binding")` 止，两行均唯一）整段替换为：

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
            # v2 目录输入：目录不是普通文件，时间收据 inputs.input 绑的是签名清单；
            # 清单正文 input 须与签名身份全等，目录只做案根内存在性检查，不重算哈希
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

  说明：①文件分支保留 identity 校验→同一实物校验→manifest 校验的原有顺序（原 `:1036-1038` 逐字保留，仅套 `kind != "directory"` 条件）；现有测试未直接匹配上述三类错误文本（`grep scripts/tests` 零命中），不以其通过代替顺序核验。②`strict_json_loads`（`:43` 导入）、`_reject_constant`（`:150`）、`Path`（`:17`）均为本模块既有名字，不新增 import；`Path.is_relative_to` 本仓库 requires-python ≥3.14 可用。③`identity["path"]` 由 `anchor_selection.input_identity` 写成 `str(path.resolve())` 绝对路径；目录与案根都 resolve，macOS `/var`→`/private/var` 别名归一后仍在案根内即可，与 `bound_case_ref:355-369` 处理一致，只拒末级 symlink。

### 2.3 `scripts/tests/test_anchor_plan_v3.py` —— 回归

- 改造 `_produce_plan`（`:99`，整行锚 `def _produce_plan(root):`，唯一）为 `def _produce_plan(root, *, directory=False):`：保留原 CSV 默认路径（`:100-107`）；`directory=True` 分支改为构造 `root / "v2" / "run_1" / {logs,blocks}.parquet`（列：logs `block_number BIGINT, block_hash VARCHAR, log_index BIGINT, transaction_hash VARCHAR, topic1 VARCHAR, topic2 VARCHAR, data VARCHAR`；blocks `number BIGINT, timestamp BIGINT`；24 行与 CSV 分支同数据：`block_number=99+index`、`transaction_hash=f"0xt{index}"`、`topic1="0x"+"0"*64`、`topic2="0x"+"0"*24+f"{index:040x}"`、`data="0x"+f"{100:064x}"`、`timestamp=1735689600+86400*(index%3)` 整数秒；用 duckdb `CREATE TABLE`+`INSERT`+`COPY … (FORMAT parquet)`，`import duckdb` 放函数内），`source = root / "v2"`；两分支共用原 `:108-128` 的 anchor_plan 调用（`--input str(source)`）与返回。不新增第二个生产函数。
  说明：`_detect_input` 目录分支只用 logs `block_number/transaction_hash/topic1/topic2/data` 与 blocks `number/timestamp`（`block_hash/log_index` 不用但保持列形态）；整数秒按 `make_timestamp((ts_i * 1000000)::BIGINT)` 正确解析；24 行与 `_produce_plan` 同数据同参数，默认 per_cell=2、edge_max=5 满足覆盖下限，空格子不触发拒收，不需调行数或余额档（复核 r1 已用同数据在内存代入目录 SQL 验证：矩阵点 4、强制点 9、截止块校验通过）。
- 在 `:521`（整行锚 `def main():`，唯一）之前插入（保持两空行）：

```python
def test_16_directory_input_binds_signed_manifest():
    with tempfile.TemporaryDirectory(prefix="anchor_v3_dir_") as td:
        root = Path(td).resolve()  # macOS TMPDIR 经 /var symlink，receipt_kernel 拒父级 symlink 输出路径
        source, plan_path, receipt_path = _produce_plan(root, directory=True)
        plan = time_spotcheck.load_validated_plan(plan_path, receipt_path)
        assert plan["input"]["kind"] == "directory"
        time_spotcheck.validate_semantic_replay(plan, source)
        manifest_path = Path(plan["input_manifest"]["path"])
        # 生产者 helper：目录输入绑清单文件；文件输入绑文件本身
        assert Path(time_spotcheck._bound_input_ref(str(source), plan)) == manifest_path
        assert time_spotcheck._bound_input_ref(str(plan_path), plan) == str(plan_path)
        # 生产者 main 接线：mock build_envelope 记录 inputs 并以受控异常终止（在任何 RPC 之前）
        captured = {}
        def fake_envelope(*args, **kwargs):
            captured.update(kwargs.get("inputs") or {})
            raise RuntimeError("stop-before-rpc")
        real_envelope, real_argv = time_spotcheck.build_envelope, sys.argv
        out = root / "time_spotcheck.json"
        sys.argv = ["time_spotcheck.py", "--plan", str(plan_path), "--input", str(source),
                    "--chain", "bsc", "--token", TOKEN, "--final-block", "300",
                    "--rpc", "http://127.0.0.1:9", "--out", str(out)]
        try:
            time_spotcheck.build_envelope = fake_envelope
            assert time_spotcheck.main() == 1
        finally:
            time_spotcheck.build_envelope, sys.argv = real_envelope, real_argv
        assert Path(captured["input"]) == manifest_path
        assert not out.exists()
        # 消费者：inputs.input=清单 → 放行；=计划文件 → 拒
        assert _shared_authority(root, manifest_path, plan_path, receipt_path) == plan
        _expect_reject(lambda: _shared_authority(root, plan_path, plan_path, receipt_path),
                       "directory input identity is not bound through the signed input manifest")
        # 清单实物篡改：先由 plan receipt envelope 校验拒绝（生产者 helper 亦拒）
        original = manifest_path.read_bytes()
        tampered = json.loads(original.decode("utf-8"))
        tampered["input"]["sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(tampered, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        _expect_reject(lambda: _shared_authority(root, manifest_path, plan_path, receipt_path),
                       "plan receipt envelope invalid")
        _expect_reject(lambda: time_spotcheck._bound_input_ref(str(source), plan),
                       "input identity differs from plan.input")
        # 自洽重绑：同步更新清单引用与 plan 输出哈希、保持 plan.input/input_identity 不变 → 正文身份检查拒
        new_ref = _ref(manifest_path, root)
        new_ref["path"] = str(manifest_path)
        plan_doc = json.loads(plan_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        plan_doc["input_manifest"] = new_ref
        receipt["inputs"]["input_manifest"] = new_ref
        plan_path.write_text(json.dumps(plan_doc, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                encoding="utf-8")
        _refresh_receipt(plan_path, receipt_path)
        _expect_reject(lambda: _shared_authority(root, manifest_path, plan_path, receipt_path),
                       "input manifest identity differs from signed identity")
        manifest_path.write_bytes(original)
```

  说明：①`_expect_reject`（`:73-80`）按 needle 子串匹配 ValueError。②`_shared_authority`（`:148-157`）第二参数即 `inputs.input` 所绑文件。③mock 依赖 `main` 通过模块全局名 `build_envelope`（`:56` 导入、`:417` 调用）；`:398-403` 的 rpc/chain/final-block 前置由 argv 满足，`:409` `assert_distinct_paths` 离线；`fake_envelope` 抛出后被 `:422-424` 捕获返回 1，任何 RPC 之前终止、不发网。④自洽重绑保留 `new_ref["path"] = str(manifest_path)`。当前 anchor_plan 生成绝对路径清单引用；`receipt_validate._input_file:67-78` 接受解析后位于案根内的绝对路径，不会因其绝对形态拒收。`_shared_authority` 的 plan/plan_receipt 引用仍由 `_ref` 生成案根相对路径；`_refresh_receipt:131-136` 同步更新 plan 输出的 size/sha256。该场景保持 plan.input/input_identity 不变，须命中清单正文身份不一致的错误。新用例由 `main`（`:522-525`）自动发现，无需登记。

### 2.4 `references/data-pipeline-evm-recon.md`

- 基线 `references/data-pipeline-evm-recon.md:158` 的唯一整行锚如下（UTF-8 326 B，不含换行）：

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`，target 绑定 chain/token/final-block，并绑定 plan、plan receipt、merged input 与逐笔 RPC transcript；verdict/exit_code 为 0 PASS/2 FAIL/1 检测自身失败禁当 PASS）；split-run 案是 READY 必备件＋AUTO_GATES（handoff_manifest 重读防手报）。
```

仅将 `merged input `（含末尾空格，13 B）替换为 `文件/清单`（13 B）；该行 UTF-8 326→326 B。替换后整行：

```text
- 产物 `time_spotcheck.json`（`time-spotcheck/v3`，target 绑定 chain/token/final-block，并绑定 plan、plan receipt、文件/清单与逐笔 RPC transcript；verdict/exit_code 为 0 PASS/2 FAIL/1 检测自身失败禁当 PASS）；split-run 案是 READY 必备件＋AUTO_GATES（handoff_manifest 重读防手报）。
```

### 2.5 版本登记 9.0.3

- `VERSION` 整文件 `9.0.2`→`9.0.3`；`pyproject.toml:15` `version = "9.0.2"`→`"9.0.3"`；`SKILL.md:23` 注释 `skill-version: 9.0.2`→`9.0.3`。
- `CHANGELOG.md:13` 的唯一整行锚如下，在其之前插入下述一行索引：

```text
- **9.0.2**（2026-09-19）口径漂移与文档-代码不符审计第二期闭环（针对 7.2.0→9.0.1 六版代码大改而文档零改动）：codex 两路盲审十三轮（a 路全范围术语表法 9→2→3→4→2→2→2→2→1→1→2→0→1，b 路 7.2.0 起代码变更区专审 0→0→2→1→1→0→1→2→2→0→0→0→0；用户裁决 R13 修完即收官），十二份工单皆先 codex 只读复核（退回 9 次全在派工前拦下）再 codex 施工，38 条/21 文件纯文本修复，零代码改动；references 930076→929092（净减 984 B）、SKILL.md 8021 不变、commands-staging 8798→8789；范围外残留一条登记（fetch_sqd_transfers_v2 帮助文字，改则变采集器 sha）。
```

插入的索引行（一行）：

```text
- **9.0.3**（2026-09-23）修复 v2 目录输入的时间抽查收据绑定（QUQ 0922 案 ANOM-008）：生产者目录输入时 inputs.input 绑 anchor_plan 已签名输入清单，发布消费者对 kind=directory 验证清单身份、不重算目录哈希；文件分支校验顺序保留。schema/键不变，references/SKILL/commands 字节不增；测试 +1 目录回归用例；版本档位 修。
```
- `CHANGELOG.md:99`（整行锚 `## [9.0.2] - 2026-09-19 — 口径漂移与文档-代码不符审计第二期闭环（零代码改动）`，唯一）之前插入详细段，标题 `## [9.0.3] - 2026-09-23 — QUQ ANOM-008：v2 目录输入的时间抽查收据绑定对齐（生产者＋发布校验器）`，条目按 9.0.1 段同款五项：出处与裁决（本工单头部压缩，含验证边界 §1.2）、生产者改法、消费者改法与信任链、字节与测试（真实 diff 数字）、成本-质量指标（生产逻辑文件 2、新公开入口 0、私有辅助函数 1、新增产物输出键 0、外部网络 0、不运行真实案卷判断链）。
- 写完跑 `python3 -B scripts/tests/changelog_lint.py` 须 PASS。

## 3. 完成报告 `T1_done.md`

开工基线两项输出；RED 取证三条摘要（指向 `T1_red_evidence.txt`）；每条施工的实际 diff 行号；§0.8 各命令尾行；三处字节前后（含 §2.4 该行 326→326）；`git diff --stat f4f80567c21f -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md` 全文（对工作树，非 HEAD），并附 `git status --short` 标明本目录新增的报告与证据文件；与工单差异（若有）；末尾披露是否读过禁读路径。不 commit。
