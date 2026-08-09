# R9 批三施工记录：正式纵切片重建

## G0 现场冻结与约束

- 施工位置：`/Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree`
- 分支：`fix/r9-closure-20260807`
- 冻结 tip：`57714197b3488cd9a12cd7a6e46a9d9642bbc86d`
- 开工时 `git status --short`：无输出（干净）。
- 边界：不做 git 写操作；不改 `VERSION`；不出网；端到端仅可替换 transport。
- 口径：Solana 观测 slot 是唯一真值；`--as-of-slot/--as-of-block` 只是可选兼容断言；`--min-context-slot` 只是 RPC 下限。
- 本工单与 skill 同步脚本冲突：同步会改分支/工作树，故以用户指定 worktree tip 为唯一基线，未执行同步。

## B3-G1：Solana observation bundle

### 红线证据

- 命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch3_solana_observation.py`
- 未修输出摘要：10 个新契约全部红，根因为生产库 `solana_observation` 不存在；错 genesis、单调双模式、声明 slot 断言、前后 mint 变化、完整模式分页中断、writable mutation、supply slot 过早、三方不闭合、loaded-address writable 解析、确定性哈希均无生产实现。
- R9-01 旧病实测：对未修 `accounting_gate_sol.main()` 注入 `getAccountInfo result.context.slot=999`，CLI 仍传 `--as-of-slot 77`；输出 `OLD_R9_01_RC 0 / RECEIPT_AS_OF 77 / RPC_CONTEXT 999`，即旧实现把声明写成了观测并 PASS。
- 追加时序反例：fake 故意返回 `jsonParsed slot < raw pre slot`，旧 observation 接受；修后拒绝，并把 GPA `minContextSlot` 推进到 parsed slot，固定 `raw pre <= parsed pre <= GPA snapshot <= raw post`。

## B3-G2：三消费者与原子发布

### 红线证据

- 动态 runner 反例先落：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch3_dynamic_runner.py` 在旧 runner 上红，原因是 `target.as_of_block=None` 被静态 schema 直接拒绝，无法先执行 supply producer 再采纳真实 GPA slot。
- txn 尾巴反例先落：在 `test_batch3_solana_producers.py` 注入提交后内容自检，旧 anchor/window 路径红于“联合提交后仍执行独立自检”，证明会出现已经发布又独立 raise 的半发布窗口。
- R9-01 进程反例由 G1 复用：旧 accounting 把 CLI 77 直接写 receipt，RPC 999 未参与冻结；新 scan 的两次运行则先成功观测 103，再用 `--as-of-slot 77` 失败，旧 bundle/snapshot 均转 `.stale.*`，当前正式位为空并产生 `bundle.error.*.json`；该 ERROR receipt 的 target 也是观测值 103，不再回写声明 77。

### 绿线证据

- `python3 scripts/tests/test_r9_batch3_dynamic_runner.py` → `PASS R9 B3-G2: Solana runner adopts observed supply snapshot slot`。
- `python3 scripts/tests/test_batch3_solana_producers.py` → `PASS B3-G2: Solana slot/envelope/txn/timestamp producer guards`。
- `scan_token_accounts.py` 现在是唯一正式 bundle producer，顶层 `as_of_slot/as_of_block/observed_context_slot` 与 target 均绑定 GPA 观测值；`accounting_gate_sol.py` 与 Solana `supply_truth_gate.py` 均独立校验 `solana-observation-bundle/v1`、producer/file hash/target，并绑定同一 bundle。两 consumer 的声明错位 ERROR 也保留 observed=103；formal accounting 未给 bundle 即拒，exploration 产物带 `execution_mode=exploration`。
- anchor/window 均删去提交后独立哈希自检与手工撤回分支，`publish_txn(data, receipt)` 是最后可失败的正式发布动作。

## B3-G3：EVM 三链纵切片

### 红线证据

- 批二基线的 `VERTICAL_SLICE_EVIDENCE_TARGETS` 为空，四链均只缺第④项而 not-ready；新增 target 前的 capability 回归按缺项红。
- `test_r9_batch2_executable_capabilities.py` 的破坏性回归逐链删除 target；任一 eth/bsc/base target 缺失，或其测试从 `run_all.SUITE` 摘除，对应链立即掉出 formal-ready。
- `test_time_spotcheck.py` 保留并通过三类 consumer 阻断反例：plan 缺/错 `final_block`、探测点越界、plan receipt 替换/哈希漂移；plan 始终现场由 `anchor_plan.py` 生成，不手写。

### 绿线证据

- target 已注册：`r9-eth/bsc/base-mainnet-vertical-slice` 分别指向 `test_batch3_evm_vertical_slice.py` 三个真实函数，测试文件挂入 SUITE。
- 只读 capability 命令输出：`formal_ready_chains()` → `{'eth', 'bsc', 'base', 'sol'}`；`test_r9_batch2_executable_capabilities.py` → `PASS R9 B3-G3/G4: six probes ready; deleting one slice drops its chain`。
- `test_time_spotcheck.py` → `time_spotcheck 契约测试全部通过（20 项）`。
- 当前沙箱的真实三链 loopback 编排尚未绿：`test_batch3_evm_vertical_slice.py` 在第一个 `ThreadingHTTPServer.bind(('127.0.0.1',0))` 即 `PermissionError: [Errno 1] Operation not permitted`，未进入 chain-id 或任何业务断言。未用 skip 或声明 PASS 掩盖。

## B3-G4：Solana 纵切片与 transport fake

### 红线证据

- G1/G4 新反例在生产库不存在时一次性 10 红；覆盖错 genesis、CLI 声明错位、mint 前后变化、完整分页中断、双模式 writable、supply slot 过早、三方不闭合、loaded address 可写判定、确定性哈希与两种活动模式。
- SQD 消费前只有 adapter、无生产 callsite；错 dataset/mint/range 不能阻断 `fetch_sqd_transfers_v2.py` 实际路径。
- 活动预算追加反例：pressure fake 令旧循环先发到第 251 次以上 RPC 才降级，`test_activity_rpc_budget_switches_before_call_251` 真实红；修后于预算边界切轻量。

