#!/usr/bin/env python3
"""全周期流转路径图（lifecycle flow）——P0 级标签实体的必配图（v2.0.0 起）。

来源：OPN(BSC) 金库流向框图形式获用户认可，但旧版 flow_box/flow_arrow 手摆坐标
文字拥挤难读（用户 2026-07-14 指定改进）。本脚本改为数据驱动自动布局：
框高按内容行数自适应、列式布局、箭头标签白底垫片、账目行独立放图底。

规范（配套 report-template.md「全周期流转路径图」节）：
- 每个 P0 级实体（项目方 / 大庄 / P0 级狙击集团）必配一张，覆盖全生命周期：
  币从哪来 → 中转/拆分结构 → 去向终点（CEX / 休眠仓 / 销毁 / 续持）
- 节点命名用标签制（项目方钱包#1），不出现完整地址（完整地址只在 JSON 附录）
- 数量一律带【总量X.X%】换算
- 意图不可区分时在 footnote 账目行并列写（如"高位变现 或 做市备货，链上不可区分"）

排版约定（防拥挤，调用方遵守）：
- 节点 title ≤14 全角字符；lines 每行 ≤16 全角字符（超长自己拆行，函数会 WARN）
- 边 label 用 \\n 拆成 ≤2 行、每行 ≤14 字符；同一节点出边 ≥3 条时 label 尽量精简
- 每列节点 ≤5 个；列数 ≤5；更复杂的结构拆成两张图（主路径图 + 细节图）
- **实体的全部体系构成必须画进图，不得"图中未单列"**（SIREN 2026-07-20 用户反馈：平行
  静置仓网 15.2% 只在 footnote 文字带过 → 读者对照正文一头雾水）。平行结构用双泳道：
  主链节点先列（列内靠上）、平行网后列（靠下）；平行网多仓的币源线按"币源框高度 ≈ 目标
  框高度"对齐排列内顺序，使各线平行走线不交叉；合流出货边共用同一 dst 节点表达"同一执
  行网"，数量大标签放最长（最底）那条边，避免压框/互叠；跨多列长线让它走图下部空档。

自解释验收（v3.8 用户定的图存在目的，交付前逐条自问，过不了返工）：
- 不看正文只看图，能把实体全部操作一眼看完（怎么关联/怎么分仓/怎么合并）
- 每张卡片带该节点持币量【总量X%】（读者要能从卡片拼出峰值/期末等体系数字）
- 分/合动作写边标签：几址→几址、方式(等额原路/碎单/一笔清仓)、时点
- 实体归属证据有落点（gas 同源 N/M、同日形成、等额指纹、出货合流）
- footnote 账目行加法自检：期初−期末=Σ各去向（SIREN 净出漏 15.2pp 的教训）
- footnote 文本勿用半角 $（成对 $ 会触发 matplotlib 数学模式、中文变乱码方块，用全角＄）

自测（生成通用化样图）：python3 lifecycle_flow.py <输出目录>
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chart_style import setup

# ── 节点配色（按标签体系语义固定，跨报告一致）──────────────────
NODE_STYLES = {
    "project": dict(fc="#f7dfe4", ec="#b03a5b"),   # 项目方（含金库/创始人）
    "whale":   dict(fc="#fdeacd", ec="#c9752a"),   # 大庄/小庄实体仓
    "hub":     dict(fc="#feF3d9", ec="#c99a2a"),   # 中转/拆分中枢
    "cex":     dict(fc="#fdf6cf", ec="#a8890a"),   # 交易所/充值走廊
    "sleep":   dict(fc="#def0e4", ec="#3f7a58"),   # 休眠仓/囤仓
    "sniper":  dict(fc="#e9def2", ec="#7d5a9e"),   # 狙击集团
    "washer":  dict(fc="#f0def0", ec="#a05aa0"),   # 对倒刷量地址
    "neutral": dict(fc="#e6ebf1", ec="#5b6b7d"),   # 其他/一次性地址
    "burn":    dict(fc="#e8e8e8", ec="#7a7a7a"),   # 销毁/锁仓
}
EDGE_COLORS = {
    "out":   "#b03a5b",   # 离开本实体（红）
    "cex":   "#a8890a",   # 充所方向（金）
    "sleep": "#3f7a58",   # 转入休眠/囤仓（绿）
    "plain": "#78848f",   # 一般中转（灰）
}

# 布局常数（单位：抽象 unit，S 换算 inch；改动会破坏跨报告一致性，勿随意调）
S = 0.165          # inch / unit
BOX_W = 15.0       # 框宽（容 ~16 全角字符 @9pt）
LH = 1.55          # 内容行高
TITLE_LH = 1.85    # 标题行高
PAD_V = 0.85       # 框内上下留白
COL_GAP = 10.0     # 列间距（容箭头标签）
V_GAP = 2.6        # 同列节点垂直间距
MARGIN = 1.6       # 绘图区四周留白


def _box_h(node):
    return PAD_V * 2 + TITLE_LH + len(node.get("lines", [])) * LH


def _warn_len(node):
    t = node["title"]
    if len(t) > 14:
        print(f"[WARN] 节点标题超 14 字符，可能挤：{t}")
    for ln in node.get("lines", []):
        if len(ln) > 16:
            print(f"[WARN] 节点内容行超 16 字符，可能挤：{ln}")


def draw_lifecycle_flow(out_png, title, nodes, edges, footnote="", subtitle=""):
    """画一张全周期流转路径图。

    nodes: [{"id","col"(0起),"title","lines":[str,...],"kind":NODE_STYLES键}, ...]
           同列节点按列表出现顺序自上而下排布
    edges: [{"src","dst","label"(可含\\n),"kind":EDGE_COLORS键}, ...]
    footnote: 账目/口径说明（可含 \\n），放图底独立灰条，不挤图内
    """
    setup()
    cols = {}
    for n in nodes:
        _warn_len(n)
        cols.setdefault(n["col"], []).append(n)
    ncol = max(cols) + 1
    col_h = {c: sum(_box_h(n) for n in ns) + (len(ns) - 1) * V_GAP for c, ns in cols.items()}
    H = max(col_h.values()) + 2 * MARGIN
    W = ncol * BOX_W + (ncol - 1) * COL_GAP + 2 * MARGIN

    pos = {}
    for c, ns in cols.items():
        x = MARGIN + c * (BOX_W + COL_GAP)
        y = (H + col_h[c]) / 2  # 每列垂直居中，从顶往下排
        for n in ns:
            h = _box_h(n)
            pos[n["id"]] = (x, y - h, BOX_W, h)
            y -= h + V_GAP

    title_h = (1.6 if subtitle else 1.0) * 0.42        # inch
    foot_lines = footnote.count("\n") + 1 if footnote else 0
    foot_h = foot_lines * 0.21 + (0.30 if footnote else 0.05)  # inch
    fig_w, plot_h = W * S, H * S
    fig_h = plot_h + title_h + foot_h
    fig = plt.figure(figsize=(fig_w, fig_h))
    ax = fig.add_axes([0, foot_h / fig_h, 1, plot_h / fig_h])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

    fig.text(0.012, 1 - 0.30 * 0.42 / fig_h, title, ha="left", va="top",
             fontsize=13, fontweight="bold")
    if subtitle:
        fig.text(0.012, 1 - (title_h - 0.18) / fig_h, subtitle, ha="left", va="top",
                 fontsize=9.5, color="#555")

    for n in nodes:
        x, y, w, h = pos[n["id"]]
        st = NODE_STYLES.get(n.get("kind", "neutral"), NODE_STYLES["neutral"])
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
                                    fc=st["fc"], ec=st["ec"], lw=1.3, zorder=2))
        ty = y + h - PAD_V - TITLE_LH / 2
        ax.text(x + w / 2, ty, n["title"], ha="center", va="center",
                fontsize=10.5, fontweight="bold", color="#222", zorder=3)
        for i, ln in enumerate(n.get("lines", [])):
            ax.text(x + w / 2, ty - TITLE_LH / 2 - LH * (i + 0.5), ln,
                    ha="center", va="center", fontsize=9, color="#333", zorder=3)

    out_seen = {}
    for e in edges:
        x1, y1, w1, h1 = pos[e["src"]]
        x2, y2, w2, h2 = pos[e["dst"]]
        color = EDGE_COLORS.get(e.get("kind", "plain"), EDGE_COLORS["plain"])
        if x2 >= x1 + w1:                    # 正向：右边中点 → 左边中点
            p1 = (x1 + w1, y1 + h1 / 2); p2 = (x2, y2 + h2 / 2)
        elif x1 >= x2 + w2:                  # 反向
            p1 = (x1, y1 + h1 / 2); p2 = (x2 + w2, y2 + h2 / 2)
        else:                                # 同列：下边 → 上边
            if y1 > y2:
                p1 = (x1 + w1 / 2, y1); p2 = (x2 + w2 / 2, y2 + h2)
            else:
                p1 = (x1 + w1 / 2, y1 + h1); p2 = (x2 + w2 / 2, y2)
        rad = 0.10 if abs(p1[1] - p2[1]) > 1e-6 else 0.0
        ax.add_patch(FancyArrowPatch(p1, p2, connectionstyle=f"arc3,rad={rad}",
                                     arrowstyle="-|>", mutation_scale=14,
                                     color=color, lw=1.5, zorder=1))
        if e.get("label"):
            k = out_seen.setdefault(e["src"], [0])
            dy = [0.0, 0.9, -0.9, 1.8, -1.8][k[0] % 5]  # 同源多出边标签错开
            k[0] += 1
            mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + rad * (p2[0] - p1[0]) * 0.5
            ax.text(mx, my + dy, e["label"], ha="center", va="center",
                    fontsize=8.5, color=color, zorder=4, linespacing=1.35,
                    bbox=dict(fc="white", ec="none", alpha=0.88, pad=1.6))

    if footnote:
        fig.patches.append(plt.Rectangle((0, 0), 1, foot_h / fig_h - 0.004,
                                         transform=fig.transFigure,
                                         fc="#f2f3f5", ec="none", zorder=0))
        fig.text(0.014, (foot_h - 0.16) / fig_h, footnote, ha="left", va="top",
                 fontsize=8.8, color="#444", linespacing=1.55)

    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"[OK] {out_png}")


# ── 自测：通用化样图（协调投放路径场景，数字为虚构自洽账）─────────
def _demo(outdir):
    os.makedirs(outdir, exist_ok=True)
    nodes = [
        {"id": "vault", "col": 0, "title": "项目方钱包#1", "kind": "project",
         "lines": ["金库·Safe 多签", "沉寂两个月后", "两日划出 40M"]},
        {"id": "hub1", "col": 1, "title": "项目方钱包#2", "kind": "hub",
         "lines": ["拆分中枢 1", "6/4 收 2×10M"]},
        {"id": "hub2", "col": 1, "title": "项目方钱包#3", "kind": "hub",
         "lines": ["拆分中枢 2", "6/5 收 20M", "留存 2M【0.2%】"]},
        {"id": "disp", "col": 2, "title": "21 个一次性新地址", "kind": "neutral",
         "lines": ["面额 0.5/1/1.5/2M", "收币后 1-15 分钟充所"]},
        {"id": "corr", "col": 2, "title": "项目方钱包#4", "kind": "cex",
         "lines": ["Bybit 充值走廊", "分钟级连续充所"]},
        {"id": "sleep", "col": 2, "title": "项目方钱包#5", "kind": "sleep",
         "lines": ["休眠仓 6M【0.6%】", "至今未动"]},
        {"id": "boost", "col": 2, "title": "Booster 分发器", "kind": "neutral",
         "lines": ["空投 2M【0.2%】"]},
        {"id": "cex", "col": 3, "title": "交易所", "kind": "cex",
         "lines": ["48h 共充入 30M", "【总量 3.0%】", "Bybit 18M·Bitget 11M", "币安 1M"]},
    ]
    edges = [
        {"src": "vault", "dst": "hub1", "kind": "out",
         "label": "20M【总量 2.0%】\n6/4 13:17+15:47"},
        {"src": "vault", "dst": "hub2", "kind": "out",
         "label": "20M【总量 2.0%】\n6/5 10:36"},
        {"src": "hub1", "dst": "disp", "kind": "plain", "label": "20M 拆散"},
        {"src": "hub2", "dst": "corr", "kind": "plain", "label": "10M"},
        {"src": "hub2", "dst": "sleep", "kind": "sleep", "label": "6M"},
        {"src": "hub2", "dst": "boost", "kind": "plain", "label": "2M"},
        {"src": "disp", "dst": "cex", "kind": "cex", "label": "20M【2.0%】"},
        {"src": "corr", "dst": "cex", "kind": "cex", "label": "10M【1.0%】"},
    ]
    draw_lifecycle_flow(
        os.path.join(outdir, "lifecycle-flow-sample.png"),
        title="全周期流转路径图 · 项目方（样图，数字虚构）",
        subtitle="2026-06-04~05（拉升次日）：金库沉寂两个月后 40M【总量 4.0%】的协调投放路径",
        nodes=nodes, edges=edges,
        footnote=("账目：40M【总量 4.0%】= 30M 充所【3.0%】+ 6M 休眠【0.6%】+ 2M 空投【0.2%】"
                  "+ 2M 留存中枢【0.2%】。\n"
                  "21 个一次性地址的面额特征与交易所充值地址吻合；"
                  "意图（高位变现 或 做市/所内活动供库存）链上不可区分，并列保留。"),
    )


if __name__ == "__main__":
    _demo(sys.argv[1] if len(sys.argv) > 1 else ".")
