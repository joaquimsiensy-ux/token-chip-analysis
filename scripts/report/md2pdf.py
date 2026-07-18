#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""md2pdf.py — 中文筹码分析报告 Markdown → PDF 渲染器（通用版）

来源：HYPE(Hyperliquid) 分析会话实战产物，通用化改造（参数化+提示框+图注不跨页）。
用法：
    python3 md2pdf.py --md 报告.md [--out 报告.pdf] [--figdir 图目录] \
                      [--title "PDF元数据标题"] [--footer "页脚左侧文字"]
约定（在 md 里直接用）：
    > i 开头的引用块 → 蓝色信息框（TL;DR / 核心结论用）
    > ! 开头的引用块 → 红色警示框（风险提示用）
    > 普通引用块     → 灰绿底浅色框
    ![题注](fig.png) 后紧跟一行 *斜体题注* → 图与题注绑定不跨页
依赖：reportlab（中文字体用 macOS 系统 STHeiti，勿改用 Hiragino——reportlab 会报 TTFError）
"""
import os, re, html, argparse
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, HRFlowable, KeepTogether)
from reportlab.lib.utils import ImageReader

# 中文字体（macOS 系统自带，TrueType 轮廓）
pdfmetrics.registerFont(TTFont("CN", "/System/Library/Fonts/STHeiti Light.ttc", subfontIndex=0))
pdfmetrics.registerFont(TTFont("CN-Bold", "/System/Library/Fonts/STHeiti Medium.ttc", subfontIndex=0))
addMapping("CN", 0, 0, "CN")
addMapping("CN", 1, 0, "CN-Bold")
addMapping("CN", 0, 1, "CN")
addMapping("CN", 1, 1, "CN-Bold")

GREEN = colors.HexColor("#0a7f4b")
DARK = colors.HexColor("#1a1a2e")
GREY = colors.HexColor("#555555")
BLUE_BG = colors.HexColor("#eef4fb")
BLUE_BD = colors.HexColor("#2b6cb0")
RED_BG = colors.HexColor("#fdf0ef")
RED_BD = colors.HexColor("#c0392b")

S = {
    "title": ParagraphStyle("title", fontName="CN-Bold", fontSize=20, leading=28, textColor=DARK, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="CN-Bold", fontSize=14.5, leading=20, textColor=GREEN, spaceBefore=14, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="CN-Bold", fontSize=12, leading=17, textColor=DARK, spaceBefore=10, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="CN", fontSize=9.5, leading=15.5, textColor=colors.HexColor("#222222"), spaceAfter=5),
    "li": ParagraphStyle("li", fontName="CN", fontSize=9.5, leading=15.5, textColor=colors.HexColor("#222222"),
                          leftIndent=14, bulletIndent=4, spaceAfter=3),
    "quote": ParagraphStyle("quote", fontName="CN", fontSize=9.5, leading=15, textColor=GREY,
                            leftIndent=12, borderPadding=6, backColor=colors.HexColor("#f2f7f4"), spaceAfter=6),
    "info": ParagraphStyle("info", fontName="CN", fontSize=9.8, leading=16, textColor=colors.HexColor("#1a365d"),
                           leftIndent=12, borderPadding=7, backColor=BLUE_BG,
                           borderWidth=0.8, borderColor=BLUE_BD, spaceAfter=6),
    "warn": ParagraphStyle("warn", fontName="CN", fontSize=9.8, leading=16, textColor=colors.HexColor("#7b241c"),
                           leftIndent=12, borderPadding=7, backColor=RED_BG,
                           borderWidth=0.8, borderColor=RED_BD, spaceAfter=6),
    "cell": ParagraphStyle("cell", fontName="CN", fontSize=8.2, leading=12, textColor=colors.HexColor("#222222")),
    "cellh": ParagraphStyle("cellh", fontName="CN-Bold", fontSize=8.4, leading=12, textColor=colors.white),
    "meta": ParagraphStyle("meta", fontName="CN", fontSize=8, leading=12, textColor=GREY),
}

def inline(md):
    """md 行内格式 → reportlab XML"""
    t = html.escape(md, quote=False)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`([^`]+)`", r'<font face="Courier" size="8.5">\1</font>', t)
    t = re.sub(r"!\[.*?\]\(.*?\)", "", t)  # 行内图片引用清掉（块级另处理）
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)  # 链接只留文字
    return t

def build(md_path, out_path, figdir, pdf_title, footer_left):
    lines = open(md_path, encoding="utf-8").read().split("\n")
    story, i = [], 0
    table_buf = []

    def flush_table():
        nonlocal table_buf
        if not table_buf:
            return
        rows = []
        for ln in table_buf:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            rows.append(cells)
        rows = [r for r in rows if not all(re.fullmatch(r":?-{3,}:?", c or "---") for c in r)]
        ncol = max(len(r) for r in rows)
        data = []
        for ri, r in enumerate(rows):
            r = r + [""] * (ncol - len(r))
            style = S["cellh"] if ri == 0 else S["cell"]
            data.append([Paragraph(inline(c), style) for c in r])
        avail = A4[0] - 30*mm
        if ncol >= 3:
            w0 = avail * 0.24
            widths = [w0] + [(avail - w0) / (ncol - 1)] * (ncol - 1)
        else:
            widths = [avail / ncol] * ncol
        t = Table(data, colWidths=widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f9f6")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(Spacer(1, 3))
        story.append(t)
        story.append(Spacer(1, 5))
        table_buf = []

    doc_title = None
    while i < len(lines):
        ln = lines[i]
        if ln.strip().startswith("|"):
            table_buf.append(ln)
            i += 1
            continue
        flush_table()
        stripped = ln.strip()
        m_img = re.match(r"^!\[(.*?)\]\((.+?)\)$", stripped)
        if m_img:
            path = m_img.group(2)
            if not os.path.isabs(path):
                path = os.path.join(figdir, path)
            if os.path.exists(path):
                iw, ih = ImageReader(path).getSize()
                w = A4[0] - 30*mm
                img_group = [Spacer(1, 4), Image(path, width=w, height=w * ih / iw)]
                nxt = lines[i+1].strip() if i + 1 < len(lines) else ""
                if nxt.startswith("*") and nxt.endswith("*") and not nxt.startswith("**") and len(nxt) > 2:
                    img_group.append(Paragraph(inline(nxt.strip("*")), S["meta"]))
                    i += 1
                img_group.append(Spacer(1, 6))
                story.append(KeepTogether(img_group))
        elif stripped.startswith("# "):
            if doc_title is None:
                doc_title = stripped[2:]
            story.append(Paragraph(inline(stripped[2:]), S["title"]))
        elif stripped.startswith("## "):
            story.append(Paragraph(inline(stripped[3:]), S["h2"]))
        elif stripped.startswith("### "):
            story.append(Paragraph(inline(stripped[4:]), S["h3"]))
        elif stripped.startswith("> i "):
            story.append(Paragraph(inline(stripped[4:]), S["info"]))
        elif stripped.startswith("> ! "):
            story.append(Paragraph(inline(stripped[4:]), S["warn"]))
        elif stripped.startswith("> "):
            story.append(Paragraph(inline(stripped[2:]), S["quote"]))
        elif re.match(r"^[-*] ", stripped):
            story.append(Paragraph(inline(stripped[2:]), S["li"], bulletText="•"))
        elif re.match(r"^\d+\. ", stripped):
            num, rest = stripped.split(". ", 1)
            story.append(Paragraph(inline(rest), S["li"], bulletText=f"{num}."))
        elif stripped == "---":
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#bbbbbb")))
            story.append(Spacer(1, 4))
        elif stripped.startswith("*") and stripped.endswith("*") and len(stripped) > 2 and not stripped.startswith("**"):
            story.append(Paragraph(inline(stripped.strip("*")), S["meta"]))
        elif stripped:
            story.append(Paragraph(inline(stripped), S["body"]))
        i += 1
    flush_table()

    final_title = pdf_title or doc_title or os.path.basename(md_path)
    final_footer = footer_left or f"{final_title} · 数据可复现，不构成投资建议"

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("CN", 7.5)
        canvas.setFillColor(GREY)
        canvas.drawString(15*mm, 10*mm, final_footer)
        canvas.drawRightString(A4[0]-15*mm, 10*mm, f"第 {doc.page} 页")
        canvas.restoreState()

    doc = SimpleDocTemplate(out_path, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=16*mm, bottomMargin=18*mm,
                            title=final_title, author="链上数据分析")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("PDF 已生成:", out_path, f"({os.path.getsize(out_path)/1024:.0f} KB)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="筹码分析报告 md → PDF")
    ap.add_argument("--md", required=True, help="输入 Markdown 文件")
    ap.add_argument("--out", help="输出 PDF 路径（默认与 md 同名同目录）")
    ap.add_argument("--figdir", help="图片目录（默认 md 所在目录）")
    ap.add_argument("--title", help="PDF 元数据标题（默认取 md 首个一级标题）")
    ap.add_argument("--footer", help="页脚左侧文字")
    a = ap.parse_args()
    md = os.path.abspath(a.md)
    out = a.out or os.path.splitext(md)[0] + ".pdf"
    figdir = a.figdir or os.path.dirname(md)
    build(md, out, figdir, a.title, a.footer)