### 绿线证据

- `test_r9_batch3_solana_observation.py` → `PASS R9 B3-G1/G4: Solana observation protocol and negative variants`；九条点名负例均 fail-closed，轻量模式 `sample_size<=50`，完整预算不越 250 RPC。
- fake 提供真实单调 context slot、`getGenesisHash`、raw/jsonParsed mint、GPA withContext/minContextSlot、两种活动、`getTokenSupply` 与 SQD payload；生产逻辑不替换，唯一 RPC 注入边界仍是 `request_json`，登记于 `transport-injections.json`。
- `fetch_sqd_transfers_v2.py` 现以 attested state session 校验 `solana-mainnet + mint + [from_slot,to_slot]`，并把 dataset scope 写入 meta；测试已穿过实际 collector main/run，证明错 dataset、空/缓存错 mint、反向 slot 在 SQD stream 前拒绝。
- Solana target 已注册到 `test_batch3_solana_vertical_slice.py:test_r9_solana_pythia_mainnet_vertical_slice` 并挂 SUITE。
- 当前沙箱真实 Solana process E2E 仍被首个 loopback `socket.bind` 的 `EPERM` 阻断，未进入 producer/runner/READY/release；不计为绿。

## B3-G5：G3-0 双载体预演壳

### 红线证据

- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch3_preflight.py` 在两个壳不存在时红，无法证明预演复用了生产 observation/activity 代码。

### 绿线证据

- 同命令现输出 `PASS R9 B3-G5: both preflight shells execute production observation code`。
- 两壳从任意 cwd 可独立 `--help`；根路径以脚本的 `parents[3]` 定位仓库，不依赖测试注入。
- `g3_0a_usdc_activity.py` 只运行 finalized tip + 512-slot activity 测量，明确禁止 GPA/holder closure，失败为 non-blocking；`g3_0b_pythia_gpa.py` 直接调用生产 `observe_snapshot`，逐 endpoint 记录 genesis、三方闭合及成本。

## B3-G6：PYTHIA mainnet smoke 入口

### 裁判执行手册（本沙箱禁止执行）

先准备独立重放产物；禁止把 bundle 里的链上 supply 抄成 replay stats，否则 supply truth 是自证循环：

```bash
cd /Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree
export REPO="$PWD"
export CASE_DIR="/absolute/path/to/fresh-pythia-smoke-case"
export REPLAY_STATS="/absolute/path/to/independent/replay_stats.json"
mkdir -p "$CASE_DIR"
cd "$CASE_DIR"
export RPC_ENDPOINT="https://mainnet.helius-rpc.com/?api-key=$(tr -d '\r\n' < ~/.config/helius/api-key)"

PYTHONDONTWRITEBYTECODE=1 python3 "$REPO/scripts/solana/scan_token_accounts.py" \
  CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump \
  --program spl --rpc "$RPC_ENDPOINT" --min-context-slot 0 --timeout 300 \
  --out supply_snapshot.json --bundle solana_observation_bundle.json \
  --work-dir data
PYTHONDONTWRITEBYTECODE=1 python3 "$REPO/scripts/lib/receipt_validate.py" \
  solana_observation_bundle.json
export OBS_SLOT="$(python3 -c 'import json; print(json.load(open("solana_observation_bundle.json"))["snapshot"]["slot"])')"

PYTHONDONTWRITEBYTECODE=1 python3 "$REPO/scripts/solana/accounting_gate_sol.py" \
  --mint CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump \
  --bundle solana_observation_bundle.json --as-of-slot "$OBS_SLOT" \
  --out accounting_mode.json
PYTHONDONTWRITEBYTECODE=1 python3 "$REPO/scripts/lib/supply_truth_gate.py" \
  --chain solana --mint CreiuhfwdWCN5mJbMJtA9bBpYQrQF2tCBuZwSPWfpump \
  --observation-bundle solana_observation_bundle.json \
  --as-of-block "$OBS_SLOT" --replay-stats "$REPLAY_STATS" \
  --out supply_truth.json
```

判定标准：expected/observed genesis 均为 mainnet 常量；`pre_slot<=snapshot_slot<=post_slot` 且窗口不超过 512；前后 raw hash 相等；supply slot 不早于 snapshot；GPA/mint raw/getTokenSupply 三数相等；activity 无 writable hit，轻量模式不得声称完整证明；bundle、accounting、supply truth 三者 target slot 均等于 `OBS_SLOT`，两个 consumer 的 bundle SHA 相同，三个回执均 PASS/0。

公共节点若所在网络必须代理，只给本次裁判 shell 设置 `HTTPS_PROXY`/`ALL_PROXY`；不要改仓库配置。Helius key 从现有 `~/.config/helius/api-key` 读取，禁止把 key 写入命令日志、报告或台账。

### G3-0 双载体命令

```bash
cd /Users/uravvv/Documents/5.6筹码分析/r9-closure-worktree
PREFLIGHT=maintenance/repair-20260806/g3_preflight
RPC_ENDPOINT="https://mainnet.helius-rpc.com/?api-key=$(tr -d '\r\n' < ~/.config/helius/api-key)"
RPC_ENDPOINT_2="https://api.mainnet-beta.solana.com"
PYTHONDONTWRITEBYTECODE=1 python3 "$PREFLIGHT/g3_0a_usdc_activity.py" \
  --endpoint "$RPC_ENDPOINT" --endpoint "$RPC_ENDPOINT_2"
PYTHONDONTWRITEBYTECODE=1 python3 "$PREFLIGHT/g3_0b_pythia_gpa.py" \
  --endpoint "$RPC_ENDPOINT" --endpoint "$RPC_ENDPOINT_2"
