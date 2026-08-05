# 批量预采集手册（/collect-data）

> v6.0.0 从 collect-data 命令文件迁入（commands 不受 git 保护，操作细节的权威源必须在仓库内）。入口命令只声明任务与硬性，本文承接全部执行细节。

**唯一职责：只采集，不分析。** 把每个币的全量转账事件采到位；不做对账、不做重放、不做聚类、不出任何结论——那些是后续分析会话的事。

## 1. 清单解析（name/chain/address 结构化）

- 支持链：bsc / eth / base / arbitrum / robinhood（HyperSync v2）＋ solana（SQD v2）。
- 来自初筛清单且已明确给出链与合约的地址可直接入队；用户只给币名没给地址时，多源核定地址与链并 AskUserQuestion 确认后再入队。
- **Solana 币必须顺手查发射时间**（GMGN/GeckoTerminal/Dexscreener 任一，取值再往前减 1 天做保守 launch_ts）——缺省只回看 90 天，老币会缺早期数据。
- 多链币按用户给定的链采；链范围核定是分析会话的多链硬关卡，届时若需补链再补采（本命令不做链分布盘点）。

## 2. 执行（plan → 脱管队列）

生成 plan.json 到 `<工作根目录>/collect_plans/plan_<YYYYMMDD_HHMM>.json`（base_dir＝工作根目录，即各 `<币名>分析/` 的父目录），然后监督器脱管执行：

```
python3 ~/.claude/skills/token-chip-analysis/scripts/run_guarded.py --detach --mem-ceiling-gb 6 --name collect \
  -- python3 ~/.claude/skills/token-chip-analysis/scripts/collect/collect_queue.py <plan.json>
```

- **队列泳道调度**：EVM 泳道与 Solana 泳道并行、各泳道内串行（HyperSync 限流 key 级共享、SQD 单 IP 带宽整形——泳道内并行只会互抢，跨泳道并行纯赚墙钟）；`--serial` 回退全串行；单项失败不阻塞后续。HyperSync key 从 `~/.config/hypersync/token` 自动读取。
- 重跑同一 plan 带 `--resume` 跳过已完成项；不带也安全（底层幂等续拉）。
- **跨进程锁**：队列启动抢 `collect_plans/queue.lock` 单实例锁——已有队列在跑则**退出码 3**（什么都没采，稍后再跑或先看在跑的是谁：锁文件里有 pid/run_id/心跳）；每币采集抢 `<币目录>/data/.collect.lock`，抢不到记 manifest `skipped_locked` 跳过不崩队列（`--resume` 会重试）。持有进程死亡内核自动放锁；进程活着但心跳超 10 分钟＝挂死，保守拒绝并附 kill 建议，不强抢。锁只保同机并发，工作根勿挪网络盘。run_id 贯通链路（nightly→run_guarded→队列→manifest/锁文件），run_guarded 日志/状态文件名带 run_id 不互覆盖。HyperSync token 全链路不进子进程 argv（--token-file 传递）。

## 3. 汇报纪律

- 脱管后向用户交代：预计总时长（按量级粗估）、manifest 路径（plan 同目录 collect_manifest.json）、查看进度的命令。用户睡前排队场景不必等完成；用户在等则用 run_guarded 状态文件轮询到结束后汇报。
- 结束汇报只给采集事实：每币 状态/行数/块范围/耗时/落盘路径＋失败与缺口原因；`done_with_gaps`（Solana 缺口）与 `failed` 项单独点名。**不给任何筹码结论**。
- 衔接（写给用户一句话）：对任一已采集币跑 /token-analyze 时，分析会话在同一工作目录开工自动发现已有数据并断点续拉增量——采集成本不重复发生。

## 4. 夜间自动模式（可选）

用户说"排到夜里跑/睡前排队"时，把 plan 存为 `<工作根>/collect_plans/pending_plan.json` 即可收工——launchd 定时器 `com.chip-analysis.nightly-collect` 每天 02:30 自动检测并开采（合盖睡过点则唤醒后补跑），采完按结果改名 done_plan_*/gaps_plan_*/failed_plan_* 归档，日志 `collect_plans/nightly.log`；rc=3（队列锁被占）保留 pending 明晚自动重试。次日开工先看归档名与日志。卸载：`launchctl bootout gui/$(id -u)/com.chip-analysis.nightly-collect`。

## 5. 每周 key 健康巡检（自动在役）

launchd `com.chip-analysis.weekly-probe` 每周一 10:00 跑 `scripts/collect/probe_keys.py --feishu`——对登记在役 key 免额度探测（12 项：hypersync/alchemy/drpc/etherscan/xapi/dune/helius/gmgn/firecrawl/bigquery；sqd/vybe 无免额度探测法恒 skipped），五分类 ok/auth_invalid/quota_exhausted/service_error/network_error，**仅异常才推飞书**（叙事哨兵 webhook），全 ok 静默。手动跑：`python3 ~/.claude/skills/token-chip-analysis/scripts/collect/probe_keys.py`；最近结果 `~/.cache/chip-analysis/probe_report.json`；卸载：`launchctl bootout gui/$(id -u)/com.chip-analysis.weekly-probe`。报告与输出全程脱敏（key 明文不落任何产物）。摘要出现意外 skipped 先查 api-keys.md 版式是否变动（md 正则提取失联归 skipped 不误报）。
