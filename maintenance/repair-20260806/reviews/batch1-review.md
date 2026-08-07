# R8 批一「公共原语」独立复核报告

- 复核对象：`/Users/uravvv/Documents/5.6筹码分析/r8-closure-worktree`（分支 `fix/r8-closure-20260806`）
- HEAD 核验：`git rev-parse HEAD` = `e6577322b1deb0bd48e4ed1b7125b826ac4cff64`，以 `e657732` 开头 ✓
- 批一区间：`66d7ba7..e657732`（5 commit：8150385 / 5801350 / 38bc632 / 8e9de5c / e657732）
- 复核纪律：全程只读仓库；临时脚本/fixture 只在系统临时目录 `mktemp -d`；测试一律 `PYTHONDONTWRITEBYTECODE=1`；先独立冻结判断再读修复方材料做归因。
- 复核完成时仓库 `git status --short` 为空、无 `__pycache__`/`.pyc` 遗留（已自查）。

---

## 一、总裁决

**PASS** —— 批一三块加固（INV-05 receipt_kernel 路径身份、INV-07 唯一 chain-attested EVM RPC session、INV-15 唯一 risk_flags parser）代码正确性扎实：边界外一步 47/47 守住、0 真实失效；10 个正式 EVM RPC 业务调用点独立 rg 复列全部经 `attested_rpc_pool`、无第 11 个漏网；risk_flags 唯一 parser 五消费者复用、写出前 canonical 兜底全覆盖；diff→finding 映射每 hunk 有主、未映射 hunk 独立复算=0；全量 suite 70/70 PASS、invariant_scan 破坏性注入自测通过。**无新引入缺陷、无半修残留、无历史 P0/P1**。发现的 4 项均为 P3 加固完备性建议，不阻断合并。

---

## 二、finding 列表（均 P3，不阻断）

> 无 P0/P1/P2。以下四项是"纵深/完备性"建议，均不属批一承诺范围、且当前均无可达的正式利用路径。

### B1R-01（P3｜视角⑥闸可绕性｜归因：历史/批四范畴）
**裸 `RpcPool(expected_chain_id=None)` 可完全绕过 attestation，且无自动守卫。**
- 证据：`scripts/lib/net.py:202` `RpcPool.__init__` 直接暴露 `expected_chain_id=None` 默认值；`net.py:259` `if self.expected_chain_id is None: return None`（attest 跳过）、`net.py:309` `if self.expected_chain_id is not None and ...` 才 attest。attestation 必经性靠工厂 `attested_rpc_pool`（`net.py:359`）+ 调用纪律，而非类型/scanner 强制。`scripts/tests/invariant_scan.py` 只扫 transport 种类（`net.py:186` 认 `REGISTERED_TRANSPORT_BACKEND=="curl"`；`174-179` 认 requests/net import），**不区分裸 RpcPool 与 attested_rpc_pool**。
- 最小复现（临时目录 boundary_check.py 的 B16）：
  ```
  bare = net.RpcPool("http://bare")          # expected_chain_id 默认 None
  bare.call_many([("eth_call", [{}, "latest"])], progress=False)
  → [记录] B16 裸 RpcPool(expected=None) attest 次数=0
  ```
- 为什么不阻断：独立 rg 已确认全部 10 个正式 EVM 调用点均走 `attested_rpc_pool`（见 §五），无裸池混入正式路径；PLAN 批四才承诺"scanner 分母来自能力矩阵、新增未登记正式入口转红"。
- 建议：批四给 `invariant_scan` 增一条——扫到 `import net` 的生产文件里出现直接 `RpcPool(` 构造（非工厂内部）即告警，把 attestation 必经性从"调用纪律"升级为"自动守卫"。

