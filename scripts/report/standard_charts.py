#!/usr/bin/env python3
"""三张标准图生成器——庄家行为分析报告的必配图（每次分析必画，规格固定）。

来源：bibi(2026-07) 分析实战定型图样；v2.0.0（2026-07-14 用户指定）改用
标签体系阵营，图 1/图 2 移到报告开头（TL;DR 问 1 直答上方）；v5.0（2026-07-30
用户修订）取消 P0/P1 分级、废止"狙击集团"标签（该阵营键仅旧数据重绘 legacy）。
配套文档：references/report-template.md「三张标准图」节。

三张图（函数一一对应）：
  图1 plot_camp_evolution   各阵营持仓占比演变（100% 堆叠面积图，占总供应量）→ 放报告开头
                            v3.12 起支持 price_series 右轴价格黑线（价格+筹码对照，
                            2026-07-21 用户定；完整分析默认传入）
  图2 plot_whale_vs_price   庄级实体持仓变动 vs 价格（双轴：左=占比%，右=价格USD线性）→ 放报告开头
  图3 plot_price_events     全历史价格与关键事件（上=价格对数+事件竖线编号，下=成交额柱状）
                            返回事件清单文本行，报告 md 里紧跟图片贴出

规格要点（不要随意改动，保持跨报告视觉一致）：
- 阵营固定配色见 CAMP_COLORS；堆叠顺序见 CAMP_ORDER（项目方在最底、锁仓/销毁在最顶）
- 阵营命名标准（v5.0 标签体系，report-template.md「标签体系」节）：
  项目方 / 大庄 / 小庄 / 离场庄 / 刷量地址(有仓才单列) / 流动性池 /
  其他大户(当前 ≥0.1%总供应 或 ≥0.2%流通、未入任何标签、已过排查前置闸) / 散户 /
  锁仓/销毁(如有)；"狙击集团"仅旧数据重绘 legacy
  其他大户与散户只出现在本图，正文不逐个开小节
- 图2 实体标签格式：项目方 / 大庄#N / 小庄#N / 离场庄#N，
  线色按标签前缀自动取语义色（与图1 阵营同色系），同前缀多实体自动变浅区分
- 图2 价格轴用线性（均匀）刻度，贴近 K 线软件直觉（2026-07-15 用户定，勿改回对数）；
  图3 价格/成交额保留对数刻度——全历史常跨 2~3 个数量级，线性会把早期行情压成贴零平线
- 图1 价格右轴（v3.12）：黑色细线+白描边（堆叠色块上唯一不撞色的组合）；默认线性对齐
  图2 直觉，仅当量程 max/min > PRICE_LOG_SWITCH_RATIO 自动切对数（SIREN 型几百倍量程
  线性会把早期压成地板线），切换后轴标签自动带"(对数)"注明
- 中文字体与负号由 chart_style.setup() 处理
- 图表标题写事实不写结论（结论放报告正文的蓝框里）

自测（合成数据出三张样图）：python3 standard_charts.py <输出目录>
"""
import os, sys, math, colorsys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import to_rgb
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chart_style import setup

# ── 阵营标准配色与堆叠顺序（图1，v2.0 标签体系）────────────────
# F-04（2026-08-13）：拆两段导出——现代段是新报告唯一合法阵营名集合
# （state_from_facts.py 的 camp_share_series 白名单直接 import 本段，禁手抄第二份清单）；
# legacy 段仅旧数据重绘兼容。CAMP_ORDER = 两段合并；“销毁”是
# EVM CHIP_LEGACY_CAMP_DENOM=1 真实产出的旧堆叠桶，F-01 起显式纳入。
CAMP_ORDER_MODERN = ["项目方", "大庄", "小庄", "离场庄", "刷量地址",
                     "CEX资金通道", "CEX托管", "疑似CEX托管", "流动性池", "其他大户",
                     "历史大户", "散户", "桥锁仓", "锁仓/销毁"]