```

裁判待登记：`g3_0a_usdc_activity.json` 状态/哈希/时间；`g3_0b_pythia_gpa.json` 状态/哈希/时间；mainnet bundle/snapshot/accounting/supply-truth 四件哈希与运行时间。G3-0a 任一失败不阻断；G3-0b 至少一个 endpoint PASS，且 G6 smoke 全部判定满足才可收口。

## B3-G7：台账与全量门禁

### 绿线与阻断证据

- `python3 -m json.tool maintenance/repair-20260806/transport-injections.json` → `TRANSPORT_JSON_OK`。
- `wc -c SKILL.md` → `7737 SKILL.md`，未改 `VERSION`，仍小于 8192B。
- `docs_lint.py --all` → `PASS: 58 个文档`。
- `invariant_scan.py` → `PASS invariant manifest: receipt_producers=51, receipt_consumers=55, transport_calls=60, atomic_writes=38, formal_entrypoints=58, exceptions=0`。
- 全量命令：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py`。
- 全量结果：87 项中 85 PASS；仅 `test_batch3_solana_vertical_slice.py` 与 `test_batch3_evm_vertical_slice.py` 失败，二者同为 fixture 启动时 `socket.bind(127.0.0.1)` 被沙箱以 `EPERM` 拒绝；其余所有业务/契约/文档/manifest 测试全绿。
- 已额外验证本沙箱 IPv4、IPv6、Unix-domain 三种本地监听全部同样 `PermissionError: [Errno 1] Operation not permitted`，故无法在当前权限内取得真实 process loopback 绿证据。
- 未映射 hunk：`0` 候选；B3-G1～G7 owner 已登记，SHA 按工单留空待 Fable 回填。

### 汇总

- 代码实现与离线 request_json 单元/负例均完成；mainnet 项从未在本沙箱出网。
- 不满足完成信号：全量 suite 非全绿，EVM/Solana 正式 process 纵切片未在可 bind 环境执行，G3-0/mainnet smoke 亦待裁判真实运行。
- 最终结果：`B3F_BLOCKED: sandbox denies all local socket bind; rerun the two loopback vertical slices and full suite in the judge environment, then execute G3-0 and PYTHIA mainnet smoke`。
- 两轮盲审与 Fable 结论：待裁判回填。

## 批内修复循环 1（B3FIX-01 / B3FIX-02）

止损计数：这是批三第 `1` 个批内修复循环；两项均按“修复中新引入”登记，源头为批一 R9-05 的 `solana_attested_session.py`，由裁判 mainnet 首跑发现。B3FIX-01=P2，B3FIX-02=P1。本文及测试只使用字面假密钥 `SECRET`，从未复写裁判真实 key。

### 现象、根因与修法

- B3FIX-01：macOS python.org Python 的系统 CA 不完整，attestation 第一跳即 `CERTIFICATE_VERIFY_FAILED`。根因是 `_urllib_json` 裸用默认 `urlopen` context；另查出 G3-0 成本 transport 复制了一份裸 urllib，绕过生产修复。现由 session 在 import 时构造一次 `_SSL_CONTEXT`：可导入 certifi 时使用 `certifi.where()`，不可导入或 cafile 不可用时回退 `ssl.create_default_context()`；`_urllib_json` 每次复用该 context。G3-0 成本壳改调生产 `_urllib_json`，不再另造 TLS 路径，urllib 默认 proxy 行为不变。
- B3FIX-02：session 六处异常把完整 endpoint 拼进字符串，上层预演报告、scan stderr/ERROR receipt 会原样持久化。新增 `endpoint_identity.py`，唯一 `public_endpoint()` 口径为去 userinfo/query/fragment 的 `scheme://netloc/path`，异常中的 endpoint/query key/value 再经 `redact_endpoint_text()` 清理；Solana session、observation fingerprint、accounting exploration、anchor 行身份统一复用。全库同族扫描还发现 EVM attested pool 异常与 anchor resume 行会暴露完整 URL，已同口径收口；window_fetch 未把 endpoint 写入 receipt/日志，supply/accounting 正式 Solana 路径仅消费 bundle public origin。
- 污染处置：`maintenance/repair-20260806/g3_preflight/g3_0a_usdc_activity.json` 已直接删除且未留副本；裁判修复后重跑再生成。

### 红线证据

1. CA 与四型异常（未修 session）：

   `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_solana_attested_session.py`

   - CA 反例红于 `AttributeError: module 'solana_attested_session' has no attribute 'ssl'`，证明旧实现没有可选择/复用的 SSL context。
   - 带 `?api-key=SECRET#private` 的 fake transport 红于异常链仍含完整 endpoint；覆盖 transport failed、RPC error、attestation mismatch、all endpoints exhausted 四型。

2. G3-0 生产 transport 旁路（修 session 后、修壳前）：

   `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch3_preflight.py`

   红于 `g3_0a_usdc_activity has no attribute '_urllib_json'`，证明真实壳仍未接生产 CA transport；修法不是只补 session 单测。

3. anchor 持久化同族（修 session 后、修 anchor 前）：

   `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sixlens_receipts.py`

   红于产出行的 `endpoint` 仍等于带 query/fragment 的 CLI 原值，public-origin 断言失败。

### 绿线证据（受影响项）

- `test_r9_solana_attested_session.py` → `PASS R9 SolanaAttestedSession: 8/8`；certifi 有/无两分支与单 context 复用均有断言，四型异常整条 cause/context 链均不含 `api-key`、`SECRET`、fragment。
- `test_batch1_rpc_attestation.py` → PASS；EVM 同族 endpoint query 异常亦不泄漏。
- `test_r9_batch3_solana_observation.py` → PASS；新增 scan stderr + ERROR receipt 持久化负例。
- `test_r9_batch3_preflight.py` → PASS；两个报告的 ERROR JSON 不含 query/key，真实成本 transport 明确调用生产 `_urllib_json`。
- `test_sixlens_receipts.py` → PASS；anchor 输出身份仅存 public origin，resume 比较同口径。
- 污染文件存在性：`test ! -e maintenance/repair-20260806/g3_preflight/g3_0a_usdc_activity.json` → `polluted_report=absent`。

### 裁判重跑提示

