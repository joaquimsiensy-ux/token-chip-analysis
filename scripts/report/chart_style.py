#!/usr/bin/env python3
"""matplotlib 中文图表通用配置。在画图脚本开头 `from chart_style import setup, log_axis`。

来源：OPN(BSC) 分析会话实战产物，原样收录（跨链通用，与链无关）。

已解决的坑：
- 中文字体：macOS 用 Hiragino Sans GB / Arial Unicode MS（rcParams 全局设；注意 reportlab 不认 Hiragino，PDF 层用 STHeiti，见 references/environment.md）
- 对数轴刻度上标乱码：中文字体缺上标字形，用 FuncFormatter 输出纯文本刻度
- 负号乱码：axes.unicode_minus=False

推荐的六张标准图（生成到 ./charts/）：
  01_price_events.png   价格（对数轴）+ 关键事件竖线标注
  02_supply.png         总量托管分布横条图（对账后的精确数）
  03_vault_flow.png     金库结构与流向框图（axis off + Rectangle + annotate 箭头）
  04_cex_flow.png       每日 CEX 净流柱状（红充入/绿提出）+ 价格双轴
  05_treasury_cex.png   金库余额 vs CEX 合计余额时序
  06_key_event.png      最重要单一发现的资金路径框图
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, FixedLocator

def setup():
    plt.rcParams["font.family"] = ["Hiragino Sans GB", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

def log_axis(ax, ticks):
    """对数轴 + 纯文本刻度（规避中文字体上标乱码）。ticks 例：[0.05,0.1,0.2,0.4]"""
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(FixedLocator(ticks))
    ax.yaxis.set_minor_locator(FixedLocator([]))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))

def flow_box(ax, x, y, w, h, text, fc="#dde8f4", ec="#4a6a8a", fs=8.8):
    ax.add_patch(plt.Rectangle((x, y), w, h, fc=fc, ec=ec, lw=1.1, zorder=2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, zorder=3)

def flow_arrow(ax, x1, y1, x2, y2, text="", color="#666", fs=7.8):
    ax.annotate("", (x2, y2), (x1, y1),
                arrowprops=dict(arrowstyle="->", color=color, lw=1.3), zorder=1)
    if text:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.015, text, fontsize=fs, color=color,
                ha="center", zorder=3)
