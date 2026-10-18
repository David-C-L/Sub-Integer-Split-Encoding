#!/usr/bin/env python3
"""Fig. 3 (sis_encode_pipeline), final rotated version (v5) as placed in the paper.

Data: derived/sec3_plan_breakdown_8sec_addr.csv (section widths, encodings and bits per value read off the SIS
tree in data/addr_toplevel_snowflake/comp_snowflake_toplevel.csv.log) and data/sec3_pipeline/snowflake_first16.txt
(first 16 Snowflake IDs of the column; the first 8 are drawn). Rendered in the tol_hc palette.
Changes only: (1) each ID is a horizontal row of 64 bits, bit 63 left, so sections are vertical bands and
the three steps stack top to bottom; (2) tol_hc encoding colours, bits stay grey; (3) no panel boxes;
(4) legend split into an Encodings group and a Bit information group.
All cells are vector Rectangles (no imshow). Everything is drawn in points; page = placed size.
Run: python3 scripts/plot/make_sis_encode_pipeline_v5.py   (writes <out>/sis_encode_pipeline_v5.pdf)
"""
import csv, itertools, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["SIS_PALETTE"] = "tol_hc"   # this figure uses tol_hc even though Sec. 1-4 are rendered in palette B
import paperstyle  # noqa: E402
assert paperstyle.PALETTE == "tol_hc"
import artifact_paths as AP  # noqa: E402

PLAN_CSV = os.path.join(AP.DERIVED, "sec3_plan_breakdown_8sec_addr.csv")
IDS = os.path.join(AP.DATA, "sec3_pipeline", "snowflake_first16.txt")
OUT = AP.OUT

COL_PT, PAD = 241.14, 1.0
INK, MUTED = "#1A1A1A", "#555555"
FS = 8
# Tol muted hues, deliberately disjoint from the SIS/OpenZL/Zstd colours of paperstyle tol_hc.
ENC = {
    "FrequencyPartition": ("#44AA99", "Frequency partitioning"),   # Tol muted teal
    "RLE": ("#DDCC77", "Run-length"),                               # Tol muted sand
    "SimdForBitpack": ("#CC6677", "FOR bit-packing"),               # Tol muted rose
    "Constant": ("#332288", "Constant"),                            # Tol muted indigo
}
ON, OFF, RAWEDGE = "#6B6B6B", "#E4E4E4", "#8A8A8A"

paperstyle.apply_rcparams()
plt.rcParams.update({"axes.grid": False, "font.size": FS, "text.color": INK})


def tint(h, a):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return (r + (1 - r) * a, g + (1 - g) * a, b + (1 - b) * a)


def shade(h, f=0.7):
    return tuple(int(h[i:i + 2], 16) / 255 * f for i in (1, 3, 5))


sections = []
with open(PLAN_CSV) as f:
    for r in csv.DictReader(l for l in f if not l.startswith("#")):
        if r["column"] != "snowflake" or r["arm"] != "SIS/realNested":
            continue
        if r["section"] == "whole":
            total_bpv = float(r["bits_per_elem"]); continue
        lo, hi = (int(v) for v in r["bits"].split("-"))
        sections.append(dict(lo=lo, hi=hi, encoding=r["encoding"], bpv=float(r["bits_per_elem"])))
sections.sort(key=lambda s: -s["hi"])            # bit 63 side first (left)
values = [int(v) for v in open(IDS).read().split()][:8]   # first 8 IDs shown
assert len(values) == 8 and sum(s["hi"] - s["lo"] + 1 for s in sections) == 64 and len(sections) == 8

S, GAP, RH = 2.7, 0.0, 2.6     # pt per bit (x), gap between sections, pt per ID row (y)
LEFT = 64.0
X0 = PAD + LEFT
BODY = len(values) * RH
LBL = 9.0                       # label row pitch
BLK_GAP = 9.0
BH = 14.0
LROW = 9.0

