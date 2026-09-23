# 工单 T1（v1）：time_spotcheck 与发布校验器对「v2 目录输入」的收据绑定对齐 —— repair-20260923-t1-spotcheck-dir-input

> 出处：QUQ 0922 案 −1 阻塞点 ANOM-008（调度方本机复现）。`anchor_plan.py` 自 1a7e685（2026-08-07）起接受目录输入（`anchor_selection.input_identity` 对目录产 `kind=directory`＋文件清单哈希；`_detect_input` 读 `run_*/logs.parquet`），并把清单写成 `anchor_plan.input.json`、以该**清单文件**绑进 `anchor_plan.receipt.json`（`anchor_plan.py:194-203`）。但下游两处仍假定输入是普通文件：
> ① 生产者 `scripts/lib/time_spotcheck.py:417-421` 把 CLI `--input`（目录）原样交给 `receipt_kernel.build_envelope`，`_resolved_input`（`receipt_kernel.py:77`）拒 `input is not a regular file: data/v2` → exit 1，`time_spotcheck.json` 不产；语义重放（`:350-351`，对目录已跑通）在其之前，故退出码是 1 不是 2。
> ② 消费者 `scripts/report/shared_release_receipt.py:_validated_time_plan_authority`（`:998-999`、`:1033-1038`）对 `plan_receipt.input_identity` 走 `_bound_case_ref`（`:371` 要求普通文件）并要求它与时间收据的 `inputs.input` 同一实物——目录身份必拒。该函数被 `validate_reconciliation_report` 调用，而 `handoff_manifest.py:349`（generate READY）与 `:483`（verify）都调它，故只修①、−1 交接 READY 仍会被自己的 generate 拒。
> 复现：`build_envelope(..., inputs={"input": "data/v2"})` → `ReceiptKernelError: input is not a regular file: data/v2`；换 `anchor_plan.input.json` 通过。前案 OPN/BITCOIN/APU 输入均为单文件 `merged.parquet` 故未暴露；QUQ 1.097 亿行按手册 §12/§12b 走不物化的 `replay_stream`，目录是正式输入形态。
> 用户 2026-09-22 裁决：走方案 A 改 skill；原则＝skill 上下文不增、能删不增、能改不增；codex 施工、codex 常规盲审（三次 FAIL 才换 opus）、收官 codex review 确认问题真正消失；版本 9.0.3（既定契约内修复：收据 schema/键不变，`inputs.input` 在目录输入时绑清单文件）。
> 内容基线：`f4f80567c21f`（v9.0.2 + labels miss-queue 追加），行号按此核。

## 0. 开工纪律

- 0.1 工作目录＝`/Users/uravvv/.claude/skills/token-chip-analysis`。开工先跑并贴进 `T1_done.md`：`git status --short`（须为空）；`git diff --stat f4f80567c21f HEAD -- scripts references SKILL.md commands-staging VERSION pyproject.toml CHANGELOG.md`（须为空）。不空即停工写 `T1_done_attempt<N>_stopped.md`。
- 0.2 **禁读** `~/.codex/`（启动搜索若已读 memories 披露一次，之后不再读）；禁读 `archive/`、`blind-reviews/`、`.staging_*`、`references/attic.md`、本目录以外的全部历史 maintenance 目录；禁读 `/Users/uravvv/Desktop`、`/Users/uravvv/Documents`。豁免：§0.8 指定测试自身以子进程访问历史目录属测试依赖，允许原样运行。
- 0.3 **白名单**：生产 `scripts/lib/time_spotcheck.py`、`scripts/report/shared_release_receipt.py`；测试 `scripts/tests/test_anchor_plan_v3.py`；文档 `references/data-pipeline-evm-recon.md`（仅 §2.4 一行）；版本登记 `VERSION`、`pyproject.toml`、`SKILL.md`（仅 `:23` 版本注释行）、`CHANGELOG.md`；本目录新建 `T1_done.md`、`T1_red_evidence.txt`，停工时 `T1_done_attempt<N>_stopped.md`。
- 0.4 **不改**：`scripts/lib/receipt_kernel.py`（`_resolved_input` 只收普通文件是收据核契约，不放宽）、`scripts/lib/anchor_selection.py`、`scripts/lib/anchor_plan.py`、`scripts/lib/receipt_validate.py`、`scripts/report/handoff_manifest.py`、`scripts/report/reconciliation_report.py`、`scripts/tests/test_time_spotcheck.py`（dry-run 不经收据封装，不在此加用例）、`invariant_manifest.json`/`contract_manifest.json`（开工与完工各跑一次 `python3 -B scripts/tests/invariant_scan.py` 证实无需登记）、`commands-staging/`、其余 references。
- 0.5 行号均指基线 f4f80567c21f；锚 `grep -n -F` 恰 1 处且行号一致，不符**停工**。删除 > 修改 > 新增；新增代码只准放在 §2 指定位置。
- 0.6 离线；不 commit、不 push；禁 stash/checkout/reset。
- 0.7 先红后绿：§2.3 新用例中的三个断言（生产者绑定、消费者放行、消费者拒篡改）在改生产代码前逐条独立求值写 `T1_red_evidence.txt`（预期：生产者绑定 → 基线无 `bound_input_ref` 属性 AttributeError／改用直接 `build_envelope(..., inputs={"input": <目录>})` 复现 `input is not a regular file`；消费者放行 → 基线 `_validated_time_plan_authority` 抛 `time plan input identity is not a regular file`）。临时脚本不得留在仓库。
- 0.8 不跑 `run_all.py`（调度方本机跑）。定向跑（全部须 PASS，贴尾行）：`python3 -B scripts/tests/test_anchor_plan_v3.py`、`test_time_spotcheck.py`、`test_recon_deep_reverify.py`、`test_handoff_manifest.py`、`test_audit_release_gate.py`、`test_batch3_evm_vertical_slice.py`、`python3 -B scripts/tests/invariant_scan.py`、`python3 -B scripts/tests/changelog_lint.py`。沙箱临时目录不可写报 `No usable temporary directory found` 的记 `SANDBOX-BLOCKED`（贴错误行）不计 FAIL，由调度方本机补验。