# 旧体系键（旧报告基线重绘兼容用，新报告禁用；"狙击集团"v5.0 起废止归此类）：
CAMP_ORDER_LEGACY = ["狙击集团", "庄家TOP1", "庄家其他组", "首30分钟狙击者", "其他散户", "销毁"]
CAMP_ORDER = CAMP_ORDER_MODERN + CAMP_ORDER_LEGACY
# 图 1 唯一允许不进堆叠图的 series 键；value 是图例收据理由码。
FIG1_EXCLUDED_SERIES = {"burn_cum_pct": "non_stacked_metric"}
# 阵营互斥优先级：设施/CEX 类判定优先于"历史大户"归属——同址两属时归 CEX/设施桶
#（SPX6900 2026-07-25：4 个 CEX 仓错分历史层致曲线返工的教训）
CAMP_COLORS = {
    "项目方":    "tab:red",
    "大庄":      "tab:orange",
    "小庄":      "#d4a017",
    "离场庄":    "tab:brown",
    "刷量地址":   "#e377c2",
    "CEX资金通道": "#8c6d1f",   # 已确证"零 DEX 交互+出口 100% 汇入 CEX"的在途库存，
                               # 与托管仓同色系区分深浅：性质是资金过境不是持仓
                               #（GOAT(Solana) 2026-07-26 定，判据见 playbook-entity-cluster-tiering 资金通道一票否决）
    "CEX托管":   "tab:olive",   # 多所标的必备（AKE(BSC) 2026-07-19 定）
    "疑似CEX托管": "#d6d675",   # CEX 黑箱分层报数"高度疑似"档与确证分开呈现（SPX6900 2026-07-25 定）
    "流动性池":   "tab:blue",
    "其他大户":   "#17becf",
    "历史大户":   "#c49c94",   # 峰值达锚但现仓衰减的历史层（筹码大换血叙事；SPX6900 2026-07-25 定）
    "散户":      "tab:green",
    "桥锁仓":    "#aec7e8",   # 跨链桥锁定=别链流通，非锁仓销毁（多链币必备；SPX6900 2026-07-25 定）
    "锁仓/销毁":  "tab:gray",
    # 旧体系键（兼容；"狙击集团"v5.0 废止）：
    "狙击集团": "tab:purple",
    "庄家TOP1": "tab:red", "庄家其他组": "tab:orange",
    "首30分钟狙击者": "tab:purple", "其他散户": "tab:green",
    "销毁": "#969696",  # EVM legacy 堆叠桶；与“锁仓/销毁”同灰色系
}
# 图2 实体线条：标签前缀 → 语义色（与图1 同色系）；匹配不到按轮换色
ENTITY_COLOR_HINT = [("项目方", "tab:red"), ("大庄", "tab:orange"), ("小庄", "#d4a017"),
                     ("离场庄", "tab:brown"), ("狙击集团", "tab:purple"), ("刷量", "#e377c2"),
                     # 与图1 CAMP_COLORS["CEX资金通道"] 同色；3.35.0 加阵营色时漏同步本表，
                     # 致通道类实体落回轮换色首位 tab:red 与「项目方」撞色（IQ(ETH) 2026-07-26 实测）
                     ("CEX资金通道", "#8c6d1f"), ("CEX托管", "tab:olive"),
                     ("HiIQ", "tab:gray"), ("质押", "tab:gray"), ("锁仓", "tab:gray")]
WHALE_LINE_COLORS = ["tab:red", "tab:orange", "tab:brown", "#c44e9d", "#8c564b"]


def _entity_line_color(label, i, seen_prefix):
    """按标签前缀取语义色；同前缀第 k 个实体亮度递增区分（大庄#1 深、大庄#2 浅）。"""
    for prefix, color in ENTITY_COLOR_HINT:
        if label.startswith(prefix):
            k = seen_prefix.get(prefix, 0)
            seen_prefix[prefix] = k + 1
            if k == 0:
                return color
            r, g, b = to_rgb(color)
            h, l, s = colorsys.rgb_to_hls(r, g, b)
            return colorsys.hls_to_rgb(h, min(0.82, l + 0.15 * k), s)
    return WHALE_LINE_COLORS[i % len(WHALE_LINE_COLORS)]

