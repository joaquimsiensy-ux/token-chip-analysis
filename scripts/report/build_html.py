#!/usr/bin/env python3
"""报告.md → 自包含单文件 HTML（图 base64 内嵌 + 机器可读 JSON 附录）。零第三方依赖。

来源：bibi(2026-07) 分析实战定型的交付格式，用户 2026-07-12 指定为默认交付
（取代 PDF；md2pdf.py 保留，仅当用户点名要 PDF 时用）。

用法：
  python3 build_html.py --mode analysis-new --md 报告.md --out 报告.html \
    --facts facts.json --state analysis-state.json --a4-seal a4_seal.json
  python3 build_html.py --mode update|legacy-recompile --degrade-reason "理由" \
    --md 简报.md --out 简报.html

支持的 md 子集（与 md2pdf.py 语法一致，报告写作按 references/report-template.md）：
  # ## ### #### 标题 | **粗体** *斜体* `代码` [链接](url) | - / 1. 列表 | 表格 | ``` 代码块
  > i 文字   → 蓝色信息框（TL;DR/图表要点解读）
  > ! 文字   → 红色警示框(⚠️)（风险/未绘制说明/局限）
  > 文字     → 普通灰引用
  ![题注](charts/x.png) 独立成行 → 图片 base64 内嵌；紧跟一行 *斜体* → 居中灰色题注
  --- → 分隔线

JSON 附录（--json）：文件校验可解析后，双轨嵌入报告末尾——
  ① 可见 <details> 折叠块（人读）② <script type="application/json" id="report-extract">（机器提取）
  id="report-extract" 是用户监控看板的硬性约定（只认此 id，旧版 chip-json 曾致抽取失败，2026-07-13 改）。
  顶层必备四键 chip_summary/addresses/unlock_events/source_line（schema 与字段纪律见
  report-template.md「监控抽取块硬性标准」节），缺键或 addresses 现缩写地址会打 [WARN]。
  另：alt/题注含「阵营」的第一张图自动加 id="chart-camps"（看板抽阵营演变图的约定）。
  监控脚本提取：python3 -c "import re,json,sys;h=open('报告.html').read();
    print(json.loads(re.search(r'<script type=.application/json. id=.report-extract.>(.*?)</script>',h,re.S).group(1))['chip_summary'])"

质检（出 HTML 后必做）：
  1) 本脚本 stdout 的告警行（缺图/图读取失败会打 [WARN]，有 WARN 不许交付）
  2) 浏览器打开目检：图片全部显示、表格无错位、蓝红框渲染正常、JSON 折叠块可展开
"""
import argparse, base64, hashlib, html, json, mimetypes, os, re, sys
from collections import Counter
from pathlib import Path

# ---- 外部代币名扫描（信息性提示；v6.4.2 起"零外部代币名"红线废止，不再拦交付）----
# 通用缩写/工具名/链与 gas 币/稳定币/CEX 名——这些全大写词不是"外部代币名"
_SCAN_COMMON = set("""
API CEX DEX URL HTML JSON CSV RPC UTC GMT OK GB KB MB TB TLDR TL DR NFT LP AMM KOL FUD
FOMO ATH ATL TVL OTC IDO ICO IEO APY APR CTO DEV BOT ID TX CA PDF PNG JPG WAF UA IP RSS
SQL CPU RAM OS AI OG PR KYC AML VIP MEV EOA ERC BEP SPL USD CNY RMB EUR JPY KRW VC DAO
DD PVP PVE ROI PNL P0 P1 P2 GAS WETH WBNB WSOL WBTC OTC CEXS DEXS
GMGN CMC CG COINGECKO GOPLUS HYPERSYNC SQD DUNE OKLINK SOLSCAN BSCSCAN ETHERSCAN
BLOCKSCOUT DEXSCREENER GECKOTERMINAL DEFILLAMA SOURCIFY HELIUS ALCHEMY BIGQUERY AWS GCP
BINANCE OKX HTX MEXC GATE KUCOIN BYBIT BITGET COINBASE KRAKEN UPBIT BITHUMB ALPHA
ETH BNB BSC SOL BTC POL ARB OP AVAX TRX TON SUI BASE MATIC FTM CRO HYPE FIL HL
USDT USDC DAI BUSD FDUSD TUSD PYUSD USD1 USDE
PANCAKESWAP UNISWAP RAYDIUM JUPITER ORCA METEORA PUMP PANCAKE V2 V3 V4 NPM
CONFIRMED REFUTED WEAKENED PLAUSIBLE
""".split())


