# 工单R2复核：通过

结论针对当前 v1（HEAD `e8363d7`；工单 SHA-256 前缀 `9562f4afcb7d`）。复核期间 §1.1 已从“净减 15 B → 930130”更新为“净减 36 B → 930109”；订正值与独立重算一致。内容基线 `07c97d6` 无差异，工作区干净。

**D1a：采纳。** [evm-channels:219](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-channels.md:219) 的锚按代码块整行执行 `grep -n -F`，恰好命中一次。

代码事实成立：`multicall_balances.py:90–92` 的 `--chain` 默认 `bsc`；107–112 行捕获 attest 错误后返回 1；`net.py:339–342` 对链 ID 不匹配抛出 `RpcChainMismatch`，该异常继承 `RpcAttestationError`。内存替身验证 ETH/Base 只补 RPC 均退出 1，补对应 `--chain` 后通过 attest。替换原文：

```text
[--chain <链> --rpc URL ...]`。默认 4 个公共节点仅适用于 BSC；跨链必须显式传对应链的 `--chain` 与 `--rpc`，禁止改源码注入标的。
```

**D1b：采纳。** [evm-sources:28](/Users/uravvv/.claude/skills/token-chip-analysis/references/data-pipeline-evm-sources.md:28) 的锚唯一、行号一致。删除重复且不完整的参数说明，保留权威段落指针，符合删除优先。替换原文：

```text
见 §3.5；禁止改源码注入标的
```

**D2：采纳。** [evidence-wording:18](/Users/uravvv/.claude/skills/token-chip-analysis/references/playbook-evidence-wording.md:18) 的锚唯一、行号一致。

`facts_gate.py:531` 确为 **build 子命令**的 `--out` 默认 `facts.json`，544 行据此构造输出路径；`report-template.md:208、212` 一致。获准现行文档仅此处出现 `report_facts.json`，`scripts/` 精确检索无命中。替换原文：

```text
`facts.json`、措辞表、facts gate
```

**D3：采纳。** [analyze-workflow:50](/Users/uravvv/.claude/skills/token-chip-analysis/references/analyze-workflow.md:50) 的锚唯一、行号一致。

`accounting_gate_sol.py:132–135` 明确要求 `--bundle` 与 `--exploration` 二选一；两者皆无或同时传入，均经 `ap.error` 退出 2，已用现行解析代码在内存验证。代码的 `--out` 默认仍是 `accounting_mode.json`；新命令显式指定探索产物名，与 `SKILL.md:43` 一致。原命令会先报参数错误，不能据此断言已覆盖正式文件。替换原文：

```text
accounting_gate_sol.py --mint <mint> --exploration --out accounting_mode.exploration.json
```

**回归面与范围：通过。** 检索 49 份获准 Markdown 并核读相关上下文，未发现其他同款现行错误，四份文档的施工白名单够用。

源码中 multicall 的“跨链必须传 `--rpc`”属于必要条件说明，头部示例及参数帮助已有 `--chain`；Solana 源码示例的输出名符合实际默认值，无需扩大到 `scripts/` 修改。正式流程中的 `accounting_mode.json`、历史 CHANGELOG 也无需随 A0 改名。三项均有执行或产物契约依据，未把措辞偏好当漂移，替换文本未引入新的不实断言。

**精简原则：通过。** 四处均为原位文本替换，按 §1.1 预算口径上下文总量减少。D1b 还有可选的更短等价写法，由 §3.5 统一承载禁止改源码的要求：

```text
见 §3.5
```

此选项可再减 **30 B**，总量变为 **930079 B**；属于非阻断精简建议，以下仍按工单原方案汇总。

| 项目 | 实测行号／命中数 | 锚→替换 UTF-8 字节 | 净变化 | 意见 |
|---|---|---:|---:|---|
| D1a | 219／1 | 136 → 164 | +28 B | 采纳 |
| D1b | 28／1 | 122 → 39 | −83 B | 采纳 |
| D2 | 18／1 | 44 → 37 | −7 B | 采纳 |
| D3 | 50／1 | 63 → 89 | +26 B | 采纳 |
| 合计 | 四锚全部吻合 | 365 → 329 | **−36 B** | **通过** |

字节预算独立重算：

- `references` 三组共 42 文件：**930145 − 36 = 930109 B ≤ 930160 B**，余量 **51 B**。
- `SKILL.md`：**8021 B**，不变。
- `commands-staging/*.md`：**8789 B**，不变。

替换使用原始字节在内存模拟；`attic.md` 仅取 `stat` 大小，未读取正文。九项施工守卫未运行，其中包含临时文件写入及禁读文档遍历；守卫全绿仍待施工验收核实。

纪律披露：全程离线，未修改或新建文件、未 commit；未读取 `~/.codex/` 或 memories，`maintenance/` 仅访问本工程。首轮文件名检索因排除顺序错误列出了 `archive/` 与 `attic.md` 路径，未打开正文，随后已纠正。临时文件及 Git 缓存创建尝试均被只读环境拒绝，未生成文件。