H_TICK = 9.0
h1 = H_TICK + BODY
h2 = BODY + 3 + 2 * LBL
h3 = BH + 3 + 2 * LBL
h_leg = 3 * LROW
H = PAD + h1 + BLK_GAP + h2 + BLK_GAP + h3 + 6 + h_leg + PAD
fig = plt.figure(figsize=(COL_PT / 72, H / 72))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, COL_PT); ax.set_ylim(0, H); ax.axis("off")


def rect(x, y, w, h, face, edge="none", lw=0.4, ls="-"):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linewidth=lw, linestyle=ls))


def cell(x, y, w, h, face):
    rect(x + 0.1, y + 0.1, w - 0.2, h - 0.2, face)


def step_label(ytop, num, text, sub):
    yc = ytop - 4.5
    ax.text(PAD + 4, yc, num, ha="center", va="center", fontsize=7, fontweight="bold", color="white",
            bbox=dict(boxstyle="circle,pad=0.15", facecolor=INK, edgecolor="none"))
    ax.text(PAD + 10, yc, text, ha="left", va="center", fontsize=FS, fontweight="bold")
    for i, line in enumerate(sub):
        ax.text(PAD + 10, yc - 9.0 * (i + 1), line, ha="left", va="center", fontsize=FS, color=MUTED)


def down_arrow(x, y0, y1):
    ax.annotate("", xy=(x, y1), xytext=(x, y0),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.9, mutation_scale=8, shrinkA=0, shrinkB=0))


def tw(text):
    return sum(4.0 if ch in "\u2013." else 5.1 for ch in text) + 1.5


def place(items):
    """Two label rows. Row 0 (next to the bars) has no leader; row 1 has a leader that must not cross a row-0
    label. Search all assignments, keep a feasible one with the most row-0 labels."""
    n = len(items)
    W = [tw(t) for _, t, _ in items]

    def clamp(x, w):
        return min(max(x, PAD + w / 2), COL_PT - PAD - w / 2)

    best = None
    for mask in range(2 ** n):
        r0 = [i for i in range(n) if mask >> i & 1]
        pos = {i: clamp(items[i][0], W[i]) for i in r0}
        if any(abs(pos[i] - pos[j]) < (W[i] + W[j]) / 2 + 1 for i, j in itertools.combinations(r0, 2)):
            continue
        r1 = [i for i in range(n) if i not in r0]
        if any(abs(items[i][0] - pos[j]) <= W[j] / 2 + 0.5 for i in r1 for j in r0):
            continue
        p1 = {i: clamp(items[i][0], W[i]) for i in r1}
        for _ in range(60):
            for a_, b_ in zip(r1, r1[1:]):
                need = (W[a_] + W[b_]) / 2 + 1
                if p1[b_] - p1[a_] < need:
                    d = (need - (p1[b_] - p1[a_])) / 2
                    p1[a_] -= d; p1[b_] += d
        if any(abs(p1[i] - items[i][0]) > W[i] / 2 - 1 or p1[i] - W[i] / 2 < PAD - 0.1 or p1[i] + W[i] / 2 > COL_PT - PAD + 0.1 for i in r1):
            continue
        if best is None or len(r0) > best[0]:
            best = (len(r0), {**{i: (0, pos[i]) for i in r0}, **{i: (1, p1[i]) for i in r1}})
    assert best, "no feasible label placement"
    return best[1]


def draw_labels(items, y_anchor):
    rows = place(items)
    for i, (xc, t, _) in enumerate(items):
        r, xt = rows[i]
        yl = y_anchor - 3 - LBL * (0.5 + r)
        if r:
            ax.plot([xc, xc], [y_anchor - 0.6, yl + 4.2], color=MUTED, lw=0.4)
        ax.text(xt, yl, t, ha="center", va="center", fontsize=FS)