## 1. 硬约束

- 1.1 `time-spotcheck/v3` 收据 schema、`inputs` 四个键名（`plan`/`plan_receipt`/`input`/`transcript`）、verdict/exit 契约不变；**文件输入路径行为逐字节不变**（`inputs.input` 仍绑 merged 文件本身）。目录输入时 `inputs.input` 绑 `anchor_plan.input.json` 清单文件（即 `plan["input_manifest"]` 所指、已由 `load_validated_plan` `:113-117` 与 plan receipt 对账过的那份实物）。
- 1.2 消费者对目录身份**不重算目录哈希**（QUQ 7.6 GB，发布期不可承受）；信任链＝时间收据 `inputs.input` 三验 ⇒ 该文件 ≡ plan receipt 绑定的清单 ⇒ 清单正文 `input` ≡ 签名身份 `input_identity` ≡ `plan.input`；目录本身只做"案根内、非 symlink、is_dir"存在性检查。
- 1.3 文档三处字节：`SKILL.md` 8021→仅 `:23` 版本号 `9.0.2`→`9.0.3`（字节不变）；`commands-staging/*.md` 8789 不变；`references/**/*.md` 929092 → **只允许 §2.4 一行替换**，净增 ≤ +21 B，完成报告贴替换前后字节。
- 1.4 `git diff --stat` 只含 0.3 白名单。
- 1.5 新增函数只准一个：`time_spotcheck.bound_input_ref`（§2.1）；`shared_release_receipt.py` 不新增函数，只在 `_validated_time_plan_authority` 内改分支。

## 2. 逐条施工

### 2.1 `scripts/lib/time_spotcheck.py` —— 生产者

- `:180`（锚 `def validate_semantic_replay(plan, raw_input, *, mem_limit="6GB", threads=4):`，唯一）之前插入（放在该函数定义前一空行处，保持两空行 PEP8）：

```python
def bound_input_ref(raw_input, plan):
    """收据 inputs.input 绑定对象：文件输入绑文件本身；v2 目录输入绑 anchor_plan 已签名的清单
    anchor_plan.input.json（receipt_kernel 只收普通文件；目录身份已由 validate_semantic_replay
    重算哈希核过）。清单正文 input 须与 plan.input 全等，否则 fail-closed。"""
    shown = Path(raw_input).expanduser()
    if not shown.is_dir():
        return raw_input
    manifest_ref = plan.get("input_manifest") or {}
    manifest_path = Path(str(manifest_ref.get("path") or ""))
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if not isinstance(manifest, dict) or manifest.get("input") != plan.get("input"):
        raise ValueError("anchor_plan.input.json input identity differs from plan.input")
    return str(manifest_path)
```

  说明：①`anchor_plan.py:194` 写清单用 `Path(a.out_dir) / "anchor_plan.input.json"`，`:199-201` 绑进收据时**未传 input_base**，`receipt_kernel._file_ref`（`:87-94`）此时记 `str(path.resolve())` 绝对路径，故 `plan["input_manifest"]["path"]` 恒为绝对路径（QUQ/OPN/BITCOIN 案实测均绝对），不需相对路径兜底。②`json`（`:38`）、`Path`（`:42`）已导入，不新增 import。