def token_name_scan(md_text, whitelist):
    """扫描报告中出现的外部代币名。返回 (cashtag note 列表, 全大写词 note 列表)。
    v6.4.2 起两类都只是信息性提示（"零外部代币名"红线已废止，用户裁定）——
    提示仅供自查是否复用了历史标的的结论（铁律 1），不再 WARN、不影响退出码。"""
    wl = _SCAN_COMMON | {w.strip().upper() for w in whitelist if w.strip()}
    cash = Counter(m.group(1).upper()
                   for m in re.finditer(r"\$([A-Za-z][A-Za-z0-9]{1,9})\b", md_text))
    caps = Counter(m.group(0)
                   for m in re.finditer(r"(?<![A-Za-z0-9$_./-])[A-Z][A-Z0-9]{2,9}(?![A-Za-z0-9_./-])",
                                        md_text))
    cash_notes = [f"${t}×{c}" for t, c in cash.most_common() if t not in wl]
    notes = [f"{t}×{c}" for t, c in caps.most_common() if t.upper() not in wl]
    return cash_notes, notes

CSS = """
:root{color-scheme:light}
*{box-sizing:border-box}
body{font-family:-apple-system,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;
  background:#f5f6f8;color:#24292f;line-height:1.8;margin:0;padding:26px 14px;font-size:15.5px}
.wrap{max-width:1060px;margin:0 auto;background:#fff;border:1px solid #e3e6ea;border-radius:14px;
  padding:44px 52px;box-shadow:0 1px 4px rgba(0,0,0,.04)}
h1{font-size:26px;border-bottom:2px solid #e3e6ea;padding-bottom:12px;margin:6px 0 18px}
h2{font-size:20px;margin:34px 0 12px;padding-left:11px;border-left:4px solid #3b7dd8}
h3{font-size:17px;margin:24px 0 8px}
h4{font-size:15.5px;margin:18px 0 6px;color:#444}
p{margin:9px 0}
code{font-family:ui-monospace,Menlo,monospace;font-size:.88em;background:#f0f1f3;
  padding:1.5px 5px;border-radius:5px;word-break:break-all}
pre{background:#f6f8fa;border:1px solid #e3e6ea;border-radius:10px;padding:13px 16px;
  overflow-x:auto;line-height:1.55}
pre code{background:none;padding:0}
table{border-collapse:collapse;width:100%;margin:13px 0;font-size:14px}
th,td{border:1px solid #dde1e6;padding:7px 11px;text-align:left;vertical-align:top}
th{background:#f2f4f7;font-weight:600;white-space:nowrap}
tr:nth-child(even) td{background:#fafbfc}
.tablebox{overflow-x:auto}
img{max-width:100%;display:block;margin:14px auto 4px;border:1px solid #e3e6ea;border-radius:10px}
figcaption{text-align:center;color:#7a828c;font-size:13px;margin:2px 0 14px}
.box{border-radius:10px;padding:11px 15px 11px 13px;margin:13px 0;display:flex;gap:9px}
.box .ic{flex:0 0 auto;font-size:15px;line-height:1.8}
.box-i{background:#eef5fd;border:1px solid #cfe3f8}
.box-w{background:#fdf1f0;border:1px solid #f5d5d2}
blockquote{border-left:4px solid #d0d7de;margin:13px 0;padding:2px 15px;color:#57606a;background:#fafbfc}
hr{border:none;border-top:1px solid #e3e6ea;margin:28px 0}
ul,ol{margin:8px 0;padding-left:26px}
li{margin:3.5px 0}
details{background:#f6f8fa;border:1px solid #e3e6ea;border-radius:10px;padding:11px 16px;margin:14px 0}
summary{cursor:pointer;font-weight:600}
details pre{background:#282c34;color:#d7dae0;border:none;font-size:12.5px;max-height:520px;overflow:auto}
.meta{color:#57606a;font-size:13.5px;background:#f6f8fa;border-radius:8px;padding:8px 14px;margin:10px 0}
.degraded-banner{background:#fff3cd;border:2px solid #d39e00;color:#5f4700;border-radius:10px;
  padding:12px 16px;margin:0 0 22px;font-weight:700}
@media(max-width:640px){.wrap{padding:22px 18px}body{padding:10px 4px}}
"""

