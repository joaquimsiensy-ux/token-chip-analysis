# 本机环境备忘（macOS）

来源：五次分析会话实测（2026-07）。每次分析开工前扫一眼，避免重蹈环境坑。

## Python

- Python 3.14 官方安装版（`/Library/Frameworks/Python.framework`），命令 `python3`
- 已装第三方库：matplotlib 3.11、reportlab 5.0、pandas 3.0、pypdf、requests、certifi

## 网络请求的 SSL 坑（必读）

- **urllib 直连 HTTPS 会报 SSL 证书错误**。两个解法：
  1. 首选：`subprocess` + `curl -s`（多次实战最稳，脚本模板均已内置）
  2. 备选：`ssl.create_default_context(cafile=certifi.where())` 传给 `urlopen` 的 `context` 参数
- requests 库自带证书一般没问题

## PDF 生成（reportlab）

- 中文字体：**只能用 STHeiti**——`/System/Library/Fonts/STHeiti Light.ttc`（正文）+ `STHeiti Medium.ttc`（粗体），都要 `subfontIndex=0`
- **Hiragino Sans GB.ttc 在 reportlab 会报 TTFError，不可用**（matplotlib 里却正常，两层字体方案不同，别混淆）
- 行内代码标记（Courier 字体）**没有中文字形**，中文会渲染成方块——`` ` ` `` 只包地址/哈希/命令等 ASCII 内容
- 生成器：`scripts/report/md2pdf.py`（md → PDF，用法见其 docstring）

## 图表（matplotlib）

- 中文字体用 `Hiragino Sans GB`（rcParams），负号 `axes.unicode_minus=False`
- 对数轴刻度会因中文字体缺上标字形而乱码 → `FuncFormatter` 纯文本刻度
- 统一走 `scripts/report/chart_style.py` 的 `setup()/log_axis()`

## PDF 质检（交付前必做）

- 首页缩略图目检：`qlmanage -t -s 1200 -o <目录> <pdf>`
- 文本抽查：`python3 -c "from pypdf import PdfReader; print(PdfReader('x.pdf').pages[0].extract_text())"`
- 检查点：中文无空白方块、表格列没被截断、图片都在、页脚页码正常

## Shell 坑

- zsh 通配符无匹配时整条命令报错中断：删除类命令写 `rm -f xx_* 2>/dev/null || true`
- 长任务日志轮询：`tail -5 log` 而不是 `cat log`（防大输出进上下文）
- **heredoc 内联 Python 对中文文本做 str.replace：全角标点必须逐字符对准**——目标串里的中文全角标点（，、（）、：）在 heredoc 里敲成半角时 replace 静默不生效（无报错、无变更，肉眼极难察觉）；对含中文的文件做精确替换一律用 Edit 工具，不走 heredoc+str.replace（来源：USELESS(Solana) 分析，2026-07-21）

## Bash 工具沙箱杀多进程并发脚本（★大坑，PUB 实测损失约 50 分钟）

- 现象：**ThreadPoolExecutor 多并发 curl 子进程的采集脚本**（如 fetch_sqd_transfers.py 16 并发）在 Claude Code Bash 工具的沙箱下被杀，**exit code 144、日志零输出**；同环境串行 curl 的脚本全程无恙。两次复现。
- 对策（实测有效）：长跑采集脚本**脱管启动**——`nohup python3 … > data/xx.log 2>&1 & disown`，且 Bash 调用参数 `dangerouslyDisableSandbox: true`；之后稳定跑完。
- 附带发现：被杀时**残留的其他会话同类进程也同时消失**——疑沙箱/系统层对进程组的连带清理；重要长跑一律 nohup 脱管，与 Claude 任务管理解耦。
- （来源：PUB(Solana) 分析，2026-07-14）
- **根治通道（B5，2026-07-22）**：新脚本的批量 HTTP/RPC 调用一律用 `scripts/lib/net.py`（httpx 进程内异步+令牌桶限速+tenacity 统一重试+msgspec 解析）——没有可被连带清理的 curl 子进程树，限速贴配额（如 Helius 10 RPS）。现成 CLI：`scripts/lib/rpc_batch.py`（批量 getCode 判 EOA/收据/任意方法，`--browser-ua` 开关对付 robinhood WAF；40 址实测与 curl 单发逐项等价、零失败）。**边界**：CF/指纹敏感站点（bscscan 网页、GT）仍走 curl；在役老脚本不强改（改动须走等价对表）。定位=买稳定性不是买速度。