- `:417-421`（锚 `                                  inputs={"plan": a.plan,` 起、`                                          "input": a.input},` 止，唯一）把 `"input": a.input` 改为 `"input": bound_input`，并在 `:416`（锚 `    try:`——注意该行不唯一，以其上一行 `:415` `    target = {"chain": a.chain, "token": token, "as_of_block": a.final_block}` 定位）之前插入：

```python
    try:
        bound_input = bound_input_ref(a.input, plan)
    except Exception as exc:
        print(f"[fatal] 输入绑定对象解析失败: {exc}", file=sys.stderr)
        return 1
```

  说明：放在 `build_envelope` 之前、`validate_semantic_replay`（`:350`）之后——目录哈希≡`plan.input.sha256` 已被重放层核过，本步只决定"收据里写哪份实物"。exit 1 与既有"检测自身失败"档一致。

### 2.2 `scripts/report/shared_release_receipt.py` —— 消费者

- `:1033-1043`（锚 `        identity = plan_receipt.get("input_identity")` 起、`                 "plan input manifest differs from signed receipt binding")` 止，唯一）整段替换为：

```python
        identity = plan_receipt.get("input_identity")
        _require(isinstance(identity, dict) and plan.get("input") == identity,
                 "plan input identity differs from signed receipt")
        manifest = (plan_receipt.get("inputs") or {}).get("input_manifest")
        manifest_path = _bound_case_ref(root, manifest, "time plan input manifest")
        _require(isinstance(manifest, dict) and plan.get("input_manifest") == manifest,
                 "plan input manifest differs from signed receipt binding")
        if identity.get("kind") == "directory":
            # v2 目录输入：目录不是普通文件，时间收据 inputs.input 绑的是签名清单；
            # 清单正文 input 须与签名身份全等，目录只做案根内存在性检查，不重算哈希
            _require(input_path == manifest_path,
                     "directory input identity is not bound through the signed input manifest")
            manifest_doc = strict_json_loads(manifest_path.read_text(encoding="utf-8"),
                                             parse_constant=_reject_constant)
            _require(isinstance(manifest_doc, dict) and manifest_doc.get("input") == identity,
                     "input manifest identity differs from signed identity")
            directory = Path(str(identity.get("path") or ""))
            _require(directory.is_absolute() and not directory.is_symlink()
                     and directory.resolve().is_dir()
                     and directory.resolve().is_relative_to(Path(root).resolve()),
                     "signed directory identity is not a directory inside the case root")
        else:
            identity_path = _bound_case_ref(root, identity, "time plan input identity")
            _require(identity_path == input_path,
                     "signed input identity is not the time receipt input object")
```

  说明：①文件分支逻辑与原 `:1036-1038` 逐字相同，只是顺序上把清单绑定提前（清单绑定原本无条件执行，提前不改变文件分支的拒收集合，但报错先后可能变：原先"identity 不是普通文件"先于"manifest 缺失"报，现反之——对文件输入两者同为 ValueError 且既有测试只匹配各自 needle，施工时跑 §0.8 证实）。②`strict_json_loads`/`_reject_constant`/`Path` 均为本模块既有名字（`:993-997` 已用），不新增 import；`Path.is_relative_to` 需 Python ≥3.9，本仓库 requires-python ≥3.14。③`identity["path"]` 由 `anchor_selection.input_identity` 写成 `str(path.resolve())` 绝对路径。

### 2.3 `scripts/tests/test_anchor_plan_v3.py` —— 回归（一个新用例，放在 `:519`（锚 `def main():` 之前两空行处，`:521` 为 `def main():`）之前）