### B1R-02（P3｜视角①字段来源 / ②失败分支｜归因：设计权衡）
**同进程内对同一 endpoint 跨 `call_many` 复用首次 attestation 结果，不重新验证。**
- 证据：`scripts/lib/net.py:309` `self._attested_endpoint != endpoint` 才 attest；`_attested_endpoint` 是实例变量，跨 `call_many` 保留。首次 attest 通过后（`net.py:292` `self._attested_endpoint = endpoint`），后续对同一 endpoint 的 call_many 直接进业务调用。
- 最小复现（boundary_check.py 的 B15，counting fake 注入 `net._request_json`）：
  ```
  第一次 call_many 后 eth_chainId 次数=1；第二次 call_many 后=1
  → [记录] 第二次未重新 attest
  ```
- 为什么不阻断：链 ID 在进程生命周期内不变，这是合理缓存；attestation 的威胁模型是"配错 endpoint/错链 RPC"（首次即拦），而非"同一 URL 同进程内后端热切链"（极罕见）。错链场景 `RpcChainMismatch`（`net.py:288-291`）仍在首次即硬失败。切换到新 endpoint 时会重新 attest（`net.py:309`，failover 分支 `316-319` 置 `_attested_endpoint=None`），我已验证该分支守住。
- 建议：如需极致严格，可为长驻进程加"attestation TTL 或每 N 次 call 重验"，但非本轮必要。

### B1R-03（P3｜视角②失败分支｜归因：历史漏检〔parse 宽进设计〕）
**`parse_risk_flags` 宽进对"零宽空格 / 非字符串"输入产生畸形单 flag。**
- 证据：`scripts/labels/risk_flags.py:10` `tuple(sorted({part.strip() for part in str(raw).split("|") if part.strip()}))`。`str.strip()` 不去零宽字符（`​`）；`str(raw)` 对 list/int/bool 会整体字符串化。
- 最小复现（boundary_check.py C5/C7）：
  ```
  parse('​|a') = ('a', '​')          # 零宽空格未 strip
  parse(['a','b'])  = ("['a', 'b']",)          # list 被 str() 当单 flag
  parse(0)=('0',)   parse(False)=('False',)
  ```
- 为什么不阻断："读取宽进"是 INV-15 明确设计（现役表零误伤），且解释统一由唯一 parser。全部 5 个消费者调用面传入的都是 CSV 字符串字段（已核 §五），不会传 list/int；零宽空格出现在 risk_flags 概率极低。canonical 幂等（C1）、二次拼接归一（C2）、unicode 常规空白 strip（C4：全角/nbsp/tab 均去）均守住。
- 建议：如加固可在写入侧（`canonical_risk_flags`）额外 `unicodedata` 归一或拒非 str 类型；非必需。

### B1R-04（P3｜视角②失败分支｜归因：历史漏检）
**`_producer_ref` 的 symlink 检查弱于 `_resolved_input` / `_secure_target`——只检最终组件，不逐级检中间目录。**
- 证据：`scripts/lib/receipt_kernel.py:81` `if ".." in path.parts or path.is_symlink()`（`path.is_symlink()` 仅测最终 path）；对比输入路径 `_resolved_input`（`43-69` 逐级 `lexical.is_symlink()`）与输出路径 `_secure_target`（`198-249` 逐级 `lstat`+dirfd+fstat）。
- 为什么不阻断：`producer_file` 来源是脚本自身路径（各 producer 传 `__file__`，如 `verify_recon.py:58` `build_envelope(SCHEMA, target, __file__, ...)`），是可信内部值而非外部输入；且随后 `resolve(strict=True)` + `relative_to(REPO)` 兜底会拒绝逃逸出仓库的结果。
- 建议：为对称起见，可让 `_producer_ref` 复用 `_resolved_input` 的逐级检查；纯健壮性、非安全缺口。

---

## 三、六视角覆盖表（对批一 diff 及其调用面）