DATE_FMT_HOUR = mdates.DateFormatter("%m-%d %H:%M")
DATE_FMT_DAY = mdates.DateFormatter("%Y-%m-%d")


def _log_price_axis(ax):
    """价格对数轴（仅图3 用），decade 刻度用纯文本 10^-3 → 0.001 形式规避中文字体上标乱码。"""
    ax.set_yscale("log")
    from matplotlib.ticker import LogLocator, FuncFormatter, NullFormatter
    ax.yaxis.set_major_locator(LogLocator(base=10))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.yaxis.set_minor_formatter(NullFormatter())


def _linear_price_axis(ax):
    """价格线性轴（图2 用）：刻度均匀、直接标数值。
    必须用 FuncFormatter 顶掉默认 ScalarFormatter——后者对 1e-4 级小价格会在轴顶
    放 ×10^n 上标 offset，中文字体下乱码（与对数轴当年规避的是同一个坑）。"""
    from matplotlib.ticker import FuncFormatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))


def _timeaxis(ax, ts, day_only=False):
    span_h = (ts[-1] - ts[0]).total_seconds() / 3600 if len(ts) > 1 else 24
    if day_only or span_h > 24 * 14:
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, round(span_h / 24 / 8))))
        ax.xaxis.set_major_formatter(DATE_FMT_DAY)
    else:
        ax.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=12))
        ax.xaxis.set_major_formatter(DATE_FMT_HOUR)
    for lb in ax.get_xticklabels():
        lb.set_rotation(25)
        lb.set_ha("right")


PRICE_LOG_SWITCH_RATIO = 30  # 图1 价格右轴：max/min 超此倍数自动切对数轴（防早期行情压成地板线）

# 图1 overlay 合并口径线的配色：深紫/深品红/深青——与阵营堆叠色和价格黑线均不撞
# （虚线+白描边，与价格线的"黑色实线"在形状与颜色两个维度都区分开）
OVERLAY_COLORS = ["#4A148C", "#880E4F", "#004D40"]


def select_fig1_series(series):
    """纯函数：把图 1 series 键分为（实绘有序列表, 豁免键, 拒绝键）。

    ``ts`` 是时间轴元数据，不属于阵营键。实绘顺序唯一来自
    ``CAMP_ORDER``；豁免键唯一来自 ``FIG1_EXCLUDED_SERIES``。
    函数不做 IO、不修改输入，供绘图、收据与后续发布闸同源消费。
    """
    keys = list(series)
    rendered = [camp for camp in CAMP_ORDER if camp in series]
    excluded = [key for key in FIG1_EXCLUDED_SERIES if key in series]
    allowed = set(CAMP_ORDER) | set(FIG1_EXCLUDED_SERIES) | {"ts"}
    rejected = [key for key in keys if key not in allowed]
    return rendered, excluded, rejected