# ---- step 1 -------------------------------------------------------------------
g_top = H - PAD - H_TICK
FIELD = "#333333"
FS_F = float(os.environ.get("FS_F", "7"))
SEQ_NUDGE = float(os.environ.get("SEQ_NUDGE", "0"))
ftexts = {}
# Snowflake fields as span lines over the grid (bit 63 unused: only a light tick). Spans are x-aligned with the bits.
yl, ytxt = g_top + 1.0, g_top + 3.8
ax.plot([X0 + S / 2] * 2, [yl, yl + 1.8], color="#AAAAAA", lw=0.5)          # bit 63, unused
ftexts["63"] = ax.text(X0 + S / 2, ytxt, "63", ha="center", va="baseline", fontsize=FS_F, color=MUTED)
ftexts["0"] = ax.text(X0 + 63.5 * S, ytxt, "0", ha="center", va="baseline", fontsize=FS_F, color=MUTED)
for name, hi, lo in (("timestamp", 62, 22), ("machine", 21, 12), ("seq.", 11, 0)):
    xa = X0 + (63 - hi) * S + 0.4
    xb = X0 + (63 - lo + 1) * S - 0.4
    ax.plot([xa, xa, xb, xb], [yl + 1.8, yl, yl, yl + 1.8], color=FIELD, lw=0.6, solid_joinstyle="miter")
    ftexts[name] = ax.text((xa + xb) / 2 + (SEQ_NUDGE if name == "seq." else 0), ytxt, name, ha="center", va="baseline", fontsize=FS_F, color=FIELD)
for row, v in enumerate(values):
    for bit in range(64):
        cell(X0 + (63 - bit) * S, g_top - (row + 1) * RH, S, RH, ON if (v >> bit) & 1 else OFF)
step_label(g_top, "1", "Values", ["first 8 IDs"])
y1_end = g_top - BODY

# ---- step 2 -------------------------------------------------------------------
b2_top = y1_end - BLK_GAP
band = {}
x = X0
for s in sections:
    nb = s["hi"] - s["lo"] + 1
    band[s["hi"]] = (x, x + nb * S)
    c = ENC[s["encoding"]][0]
    for row, v in enumerate(values):
        for bit in range(s["lo"], s["hi"] + 1):
            cell(x + (s["hi"] - bit) * S, b2_top - (row + 1) * RH, S, RH, c if (v >> bit) & 1 else tint(c, 0.82))
    rect(x, b2_top - BODY, nb * S, BODY, "none", shade(c, 0.55), 1.1)
    x += nb * S + GAP
b2_bot = b2_top - BODY
draw_labels([((band[q["hi"]][0] + band[q["hi"]][1]) / 2, f"{q['hi']}\u2013{q['lo']}", q["hi"] - q["lo"] + 1) for q in sections], b2_bot)
step_label(b2_top, "2", "Decompose", ["8 sections"])
y2_end = b2_bot - 3 - 2 * LBL

# ---- step 3 -------------------------------------------------------------------
b3_top = y2_end - BLK_GAP
for i, s in enumerate(sections):
    x0, x1 = band[s["hi"]]
    c = ENC[s["encoding"]][0]
    raw = s["hi"] - s["lo"] + 1
    rect(x0, b3_top - BH, raw * S, BH, "white", RAWEDGE, 0.5, (0, (2, 1.2)))
    rect(x0, b3_top - BH, max(s["bpv"] * S, 0.5), BH, c, shade(c), 0.4)
draw_labels([((band[q["hi"]][0] + band[q["hi"]][1]) / 2, f"{q['bpv']:.2f}", q["hi"] - q["lo"] + 1) for q in sections], b3_top - BH)
step_label(b3_top, "3", "Encode", ["bits/value", f"total {total_bpv:.2f}"])
y3_end = b3_top - BH - 3 - 2 * LBL
down_arrow(PAD + 4, y1_end - 0.5, b2_top + 0.5)
down_arrow(PAD + 4, b2_bot - 0.5, b3_top + 0.5)

# ---- legend: two side-by-side groups -----------------------------------------------
def sw(face, edge="none", lw=0.4, ls="-"):
    return lambda x, yc: rect(x, yc - 3, 8, 6, face, edge, lw, ls)


