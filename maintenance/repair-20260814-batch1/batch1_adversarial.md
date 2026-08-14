# 批 1 修复工程独立盲审报告（adversarial review）

> 盲审员：Fable（与施工过程零接触，只看仓库现状与落盘材料）
> 基线 main@c41ed07；修复 HEAD=deb073e（分支 repair-20260814-batch1）
> 日期：2026-08-14

## 审计范围与方法

范围＝批 1 五项修复（RV-07 publish_supersede／RV-04 proxy_config＋RV-17／F-03 replay gate／F-01+A5 legend receipt／F-04 token）。方法：读 `plan.md`＋七份施工报告→读 `c41ed07..HEAD` 全量 diff 与关键源码→站在施工方七条反例矩阵的边界外一步，对生产脚本构造恶意输入实跑攻击（沙箱 `/private/tmp/batch1-adversarial/`，全部用 `--data-dir`/临时目录重定向，未改仓库任一生产/测试/文档文件，未执行 git 写命令；`git status --short` 收尾为空）。已核实施工报告的关键绿灯属实：`invariant_scan.py` exit 0（producers=55/atomic=49/exceptions=0）、`test_repair_batch1.py` exit 0、`test_token_no_positional.py` exit 0。

## 总体结论

五项修复的**主体都做对了**，且比修复前显著更硬：真 FAIL 能落盘、pass2 fail-closed、诊断序列被 sidecar 链拒之门外、fig1 双层信任根、位置明文 token 移除、RV-17 断网假闭合被关死——这些我都独立复现为"攻击失败"。但 **RV-07 引入了一条与被修 bug 同类的边界回归**：`publish_supersede` 用 O_EXCL 锁做并发防护，进程在持锁期间被非可捕获信号（SIGKILL/OOM/断电）杀死后，锁文件遗留，此后**同一 canonical 的所有真 FAIL 落盘被永久拒绝**——正是本次修复要消灭的"真 FAIL 落盘死锁"以更窄触发面复活，且错误消息不指认锁文件、五出口把它折叠成与普通降级拒绝无法区分的 `exit 1`。据此 RV-07 判 **FAIL**，其余四项 PASS（含 3 条 P2/P3 深度建议）。

发现计数：**P0×0　P1×1　P2×1　P3×3**。

---

## 发现列表

### [P1] RV-07：supersede 持锁期间崩溃 → 锁遗留 → 真 FAIL 落盘永久死锁（被修 bug 复活）

**攻击路径**　`receipt_kernel.py::_supersede_lock`（:349-374）用 `os.O_CREAT|O_EXCL` 建 `.<canonical>.supersede.lock` 做跨进程并发闸，正常路径由 contextmanager 的 `finally` 删锁。但施工方注释已自陈"A crash can leave the lock behind; treating that as a hard failure is intentional"——一旦进程在**持锁期间**被 SIGKILL / OOM killer / 断电杀死（不可捕获，`finally` 不执行），锁文件永久遗留。此后任何对同一 canonical 的 `publish_supersede` 在 `os.open(...O_EXCL)` 撞 `FileExistsError`→`ReceiptKernelError("concurrent or interrupted supersede detected")`。五个真 FAIL 出口全部 `except Exception → print("receipt 写入失败: {exc}") → return 1`（如 `supply_truth_gate.py:553-555`），于是**旧 PASS 原地不动、真 FAIL 永远无法成为 canonical、重跑永远撞同一锁**——与修复前 `_reject_pass_downgrade` 死锁的终态字节级一致（旧 PASS 在场、exit 1、同一句"receipt 写入失败"前缀）。

这直接击穿 step1 报告①声明的不变量原文——"合法的真 FAIL（verdict=FAIL 且 exit_code=2）必须能成为 canonical 收据"。施工方七条反例矩阵覆盖了 stage/link/replace/回滚/命名碰撞/快速循环/target-schema 不同，**唯独没有"锁遗留后的恢复"这一条**（即计划让我找的"第八条"）。

**可复现命令与真实输出**（子进程在 `os.replace` 时 `os.kill(pid, SIGKILL)` 模拟崩溃，随后父进程连跑 3 次合法 supersede）：

```
PASS canonical established: PASS
阶段A 子进程 returncode=-9 (预期 -9=SIGKILL)
阶段A 崩溃后目录残留: ['.supply_truth.json.supersede.lock',
  '.supply_truth.json.tmp.20260814T115549.033537Z.6854',
  'supply_truth.json',
  'supply_truth.json.superseded-20260814T115549.033893Z.6854']
锁文件遗留: True
阶段B 第1次: ReceiptKernelError: concurrent or interrupted supersede detected: .../supply_truth.json
阶段B 第2次: ReceiptKernelError: concurrent or interrupted supersede detected: .../supply_truth.json
阶段B 第3次: ReceiptKernelError: concurrent or interrupted supersede detected: .../supply_truth.json
canonical 最终 verdict: PASS
错误消息是否含锁文件名 '.supersede.lock': False
```

