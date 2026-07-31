# 本机环境备忘（macOS）

来源：五次分析会话实测（2026-07）。每次分析开工前扫一眼，避免重蹈环境坑。

> **平台适用性（搬迁服务器必读，2026-07-31 标注）**：本册是 macOS 本机坑册。迁 Linux 服务器时：字体（STHeiti/Hiragino）、qlmanage 质检、TCC 权限、「macOS 无 /proc」等条目全部失效或反转，服务器首战后须重建服务器版；SSL/certifi、zsh 词分割（服务器若用 zsh）、Claude Code 工具层坑（沙箱杀并发/Bash 超时/前台 sleep 禁令）与 OS 无关，照用。

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
- 前台 `sleep` 被环境禁止：等待用 until 循环 / Monitor / run_in_background；**until 前台等待同样受 Bash 超时上限（最长 10 分钟）约束**——实测 10 分钟被杀（exit 143），预计等待超 10 分钟必须 run_in_background 或 Monitor（外部 CLAW 考古，2026-07）
- 长任务日志轮询：`tail -5 log` 而不是 `cat log`（防大输出进上下文）
- **heredoc 内联 Python 对中文文本做 str.replace：全角标点必须逐字符对准**——目标串里的中文全角标点（，、（）、：）在 heredoc 里敲成半角时 replace 静默不生效（无报错、无变更，肉眼极难察觉）；对含中文的文件做精确替换一律用 Edit 工具，不走 heredoc+str.replace（USELESS，07-21）

## Bash 工具沙箱杀多进程并发脚本（★大坑）

- **ThreadPoolExecutor 多并发 curl 子进程**的采集脚本在 Claude Code Bash 沙箱下被杀（exit 144、日志零输出，两次复现；被杀时其他会话同类进程连带消失）；同环境串行 curl 无恙（PUB 07-14）。
- 对策：长跑采集**脱管启动**——`nohup python3 … > data/xx.log 2>&1 & disown` ＋ Bash 参数 `dangerouslyDisableSandbox: true`；重要长跑一律与 Claude 任务管理解耦。
- **根治通道（B5）**：新脚本批量 HTTP/RPC 一律用 `scripts/lib/net.py`（httpx 进程内异步+令牌桶限速+tenacity 重试——没有可被连带清理的子进程树）；现成 CLI `scripts/lib/rpc_batch.py`（批量 getCode/收据/任意方法，`--browser-ua` 开关对付 WAF）。**边界**：CF/指纹敏感站点（bscscan 网页、GT）仍走 curl；在役老脚本不强改（改动须走等价对表）。定位=买稳定性不是买速度。

## 脚本 stdout 与实际行为不一致的误判坑（操作纪律）

- stdout 打印的文件名可能是硬编码旧串、与实际写入目标不一致——曾据此误判"文件被覆盖"并执行"恢复"，反而人为制造覆盖事故（PUB 07-15）。
- 纪律：①判定脚本产出以 `grep` 写入语句 + `ls -la` 时间戳为准，stdout 的文件名叙述不可信；②危机处置（恢复/回滚/删除）动手前先验证事故是否真的发生；③改造脚本后 `grep -n "json.dump\|open("` 核对全部写入目标。

## matplotlib 文本中 $ 符号触发 mathtext 解析崩溃

- 现象：lifecycle_flow footnote / 图表任意文本含成对 `$`（如"已收 $27.4万…($3.4万)"）时，matplotlib 把 `$...$` 段当 LaTeX mathtext 解析，遇中文/特殊字符直接 `ParseException` 崩溃 savefig；单个 `$` 也会告警。
- 对策：图表文本里金额一律写"27.4万U/30.8万美元"或转义 `\$`；报告 md 正文不受影响（只有 matplotlib 渲染的字符串有此坑）。
- （HAN，07-16）

## zsh 变量存 curl 选项不分词（exit 5 假死）

- 现象：`P="-x http://127.0.0.1:7897"; curl $P …` 在 zsh 下 `$P` 不做词分割（zsh 默认 SH_WORD_SPLIT 关闭），整串被当**一个**参数传给 curl，报 exit 5（CURLE_COULDNT_RESOLVE_PROXY）；同一命令在 bash 正常，极易误判为代理挂了。
- 对策：代理/多段选项要么直接写死在命令里，要么用 `${=P}` 强制分词，要么数组 `P=(-x http://127.0.0.1:7897); curl $P[@]`。
- （ASTEROID，07-18）

## 监视器脚本的进程存活检测（macOS 无 /proc）

- `[ ! -d /proc/<pid> ]` 判"进程已退出"在 macOS 恒真（无 /proc 文件系统），监视器启动即误报秒退（SQD 07-20）。
- 对策：存活检测一律 `ps -p <pid> >/dev/null`——跨平台通用（Linux 服务器虽有 /proc，仍用 ps 写法，脚本免改）；不依赖 `kill -0`（跨用户有权限差异）。

## 案目录自包含原则（TCC 权限事故后立规，2026-07-25）

**起因**：macOS TCC 中途撤销 `~/Documents` 访问权，跨卷 symlink 指向的 1.2GB 采集产物全部失读，被迫中途重采恢复（诱因 macOS 专属，原则跨平台适用）。

**新规**：
1. 案目录内数据产物一律**实体文件**，禁止跨卷/跨用户目录 symlink——复用其他案目录产物用 `cp` 不用 `ln -s`（磁盘成本远低于中途失读的返工）。
2. 外部数据（价格序列、标签快照等）同样落本案目录，不引用其他案目录路径。
3. 复用既有产物前先做读取探针（`duckdb` 读一行）确认可读，再规划工序。
