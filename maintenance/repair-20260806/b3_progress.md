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
- 观测：OBS_SLOT=**438,010,504**（GPA context 真实观测，非 CLI 声明）；非零账户 37,929 / owner 37,902（本地历史基线 38,039/38,012 同量级，仅作对照）；activity=complete。
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