崩溃残留三件套（`ls -la` 复核）：0 字节锁文件、孤儿 `.tmp` staged 件、以及一个**误导性的孤儿 `.superseded-<runid>` 归档**（旧 PASS 的 hard-link，在 replace 前就已建好；审计时会被误读成"发生过一次成功 supersede"，实则 canonical 仍是旧 PASS）。三者均无 GC。

**影响面**　五个真 FAIL 出口全部中招（supply_truth_gate / verify_recon / time_spotcheck×2 / window_fetch）。`window_fetch` 更重：若 SIGKILL 落在 `publish_supersede` 的 `replace` 之后、`os.fsync` 之前，canonical receipt 已翻 FAIL 但旧 data 尚未删除（window_fetch 还没走到删 data 那步），叠加锁遗留 → 留下"FAIL receipt + 旧正式 data 都在"的混合态且无法自愈。触发前提是进程被不可捕获信号终止——对一个动辄数小时、跑网络采集、易被 Ctrl-C 连击/Mac 睡眠/OOM 打断的工作流，这不是理论边角。错误消息（"concurrent or interrupted supersede detected: `<canonical路径>`"）**不含锁文件路径**（实测确认），本项目的非程序员用户几乎不可能自己定位到要删 `.supply_truth.json.supersede.lock`。

**为何判 P1 而非 P0**　需要"supersede 持锁期间被非可捕获信号杀死"的崩溃前置，不是攻击者常态可稳定触发的路径；且施工方 fail-closed 有合理安全动机（"不能盲猜被中断的发布是否已提交"）。但 fail-closed 到"永久死锁 + 不告诉用户删什么 + 与普通降级拒绝无法区分"是过度的——真 FAIL 落盘不变量在 crash 后被实测击穿且无自助恢复路径，属边界外真实风险需修。

**建议修法**（消化轮小修，不推翻 hard-link 设计）：①锁遗留错误消息如实指认锁文件**绝对路径**＋恢复指引，并与普通 `_reject_pass_downgrade` 用不同 exit code/前缀区分，让五出口能给用户不同话术；②supersede 的崩溃态本就可判定（设计保证 canonical 无缺失窗口）——检测到遗留锁时，比对当前 canonical verdict：已是目标 FAIL＝上次已提交，删锁续跑即可；仍是 PASS 且存在孤儿 `.superseded-<runid>`＝replace 未完成，可安全撤归档+删锁重来。至少提供一个经校验的恢复原语，而非让合法真 FAIL 无限撞锁。

---

### [P2] F-04：`--token-file` 值经 `_load_token → ap.error` 回显（计划方向⑤点名但未闭合）

**攻击路径**　SafeParser 抑制了 `from_block` 类型错误（`_safe_int` 报"须为整数（输入值已隐去）"）与 extras（"存在未识别参数（输入值已隐去）"）两条回显——位置明文 token 泄露已关死（实测下方绿例）。但 `_load_token`（`fetch_hypersync_v2.py:429-444`，v1 三支同构）在 token 文件缺失/为空时走 `ap.error(f"...token 文件缺失或为空：{path}...")`，`path=os.path.expanduser(token_file)` 原样进 stderr。若用户按已被删除的位置-token 老习惯误将 secret 塞给 `--token-file`（`--token-file <secret>`），该 secret 二次落进 stderr。计划"修复 5"改法 5 明确点名要查"argparse 的其他错误路径（如 `--token-file` 值本身）会不会回显敏感内容"——step6 只抑制了 from_block/extras，**这条被点名的路径未处理**。

**可复现命令与真实输出**（in-process 喂四支脚本 `parse_args`，捕获 stdout+stderr）：

```
===== F-04：--token-file 误传 secret 值的回显 =====
v2 --token-file <secret>：exit=2 sentinel_in_output=True
v2 位置 token：exit=2 sentinel_in_output=False        ← 位置 token 主目标：已关死
fetch_hypersync.py --token-file <secret>：exit=2 sentinel_in_output=True
fetch_hypersync_logs.py --token-file <secret>：exit=2 sentinel_in_output=True
fetch_pool_swaps.py --token-file <secret>：exit=2 sentinel_in_output=True
```

**影响面**　需用户误用（把 secret 当路径），且此时 secret 已在 argv/ps；回显是向 stderr 的边际二次暴露——但 CI/shell 常把 stderr 落盘成持久日志，比瞬时 ps 泄露面更广。不构成 FAIL 标准（非 P0/P1），列为深度建议。