G3-0A 报告已删除；沿上文 G3-0 命令重跑即可。验收时除原活动/成本判据外，先对新 JSON 做 key 泄漏检查：报告可含 `endpoint.public_origin` 与不可逆 SHA256，但任一 error/字符串不得含 endpoint query、fragment、query key 或真实 key 值。B3FIX-01 的裁判实证是至少一个 HTTPS endpoint 完成 `getGenesisHash` attestation；若所有端点仍失败，报告必须只展示 public origin。

### 循环 1 最终门禁

- 五个受影响文件串行重跑：`test_r9_solana_attested_session.py`、`test_batch1_rpc_attestation.py`、`test_r9_batch3_solana_observation.py`、`test_r9_batch3_preflight.py`、`test_sixlens_receipts.py` → 全部 rc=0。
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/docs_lint.py --all` → `PASS: 58 个文档`。
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/invariant_scan.py` → `PASS invariant manifest: receipt_producers=51, receipt_consumers=55, transport_calls=60, atomic_writes=38, formal_entrypoints=58, exceptions=0`。
- `python3 -m json.tool maintenance/repair-20260806/transport-injections.json` → `TRANSPORT_JSON_OK`；`wc -c SKILL.md` → `7737 SKILL.md`；`VERSION` 未改。
- 全量 `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` → 87 项中 85 PASS；仍且仅有 `test_batch3_solana_vertical_slice.py`、`test_batch3_evm_vertical_slice.py` 两项在首个 `ThreadingHTTPServer.bind(('127.0.0.1',0))` 处 `PermissionError: [Errno 1] Operation not permitted`。这与循环前相同，未进入业务断言；按工单如实登记为沙箱 EPERM，不算本循环回归失败，也不伪记 loopback 绿。
- 循环结论：B3FIX-01/02 代码、离线反例、污染清理与台账闭合；真实 HTTPS CA 与新报告需裁判复跑。批三总任务仍保留既有环境验真待登记位，本批内修复循环输出 `B3F2_COMPLETE`。

## 批内修复循环 2（opus 15 finding）

止损计数：这是批三第 `2` 个批内修复循环。审查报告 `reviews/r9-batch3-review.md` 的 B3R9-01～15 全部按 CONFIRMED 施工；严格限于点名项及其同族等深面，不扩做批四通用守卫。基线 `b4e9595`，分支 `fix/r9-closure-20260807`；本循环禁 git 写、禁改 VERSION、零出网。

### B3F3-G1：B3R9-01 endpoint path 密钥脱敏

- 不变量：任何 endpoint 的 userinfo、query、fragment 或凭据型 path 段都不得进入异常、stderr、receipt、报告或身份行；脱敏不得腐蚀普通诊断正文。
- 同族：`endpoint_identity.py` 是 `net.py`、`solana_attested_session.py`、`solana_observation.endpoint_fingerprint`、accounting result、anchor 行身份和 G3 两壳的共享口径；生产 sink 均复用它。
- 红：`test_r9_solana_attested_session.py` 新增 Alchemy `/v2/FAKEKEY123`、Infura `/v3/FAKEKEY123`、无 scheme `rpc.example.com/v2/FAKEKEY123` 与 query-key 正文负例。未修输出 path key 原文，首个 public-origin 断言红；`test_batch1_rpc_attestation.py` 的 EVM path key 异常也红于 `FAKEKEY123` 仍在异常串。
- 绿：`public_endpoint()` 对 v1/v2/v3/key/token/api-key 后继段、UUID、长 hex、长 base58/base64 风格 token 段替换为 `[redacted]`，保留 host 与结构前缀；`redact_endpoint_text()` 不再全局替换 query key 普通词，只清理完整 query/fragment、query value 与凭据 path 段。`test_r9_solana_attested_session.py` → `PASS ... 10/10`；`test_batch1_rpc_attestation.py` → PASS，输出中的 Alchemy endpoint 为 `/v2/[redacted]`。
- 同族扫描增补：EVM accounting receipt 的 Infura `/v3/FAKEKEY123`、Solana decode output/cache receipt 与 SQD cache meta 仍曾持久化完整 URL。三条正式反例在未修 callsite 分别红于 receipt/meta 含假 key（SQD 红于缺少安全 identity 构造点）；现统一只落 `public_origin` 与完整 URL 的不可逆 SHA256，既不泄密又保留跨端点身份判别。既有 SQD v3 raw-endpoint meta 经精确 digest/原值匹配后原子清洗，不要求重采；新增原子点首次令 invariant scan 红于 manifest 缺登记，补入 manifest 后收口。`test_review_solana_integrity.py`、`test_review_resume_integrity.py`、`test_r9_batch3_solana_observation.py` 纳入回归。

### B3F3-G2：B3R9-02/09/13 producer-validator 机器等价与观测时序