| # | 视角 | 检查的文件 | 结论 |
|---|---|---|---|
| ① | 字段来源审计 | `net.py`（`_attest_endpoint` 258-293、`attested_rpc_pool` 359-373）、`chain_registry.py`（全）、`risk_flags.py`、`receipt_kernel.py`（`finalize_envelope` 135-154） | `expected_chain_id` 单源自 `chain_registry.evm_chain_id_for`（唯一 dict `CHAIN_REGISTRY`，含 record 字段完整性自校验 114-116、别名冲突检测 119-120）；endpoint 自报的 `eth_chainId` 只作 observed 值比对，绝不覆盖 expected（`net.py:288`）；risk_flags 唯一解释器 `parse_risk_flags`。**守住**（见 B1R-02 为设计权衡） |
| ② | 失败分支审计 | `net.py`（`_run` 301-337、`_attest_endpoint`）、`receipt_kernel.py`（`publish_txn` 345-418、`publish_restore_on_fail` 421-482）、`validate_labels.py` | 链身份校验失败/超时/异常/空/非hex/非对象/带error 全部 fail-closed（B1-B7/B8 实测）；回滚二次失败保留备份不销毁（`receipt_kernel.py:373-381`、`405-414`）；`publish_restore_on_fail` validate 非 `is True` 即判失败并回滚旧字节（A9/A9b 实测）。**守住** |
| ③ | 存量迁移 | `validate_labels.py:51-57`、`build_labels.py:566-577`、batch1-report §1/§2-C | 新 schema 旧数据处理明确：现役 labels 目录 `strict_canonical=False`（宽进告警、59 条历史非 canonical 零误伤），其他目录严出；写出侧 `build_labels` if/elif/else 全覆盖 canonical。R8-12 producer 迁移显式"留批三"，边界诚实。**守住** |
| ④ | 同族调用面 | 独立 rg：`RpcPool(` / `attested_rpc_pool` / `risk_flags` import / `publish_*` / `eth_call\|eth_getLogs\|...` / `json.dump\|write_text` | 10 个正式 EVM 调用点全走工厂、无第 11 漏网；risk_flags 五消费者全复用；receipt 直写点均属批三 producer 或历史/探针（已标记）。详见 §五。**守住** |
| ⑤ | 双向一致性 | `chain_registry.py`、各 `--chain` choices、`verify_recon.py:45`、`supply_truth_gate.py:107`、`identity_snapshot_receipt.py:174`、`handoff_manifest.py` | registry↔attestation 单源对得上；`identity_snapshot_receipt` 已从 `identity_chains()` 派生。CLI `--chain` choices 各文件硬编码仍漂移（范围外观察 OB-1），但 attestation 对无 chain_id 链 fail-closed 兜底。CLI choices 从矩阵派生属批二承诺。**守住（批一范围内）** |
| ⑥ | 闸可绕性 | `net.py`（工厂 vs 裸池）、`receipt_kernel.py`（`finalize_envelope` RESERVED_FIELDS 27-28/145-149）、`invariant_scan.py` | finalize kwargs 无法覆盖身份/verdict（A6 实测 + Python 位置参数层双重拦截）；PASS 降级保护、publish_exclusive 已存在即拒守住。裸 RpcPool 可绕 attestation（B1R-01，靠调用纪律+工厂，非自动守卫）。**基本守住，B1R-01 为完备性建议** |

**对修复新建代码本身过①②（方法论特别要求）**：receipt_kernel 的 `_secure_target`/`_assert_distinct`/回滚三态、net 的 `_attest_endpoint`、risk_flags 三函数均按新功能标准审过，未发现修复代码自身引入的洞（这正是历史上 5 个新引入洞的高发区，本批干净）。

---

## 四、边界外一步核验记录表（超出修复方反例；47 守住 / 0 真实失效 / 5 记录）

脚本：系统临时目录 `boundary_check.py`（realpath 工作目录规避 macOS `/var→/private/var` symlink；producer 用 REPO 内真实文件）。

