"""Analyze a pilot run. Usage: python analyze.py --run pilot

Writes results/<run>/summary.md and figures/<run>_overview.png:
  A. spread of false headlines by condition
  B. indirect protection: unprotected agents who ever saw the false headline
  C. knowing vs doing: agents spot fakes on the MIST yet share them in the feed
"""
import argparse
import json
import os
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from pilot.items import ITEMS
from pilot.sim import build_graph, hub_set

# Reference dataviz palette (light). Control is the gray baseline; the prebunking
# conditions take categorical slots 1-3 in fixed order. Panel C uses neutrals only,
# so no hue means two different things in one figure.
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
COND = {
    "control": ("No prebunking", "#8a8984"),
    "random30": ("30% random users prebunked", "#2a78d6"),
    "hubs30": ("30% hubs prebunked", "#eb6834"),
    "hubs30_late": ("30% hubs prebunked late (round 3)", "#1baf7a"),
}
SHORT = {"control": "None", "random30": "Random", "hubs30": "Hubs", "hubs30_late": "Hubs, late"}
TEST_C, FEED_C = "#c9c8c3", "#3d3c39"


def ci95(x):
    x = np.asarray(x, float)
    return 0.0 if len(x) < 2 else stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))


def style(ax, ygrid=True):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)
    if ygrid:
        ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def protection_sets(rep, item, n=100, frac=0.30, n_seeds=3):
    """Rebuild seeds and prebunked sets exactly as pilot/sim.py does."""
    g = build_graph(n, rep)
    hubs = hub_set(g, frac)
    rng = random.Random(f"{rep}-{item}")
    seeds = set(rng.sample(sorted(v for v in g.nodes if v not in hubs), n_seeds))
    rnd = set(random.Random(f"rand-{rep}").sample(sorted(v for v in g.nodes if v not in seeds), int(round(frac * n))))
    return g, seeds, {"control": set(), "random30": rnd, "hubs30": hubs - seeds, "hubs30_late": hubs - seeds}