- 不变量：scan 写入正式 bundle/snapshot 前，内存中的最终 bundle 对象必须通过消费者使用的同一个 `validate_observation_bundle()`；RPC 返回 slot 还必须满足调用时下达的本地下限/单调关系。`bundle_path` 字节比对仅因原子写尚未发生而留给下游，所有对象级约束完全同源。
- 红：正式测试一次呈现 6 红：GPA=101<jsonParsed=102 被 producer 接受；CLI `min_context_slot=1000000` 而 pre=5 被接受；supply 首次落后直接硬错未重试；中途降级写出 lightweight `sample_size=55`；GPA 早退仍 rc=0 发布正式位；scan 模块不存在可注入的 `validate_observation_bundle` 自校验点。
- 绿：complete→lightweight 时同步把 `successful` 与报告 `checked` 截到 `LIGHT_SAMPLE_LIMIT`；GPA 复核改为 `snapshot_slot>=parsed_slot`；第一 raw pre 复核 `pre_slot>=min_context_slot`；`getTokenSupply` 官方不支持 `minContextSlot`，保留 commitment-only 调用并把 supply slot 落后归为 `RetryableObservationError`。scan 在 `publish_txn` 前调用共享 validator；注入 validator 失败时 rc!=0、正式 bundle/snapshot 均不存在、只产 ERROR receipt。
- 证据：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch3_solana_observation.py` → PASS；lag fake 第 1 轮 supply 早退、第 2 轮成功且 `attempt==2`；downgrade 最终样本≤50；GPA<parsed 与自校验注入均 fail-closed。

### B3F3-G3：B3R9-03 发布层六断言负例

- 新增并挂 SUITE：`test_r9_batch3_release_guards.py`。fixture 只替换 Solana transport，实际运行 scan→accounting→supply_truth 三个生产者；测试再逐项篡改产物并直接进入 `shared_release_receipt` 对应发布分支。
- 六负例：① exploration accounting；② accounting 缺 bundle ref；③ accounting observed slot≠snapshot slot；④ supply_truth 缺 bundle input；⑤ supply_truth observed slot≠bundle supply slot；⑥ reconciliation supply bundle genesis 非 mainnet。每条均断言发布层的精确拒绝原因。
- 红（临时源副本，不改仓库）：D1 删除 exploration 块、D2 删除 accounting binding+slot 块、D3 删除 supply_truth binding+slot 块、D4 删除 supply bundle validator；四个 mutant 运行正式测试分别 `rc=1/1/1/1`，证明六负例确实到达并依赖目标分支。
- 绿：未变异生产文件运行 `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_r9_batch3_release_guards.py` → `PASS R9 B3F3-G3: Solana release negatives 6/6`。

### B3F3-G4：B3R9-04/05/06 测试守卫判别力

- B3R9-04 红：`test_r9_batch2_executable_capabilities.py` 新增 AST 守卫后，旧 observation 文件因定义与注册 target 同名的 `test_r9_solana_pythia_mainnet_vertical_slice` 立即红。绿：影子改名为 `test_r9_observation_negative_suite`，删除 evidence-target 自述并纳入本文件 `main()`；真实注册 target 仍唯一位于 process E2E 文件。capability 测试 PASS。
- B3R9-05：harness 两测试先把生产 evidence targets 临时置为空，确认 not-ready，再验证 context 内四链 ready、退出后恢复同一空对象且仍 not-ready；import 泄漏测试亦在空基线上运行，finally 再恢复真实生产表。临时 H1“不恢复”与 H2“缺 sol 且泄漏” mutant 均令正式测试 `rc=1`；正常文件 PASS。
- B3R9-06：R7-04 的 exploration/formal 两处 `observed_context_slot` 均精确等于 `bundle["supply"]["slot"]`，不再只验非 None。临时把生产 supply_truth 写值改成 0 后 `test_r7_findings.py rc=1`；正常生产文件 `15/15 observed green`。
- 组合绿：`test_r9_batch2_executable_capabilities.py`、`test_batch2_registry_harness_hardening.py`、`test_r7_findings.py`、`test_r9_batch3_solana_observation.py` 全部 rc=0。

### B3F3-G5：B3R9-07/08 台账诚实与闭合边界

- 红：`test_sixlens_docs.py` 增加四个裁判证据逐文件 owner、SQD 跨批 owner、R9-01 三条闭合边界 needle 后，先红于 `g3_preflight/g3_0b_pythia_gpa.json` 在 map 中零命中。
- 绿：B3F3-G5 显式登记 G3-0B 与 smoke 的 accounting/bundle/supply_truth 四个 JSON；`solana_sqd_dataset.py` 的批三 docstring hunk 增加“物理落 160a852、批二实现 owner 见 R9-B2-G3”的跨批行。循环 2 当前 hunk 全部纳入 G1～G6，未映射候选复算为 0。
- R9-01 最终结果明确限界：批三闭合的是“CLI 声明当观测”——RPC 观测唯一真值、genesis 常量、前后 raw、GPA snapshot、三方 supply 与 13 项字段约束；**不含 bundle 防伪**。producer path/sha 与内部自洽不是产出凭证，测试关键输入必须由登记生产者现场生成，依赖批四 producer/consumer 通用守卫。
- `PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_sixlens_docs.py` → PASS。

### B3F3-G6：B3R9-10～15 P3 收口

- B3R9-10 红：addressTableLookups 非空而 meta 无 loadedAddresses 时旧判定静默 False；header 推导 mint writable=True 但 parsed key 自报 false 时旧判定亦 False。绿：前者抛 `SolanaObservationError` fail-closed；后者采用 `derived or explicit_true`，自报只能加严不能放松。
- B3R9-11 红：complete 且零引用 fake 的 coverage 仍声称“all successful referenced transactions ... parsed”。绿：零引用明确写 `zero referenced signatures`、`sample_size=0`、未执行 writable checks；G6 裁判事实补记引用=0/sample=0，不再只写 activity=complete。
- B3R9-12 红：docs 契约先红于 accounting docstring 缺 `--bundle`。绿：accounting/supply_truth/scan 三个 docstring 补正式 bundle 与 min-context 用法；formal probes/harness 删除 batch2/“batch3 must add”过时叙述；`test_sixlens_docs.py` 双向守卫。
- B3R9-13 已在 G2 修：getTokenSupply 无官方 minContextSlot，保留 commitment-only 并把 supply slot 落后归入整轮 Retryable；两轮 fake 证明可恢复。
- B3R9-14：删除控制流不可达的 `not complete and not high_activity` 假闸，保留注释说明所有非 complete 出口已由 pagination_error 或 high-activity flags 穷尽；正式 docs 守卫禁止该死条件回流，临时回植真实分支 mutant 后 `test_sixlens_docs.py rc=1`。
- B3R9-15 红：publish_txn 注入失败后旧顺序已删 `.partial`，恢复证据断言红。绿：先原子提交 data+receipt，成功后 best-effort 删除 partial；txn 失败保留完整 partial，cleanup 自身失败只 WARN 且不反转已提交 PASS。anchor 从未写 partial，删除无效变量及 alias 参数，仅保留真实 out/receipt 路径约束。
- 绿：`test_r9_batch3_solana_observation.py`、`test_batch3_solana_producers.py`、`test_sixlens_docs.py` 全部 rc=0。

## 裁判 mainnet 证据登记（Fable 总验收，2026-08-08）

角色纪律：以下全部为裁判亲自执行的真实 mainnet 运行与复现级核实；攻击式审查另由 Opus 子代理批内执行，不由裁判本人做。

### 裁判环境全量门禁（两次）

- 修复循环 1 前：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` → exit=0 全绿（codex 沙箱内 EPERM 的 `test_batch3_solana_vertical_slice.py` / `test_batch3_evm_vertical_slice.py` 两项在裁判环境真实通过，loopback 编排完整走完）。
- 修复循环 1 后：同命令 → exit=0 全绿。
- 关键单跑亲验：`test_r9_batch3_solana_observation.py`、`test_r9_batch3_dynamic_runner.py`、`test_batch3_solana_vertical_slice.py`、`test_r9_solana_attested_session.py`（8/8）均 PASS；`formal_ready_chains()` 亲跑输出 `{'base','bsc','eth','sol'}`，`missing_formal_capabilities('sol')==()`。

