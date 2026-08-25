# 批 2d 正式完工报告

## 结论

批 2d 已按两段提交方案 1 完成。第一段生产修复由验收方冻结在
`55d4efede78f6afb6c1d3c8aa3bbec95b6faa33f`；第二段已完成 producer_history
登记、run_all 注册、版本 6.52.3 五处收口、CHANGELOG、绿证追加和全量验收。
未 commit、未 push、未联网，未修改白名单外文件。

## 冻结基线与两段叙事

- 原始施工基线为 `e3969e1` / VERSION `6.52.2`。第一段真实 RED 证明 incumbent
  probe 把 SQD HTTP 200 空体尾段留成失败和 UNSCANNED。
- 第一段只修 probe 的严格三条件流结束语义、给 `net.py` 加交叉注释并新增测试；
  验收方随后提交为 `55d4efede78f6afb6c1d3c8aa3bbec95b6faa33f`。
- 第二段开工时 HEAD 正是该 40 位锚，分支为 `fix/sqd-gap-batch2d`。冻结脚本
  通过 `git show <commit>:<script> | shasum -a 256` 复算为
  `bccf1802b6a5c9d9bbbdb12e19354ad761416c631e3cdfde2449f7fe1794f176`。

## 第一段红绿闭环

- RED：`test_batch2d_stream_tail.py` 在修复前 exit 1，断言 200 空体续页应
  `ok=True` 时失败；原始 traceback 已保存在绿证。
- GREEN：严格匹配 `category=decode`、`http_status=200`、
  `message="curl returned empty stdout"` 后按空数组语义落 NO_HEADER；HTTP 529
  空体、HTTP 200 非法 JSON、其他 transport/decode 失败继续 fail-closed。
- 新测试 4/4、既有 coverage 12/12、net Result 与第五查定向回归均通过；
  未改 `solana_exact_validate.py`，由其独立接受新发布件。

## 第二段逐任务结果

1. **producer_history 登记完成**：为 `sqd-solana-coverage/v1` 与
   `sqd-solana-coverage-pointer/v1` 各新增一条六字段 ACTIVE 记录，commit 为
   `55d4efe...33f`，sha256 为 `bccf1802...f176`。旧 `c237263...` / `e41370b...`
   两条继续 ACTIVE：现役纪律允许同一脚本多代可验证生产者并存；REVOKED 是
   hash-wide 否决，无撤销旧正式收据的依据。`test_anchor_plan_v3.py` 15/15 PASS。
2. **run_all 注册完成**：`test_batch2d_stream_tail.py` 在 SQD coverage 组唯一
   注册一次；`len(SUITE)=132`，机械分母 131→132。
3. **版本五处完成**：VERSION、`pyproject.toml`、SKILL 版本注释均为 6.52.3；
   CHANGELOG 首索引与首详情各新增 6.52.3 条目。写前 lint 为活跃 44＋归档
   139，写后为活跃 45＋归档 139；`test_version_consistency.py` PASS。
4. **CHANGELOG 内容完成**：记录批 2d 根因、严格三条件语义、两段提交、历史
   producer 兼容和 SUITE 131→132；没有写入标的结论。
5. **报告与绿证完成**：本报告合并两段事实，`batch2d_green_evidence.txt` 保留
   第一段真实 RED、两段 GREEN、受限环境失败及正式全量通过记录。

## 全量验收

- 受限 workspace sandbox 首次全量：130 PASS / 2 FAIL。两项分别是 Solana、
  EVM 纵切片在 `ThreadingHTTPServer(("127.0.0.1", 0), ...)` 绑定时收到
  `PermissionError: [Errno 1] Operation not permitted`；其余 130 项全过。
- 在获准的 loopback 环境先独立重跑两项，均 PASS。
- 同一工作树随后完整执行 `python3 scripts/tests/run_all.py`：exit 0，
  **132/132 PASS，全部通过**。因此最终全绿不是把两次结果拼接宣称，而是有一
  次完整 runner 的 rc=0 证明。

## 白名单与未做边界

第二段实际写入仅有：

- `scripts/lib/producer_history.py`：仅新增 probe 两个 protocol 条目；
- `scripts/tests/run_all.py`：仅新增一条测试注册；
- VERSION、`pyproject.toml`、SKILL.md：仅版本行；
- CHANGELOG.md：仅首索引与首详情新条目；
- `batch2d_green_evidence.txt`：仅追加 Stage 2 证据；
- 本 `batch2d_done.md`：新增正式报告。

第一段已提交的 probe、`net.py`、新测试均未在第二段改动。用户提供的未跟踪
`batch2d_workorder_stage2.md` 未修改。没有创建停工报告，因为未发现新矛盾；
没有 commit/push，没有切分支，没有网络调用。