### A. receipt_kernel（12 项全守住）
| 编号 | 构造 | 实际输出 | 判定 |
|---|---|---|---|
| A1 | broken symlink（指向不存在目标）作输出 | `output path contains symlink` | 守住 |
| A2 | 中间父目录是 symlink | `output parent contains symlink` | 守住 |
| A3 | 相对路径 vs 绝对路径指同一文件（publish_txn） | `publication paths must be lexically distinct` | 守住 |
| A4 | 大小写别名 `CASE.json`/`case.json` | `publication paths must be lexically distinct` | 守住 |
| A5 | 硬链接同 inode（不同词法名） | `publication paths alias the same physical file` | 守住 |
| A6 | finalize kwargs 覆盖 target/producer/inputs/schema/mode | `finalize fields conflict with reserved envelope keys` | 守住 |
| A6' | finalize kwargs 覆盖 verdict/exit_code | Python 位置参数层 `TypeError: got multiple values`（比 RESERVED 更早拦） | 守住（见下注） |
| A7 | ERROR 回执后 canonical 是否被降级 | canonical.verdict 仍 PASS，err_path=`canon.error.fixed1.json`（side path） | 守住 |
| A8 | 已存在 PASS → FAIL overwrite | `existing PASS artifact cannot be downgraded` | 守住 |
| A9 | publish_restore_on_fail validate 返回 `1`（非 True） | `post-publish validation failed` + 回滚后旧字节完整 | 守住 |
| A10 | publish_exclusive 已存在 | `exclusive receipt already exists` | 守住 |
| A11/A12 | 输入/输出路径 `..` 逃逸 | `input/output path ... rejected` | 守住 |

> 注：A6' 我最初把 TypeError 误标"守卫失效"，复核后确认——verdict/exit_code 是 `finalize_envelope` 的**位置参数**，用 `**{"verdict":...}` 注入在 Python 参数绑定层即 TypeError，根本到不了 RESERVED_FIELDS 检查。RESERVED_FIELDS 含 verdict/exit_code 是冗余但无害；对 schema/target/producer/mode/inputs（非显式参数）的拦截才是必需且已验证有效。**"finalize kwargs 覆盖身份绑定"这一历史先例被彻底堵死。**

### B. net RpcPool attestation（14 类守住 / B15·B16 记录）
| 编号 | 构造 | 实际输出 | 判定 |
|---|---|---|---|
| B1 | result 正确(0x38)但同时带 error 字段 | `eth_chainId RPC error`（error 优先） | 守住 |
| B2 | 返回 list（非 dict） | `returned non-object` | 守住 |
| B3 | result 是嵌套对象 | `returned invalid result` | 守住 |
| B4 | result `"0x"`（空） | `returned invalid result` | 守住 |
| B5 | result `"0X38"`（大写前缀） | `returned invalid result`（fail-closed 方向） | 守住 |
| B6 | result `"56"`（非 0x） | `returned invalid result` | 守住 |
| B7 | 0x38==56 正确 | 返回 56 | 守住 |
| B8 | 网络异常 | `eth_chainId failed`（RpcAttestationError） | 守住 |
| B9 | expected_chain_id = True/0/-5/"56"/56.0 | 全 `ValueError: must be positive integer or None` | 守住 |
| B10 | robinhood(chain_id=None)+formal | `no formal EVM chain identity for robinhood` | 守住 |
| B11 | arbitrum(42161)+formal | 建池，expected==42161 | 守住 |
| B12 | polygon+formal=False | 建池，expected==None（探索允许） | 守住 |
| B13 | polygon(chain_id=None)+formal | `no formal EVM chain identity for polygon` | 守住 |
| B14 | 别名 'ethereum'→eth | expected==1 | 守住 |
| B15 | 跨 call_many 同 endpoint | attest 次数 1→1（复用） | 记录（B1R-02） |
| B16 | 裸 RpcPool(expected=None) | attest 次数 0（不 attest） | 记录（B1R-01） |