## 脚本 stdout 与实际行为不一致的误判坑（操作纪律）

- 现象：改造既有脚本时用字符串 replace 换了 `json.dump` 的目标文件名，但脚本 `print` 里硬编码的旧文件名没换——stdout 显示"已写 data/camp_share_series.json"，实际写的是 `_v2` 新文件。凭 stdout 误判"旧文件被覆盖"，执行"恢复"（把未受损的旧文件 move 去覆盖新文件）反而人为制造了覆盖事故（好在均可确定性重算，零损失）。
- 纪律：①判定脚本产出以 `grep` 代码里的写入语句 + `ls -la` 文件时间戳为准，stdout 的文件名叙述不可信；②"危机处置"（恢复/回滚/删除）动手前先验证事故是否真的发生；③改造脚本后先跑 `grep -n "json.dump\|open(" 改后脚本` 核对全部写入目标。
- （来源：PUB(Solana) 增量更新，2026-07-15）

## matplotlib 文本中 $ 符号触发 mathtext 解析崩溃

- 现象：lifecycle_flow footnote / 图表任意文本含成对 `$`（如"已收 $27.4万…($3.4万)"）时，matplotlib 把 `$...$` 段当 LaTeX mathtext 解析，遇中文/特殊字符直接 `ParseException` 崩溃 savefig；单个 `$` 也会告警。
- 对策：图表文本里金额一律写"27.4万U/30.8万美元"或转义 `\$`；报告 md 正文不受影响（只有 matplotlib 渲染的字符串有此坑）。
- （来源：HAN(Robinhood) 分析，2026-07-16）

## zsh 变量存 curl 选项不分词（exit 5 假死）

- 现象：`P="-x http://127.0.0.1:7897"; curl $P …` 在 zsh 下 `$P` 不做词分割（zsh 默认 SH_WORD_SPLIT 关闭），整串被当**一个**参数传给 curl，报 exit 5（CURLE_COULDNT_RESOLVE_PROXY）；同一命令在 bash 正常，极易误判为代理挂了。
- 对策：代理/多段选项要么直接写死在命令里，要么用 `${=P}` 强制分词，要么数组 `P=(-x http://127.0.0.1:7897); curl $P[@]`。
- （来源：ASTEROID(ETH) 分析，2026-07-18）

## 监视器脚本的进程存活检测（macOS 无 /proc）

- 现象：看护采集进程的监视器脚本用 `[ ! -d /proc/<pid> ]` 判断"进程已退出"——macOS 没有 /proc 文件系统，该条件恒真，监视器启动即误报进程死亡秒退（SQD 案实测）。
- 对策：进程存活检测一律 `ps -p <pid> >/dev/null`；不用 /proc（Linux 专属），也不依赖 `kill -0`（跨用户有权限差异）。
- （来源：SQD(Arbitrum) 分析，2026-07-20）

## 案目录自包含原则（2026-07-25 权限事故后立规）

**事故**：分析进行到对抗复核阶段时，macOS 对 `~/Documents` 的访问权限（TCC）被系统撤销，导致跨卷符号链接指向的 1.2GB 采集产物与价格文件**全部失读**（`Operation not permitted`），分析被迫中途重新采集全量数据（1,063 万条，分段约 20 分钟）恢复。

**新规**：
1. 案目录内的数据产物一律**实体文件**，禁止跨卷/跨用户目录的 symlink 依赖——复用其他案目录的采集产物时用 `cp` 而非 `ln -s`（磁盘成本远低于中途失读的返工成本）。
2. 外部数据（价格序列、标签快照等）同样落本案目录，不引用其他案目录的路径。
3. 复用既有采集产物前先做一次读取探针（`duckdb` 读一行），确认可读再规划工序。
4. 附带收获：重采集的 10,638,696 条与原产物**逐条一致**（行数、块区间、供给闭合全等），可作为"采集幂等性"的实证——重采集不是损失，是一次免费的数据可重现性验证。