def plot_camp_evolution(series, out_png, token, note_supply="占总供应量", price_series=None,
                        overlay=None):
    """图1：各阵营持仓占比演变（全量转账重放后的快照序列）。

    series: {"ts": [datetime,...], "<阵营名>": [pct,...], ...}
            阵营名用 CAMP_ORDER 标准名；缺的阵营不画；锁仓/销毁如有必须传入。
            pct 为占总供应量的百分数（0-100）。多个庄家组自行先合并成
            「庄家TOP1」+「庄家其他组」两条（TOP1=现仓最大的庄家组）。
    price_series: 可选 {"ts": [...], "usd": [...]}——传入则右轴叠加价格黑线（白描边），
            价格+筹码分布对照（v3.12，2026-07-21 用户定，完整分析默认传入）。
            量程 max/min > PRICE_LOG_SWITCH_RATIO 自动切对数轴并在轴标签注明；
            序列自动裁剪到阵营时间范围。不传则保持纯占比图（旧调用/基线重绘兼容）。
    overlay: 可选 [{"label": str, "pct": [...], "color": str（可选）}]——在堆叠图上叠加
            **跨阵营合并口径**的占比虚线（与阵营同左轴，长度须与 ts 对齐）。

            **什么时候必须加**：当某实体的筹码会在两个并列阵营之间来回搬家时，分列的堆叠
            图会让读者把"搬家"误读成"增减持"。最典型的是项目方自挂 LP——币从项目方钱包
            挂进池子，"项目方"色块掉、"流动性池"色块涨，一枚都没买卖，图形却大变。
            KOGE(BSC) 实测：2026-04-22 撤墙日项目方 2,185,639 枚，43 天后的 06-04 挂墙日
            只剩 1,426,049 枚（账面 −76 万），同期池子 +83 万，**两者合计几乎不动**；
            用户正是据分列图问出"项目方在吸筹还是卖币"。加一条"项目方＋流动性池"的合计线，
            歧义当场消失。同类场景：金库↔质押合约、金库↔CEX 托管。
            口径诚实：池中可能混有他方 LP，故该线是**上界**，题注须写明。
            （v3.33 新增，KOGE(BSC) 用户追问驱动，2026-07-25；不传则行为与旧版逐像素一致）
    """
    setup()
    ts = series["ts"]
    camps, _excluded, rejected = select_fig1_series(series)
    if rejected:
        raise ValueError(f"图 1 series 含白名单外键 {rejected}")
    fig, ax = plt.subplots(figsize=(12, 5.6))
    ax.stackplot(ts, [series[c] for c in camps],
                 labels=camps, colors=[CAMP_COLORS[c] for c in camps],
                 alpha=0.92, linewidth=0)
    ax.set_ylim(0, 100)
    ax.set_ylabel(f"{note_supply} %")
    ax.set_title(f"{token} 各阵营持仓占比演变（全量转账重放）")
    ax.margins(x=0)
    _timeaxis(ax, ts)
    handles, labels = ax.get_legend_handles_labels()
    legend_x = 1.01

    if overlay:
        import matplotlib.patheffects as pe
        for i, ov in enumerate(overlay):
            ln = ax.plot(ts, ov["pct"], color=ov.get("color", OVERLAY_COLORS[i % len(OVERLAY_COLORS)]),
                         lw=2.0, ls=(0, (6, 2.5)), zorder=6,
                         path_effects=[pe.withStroke(linewidth=3.6, foreground="white")])
            handles += ln
            labels += [ov["label"]]

    if price_series and price_series.get("ts"):
        # 裁剪到阵营时间范围，防价格序列更长把 x 轴撑出堆叠区
        pairs = [(t, v) for t, v in zip(price_series["ts"], price_series["usd"])
                 if ts[0] <= t <= ts[-1]]
        if pairs:
            import matplotlib.patheffects as pe
            pts, pusd = zip(*pairs)
            ax2 = ax.twinx()
            ln = ax2.plot(pts, pusd, color="black", lw=1.5, alpha=0.9, zorder=5,
                          path_effects=[pe.withStroke(linewidth=3.0, foreground="white")])
            pos = [v for v in pusd if v > 0]
            use_log = bool(pos) and max(pos) / min(pos) > PRICE_LOG_SWITCH_RATIO
            if use_log:
                _log_price_axis(ax2)
            else:
                _linear_price_axis(ax2)
            # 单位注在图例条目里，不用右轴 ylabel——外置图例与 ylabel 在同一位置会重叠
            handles += ln
            labels += ["价格 USD(对数,右轴)" if use_log else "价格 USD(右轴)"]
            # 图例右移给右轴刻度数字让位（1.01 会压住线性轴的多位小数刻度）
            legend_x = 1.075

    ax.legend(handles, labels, loc="center left", bbox_to_anchor=(legend_x, 0.5), framealpha=0.95)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    return out_png