```python
def _produce_directory_plan(root):
    """v2 目录输入：run_1/{logs,blocks}.parquet（与 anchor_selection._detect_input 目录分支同列）。"""
    import duckdb
    source = root / "v2"
    run_dir = source / "run_1"
    run_dir.mkdir(parents=True)
    con = duckdb.connect()
    try:
        con.execute("CREATE TABLE logs(block_number BIGINT, block_hash VARCHAR, log_index BIGINT, "
                    "transaction_hash VARCHAR, topic1 VARCHAR, topic2 VARCHAR, data VARCHAR)")
        for index in range(1, 25):
            con.execute("INSERT INTO logs VALUES (?,?,?,?,?,?,?)",
                        [99 + index, "0xhash", 0, f"0xt{index}", "0x" + "0" * 64,
                         "0x" + "0" * 24 + f"{index:040x}", "0x" + f"{100:064x}"])
        con.execute(f"COPY logs TO '{run_dir / 'logs.parquet'}' (FORMAT parquet)")
        con.execute("CREATE TABLE blocks(number BIGINT, timestamp BIGINT)")
        for index in range(1, 25):
            con.execute("INSERT INTO blocks VALUES (?,?)",
                        [99 + index, 1735689600 + 86400 * (index % 3)])
        con.execute(f"COPY blocks TO '{run_dir / 'blocks.parquet'}' (FORMAT parquet)")
    finally:
        con.close()
    out = root / "plan"
    proc = subprocess.run(
        [sys.executable, str(LIB / "anchor_plan.py"), "--input", str(source),
         "--chain", "bsc", "--token", TOKEN, "--total-supply", "10000", "--decimals", "0",
         "--min-pct", "0", "--final-block", "300", "--boundary-blocks", "110",
         "--out-dir", str(out)],
        cwd=ROOT, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return source, out / "anchor_plan.json", out / "anchor_plan.receipt.json"


def test_16_directory_input_binds_signed_manifest():
    with tempfile.TemporaryDirectory(prefix="anchor_v3_dir_") as td:
        root = Path(td)
        source, plan_path, receipt_path = _produce_directory_plan(root)
        plan = time_spotcheck.load_validated_plan(plan_path, receipt_path)
        assert plan["input"]["kind"] == "directory"
        manifest_path = Path(plan["input_manifest"]["path"])
        # 生产者：目录输入绑清单文件；文件输入绑文件本身
        assert Path(time_spotcheck.bound_input_ref(str(source), plan)) == manifest_path
        assert time_spotcheck.bound_input_ref(str(plan_path), plan) == str(plan_path)
        # 消费者：inputs.input=清单 → 放行；=计划文件 → 拒；清单正文身份被改 → 拒
        assert _shared_authority(root, manifest_path, plan_path, receipt_path) == plan
        _expect_reject(lambda: _shared_authority(root, plan_path, plan_path, receipt_path),
                       "directory input identity is not bound through the signed input manifest")
        tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
        tampered["input"]["sha256"] = "0" * 64
        manifest_path.write_text(json.dumps(tampered, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        _expect_reject(lambda: time_spotcheck.bound_input_ref(str(source), plan),
                       "input identity differs from plan.input")
```

  说明：①`_expect_reject`（`:73`）签名按现文件用法核实（needle 子串匹配）；篡改清单后消费者会先在 `_bound_case_ref(manifest)` 处按 sha 不符拒，故消费者篡改拒收由既有三验覆盖，用例只对生产者断言篡改。②`_shared_authority`（`:148-157`）第二参数即 `inputs.input` 所绑文件，无需改动。③`timestamp` 用整数秒，`_detect_input` 目录分支按 `make_timestamp(ts*1e6)` 解析。若 `anchor_plan.py` 对该合成目录因 `min coverage` 拒收，把行数/余额档参数调到与 `_produce_plan` 同量级即可，不得改生产代码。

### 2.4 `references/data-pipeline-evm-recon.md`

- `:158`（锚 `并绑定 plan、plan receipt、merged input 与逐笔 RPC transcript`，唯一）把 `merged input` 替换为 `输入（文件或目录清单）`（+21 B）。同行其余字符不动。

### 2.5 版本登记 9.0.3

- `VERSION` 整文件 `9.0.2`→`9.0.3`；`pyproject.toml:15` `version = "9.0.2"`→`"9.0.3"`；`SKILL.md:23` 注释 `skill-version: 9.0.2`→`9.0.3`。
- `CHANGELOG.md:13`（锚 `- **9.0.2**（2026-09-19）`）之前插入一行索引：`- **9.0.3**（2026-09-23）QUQ 0922 案 ANOM-008：time_spotcheck 与发布校验器对 v2 目录输入的收据绑定对齐（生产者目录输入时 inputs.input 绑 anchor_plan 已签名清单；消费者 _validated_time_plan_authority 对 kind=directory 走清单信任链、不重算目录哈希；文件输入行为不变）。references +21 B（evm-recon §12 一行）、SKILL/commands 不变；测试 +1 用例；版本档位 修。`
- `CHANGELOG.md:99`（锚 `## [9.0.2] - 2026-09-19`）之前插入详细段，标题 `## [9.0.3] - 2026-09-23 — QUQ ANOM-008：v2 目录输入的时间抽查收据绑定对齐（生产者＋发布校验器）`，条目按 9.0.1 段同款五项：出处与裁决（本工单头部三段压缩）、生产者改法、消费者改法与信任链、字节与测试（真实 diff 数字）、成本-质量指标（生产逻辑文件 2、新公开入口 1 `bound_input_ref`、新增产物输出键 0、外部网络 0、不运行真实案卷判断链）。
- 写完跑 `python3 -B scripts/tests/changelog_lint.py` 须 PASS。

## 3. 完成报告 `T1_done.md`

开工基线两项输出；RED 取证三条摘要（指向 `T1_red_evidence.txt`）；每条施工的实际 diff 行号；§0.8 各命令尾行；三处字节前后；`git diff --stat f4f80567c21f HEAD` 全文；与工单差异（若有）；末尾披露是否读过禁读路径。不 commit。