def main(run):
    d = os.path.join("results", run)
    casc = pd.read_csv(os.path.join(d, "cascades.csv"))
    dec = pd.read_csv(os.path.join(d, "decisions.csv"))
    mist = pd.read_csv(os.path.join(d, "mist.csv"))
    meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
    per = pd.DataFrame(json.load(open(os.path.join(d, "personas.json"), encoding="utf-8")))
    a = meta["args"]
    casc["pct"] = 100 * casc["shared"] / casc["n"]
    conds = [c for c in COND if c in set(casc["condition"])]
    rounds = int(casc["round"].max())
    final = casc[casc["round"] == rounds]
    fake_items = sorted(final[final.veracity == "fake"]["item"].unique())

    # 1. Final reach, all headlines
    rows = []
    for ver in ("fake", "real"):
        base = final[(final.veracity == ver) & (final.condition == "control")]["pct"].mean()
        for c in conds:
            x = final[(final.veracity == ver) & (final.condition == c)]["pct"]
            rows.append({"headlines": ver, "condition": COND[c][0], "final_reach_pct": round(x.mean(), 1),
                         "ci95": round(ci95(x), 1), "n_cascades": len(x),
                         "change_vs_control_pct": None if c == "control" or base == 0 else round(100 * (x.mean() - base) / base)})
    reach = pd.DataFrame(rows)

    # 2. Paired tests on false headlines (same network, seeds and headline across conditions)
    piv = final[final.veracity == "fake"].pivot_table(index=["rep", "item"], columns="condition", values="pct")
    tests = []
    for x, y in (("random30", "control"), ("hubs30", "control"), ("hubs30_late", "control"),
                 ("hubs30", "random30"), ("hubs30_late", "hubs30")):
        if x in piv and y in piv:
            diff = piv[x] - piv[y]
            w = stats.wilcoxon(piv[x], piv[y]) if (diff != 0).any() else None
            tests.append({"comparison": f"{COND[x][0]} vs {COND[y][0].lower()}", "diff_pts": round(diff.mean(), 1),
                          "ci95": f"[{diff.mean() - ci95(diff):+.1f}, {diff.mean() + ci95(diff):+.1f}]",
                          "lower_in": f"{int((diff < 0).sum())}/{len(diff)}",
                          "wilcoxon_p": None if w is None else float(f"{w.pvalue:.2g}")})
    tests = pd.DataFrame(tests)

    # 3. Indirect protection: agents who were never prebunked (and did not seed the rumor)
    herd = []
    for rep in sorted(int(r) for r in casc.rep.unique()):
        for item in fake_items:
            g, seeds, sets = protection_sets(rep, item, a["agents"], a["frac"], a["seeds"])
            for c in conds:
                dd = dec[(dec.rep == rep) & (dec["item"] == item) & (dec.condition == c)]
                ev, sh = set(dd.agent), set(dd[dd.share == 1].agent)
                unprot = [v for v in g.nodes if v not in sets[c] and v not in seeds]
                herd.append({"rep": rep, "item": item, "condition": c,
                             "exposed": 100 * np.mean([v in ev for v in unprot]),
                             "shared": 100 * np.mean([v in sh for v in unprot])})
    herd = pd.DataFrame(herd)
    herd_tab = herd.groupby("condition").agg(exposed=("exposed", "mean"), exposed_ci=("exposed", ci95),
                                             shared=("shared", "mean")).reindex(conds).round(1)
    herd_tab.index = [COND[c][0] for c in herd_tab.index]

    # 4. Direct effect: share rate when exposed, prebunked vs not
    fk = dec[dec.veracity == "fake"]
    direct = pd.DataFrame([
        {"agents": "Not prebunked (all conditions)", "share_rate_pct": round(100 * fk[fk.inoculated == 0].share.mean(), 1),
         "mean_belief": round(fk[fk.inoculated == 0].believe.mean(), 2), "decisions": int((fk.inoculated == 0).sum())},
        {"agents": "Prebunked (active)", "share_rate_pct": round(100 * fk[fk.inoculated == 1].share.mean(), 1),
         "mean_belief": round(fk[fk.inoculated == 1].believe.mean(), 2), "decisions": int((fk.inoculated == 1).sum())}])

    # 5. Traits and knowing vs doing (control condition, false headlines)
    ctrl = fk[fk.condition == "control"].merge(per[["id", "conspiracy", "thinking", "sharing"]], left_on="agent", right_on="id")
    m = mist.dropna(subset=["correct"])
    plain = m[m.inoculated == 0]
    fake_test = plain[plain.veracity == "fake"].merge(per[["id", "conspiracy"]], left_on="agent", right_on="id")
    levels = [l for l in ("low", "moderate", "high") if l in set(ctrl.conspiracy)]
    kd = pd.DataFrame({
        "called_fake_on_MIST_pct": fake_test.groupby("conspiracy")["correct"].mean().mul(100),
        "shared_in_feed_pct": ctrl.groupby("conspiracy")["share"].mean().mul(100),
        "feed_decisions": ctrl.groupby("conspiracy").size()}).reindex(levels).round(1)
    traits = {t: ctrl.groupby(t).agg(share_rate=("share", "mean"), belief=("believe", "mean"), n=("share", "size")).round(2)
              for t in ("conspiracy", "thinking", "sharing")}

    # 6. MIST: agents vs humans, and does the score predict sharing?
    human = {v: np.mean([i["human_pct"] for i in ITEMS.values() if i["veracity"] == v]) for v in ("fake", "real")}
    agent_acc = plain.groupby("veracity")["correct"].mean() * 100
    pre_acc = m[m.inoculated == 1].groupby("veracity")["correct"].mean() * 100
    item_acc = plain.groupby("item")["correct"].mean() * 100
    hp = pd.Series({k: v["human_pct"] for k, v in ITEMS.items()})
    r_items, p_items = stats.pearsonr(item_acc, hp.loc[item_acc.index])
    tot = plain.groupby("agent")["correct"].sum()
    ic = plain.set_index(["agent", "item"])["correct"]
    pv = fk[fk.condition == "control"].copy()
    pv["mist_loo"] = [tot.get(x, np.nan) - ic.get((x, it), 0) for x, it in zip(pv.agent, pv["item"])]
    pv = pv.dropna(subset=["mist_loo"])
    r_pv, p_pv = stats.pointbiserialr(pv["share"], pv["mist_loo"])

    # ---------------- Figure ----------------
    fig = plt.figure(figsize=(14, 4.6), facecolor=SURFACE)
    gs = fig.add_gridspec(1, 3, wspace=0.32, width_ratios=[1.15, 1, 1])
    ax = fig.add_subplot(gs[0, 0])
    style(ax)
    for c in conds:
        g = casc[(casc.veracity == "fake") & (casc.condition == c)].groupby("round")["pct"]
        mu, ci = g.mean(), g.apply(ci95)
        ax.fill_between(mu.index, mu - ci, mu + ci, color=COND[c][1], alpha=0.10, linewidth=0)
        ax.plot(mu.index, mu, color=COND[c][1], linewidth=2, label=COND[c][0])
        ax.text(rounds + 0.15, mu.iloc[-1], f"{mu.iloc[-1]:.0f}%", color=INK2, fontsize=8.5, va="center")
    ax.set_xlim(0, rounds + 0.9)
    ax.set_ylim(0, None)
    ax.set_xlabel("Round", color=INK2, fontsize=9)
    ax.set_ylabel("Agents who shared the false headline (%)", color=INK2, fontsize=9)
    ax.set_title("A. Prebunking slows the rumor", loc="left", color=INK, fontsize=11, fontweight="bold")

    ax = fig.add_subplot(gs[0, 1])
    style(ax)
    hb = herd.groupby("condition")["exposed"]
    xs = np.arange(len(conds))
    vals = [hb.mean()[c] for c in conds]
    errs = [ci95(herd[herd.condition == c]["exposed"]) for c in conds]
    ax.bar(xs, vals, width=0.62, color=[COND[c][1] for c in conds], edgecolor=SURFACE, linewidth=2)
    ax.errorbar(xs, vals, yerr=errs, fmt="none", ecolor=INK2, elinewidth=1, capsize=3)
    for x, v, e in zip(xs, vals, errs):
        ax.text(x, v + e + 2, f"{v:.0f}%", ha="center", color=INK, fontsize=9)
    ax.set_xticks(xs, [SHORT[c] for c in conds])
    ax.set_ylim(0, 100)
    ax.set_ylabel("Never-prebunked agents who saw it (%)", color=INK2, fontsize=9)
    ax.set_title("B. It protects agents who were never prebunked", loc="left", color=INK, fontsize=11, fontweight="bold")

    ax = fig.add_subplot(gs[0, 2])
    style(ax)
    xs = np.arange(len(levels))
    w = 0.36
    b1 = ax.bar(xs - w / 2 - 0.01, kd["called_fake_on_MIST_pct"], width=w, color=TEST_C, edgecolor=SURFACE, linewidth=2,
                label="On the MIST test: called fakes fake")
    b2 = ax.bar(xs + w / 2 + 0.01, kd["shared_in_feed_pct"], width=w, color=FEED_C, edgecolor=SURFACE, linewidth=2,
                label="In the feed: shared the false headline")
    for bars in (b1, b2):
        for r in bars:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 2, f"{r.get_height():.0f}%", ha="center", color=INK, fontsize=9)
    ax.set_xticks(xs, [f"{l.capitalize()}" for l in levels])
    ax.set_xlabel("Agent's conspiracy mentality", color=INK2, fontsize=9)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("%", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper center", ncol=1, bbox_to_anchor=(0.45, -0.15))
    ax.set_title("C. Knowing a headline is fake is not enough", loc="left", color=INK, fontsize=11, fontweight="bold")

    h, l = fig.axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, frameon=False, fontsize=9, labelcolor=INK2, bbox_to_anchor=(0.5, 1.05))
    n_casc = len(piv)
    fig.text(0.01, -0.2, f"Pilot. {a['model']}, {a['agents']} agents, scale-free networks, {n_casc} matched cascades per condition "
             f"({a['reps']} networks x {len(fake_items)} MIST-20 false headlines). Bars and bands: 95% CI. C: no-prebunking condition.",
             color=INK2, fontsize=8)
    os.makedirs("figures", exist_ok=True)
    fig_path = os.path.join("figures", f"{run}_overview.png")
    fig.savefig(fig_path, dpi=200, bbox_inches="tight", facecolor=SURFACE)

    # ---------------- Summary ----------------
    u = meta["usage"]
    L = [f"# Pilot results: {run}", "",
         f"Model {a['model']} | {a['agents']} agents | {a['reps']} networks | {rounds} rounds | {a['frac']:.0%} prebunked | "
         f"{u['calls']} API calls, {u['failures']} failures", "",
         "## 1. Final reach (share of all agents who shared the headline)", "", reach.to_markdown(index=False), "",
         "## 2. Paired tests, false headlines (same network, seeds and headline in every condition)", "",
         tests.to_markdown(index=False), "",
         "## 3. Indirect protection: agents who were never prebunked and did not seed the rumor", "",
         herd_tab.rename(columns={"exposed": "saw_it_pct", "exposed_ci": "ci95", "shared": "shared_it_pct"}).to_markdown(), "",
         "## 4. Direct effect: share rate once exposed (false headlines)", "", direct.to_markdown(index=False), "",
         "## 5. Knowing vs doing, by conspiracy mentality (no-prebunking condition)", "", kd.to_markdown(), "",
         "Other traits (share rate when exposed):", ""]
    for t in ("thinking", "sharing"):
        L += [traits[t].to_markdown(), ""]
    L += ["## 6. MIST-20: agents vs humans", "",
          f"Fake headlines spotted: humans {human['fake']:.1f}%, agents {agent_acc['fake']:.1f}%, agents after prebunk {pre_acc['fake']:.1f}%",
          f"Real headlines accepted: humans {human['real']:.1f}%, agents {agent_acc['real']:.1f}%, agents after prebunk {pre_acc['real']:.1f}%",
          f"Item difficulty, agents vs humans: r = {r_items:.2f} (p = {p_items:.2g})",
          f"MIST score (leaving out the spreading item) vs sharing: point-biserial r = {r_pv:.2f} (p = {p_pv:.2g}, n = {len(pv)} decisions)", ""]
    open(os.path.join(d, "summary.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    print("figure:", fig_path)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run", default="pilot")
    main(p.parse_args().run)