INLINE_RULES = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<strong>\1</strong>"),
    (re.compile(r"(?<![\w*])\*([^*\n]+?)\*(?![\w*])"), r"<em>\1</em>"),
    (re.compile(r"`([^`]+?)`"), r"<code>\1</code>"),
    (re.compile(r"\[([^\]]+?)\]\((https?://[^)\s]+?)\)"), r'<a href="\2" target="_blank">\1</a>'),
]


def inline(s):
    s = html.escape(s, quote=False)
    for pat, rep in INLINE_RULES:
        s = pat.sub(rep, s)
    return s


def embed_img(path, mddir, warns):
    p = path if os.path.isabs(path) else os.path.join(mddir, path)
    if not os.path.isfile(p):
        warns.append(f"[WARN] 图片缺失: {path}")
        return None
    mime = mimetypes.guess_type(p)[0] or "image/png"
    try:
        b64 = base64.b64encode(open(p, "rb").read()).decode()
    except Exception as e:
        warns.append(f"[WARN] 图片读取失败: {path} ({e})")
        return None
    return f"data:{mime};base64,{b64}"


def md_to_html(md_text, mddir, warns):
    lines = md_text.split("\n")
    out, i, n = [], 0, len(lines)
    para = []
    camp_tagged = False  # 首张 alt/题注含「阵营」的图加 id=chart-camps（监控看板抽图约定）

    def flush():
        if para:
            out.append(f"<p>{inline(' '.join(para))}</p>")
            para.clear()

    while i < n:
        ln = lines[i]
        s = ln.strip()
        # 代码块
        if s.startswith("```"):
            flush()
            buf = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf)) + "</code></pre>")
            i += 1; continue
        # 空行
        if not s:
            flush(); i += 1; continue
        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            flush()
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            i += 1; continue
        # hr
        if re.match(r"^-{3,}$", s):
            flush(); out.append("<hr>"); i += 1; continue
        # 引用框（> i / > ! / >）
        if s.startswith(">"):
            flush()
            buf, kind = [], "q"
            while i < n and lines[i].strip().startswith(">"):
                body = lines[i].strip()[1:].lstrip()
                if not buf and body[:2] in ("i ", "! "):
                    kind = "i" if body[0] == "i" else "w"
                    body = body[2:]
                buf.append(inline(body))
                i += 1
            txt = "<br>".join(b for b in buf if b)
            if kind == "i":
                out.append(f'<div class="box box-i"><span class="ic">ℹ️</span><div>{txt}</div></div>')
            elif kind == "w":
                out.append(f'<div class="box box-w"><span class="ic">⚠️</span><div>{txt}</div></div>')
            else:
                out.append(f"<blockquote>{txt}</blockquote>")
            continue
        # 表格
        if s.startswith("|") and i + 1 < n and re.match(r"^\|[\s:|-]+\|?$", lines[i + 1].strip()):
            flush()
            header = [c.strip() for c in s.strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            t = ['<div class="tablebox"><table><tr>' + "".join(f"<th>{inline(h)}</th>" for h in header) + "</tr>"]
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</table></div>")
            out.append("".join(t)); continue
        # 图片（独立成行）+ 可选题注
        m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", s)
        if m:
            flush()
            src = embed_img(m.group(2), mddir, warns)
            cap = None
            if i + 1 < n:
                mc = re.match(r"^\*([^*].*?)\*$", lines[i + 1].strip())
                if mc:
                    cap = mc.group(1); i += 1
            if src:
                img_id = ""
                if not camp_tagged and ("阵营" in m.group(1) or (cap and "阵营" in cap)):
                    img_id = ' id="chart-camps"'
                    camp_tagged = True
                fig = f'<figure style="margin:0"><img{img_id} src="{src}" alt="{html.escape(m.group(1))}">'
                if cap:
                    fig += f"<figcaption>{inline(cap)}</figcaption>"
                out.append(fig + "</figure>")
            else:
                out.append(f'<div class="box box-w"><span class="ic">⚠️</span><div>缺图占位：{html.escape(m.group(2))}</div></div>')
            i += 1; continue
        # 列表
        if re.match(r"^[-*]\s+", s) or re.match(r"^\d+\.\s+", s):
            flush()
            ordered = bool(re.match(r"^\d+\.", s))
            tag = "ol" if ordered else "ul"
            items = []
            while i < n:
                t2 = lines[i].strip()
                m2 = re.match(r"^\d+\.\s+(.*)$" if ordered else r"^[-*]\s+(.*)$", t2)
                if not m2:
                    break
                items.append(f"<li>{inline(m2.group(1))}</li>")
                i += 1
            out.append(f"<{tag}>" + "".join(items) + f"</{tag}>")
            continue
        # 普通段落（首个非空段若形如元信息行，套 .meta 样式）
        para.append(s)
        i += 1
    flush()
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    formal_modes = {"analysis-new": "new-analysis",
                    "analysis-audit": "independent-audit"}
    ap.add_argument("--mode", choices=[*formal_modes, "update", "legacy-recompile"], required=True,
                    help="analysis-new/analysis-audit=两条必经正式门禁；其余为降级产物")
    ap.add_argument("--degrade-reason",
                    help="update/legacy-recompile 必填；写入可见水印与 HTML 注释")
    ap.add_argument("--md", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", help="机器可读 JSON 附录文件（schema 见 monitoring-package.md）")
    ap.add_argument("--title", default=None)
    ap.add_argument("--token-whitelist", default="",
                    help="逗号分隔：标的符号等已知代币名，用于减少外部代币名提示噪音"
                         "（v6.4.2 起扫描仅信息性 NOTE，不再拦交付）")
    ap.add_argument("--facts", help="facts.json 事实源（3.18.0 报告编译化：渲染宏+语义 gate，"
                                    "见 facts_gate.py docstring；不给则旧行为不变）")
    ap.add_argument("--state", help="analysis-state.json（与 --facts 同给时做 G1 成员集合对账）")
    ap.add_argument("--a4-seal", help="a4_seal.json（A4 封口凭证，触发 G9：封口哈希重验+报告图必须"
                                      "全在封口 charts_dir 下；分析流程 A5/E5 编译必传，update 流程不传）")
    a = ap.parse_args()

    if a.mode in formal_modes:
        missing = [flag for flag, value in (("--facts", a.facts), ("--state", a.state),
                                             ("--a4-seal", a.a4_seal)) if not value]
        if missing:
            ap.error(f"{a.mode} 模式缺正式 gate 资产: " + ", ".join(missing))
        # P0-01：正式编译的事实输入只能来自 seal 所在案目录的标准资产。
        # CLI 参数保留是为了兼容显式调用和清晰报错，不是自由输入通道。
        _formal_case = Path(a.a4_seal).resolve().parent
        _formal_facts = (_formal_case / "facts.json").resolve()
        _formal_state = (_formal_case / "analysis-state.json").resolve()
        for _flag, _given, _expected in (
                ("--facts", a.facts, _formal_facts),
                ("--state", a.state, _formal_state)):
            if Path(_given).resolve() != _expected:
                ap.error(f"{a.mode} 模式 {_flag} 必须等于 seal 案目录标准路径: {_expected}")
        # 后续渲染不再使用 CLI 原始字符串，从 seal 案目录重建唯一输入。
        a.facts = str(_formal_facts)
        a.state = str(_formal_state)
    elif not str(a.degrade_reason or "").strip():
        ap.error(f"{a.mode} 模式必须提供 --degrade-reason")
    elif a.a4_seal:
        ap.error("update/legacy-recompile 只用模式水印留痕，不接受正式 gate 参数")

    md_text = open(a.md, encoding="utf-8").read()
    mddir = os.path.dirname(os.path.abspath(a.md))
    warns = []

    # ---- G9 A4 封口闸（6.7.0 2026-08-01，A4 前提前做 A5 七案返工根治）----
    # --a4-seal 给出时强制：seal 必须 PASS、封口文件哈希与当前一致（封口后改结论不重封
    # ＝报告编不出来）、md 引用的全部图片位于封口 charts_dir 下；mtime 仅 NOTE 不裁决。
    mode_note_html = ""
    degraded_banner = ""
    _sealed_paths = set()
    _formal_case = Path(a.a4_seal).resolve().parent if a.mode in formal_modes else None
    if a.mode not in formal_modes:
        reason = str(a.degrade_reason).strip()
        print(f"[NOTE] {a.mode} 显式降级构建: {reason}")
        mode_note_html = f"<!-- build-mode={a.mode}; degraded: {html.escape(reason)} -->\n"
        degraded_banner = (f'<div class="degraded-banner">非正式分析交付物 · {html.escape(a.mode)}：'
                           f'{html.escape(reason)}</div>')
    if a.mode in formal_modes:
        try:
            _seal = json.load(open(a.a4_seal, encoding="utf-8"))
            _sdir = Path(a.a4_seal).resolve().parent
            _case = Path(mddir).resolve()
            if _sdir != _case:
                warns.append("[WARN] G9 seal 与报告不在同一案目录")
            if _seal.get("schema") != "a4-seal/v3" or _seal.get("verdict") != "PASS" \
                    or not _seal.get("claims"):
                warns.append("[WARN] G9 a4_seal.json 无效（schema/verdict/claims 缺失）——"
                             "A4 收尾必须 a4_gate.py finalize 封口成功后才编报告")
            elif _seal.get("workflow_type") != formal_modes[a.mode]:
                warns.append(f"[WARN] G9 workflow_type 与构建模式不匹配: "
                             f"seal={_seal.get('workflow_type')} mode={a.mode}")
            else:
                def checked(rel, label):
                    if not isinstance(rel, str) or os.path.isabs(rel) or ".." in Path(rel).parts:
                        raise ValueError(f"{label} 路径非法: {rel}")
                    raw = _case / rel
                    if raw.is_symlink():
                        raise ValueError(f"{label} 拒绝符号链接: {rel}")
                    resolved = raw.resolve()
                    resolved.relative_to(_case)
                    if not resolved.is_file():
                        raise ValueError(f"{label} 不存在: {rel}")
                    return resolved

                all_entries = list(_seal.get("sealed_files", []))
                all_entries += [_seal.get("registry") or {}, _seal.get("verdicts") or {}]
                for ent in all_entries:
                    try:
                        rel = ent["path"]
                        if rel in _sealed_paths:
                            raise ValueError(f"封口路径重复: {rel}")
                        _sealed_paths.add(rel)
                        _p = checked(rel, "封口文件")
                        _h = hashlib.sha256(_p.read_bytes()).hexdigest()
                        if _h != ent.get("sha256"):
                            warns.append(f"[WARN] G9 封口后被改动: {rel}")
                    except Exception as e:
                        warns.append(f"[WARN] G9 封口条目非法: {e}")
                required = {"findings.md", "analysis-state.json", "facts.json", "identity_gate.json",
                            "a4_claims.json"}
                if _seal.get("workflow_type") == "independent-audit":
                    required.add("claim_registry.json")
                if not required <= _sealed_paths:
                    warns.append(f"[WARN] G9 封口资产不全: {sorted(required - _sealed_paths)}")
                if not set(_seal.get("claim_files") or []) <= _sealed_paths:
                    warns.append("[WARN] G9 claim 引用文件未全部封口")

                _cdir = (_seal.get("charts_dir") or "charts/final").rstrip("/")
                try:
                    if os.path.isabs(_cdir) or ".." in Path(_cdir).parts:
                        raise ValueError(_cdir)
                    _charts_abs = (_case / _cdir).resolve()
                    _charts_abs.relative_to(_case)
                    if (_case / _cdir).is_symlink():
                        raise ValueError("charts_dir 是符号链接")
                except Exception as e:
                    warns.append(f"[WARN] G9 charts_dir 非法: {e}")
                    _charts_abs = _case / "__invalid_charts__"
                _seal_ts = _seal.get("sealed_at_utc", "")
                for m_img in re.finditer(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", md_text, re.M):
                    _ipath = m_img.group(1).strip()
                    try:
                        if os.path.isabs(_ipath) or ".." in Path(_ipath).parts:
                            raise ValueError("绝对路径或 ..")
                        _raw_img = _case / _ipath
                        if _raw_img.is_symlink():
                            raise ValueError("符号链接")
                        _iabs = _raw_img.resolve()
                        _iabs.relative_to(_charts_abs)
                        if not _iabs.is_file():
                            raise ValueError("文件不存在")
                        if _seal_ts:
                            _mt = os.path.getmtime(_iabs)
                            import calendar as _cal, time as _time
                            try:
                                _st = _cal.timegm(_time.strptime(_seal_ts, "%Y-%m-%dT%H:%M:%SZ"))
                                if _mt < _st:
                                    print(f"[NOTE] G9 图片 mtime 早于封口时间（仅提示，mtime 不作裁决）: {_ipath}")
                            except ValueError:
                                pass
                    except Exception as e:
                        warns.append(f"[WARN] G9 报告图路径非法或越界: {_ipath} ({e})")
        except Exception as e:
            warns.append(f"[WARN] G9 a4_seal.json 解析失败: {e}")

        if a.json:
            try:
                _json_raw = Path(a.json)
                if _json_raw.is_symlink():
                    raise ValueError("JSON 附录是符号链接")
                _json_abs = _json_raw.resolve()
                _json_abs.relative_to(_formal_case)
                if not _json_abs.is_file():
                    raise ValueError("JSON 附录不存在")
                _json_rel = _json_abs.relative_to(_formal_case).as_posix()
                if _json_rel not in _sealed_paths:
                    raise ValueError(f"JSON 附录未进入 A4 seal: {_json_rel}")
                a.json = str(_json_abs)
            except Exception as e:
                warns.append(f"[WARN] G9 正式监控 JSON 非封口资产: {e}")

    # ---- G8 实体身份闸（v4.2 2026-07-30，IQ/LPT/PYTHIA 托管误判三案根治）----
    # --state 给出时强制：state 同目录必须有 identity_gate.json，实体地址全覆盖、
    # flag 全解决，否则 WARN（有 WARN 不许交付）。生成/填写见 entity_identity_gate.py。
    if a.state:
        gate_path = os.path.join(os.path.dirname(os.path.abspath(a.state)), "identity_gate.json")
        if not os.path.exists(gate_path):
            warns.append("[WARN] G8 实体身份闸缺失：未找到 identity_gate.json——实体判级前必须跑 "
                         "entity_identity_gate.py（标签双源+曲线判定+托管假设四查）")
        else:
            try:
                import entity_identity_gate
                _identity_errors = entity_identity_gate.validate_gate(gate_path, a.state)
                warns += [f"[WARN] G8 identity_gate 严格校验: {e}"
                          for e in _identity_errors]
            except Exception as e:
                warns.append(f"[WARN] G8 identity_gate.json 解析失败: {e}")
    if a.facts:
        import facts_gate
        try:
            rendered, gate_errs, gate_notes = facts_gate.load_and_check(
                a.facts, a.state, md_text)
            md_text = rendered
        except (KeyError, ValueError) as e:
            print(f"[FAIL] facts 宏渲染失败: {e}")
            sys.exit(1)
        warns += [f"[WARN] {e}" for e in gate_errs]
        for nt in gate_notes:
            print(f"[NOTE] {nt}")
    if a.mode in formal_modes:
        import audit_release_gate
        audit_errors = audit_release_gate.run(
            Path(mddir), Path(a.md).resolve(), profile=formal_modes[a.mode])
        warns += [f"[WARN] audit release gate: {e}" for e in audit_errors]
    body = md_to_html(md_text, mddir, warns)

    tk_cash, tk_notes = token_name_scan(md_text, a.token_whitelist.split(","))
    if tk_cash:
        print("[NOTE] 报告出现外部代币名（信息性提示，不拦交付；自查未复用历史案结论即可）: "
              + " ".join(tk_cash[:20]) + (" …" if len(tk_cash) > 20 else ""))
    if tk_notes:
        print("[NOTE] 全大写词人工扫一眼（确认非误写即可）: "
              + " ".join(tk_notes[:20]) + (" …" if len(tk_notes) > 20 else ""))

    title = a.title
    if not title:
        m = re.search(r"^#\s+(.+)$", md_text, re.M)
        title = m.group(1).strip() if m else os.path.basename(a.md)

    appendix = ""
    if a.json:
        try:
            data = json.load(open(a.json, encoding="utf-8"))
            if not isinstance(data, dict):
                warns.append("[WARN] JSON 附录顶层必须是对象（含监控抽取四键），当前不是")
            else:
                for k in ("chip_summary", "addresses", "unlock_events", "source_line"):
                    if k not in data:
                        warns.append(f"[WARN] JSON 附录缺监控抽取必备键: {k}（看板按四键取值，schema 见 monitoring-package.md）")
                for ad in (data.get("addresses") or []):
                    addr = str(ad.get("address", "")) if isinstance(ad, dict) else str(ad)
                    if any(t in addr for t in ("…", "...", "*")):
                        warns.append(f"[WARN] addresses 含疑似缩写地址: {addr}（必须完整地址，从落盘数据文件复制）")
            pretty = json.dumps(data, ensure_ascii=False, indent=2)
            safe_script = pretty.replace("</", "<\\/")  # 防 </script> 提前闭合
            appendix = (
                "<hr><h2>附录 E · 机器可读 JSON（监控用）</h2>"
                "<p>庄家概况 / 监控地址名单 / 解锁日程 / 完整数据键。监控看板从本文件提取 "
                "<code>&lt;script id=\"report-extract\"&gt;</code> 内容（id 为看板硬性约定，不可改）。</p>"
                f"<details><summary>展开 JSON（{len(pretty)//1024} KB）</summary>"
                f"<pre>{html.escape(pretty)}</pre></details>"
                f'<script type="application/json" id="report-extract">{safe_script}</script>'
            )
        except Exception as e:
            warns.append(f"[WARN] JSON 附录解析失败，未嵌入: {e}")

    doc = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
{mode_note_html}<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head>
<body><div class="wrap">
{degraded_banner}
{body}
{appendix}
</div></body></html>"""
    # gate 前置语义（6.7.0 codex 复核修正）：有 WARN 不写出任何文件——旧行为先落盘再
    # exit 1，"物理编不出"名不副实（带 WARN 的 HTML 已经在盘上可被交付）。
    if warns:
        for w in warns:
            print(w)
        print(f"[FAIL] 未写出 {a.out}——{len(warns)} 条告警，修复后重跑（有 WARN 不许交付）")
        sys.exit(1)
    import tempfile
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(a.out)) or ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(doc)
        os.replace(tmp, a.out)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    print(f"[OK] {a.out} ({os.path.getsize(a.out)//1024} KB)")
    sys.exit(0)


if __name__ == "__main__":
    main()