### C. risk_flags（6 守住 / C5·C7 记录）
| 编号 | 构造 | 实际输出 | 判定 |
|---|---|---|---|
| C1 | parse(canonical(x))==parse(x) 幂等 | True（多样本） | 守住 |
| C2 | 二次拼接再归一 | `a|b|c` | 守住 |
| C3 | `a||b|`（多分隔符/空段） | `(a,b)` | 守住 |
| C4 | 全角/nbsp/tab 空白 | strip 为 `(a,b)` | 守住 |
| C5 | 零宽空格 `​` | 未 strip：`(a,'​')` | 记录（B1R-03） |
| C6 | merge()/merge(None,'')/merge 并集 | `''`/`''`/`a|b|c` | 守住 |
| C7 | parse(list/int/bool) | str 化当单 flag | 记录（B1R-03） |
| C8 | `tornado-user` 单 flag | 保持不拆 | 守住 |

---

## 五、④同族调用面独立重列（不采信修复方清单，自行 rg）

### 5.1 EVM RPC 正式业务调用点（INV-07）
独立 `grep -rn "attested_rpc_pool"` 得 10 个生产调用点，与修复方声称 100% 吻合、无第 11 个漏网：
- `scripts/lib/rpc_batch.py:67`、`scripts/lib/time_spotcheck.py:142`、`scripts/lib/supply_truth_gate.py:94`
- `scripts/evm/accounting_gate.py:98`（`Rpc` 适配器，`call` 105 转调 `self.pool`、`RpcAttestationError`→`RpcNetError` fail-closed）、`fetch_alchemy.py:45`、`lp_positions.py:98`、`verify_recon.py:93`（含 `pool.attest()` + `RpcChainMismatch`→`ReconFailure`，即"私有 attestation 删除合并"）、`scan_bloxroute_seg.py:36`、`pierce_stake.py:136`、`multicall_balances.py:106`
- 直接 `RpcPool(` 构造仅在 `net.py:373`（工厂内部）与测试文件。**无生产裸池。**

其余发 `eth_*` RPC 的点，逐一判非批一漏网：
- `scan_transfers.py`（curl 发 eth_getLogs/getBlockByNumber/blockNumber）：**批一未动此文件**；`scan_transfers.py:17` `FORMAL_CHANNEL_ELIGIBLE = False`（非批一 commit `a620fd9` 引入，`fetch_etherscan.py:15`/`fetch_bigquery.py:28` 同标记）。历史/诊断，preflight 拒。
- `labels/probe_codetype.py`（urllib eth_getCode）、`labels/fingerprint_check.py`（urllib eth_getCode，robinhood）：labels 库维护/探针工具，非单代币 formal 发布运行时。
- `robinhood/pull_transfers_rpc.py`、`pull_block_ts_anchors.py`：RH exploration（registry `evm_chain_id=None`，formal 工厂显式拒）。
- `supply_truth_gate.py:79` `requests.post`：仅 **Solana 分支**（getTokenSupply），EVM 分支走 attested（94-96）。**非 EVM 旁路。**
- `accounting_gate.py:155` `requests.post`、`fetch_hypersync*`、`fetch_etherscan`、`fetch_sqd_evm`：HyperSync/Sourcify/SQD/etherscan 非 JSON-RPC 协议，不套 eth_chainId attestation（各自协议守卫）。

### 5.2 risk_flags 消费面（INV-15）
五消费者全部 `from risk_flags import ...` 并复用：`add_labels.py:22`（105/153-154/176 canonical+merge）、`validate_labels.py:28`（92-98 读宽/写严守卫）、`roundtrip_check.py:20`（59 canonical）、`labels_resolver.py:37`（324 `risk_partition` 走 parse；`serial` 由 category 派生 214，非 risk_flags 子串）、`build_labels.py:22`（566-577 写出 canonical 全覆盖）。
- 疑似"第六消费者"逐一排除：`label_lookup.py:175/202` 仅原样透传/展示已归一表（`risk_partition` 走 resolver）；`accumulate_offenders.py:276` 写 canonical 单值 `'serial-offender'`，下游 `add_labels:105` 再归一；`build_labels.py:143-144` 本地拼接是中间累积、576-577 canonical 兜底（范围外观察 OB-2）。
- 独立复算 `split("|")` 于 `scripts/labels`：只命中 `risk_flags.py:10` 一处，与 report 3.3 一致。