### G3-0A（USDC 活动量级，non-blocking）

- 第一轮（未修 CA）：双 endpoint 全灭于 attestation 第一跳 `CERTIFICATE_VERIFY_FAILED`，且 error 字符串携带完整 endpoint（含 api-key）落盘——触发批内修复循环 1（B3FIX-01/02），污染报告已删。
- 第二轮（修复后）：报告 `g3_0a_usdc_activity.json` sha256=`c89ec1d635dcddc31749e83024f86470a9a24d5809b8d8e628a8bf843348a16b`，key 泄漏检查干净。
  - 公共节点轮 PASS：高活动分支命中，轻量抽样中只读 transferChecked 引用全部正确分类（29 次 RPC / 737KB / 60s）。
  - Helius 轮 ERROR=正确阻断非故障：观测窗口内命中 USDC mint 真实 writable 交易（Circle 铸造/销毁），writable 判定器在真实数据上正确识别并阻断（37 次 RPC / 822KB / 70s）。两轮合计恰好覆盖判定器两个分支。
- G3-0A 任何失败不触发批三停止（PLAN 条款），此处两分支实证均为正向证据。

### G3-0B（PYTHIA GPA+三方闭合，绑定批三停止条款）

- 报告 `g3_0b_pythia_gpa.json` sha256=`faf8d902ee1aa1d52f4a8e6c99084274b90f9d18f37ce9bc4b007d1e1d4023ea`，verdict=**PASS**，批三停止条款不触发。
- 公共节点 `api.mainnet-beta.solana.com` 全协议 PASS：GPA 原子快照 82,223 账户（23.5MB/35s），snapshot slot=438,010,311，观测窗口 pre 438,010,301 → post 438,010,364 = 63 slots（≤512），attempt=1；三方闭合精确相等 `gpa=mint_raw=getTokenSupply=998,158,041,739,995`；活动 complete 模式（窗口内 PYTHIA 引用 0 笔，writable 零命中）。
- Helius 轮 ERROR：`Too many accounts requested (Large number of pubkeys)`——免费层拒大 GPA，按 PLAN 记为单一供应商渠道限制，不判协议不可行。已尝试两个已验证 endpoint，满足条款。

### G6 PYTHIA mainnet transport smoke（最终实现全链）

- 执行链：`scan_token_accounts.py`（producer，公共节点）→ `receipt_validate.py`（独立校验 PASS）→ `accounting_gate_sol.py --bundle` → `supply_truth_gate.py --observation-bundle`（独立重放产物 `PYTHIA分析/replay_stats.json`，未用 bundle 自证）。
- 观测：OBS_SLOT=**438,010,504**（GPA context 真实观测，非 CLI 声明）；非零账户 37,929 / owner 37,902（本地历史基线 38,039/38,012 同量级，仅作对照）；activity=complete，但窗口引用签名=0、sample_size=0、未执行任何 getTransaction writable 判定，零样本事实不表述成“已解析过交易”。
- 三件回执终判：bundle PASS / accounting PASS,exit=0 / supply_truth PASS,exit=0；三者 target slot 均=438,010,504；accounting 的 bundle sha256 绑定与磁盘文件一致；supply_truth `diff=0`（0.0bps，容差 10bps），supply 观测 slot=438,010,552（>snapshot，交叉语义正确）；三件合并全文 key 泄漏检查干净。
- 证据哈希：bundle=`1d606ec406a8eb313976a452de7170473c57af780b0b45ba00240c981db205f9`，snapshot（8.85MB 未入档只记哈希）=`46e0fd16ba1da38eef86e4e5fc7368b8fe3f6a9bd304cb2bbdf43d3067b613a3`，accounting=`5fa831ceac129b928c289fef9bada9564c291de4243f067e5926db379b081ff7`，supply_truth=`67767aa1b3f4c2f0594692a4445d3494063a31cbd3a7a5e326384f9dcb131b37`；三件小回执副本入档 `g3_preflight/smoke-20260808/`。

### 遗留与建议

- 首轮 G3-0A 的含 key error 曾短暂落盘（文件已删）且出现在裁判会话输出中；建议用户择机在 Helius 后台轮换 api-key（免费层，风险低，按红线执行）。
- R9-01/R9-05 的 mainnet 待登记位由本节补齐；批内 Opus 攻击审查及其消化仍在后（未做完不收口批三）。

## 批三批内审查裁决（Fable 总验收，2026-08-08）

**裁决：BLOCK，进批内修复循环 2。** Opus 4.8 只读子代理六视角+边界外一步攻击，15 finding（P0=0 / P1=1 / P2=7 / P3=7）全部自称 CONFIRMED。报告入库 `reviews/r9-batch3-review.md`，证据脚本 13 个在 `r9-reviews/b3/evidence/`。