**建议修法**　`ap.error` 对 token_file 路径脱敏（只显 basename 或 dirname＋长度提示），或在 help/文档明确 `--token-file` 只接受文件路径、绝不接受明文 token。

---

### [P3] F-04：枚举器 endpoint 证据与 `fetch_` 前缀 AND 绑定，非 fetch_ 命名的直连采集器漏出安全分母

**攻击路径**　`test_token_no_positional.py::enumerate_hypersync_entrypoints`（:22-38）三路并集里，第 2 路 `endpoint_collector = path.name.startswith("fetch_") and ("hypersync.xyz" in source or "hypersync" in path.stem.lower())`——**把"源码含 hypersync.xyz"与"文件名 fetch_ 前缀"用 AND 绑死**。一个新采集器若①不以 `fetch_` 命名（如 `collect_*`/`pull_*`/`<chain>_capture.py`）②用 requests/httpx 直连 `*.hypersync.xyz` 而不 `import hypersync` SDK ③未进 `formal_entrypoints`，则三路全不命中→漏出分母，其位置 token 回归不被自动覆盖。计划方向⑤正是要防"用 requests 直连 hypersync.xyz 但不 import SDK 的新采集器绕出分母"——现实现对**自然新增**（fetch_ 命名或 import SDK 或源码含 endpoint 字面量）是稳的，但对"非 fetch_ 命名 + 直连"这一组合 fail-open。

**影响面**　需刻意规避命名，非常态；但枚举器自陈用途就是"未来新入口默认进安全回归"，此缝让该承诺对一类命名失效。P3 观察。

**建议修法**　把 endpoint 证据从 fetch_ 前缀解耦——`"hypersync.xyz" in source` 单独成一路命中，不再 AND 文件名前缀。

---

### [P3] F-03：`replay_pass2` 纯信任 `replay_stats.json` 的 `gate_pass` 布尔，不独立重算 merged.csv（信任边界说明）

**攻击路径**　`replay_pass2.py:37-45` 读 `{data-dir}/replay_stats.json` 的 `gate_pass` 布尔分流（False→exit4、缺失/非布尔/损坏→exit2），**但不重新核算同目录 merged.csv 是否真的无负余额**。构造"负余额 merged.csv + 如实反映负余额的 balances_final + 手写 `gate_pass=true` 的 stats（模拟 stats 与序列数据不同源/被篡改）"喂 pass2：

```
攻击A pass2_rc=0
攻击A pass2 产出正式件=['camp_series.json', 'camp_series.provenance.json',
  'entity_series.json', 'entity_series.provenance.json']
攻击A 结论：pass2 纯信任 stats.gate_pass（不独立重算 merged 负余额）
```

**评估：这不是 F-03 声明不变量的洞，是其信任边界。** F-03 防的是"重放引擎自身算出 gate_pass=false 却 fail-open"，这条已关死（引擎必 exit 4/隔离诊断目录）。攻击 A 靠的是**手写 gate_pass=true 篡改产物**，超出 F-03 边界；且下游有兜底——`state_from_facts --series-source` 的 `registry_anchor_check` 要求 sidecar 绑定的 replay_stats sha256 命中 `supply_truth.json` 的 `inputs.replay_stats.sha256`，而 supply_truth 独立查链上 totalSupply 对账，不信任 gate_pass。链条要击穿需同时伪造 supply_truth。列 P3 是为**明确写下这个信任边界**：pass2 的 gate 是"消费 pass1 判定"而非"pass2 独立重算"，防篡改责任在下游 sidecar 哈希链——维护者应知边界所在，避免误以为 pass2 自证。

**建议**　文档标明该信任边界即可；如需加固，可让 pass2 复用 pass1 的负余额判据对 merged 做一次廉价二次核验（计划"不设放行参数"原则不冲突）。

---

### [P3] RV-17：`stake_decode.all_sigs` 的 cap 截断静默，超 cap 池仍可能打「[闭合]」

**攻击路径**　RV-17 把"签名页/交易解码/余额"三类**观测失败**关进 fail-closed（实测下方绿例）。但 `all_sigs`（:69-85）的 `cap`（默认 2500）触顶是**静默截断**：签名数 > cap 时 `while len(sigs) < cap` 到顶退出，只处理前若干页、**无任何 truncated 标记**。若漏拉的签名段恰为净零（存入后又取出），ledger 净额仍可能与 onchain 余额闭合 → 打正式「[闭合]」，与脚本自身"[不闭合：签名史没拉全]"的警示口径相悖。这不是"观测失败"（RPC 成功返回），故不在 RV-17 修复的三类之内。

**影响面**　需活跃池签名数 > 2500 且漏拉段净零；既有缺陷（cap 逻辑早于本批），本批 RV-17 范围未覆盖。P3 观察。

**建议修法**　`all_sigs` 触顶 cap 时返回 truncated 标志，`main` 据此把 `complete` 记 false / verdict 记 ERROR，不打正式「[闭合]」。