def plot_whale_vs_price(whale_series, price_series, out_png, token):
    """图2：庄级实体持仓变动 vs 价格（判断建仓后是否加减仓、拉升期有没有出货）。

    whale_series: [{"label": "项目方", "ts": [...], "pct": [...]},
                   {"label": "大庄#1", "ts": [...], "pct": [...]}, ...]
                  label 用标签制（项目方/大庄#N/小庄#N/离场庄#N），
                  pct=占总供应量百分数；线色按前缀自动取语义色。
                  标签实体各画一线；线超 8 条时可将持仓较小的实体合并成一条避免花屏。
    price_series: {"ts": [...], "usd": [...]}
    """
    setup()
    fig, ax = plt.subplots(figsize=(12, 5.6))
    seen = {}
    for i, w in enumerate(whale_series):
        ax.plot(w["ts"], w["pct"], color=_entity_line_color(w["label"], i, seen),
                lw=2.4, label=w["label"], zorder=3)
    ax.set_ylabel("实体持仓占总供应 %", color="tab:red")
    ax.tick_params(axis="y", labelcolor="tab:red")
    ax.set_ylim(bottom=0)
    ax.margins(x=0.01)

    ax2 = ax.twinx()
    ax2.plot(price_series["ts"], price_series["usd"], color="tab:blue", lw=1.4,
             alpha=0.85, label="价格", zorder=2)
    _linear_price_axis(ax2)
    ax2.set_ylabel("价格 USD", color="tab:blue")
    ax2.tick_params(axis="y", labelcolor="tab:blue")

    ax.set_title(f"{token} 庄级实体持仓变动 vs 价格（全量转账逐笔重放）")
    _timeaxis(ax, price_series["ts"], day_only=True)
    h1, l1 = ax.get_legend_handles_labels()
    ax.legend(h1, l1, loc="upper right", framealpha=0.95)
    fig.tight_layout()
    fig.savefig(out_png, dpi=150)
    plt.close(fig)
    return out_png


def _circled(i):
    """1→① … 20→⑳，超出用 (21) 文本。"""
    return chr(0x2460 + i - 1) if 1 <= i <= 20 else f"({i})"


def plot_price_events(price_series, volume_series, events, out_png, token, granularity="小时线"):
    """图3：全历史价格与关键事件（上 panel 价格对数+编号事件竖线，下 panel 成交额柱）。

    granularity: 标题括注的数据粒度（"小时线"/"日线"等，v3.9 参数化——老币日线数据时勿再硬扛"小时线"标题）
    price_series:  {"ts": [...], "usd": [...]}（K线 close 即可，小时粒度典型）
    volume_series: {"ts": [...], "usd": [...]}（成交额）
    events: [{"ts": datetime, "desc": "07-06 18:35 — 代币铸造/交易开始；…"}]
            desc 不带编号（本函数自动编 ①②③…）。同一时点多件事合并进一条 desc，
            用「；」分隔。事件类型参考：铸造/开盘、≥5%供应单笔转移、庄家组首建仓
            或大幅加减仓、单根K线 |涨跌|≥40%、成交额突增、锁仓/销毁、迁移/上所。
    返回：事件清单文本行 ["① 07-06 18:35 — …", ...]，报告 md 里紧跟图片贴出。
    """
    setup()
    fig, (ax, axv) = plt.subplots(2, 1, figsize=(12, 7.2), sharex=True,
                                  gridspec_kw={"height_ratios": [2.3, 1], "hspace": 0.08})
    ax.plot(price_series["ts"], price_series["usd"], color="tab:blue", lw=1.6)
    _log_price_axis(ax)
    ax.set_ylabel("价格 USD(对数)")
    ax.set_title(f"{token} 全历史价格与关键事件（{granularity}）")
    ax.margins(x=0.01)

    lines = []
    for i, ev in enumerate(sorted(events, key=lambda e: e["ts"]), 1):
        ax.axvline(ev["ts"], color="tab:orange", ls="--", lw=1.2, alpha=0.85)
        ax.annotate(_circled(i), (ev["ts"], 1.03), xycoords=("data", "axes fraction"),
                    ha="center", fontsize=13, color="tab:orange",
                    bbox=dict(boxstyle="circle,pad=0.08", fc="white", ec="tab:orange", lw=1.2))
        lines.append(f"{_circled(i)} {ev['desc']}")

    if len(volume_series["ts"]) > 1:
        w = (volume_series["ts"][1] - volume_series["ts"][0]).total_seconds() / 86400 * 0.8
    else:
        w = 0.03
    axv.bar(volume_series["ts"], volume_series["usd"], width=w, color="tab:blue", alpha=0.55)
    axv.set_yscale("log")
    axv.set_ylabel("成交额 USD")
    _timeaxis(axv, volume_series["ts"], day_only=False)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return lines