### 5.3 receipt 发布原语面（INV-05）
生产用原语点：`solana/window_fetch.py`、`solana/anchor_sampler.py`、`lib/time_spotcheck.py`、`lib/supply_truth_gate.py`、`evm/verify_recon.py`。绕开原语直写 receipt 的点（`solana/replay_edges.py:171`、`evm/replay_duck.py:529`、`evm/replay_stream.py:136`、`evm/make_channel_receipt.py:112` 等）均属 producer 未迁移——批一 commit message 与 report §1 明确"producer 迁移留批三"，不在批一承诺内。`receipt_validate.py:4` 有意不 import receipt_kernel（发射/验证分离，防同 bug 双骗），设计正确。

---

## 六、diff→finding 映射复核结论

逐 commit `git show --stat` + 关键 hunk 核对 `diff-finding-map.md`：

| commit | 文件数 | owner | 复核结论 |
|---|---|---|---|
| 8150385 (B1-G1) | 3 | INV-05 / R8-04, R8-12(kernel-only) | receipt_kernel + 两测试，全属 INV-05。✓ |
| 5801350 (B1-G2) | 14 | INV-07 / R7-12, R8-07, R8-09 | net.py + 10 调用点 + test_batch1_rpc_attestation（全 G2）；test_r7_findings/test_sixlens_receipts 的 `Path(td).resolve()` 为 G1 临时根解析 hunk（文件级暂存并入，diff-map 已注记）、`requests.post`→`net._request_json`/`rpc_chain_id`→`attested_rpc_pool` 为 G2 适配。**无夹带。** |
| 38bc632 (B1-G3) | 7 | INV-15 / R7-14, R8-10 | risk_flags + 五消费者 + 测试，全属 INV-15。✓ |
| 8e9de5c (B1-G4) | 6 | 跨组维护件 | run_all.py 仅 +3 行（挂三新测试）；invariant_manifest.json 同步；transport-injections.json 10 条；三台账。**无夹带。** |
| e657732 | 1 | G4 台账维护 | 仅 diff-finding-map.md 回填分组→SHA 对照。 |

**未映射 hunk 独立复算 = 0**（覆盖全区间 `66d7ba7..e657732`）。修复方声称"批一(66d7ba7..8e9de5c)=0"；e657732 自身回填 owner 明确（台账 SHA 维护），补齐后全区间仍为 0，与修复方一致。跨组混入已如实注记且实 diff 印证，无"顺手整理"。

**守卫佐证**：`invariant_scan.py` 正常运行 `PASS invariant manifest: receipt_producers=44, receipt_consumers=51, transport_calls=39, atomic_writes=37, formal_entrypoints=54, exceptions=0`（manifest 与代码完全一致）；`--self-test` 破坏性注入：删点→RED、加不存在点→RED（守卫真能拦）。

---

## 七、归因小结（视角 D）

批一未发现"新引入"缺陷、"半修残留"或"历史 P0/P1"。四项 finding 归因：
- B1R-01 历史/批四范畴（attestation 自动守卫属批四承诺，批一只承诺 10 点全迁——已达成）
- B1R-02 设计权衡（进程内链 ID 缓存，非错链绕过）
- B1R-03 历史漏检（parse 宽进设计的边角，调用面已核安全）
- B1R-04 历史漏检（producer 为可信 __file__，有 relative_to 兜底）

修复方 batch1-report §5 归因预判（R8-04 新引入、R8-12 半修残留仅 kernel、R7-12/R7-14 新引入+后续同族半修链、R8-07/R8-10 半修残留、R8-09 历史漏检）与其边界声明诚实一致；§4 主动披露的三项自审遗漏（同族补迁 5 点+Alchemy 专有 RPC、os.replace 移出私有 helper 让 scanner 可定位、C 拆宽进/严出）均与我独立观察吻合，无夸大。