**Fable 读码复现核实**：抽核 P1 + 6 条（B3R9-01/02/04/05/06/07）逐条属实——B3R9-01 `endpoint_identity.py:19` 确剥 query 留 path（Alchemy/Infura path 型 key 泄漏，落在循环1 B3FIX-02 半修残留上）；B3R9-02 producer 自检弱于 validator（降级 checked 不截断 + GPA slot 只查 <pre 不查 <parsed）；B3R9-04 影子函数 `test_r9_batch3_solana_observation.py:399` 孤儿空壳（不被注册表指、不在自己 main tests、自称 Executable evidence target）；B3R9-05 harness 两守卫四链基线下进/出观测相同退化恒真；B3R9-06 r7 断言弱化为 is None；B3R9-07 smoke-20260808/g3_0b 在 diff-finding-map grep=0 属实（Fable 入档证据未回补 map）。Opus 报告质量高（13 条 REFUTED-CANDIDATE 含自我推翻 R-1、克制归因 R-10/R-13、裁判证据 5/5 哈希逐字核对），采信全部 15 条。

**止损计数**：批三第 `2` 个批内修复循环（循环1=B3FIX SSL/脱敏）。B3R9-01=半修残留（落在循环1 B3FIX-02 上）计数、B3R9-02~06=修复中新引入计数。当前 **2/3**；循环 2 修完仍 BLOCK=3/3 冻结上报用户。B3R9-01 不构成「同 INV 再穿」加重（循环1修复未经独立重审宣告闭合，属半修残留非闭合再穿）。

**流程教训**：批内修复循环 1（B3FIX）当时仅由 codex 自报+Fable mainnet 验收即 commit，未过 opus 独立攻击——正是这轮 opus 才抓出 B3FIX-02 只修 query 半。今后批内修复循环也应过一次攻击审查，不以 codex 自报修完为闭合。

**循环 2 修复清单**（P1 全修+P2 全修+P3 随手/登记）：
- P1 B3R9-01：public_endpoint 补 path 脱敏 + redact 只替换 key=value 片段 + path/无 scheme 负例。
- P2 B3R9-02：根治=producer publish 前自跑 validate_observation_bundle（约束集机器闭合）+ GPA≥parsed 断言 + 降级 checked 截断。
- P2 B3R9-03：发布层 6 断言各补先红后绿负例。
- P2 B3R9-04：删/改影子函数去 Executable evidence target 自述。
- P2 B3R9-05/06：harness 守卫测试内先建 not-ready 基线验对称 + r7 断言改精确值。
- P2 B3R9-07：补 4 证据 JSON owner 行 + solana_sqd_dataset 跨批注记 + 未映射 hunk 复算真实数。
- P2 B3R9-08：ledger R9-01 登记闭合边界（不含防伪，依赖批四通用守卫）。
- P3 B3R9-09~15：min-context-slot producer 复核 / writable lookups fail-closed / 零样本 coverage 措辞 / docstring 同步 / getTokenSupply 时序改 Retryable / 删不可达死闸 / window partial 顺序登记取舍。

## 批内修复循环 2 最终汇总

- 覆盖结论：B3R9-01～15 全部进入仓库正式测试并完成红→绿；没有用 skip、手写 PASS 或批四通用守卫替代批三自身负例。G2 的根治点位于 scan 正式发布前的共享 `validate_observation_bundle()` 自校验，producer/consumer 对对象级约束机器同源。
- 密钥面：除审查点名的 session/observation/accounting/anchor/G3 壳外，同族扫描继续打到 EVM accounting receipt、Solana decode output/cache receipt、SQD cache meta；三者均以字面假 key 先红，现只持久化脱敏 public origin 与不可逆 SHA256。裁判既有 mainnet JSON 未重跑、未出网、未写入任何真实 key。
- 受影响组合绿：`test_r9_solana_attested_session.py`、`test_batch1_rpc_attestation.py`、`test_r9_batch3_solana_observation.py`、`test_batch3_solana_producers.py`、`test_r9_batch3_release_guards.py`、`test_r9_batch2_executable_capabilities.py`、`test_batch2_registry_harness_hardening.py`、`test_r7_findings.py`、`test_review_solana_integrity.py`、`test_review_resume_integrity.py`、`test_sixlens_docs.py` 全部 rc=0。
- 机器门禁：`formal_ready_chains()=={'eth','bsc','base','sol'}`；`docs_lint.py --all` → `PASS: 58 个文档`；`invariant_scan.py` → `PASS ... exceptions=0`；transport JSON 可解析；`git diff --check` 绿；`SKILL.md=7737B`；`VERSION=6.36.0` 且无 diff；未执行任何 git 写操作。
- 全量：`PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/run_all.py` → 88 项中 86 PASS。仍且仅 `test_batch3_solana_vertical_slice.py`、`test_batch3_evm_vertical_slice.py` 两项失败；均在首个 `ThreadingHTTPServer(('127.0.0.1',0))` 的 `socket.bind` 处 `PermissionError: [Errno 1] Operation not permitted`，未进入 transport 或业务断言。按工单要求如实登记为本沙箱既有 loopback EPERM，需裁判允许 bind 的环境复跑，不改成 skip。
- 未映射 hunk：`0` 候选；B3F3-G1～G6 全部在 `diff-finding-map.md` 登记，SHA 留空待 Fable 回填。
- 循环结论：代码、正式反例、台账与本沙箱可执行门禁闭合；完成信号 `B3F3_COMPLETE`。

## 批内修复循环 2 — Fable 总验收登记（2026-08-08）

**裁决：PASS，15 finding 全部读码复现核实真修。** 攻击式复现交后续 opus 复审，Fable 只做读码复现级核实+跑既有 suite+主网数据复现+代 commit。codex resume 本轮未 commit（改动全在工作区含 untracked），由 Fable 代 commit。