# ── 自测：合成数据出三张样图（风格基准，不代表任何真实代币）──────────
def _demo(outdir):
    os.makedirs(outdir, exist_ok=True)
    t0 = datetime(2026, 7, 6, 18, 0)
    n = 110
    ts = [t0 + timedelta(hours=i) for i in range(n)]

    # 图1 合成（标签体系）：大庄开盘 2 小时冲到 55% 后平线；离场庄从 25% 衰减
    proj = [12.0 for _ in range(n)]
    big = [min(55, 55 * min(1, i / 2)) for i in range(n)]
    small = [min(6.0, 6.0 * min(1, i / 6)) for i in range(n)]
    pool = [3.0 + 1.2 * math.sin(i / 9) + (1.5 if i < 8 else 0) for i in range(n)]
    snip = [max(1.2, 25 * math.exp(-i / 7)) for i in range(n)]
    whale_rest = [2.5 for _ in range(n)]
    rest = [max(0, 100 - a - b - c - d - e - f)
            for a, b, c, d, e, f in zip(proj, big, small, pool, snip, whale_rest)]

    # 价格合成：1.5e-4 → 冲高 1.5e-2 → 回落 6e-3
    price = []
    for i in range(n):
        base = 1.5e-4 * math.exp(i / 9) if i < 30 else 1.5e-2 * math.exp(-(i - 30) / 90)
        price.append(min(base, 1.5e-2) * (1 + 0.18 * math.sin(i / 3.3)))

    plot_camp_evolution({"ts": ts, "项目方": proj, "大庄": big, "小庄": small,
                         "离场庄": snip, "流动性池": pool,
                         "其他大户": whale_rest, "散户": rest},
                        os.path.join(outdir, "demo_fig1_camp_evolution.png"), "DEMO",
                        price_series={"ts": ts, "usd": price})
    plot_whale_vs_price(
        [{"label": "项目方", "ts": ts, "pct": proj},
         {"label": "大庄#1", "ts": ts, "pct": big},
         {"label": "小庄#1", "ts": ts, "pct": small},
         {"label": "离场庄#1", "ts": ts, "pct": snip}],
        {"ts": ts, "usd": price},
        os.path.join(outdir, "demo_fig2_whale_vs_price.png"), "DEMO")

    vol = [10 ** (4 + 2 * abs(math.sin(i / 5.5)) + (1 if 26 < i < 32 else 0)) for i in range(n)]
    lines = plot_price_events(
        {"ts": ts, "usd": price}, {"ts": ts, "usd": vol},
        [{"ts": ts[1], "desc": "07-06 19:00 — 代币铸造/交易开始；单笔转移 5.5 亿枚【总量 55%】→ 大庄#1"},
         {"ts": ts[6], "desc": "07-07 00:00 — 单根 -48%"},
         {"ts": ts[28], "desc": "07-07 22:00 — 放量 1.8M USD"},
         {"ts": ts[90], "desc": "07-10 12:00 — 小庄#1 加仓 500 万枚【总量 0.5%】"}],
        os.path.join(outdir, "demo_fig3_price_events.png"), "DEMO")
    print("\n".join(lines))
    print(f"[OK] 3 charts -> {outdir}")


if __name__ == "__main__":
    _demo(sys.argv[1] if len(sys.argv) > 1 else "./demo_charts")