---

## 八、范围外观察（不计入批一 finding）

- **OB-1（批二）**：各命令 `--chain` choices 硬编码漂移——`verify_recon.py:45`=`["eth","bsc","base","arbitrum"]`、`supply_truth_gate.py:107`/`accounting_gate.py:380`=`sorted(DEFAULT_RPC)`（含 polygon/solana）、`time_spotcheck.py:74`=`["eth","bsc","base","arbitrum"]`、`fingerprint_check.py:73`=`list(RPC)`。CLI choices 从 registry/矩阵派生是 PLAN 批二承诺；attestation 已对无 chain_id 链 fail-closed 兜底，危害受限。
- **OB-2（代码整洁）**：`build_labels.py:143-144` 用字符串 `+ '|' +` 拼接 risk_flags（未用 `merge_risk_flags`），为中间累积、576-577 canonical 兜底覆盖全部行、功能正确；可改用 merge 更一致。
- **OB-3（健壮性）**：`validate_labels.py:53-57` `strict_canonical` 默认按 `os.path.dirname(path) != active` 路径字符串比较决定松紧；符号链接/异写法指向 active 目录理论上可致 strict 误判。labels 为本地可信资产、非安全边界。
- **未独立验证的数字**：report 称现役 470879 行 / 59 条历史非 canonical——机制正确（strict 按目录分流），但具体行数我未逐表跑 validate 复核，仅记录。

---

## 九、执行的命令清单（关键）

```text
# 核验与建立标准
git -C <worktree> rev-parse HEAD / --abbrev-ref HEAD
git log --oneline 66d7ba7..e657732
git diff --stat 66d7ba7..e657732
读 references/maintenance-review-repair.md、PLAN(4).md

# 独立调用面 rg（不采信修复方清单）
grep -rn "RpcPool(|attested_rpc_pool|from net import" scripts --include=*.py
grep -rn "risk_flags|parse_risk_flags|canonical_risk_flags|merge_risk_flags" scripts --include=*.py
grep -rn 'split("|")' scripts --include=*.py
grep -rn "publish_exclusive|publish_overwrite|publish_txn|publish_restore_on_fail|publish_error_receipt" scripts
grep -rn "eth_call|eth_getLogs|eth_getCode|eth_getBalance|eth_blockNumber|eth_chainId|..." scripts
grep -rn "FORMAL_CHANNEL_ELIGIBLE" scripts
git log -1 -S "FORMAL_CHANNEL_ELIGIBLE" -- scripts/evm/scan_transfers.py

# 读码（核心加固 + 调用面 + 单源）
receipt_kernel.py / net.py / risk_flags.py / chain_registry.py（全）
supply_truth_gate.py / scan_transfers.py / accounting_gate.py / verify_recon.py
build_labels.py / label_lookup.py / accumulate_offenders.py / labels_resolver.py / validate_labels.py
invariant_scan.py / invariant_manifest.json

# 基线与边界外一步（PYTHONDONTWRITEBYTECODE=1；临时目录 mktemp -d）
python3 scripts/tests/test_batch1_{receipt_paths,risk_flags,rpc_attestation}.py   # 全 PASS
python3 <tmp>/boundary_check.py                                                    # 47 守住 / 0 真失效
python3 scripts/tests/invariant_scan.py            # PASS（producers=44...exceptions=0）
python3 scripts/tests/invariant_scan.py --self-test # 删/加点均 RED
python3 scripts/tests/run_all.py                    # 70/70 PASS, exit=0

# diff→finding 映射复核
git show --stat / git show <commit> -- <file>（8150385/5801350/38bc632/8e9de5c/e657732）
rg -l 'json\.dump|write_text|rename|os\.replace' scripts --type py  # 154=103+51 复算吻合

# 收尾自查
git status --short（空）；find scripts -name __pycache__ -o -name *.pyc（空）
```

---
*复核者：独立质量复核子代理｜完成日期 2026-08-07｜仓库零写入已自查*