**读码核实 7 条核心（P1+6 咬合 P2）**：
- B3R9-01（P1，按用户降档「够用」标准）：`endpoint_identity.py` 新增 `_redacted_path`——path 段启发式（v1/v2/v3/key/token 前缀 + UUID/长hex≥24/长token≥24）替换 [redacted]，覆盖 Alchemy `/v2/KEY`、Infura `/v3/KEY`；`redact_endpoint_text` query-key 全局替换改为只替 value（不再腐蚀正文）。够用，不苛求边界完备（用户 2026-08-08 明示密钥可替换、脱敏不必追完美）。
- B3R9-02（P2，最有价值根治）：`scan_token_accounts.py:297` publish_txn 前调 `validate_observation_bundle(bundle, expected_mint=args.mint)`（consumer 同一函数），失败即 except→ERROR receipt→return 1 不发布正式位。try 块内必经之路，producer/validator 约束机器同源。附带降级 checked 截断、GPA≥parsed 断言、min-context-slot producer 复核、getTokenSupply 时序改 Retryable。
- B3R9-03（P2）：新建 `test_r9_batch3_release_guards.py` 6 负例（exploration 拒/无 bundle 绑定拒×2/slot 不匹配拒×2/无效 supply bundle 拒），挂 SUITE，单跑 PASS 6/6。
- B3R9-04（P2）：影子函数改名 `test_r9_observation_negative_suite`，去 "Executable evidence target" 自述，纳入 main tests 列表（22 项含循环 2 全部新负例）；另加 `test_solana_evidence_function_has_no_same_named_shadow` 防同名回流。
- B3R9-05（P2）：`test_batch2_registry_harness_hardening.py` 两守卫先置空 VERTICAL_SLICE_EVIDENCE_TARGETS 建 not-ready 基线（断言 formal_ready==set()）再验 harness 进/出对称与不泄漏，finally 恢复；判别力恢复（harness 不恢复即红）。
- B3R9-06（P2）：`test_r7_findings.py:161,191` 断言从 `is None` 改 `!= bundle["supply"]["slot"]` 精确值。
- B3R9-07/08（P2 台账）：diff-finding-map 补 4 证据 JSON owner 行（smoke-20260808/g3_0b grep≥1）；ledger R9-01 最终结果登记闭合边界=闭合「声明当观测」P0 病根但**不含 bundle 防伪**，依赖批四 producer/consumer 通用守卫。

**G6 P3 负例**（从新增 def 与 main 列表核实）：writable lookups fail-closed、explicit 不覆盖 header writable、零样本 coverage explicit、supply lag retryable、window partial 两顺序、docstring 同步、死闸处理——均落成正式测试。

**门禁**：裁判环境全量 `run_all.py` exit=0（88 项全绿，codex 沙箱 EPERM 两项在裁判环境真跑通）；formal_ready_chains()=={eth,bsc,base,sol}；SKILL 7737B；VERSION 未改；docs_lint/invariant_scan 绿。

**主网数据复现（循环 2 后全链重跑，公共节点）**：producer 自校验**未误伤**真实 bundle——正常落盘 snapshot slot=438,104,303（新实时观测）、GPA 82,218 账户、非零 37,932/owner 37,905（与基线 38,039 同量级）；独立 receipt_validate PASS；accounting PASS exit 0（rpc 字段=公共节点无 key 脱敏后不变，合理）；supply_truth PASS exit 0 **diff=0**；三件 target slot 一致、api-key 干净。根治在真实主网未跑坏。

**止损**：循环 2 消化完成，Fable 验收 PASS。攻击式真闭合待 opus 复审确认（复跑 13 evidence 脚本转绿+边界外一步）。复审若 ALL-CLEAR→批三收口进批四；若再 BLOCK→止损 3/3 冻结上报用户。

## 循环 2 复审进度（Fable，2026-08-08）— 第一发部分完成 + Fable 读码补收

**opus 复审第一发（agent a9a869c038dee17f9）：INCONCLUSIVE，工具通道故障中止**（完成前 4 条后 Bash/Read/Monitor 全通道近 30 次探活无响应——记忆在案的 opus 后台子代理故障老毛病）。该代理表现诚实：验证 4 条全 CLOSED、自我纠正一次 Read 渲染幻觉（sed+shasum 核实 atk3a/atk4 为正常脚本非注入）、如实交付部分不编造。报告存档 `reviews/r9-batch3-rereview-partial.md`。

**opus 已攻击验证 CLOSED（4）**：B3R9-01（脱敏 path 型 key 被挡、正文不腐蚀、host 保留无回归，降档口径）、B3R9-02A（降级 sample_size 截断至 50、coverage 诚实措辞）、B3R9-02B（GPA<parsed producer 侧 FATAL 不发布）、B3R9-09（min-context-slot 返回值 producer 复核 FATAL）。

**Fable 读码/台账复现补收 CLOSED（7）**：B3R9-04（影子函数改名 test_r9_observation_negative_suite、grep 无孤儿同名、防回流测试在）、B3R9-07（循环2 25 文件全在 B3F3 owner 清单命中≥1、无未映射孤儿）、B3R9-08（ledger R9-01 登记闭合边界不含防伪依赖批四）、B3R9-11（coverage_statement 三分支：零样本单列"no writable checks performed"）、B3R9-12（过时注释 grep 空已删）、B3R9-14（不可达死闸删除+穷尽性注释，保留 pagination_error 真实可达 raise）、B3R9-15（改回 publish_txn 后删 partial、unlink 失败不反转 PASS）。

**待 opus 攻击补验（4 mutant + 边界外一步）**：B3R9-03（发布层6负例先红后绿 mutant）、B3R9-05（harness 两守卫 H1/H2 mutant 转红）、B3R9-06（r7 断言写错值 mutant 转红）、B3R9-10（writable 判定器 lookups/explicit mutant）；边界外一步 5 项（B3R9-02 完备性=自校验对象vs落盘字节同一/约束集反向 fail-open、6负例抽样先红后绿、harness not-ready 基线是否污染模块级全局、endpoint_identity 脱敏对全链 receipt 连带、window partial 新面）。→ 重发聚焦 opus（错峰、强抗故障预案）。

**注**：Fable 读码补收非攻击式（读逻辑/grep/台账对表），符合角色纪律；mutant 先红后绿与边界外构造新攻击属攻击式，坚持交 opus。11/15 已 CLOSED，剩 4 mutant 有 Fable 读码确认负例存在+codex 先红后绿自述+opus 首轮确认原缺陷三重旁证，风险可控但仍待独立攻击定论。
