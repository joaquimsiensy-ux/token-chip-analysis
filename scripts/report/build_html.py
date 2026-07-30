#!/usr/bin/env python3
"""报告.md → 自包含单文件 HTML（图 base64 内嵌 + 机器可读 JSON 附录）。零第三方依赖。

来源：bibi(2026-07) 分析实战定型的交付格式，用户 2026-07-12 指定为默认交付
（取代 PDF；md2pdf.py 保留，仅当用户点名要 PDF 时用）。

用法：
  python3 build_html.py --md 报告.md --out 报告.html [--json appendix.json] [--title 标题]

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
import argparse, base64, html, json, mimetypes, os, re, sys
from collections import Counter

# ---- 外部代币名自查（铁律 1 报告红线的自动化，3.18.0）----
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
    """扫描报告中的疑似外部代币名。返回 (warn 列表, note 列表)。
    $XXX cashtag=强信号(非白名单即 WARN)；孤立全大写词=弱信号(NOTE 供人工扫一眼)。"""
    wl = _SCAN_COMMON | {w.strip().upper() for w in whitelist if w.strip()}
    cash = Counter(m.group(1).upper()
                   for m in re.finditer(r"\$([A-Za-z][A-Za-z0-9]{1,9})\b", md_text))
    caps = Counter(m.group(0)
                   for m in re.finditer(r"(?<![A-Za-z0-9$_./-])[A-Z][A-Z0-9]{2,9}(?![A-Za-z0-9_./-])",
                                        md_text))
    warns = [f"[WARN] 疑似外部代币名 ${t}×{c}（铁律 1：除标的与生态 gas 币外禁现其他代币名；"
             f"误报则加 --token-whitelist）" for t, c in cash.most_common() if t not in wl]
    notes = [f"{t}×{c}" for t, c in caps.most_common() if t.upper() not in wl]
    return warns, notes

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
    ap.add_argument("--md", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", help="机器可读 JSON 附录文件（schema 见 monitoring-package.md）")
    ap.add_argument("--title", default=None)
    ap.add_argument("--token-whitelist", default="",
                    help="逗号分隔：标的符号+用户点名对比项等合法代币名（外部代币名自查白名单）")
    ap.add_argument("--facts", help="facts.json 事实源（3.18.0 报告编译化：渲染宏+语义 gate，"
                                    "见 facts_gate.py docstring；不给则旧行为不变）")
    ap.add_argument("--state", help="analysis-state.json（与 --facts 同给时做 G1 成员集合对账）")
    ap.add_argument("--skip-identity-gate", action="store_true",
                    help="显式跳过 G8 实体身份闸（仅限历史报告重编译等无 gate 场景；跳过会打 NOTE 留痕）")
    a = ap.parse_args()

    md_text = open(a.md, encoding="utf-8").read()
    mddir = os.path.dirname(os.path.abspath(a.md))
    warns = []

    # ---- G8 实体身份闸（v4.2 2026-07-30，IQ/LPT/PYTHIA 托管误判三案根治）----
    # --state 给出时强制：state 同目录必须有 identity_gate.json，实体地址全覆盖、
    # flag 全解决，否则 WARN（有 WARN 不许交付）。生成/填写见 entity_identity_gate.py。
    if a.state and not a.skip_identity_gate:
        gate_path = os.path.join(os.path.dirname(os.path.abspath(a.state)), "identity_gate.json")
        if not os.path.exists(gate_path):
            warns.append("[WARN] G8 实体身份闸缺失：未找到 identity_gate.json——实体判级前必须跑 "
                         "entity_identity_gate.py（标签双源+曲线判定+托管假设四查）；"
                         "历史报告重编译可用 --skip-identity-gate 显式跳过")
        else:
            try:
                _gate = json.load(open(gate_path, encoding="utf-8"))
                _gaddrs = {r.get("address") for r in _gate.get("rows", [])}
                _sd = json.load(open(a.state, encoding="utf-8"))
                _missing = [x for g in _sd.get("whale_groups", [])
                            for x in g.get("addresses", []) if x not in _gaddrs]
                if _missing:
                    warns.append(f"[WARN] G8 实体地址未全入闸：{len(_missing)} 址无 gate 记录"
                                 f"（如 {_missing[0][:14]}…）——重跑 entity_identity_gate.py")
                _unres = [r for r in _gate.get("rows", [])
                          if r.get("flag") and not str(r.get("resolution", "")).strip()]
                if _unres:
                    warns.append(f"[WARN] G8 有 {len(_unres)} 个身份疑点未解决"
                                 f"（{'/'.join(sorted({r['flag'] for r in _unres}))}）——"
                                 "逐条填写 resolution（查了什么、结论是什么）后重编译")
            except (ValueError, KeyError) as e:
                warns.append(f"[WARN] G8 identity_gate.json 解析失败: {e}")
    elif a.state and a.skip_identity_gate:
        print("[NOTE] G8 实体身份闸已显式跳过（--skip-identity-gate）——仅限历史重编译场景")
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
    body = md_to_html(md_text, mddir, warns)

    tk_warns, tk_notes = token_name_scan(md_text, a.token_whitelist.split(","))
    warns += tk_warns
    if tk_notes:
        print("[NOTE] 全大写词人工扫一眼（checklist 第 10 条；确认非代币名可交付）: "
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
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head>
<body><div class="wrap">
{body}
{appendix}
</div></body></html>"""
    open(a.out, "w", encoding="utf-8").write(doc)
    for w in warns:
        print(w)
    print(f"[{'FAIL' if warns else 'OK'}] {a.out} ({os.path.getsize(a.out)//1024} KB)"
          + (f"，{len(warns)} 条告警——修复后重跑，有 WARN 不许交付" if warns else ""))
    sys.exit(1 if warns else 0)


if __name__ == "__main__":
    main()