def group(x, ytop, heading, items):
    ax.text(x, ytop - LROW / 2, heading, ha="left", va="center", fontsize=FS, fontweight="bold")
    for r, (draw, text) in enumerate(items):
        yc = ytop - LROW / 2 - (r + 1) * LROW
        draw(x, yc)
        ax.text(x + 11, yc, text, ha="left", va="center", fontsize=FS)


leg_top = y3_end - 5
ax.plot([PAD, COL_PT - PAD], [leg_top + 2.5, leg_top + 2.5], color="#BBBBBB", lw=0.5)
k = lambda key: sw(ENC[key][0], shade(ENC[key][0]))
fig.canvas.draw()
rend = fig.canvas.get_renderer()
inv = ax.transData.inverted()


def text_w(t, bold=False):
    tt = ax.text(0, 0, t, fontsize=FS, fontweight="bold" if bold else "normal")
    w = tt.get_window_extent(rend).transformed(inv).width
    tt.remove()
    return w


# Encodings: heading left, 2x2 grid (swatch + label)
ax.text(PAD, leg_top - LROW / 2, "Encodings", ha="left", va="center", fontsize=FS, fontweight="bold")
c1 = X0
c2 = c1 + 11 + max(text_w(ENC["FrequencyPartition"][1]), text_w(ENC["SimdForBitpack"][1])) + 8
for (key, cx, r) in (("FrequencyPartition", c1, 0), ("Constant", c2, 0), ("SimdForBitpack", c1, 1), ("RLE", c2, 1)):
    yc = leg_top - LROW / 2 - r * LROW
    k(key)(cx, yc)
    ax.text(cx + 11, yc, ENC[key][1], ha="left", va="center", fontsize=FS)
assert c2 + 11 + text_w("Run-length") <= COL_PT - PAD and c2 + 11 + text_w("Constant") <= COL_PT - PAD
# separator, then Bit information: heading + one row of three
ysep = leg_top - 2 * LROW - 1
ax.plot([PAD, COL_PT - PAD], [ysep + 0.5, ysep + 0.5], color="#DDDDDD", lw=0.4)
yb = ysep - LROW / 2 - 0.5
ax.text(PAD, yb, "Bit info", ha="left", va="center", fontsize=FS, fontweight="bold")
x = PAD + text_w("Bit info", True) + 8
for draw, t in ((sw(ON), "bit = 1"), (sw(OFF), "bit = 0"), (sw("white", RAWEDGE, 0.5, (0, (2, 1.2))), "raw section width")):
    draw(x, yb)
    ax.text(x + 11, yb, t, ha="left", va="center", fontsize=FS)
    x += 11 + text_w(t) + 8
assert x - 8 <= COL_PT - PAD, x
assert yb - LROW / 2 >= PAD - 0.6, (yb, PAD)

fig.canvas.draw()
_r = fig.canvas.get_renderer(); _inv = ax.transData.inverted()
_e = {k: t.get_window_extent(_r).transformed(_inv) for k, t in ftexts.items()}
print(f"field font {FS_F} pt; gaps: timestamp-machine {_e['machine'].x0-_e['timestamp'].x1:.1f}, machine-seq {_e['seq.'].x0-_e['machine'].x1:.1f}, seq-0 {_e['0'].x0-_e['seq.'].x1:.1f}, 63-timestamp {_e['timestamp'].x0-_e['63'].x1:.1f}; machine {_e['machine'].width:.1f} pt vs span {10*S:.1f}; right edge {max(e.x1 for e in _e.values()):.1f}")
fig.savefig(os.path.join(OUT, "sis_encode_pipeline_v5.pdf"))
print(f"size {COL_PT:.2f} x {H:.2f} pt")
for s in sections:
    print(f"{s['hi']}-{s['lo']} {s['encoding']} {s['bpv']:.2f}")
print(f"total {total_bpv:.2f}")