---

## 尝试-失败清单（证明覆盖面：五方向各≥1 真实攻击，均被挡）

| # | 方向 | 尝试的攻击 | 为什么失败（被挡） |
|---|---|---|---|
| 1 | RV-07 | 崩溃遗留锁后连跑 3 次合法 supersede | 锁 fail-closed 拒绝——但这恰是 P1（死锁复活），见上 |
| 2 | RV-07 | 旧件 target/schema 家族不同时被误归档 | `_validate_supersede_payload`＋归档前三键校验拒绝，canonical 字节不变（复核 step1 矩阵第 7 条属实） |
| 3 | RV-07 | 锁文件位置预置符号链接 | `O_EXCL|O_NOFOLLOW` 建锁，文件已存在即 FileExistsError fail-closed |
| 4 | RV-04 | `--proxy ''`/`none` 是否真压过已设的 CHIP_PROXY | `resolve_proxy(cli!=None)→_normalize("")→None`，显式直连优先序正确，压过 env 与探测 |
| 5 | RV-04 | CHIP_PROXY 设非法 scheme（ftp://、残缺 URL） | `_normalize` raise→调用点 `ap.error`（exit2），且 `redact_proxy` 脱敏 userinfo，不降级直连/探测 |
| 6 | RV-17 | RPC 全失败（mock rpc→None）跑 stake_decode | `rc=1 / verdict=ERROR / complete=false / 无「[闭合]」`——假闭合被关死（实测） |
| 7 | F-03 | duck 诊断件（无 sidecar）喂 `load_series_with_sidecar` | `SeriesProvenanceError: 序列缺 provenance sidecar`——诊断序列进不了正式消费（实测） |
| 8 | F-03 | data-dir 指向 gate-FAIL 目录能否让 pass2 天真产序列 | gate_pass=false→exit4；缺失/非布尔/损坏→exit2；仅"手写 stats=true 篡改"能过（P3 边界，非 F-03 洞） |
| 9 | F-01 | overlay 声明 camps 与实际画的 pct 不一致 | mode_fig1 的 pct＝从 names 按 state 求和、camps＝同一 names，CLI 层无法解耦；发布闸＋A5 双层从当前 state 经 `select_fig1_series` 重算 rendered、校验 overlay.camps⊆rendered |
| 10 | F-01 | select 在收据(mode)与 plot 两处调用间 series 被改 | 收据 rendered 用 plot 前的 `select(series_by_camp)`；plot 内 `select(series=+ts)`，ts∈allowed 且∉CAMP_ORDER→两次 rendered 恒等；收据在 plot 成功后写，rejected 会先 raise |
| 11 | F-01/A5 | 手工 v2 seal 冒充 v3 / 收据自证自洽 | validator 要求 schema/status/producer 三者均 v3；`fig1_legend_bundle` create＋validate 均从当前 state 重算，收据无法定义自己的 rendered/excluded 宇宙 |
| 12 | F-04 | 位置明文 token（老习惯 `<secret> <from_block>`） | `_safe_int` 隐去值＋SafeParser extras 隐去，sentinel 不进 stdout/stderr（实测绿例） |

---

## 裁决

| 项 | 裁决 | 依据 |
|---|---|---|
| **RV-07** publish_supersede | **FAIL** | P1：持锁崩溃后锁遗留→真 FAIL 落盘永久死锁，击穿"合法真 FAIL 必须能落盘"不变量；错误消息不指路、与普通降级拒绝无法区分。主体修复扎实，需消化轮补错误消息＋恢复路径 |
| **RV-04** proxy_config＋RV-17 | **PASS** | 10 点接线齐全、无裸端口残留、优先序/空串/非法 scheme 均 fail-closed；RV-17 断网假闭合实测关死。附 1 条 P3（cap 静默截断，既有缝本批未覆盖） |
| **F-03** replay gate | **PASS** | 三引擎 gate 语义统一 fail-closed、诊断序列被 sidecar 链拒之门外均实测属实。附 1 条 P3（pass2 信任边界说明，下游哈希链兜底） |
| **F-01** fig1 白名单＋A5 legend | **PASS** | overlay 同源、select 单源、发布闸＋A5 双层从 state 重算，多路攻击均失败 |
| **F-04** token 移除 | **PASS** | 位置明文 token 关死、四支同族等深、RV-17 邻域不混入。附 1 条 P2（--token-file 值回显，计划方向⑤点名未闭合）＋1 条 P3（枚举器 fetch_ 前缀 AND） |

**一句话**：批 1 五项主体质量高，唯 RV-07 存在一条 crash 边界的死锁回归（P1）需在消化轮闭合；其余四项通过，附 P2×1、P3×3 深度建议供裁量。
