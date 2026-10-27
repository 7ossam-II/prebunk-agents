"""Analyze a pilot run. Usage: python analyze.py --run pilot

Writes results/<run>/summary.md and figures/<run>_overview.png:
  A. spread of false headlines by condition
  B. indirect protection: unprotected agents who ever saw the false headline
  C. knowing vs doing: agents with a perfect MIST score still share the false headline in the feed

Every condition runs on the same matched cascades, so conditions are compared pairwise: Hodges-Lehmann
estimate of the paired difference, paired bootstrap 95% CI, Wilcoxon signed-rank p and Holm-adjusted p
within each family of tests. Feed decisions are nested in agents, so the MIST-vs-sharing link is tested
with agent-clustered models rather than treating decisions as independent.
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
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests

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
N_BOOT = 10_000


def ci95(x):
    x = np.asarray(x, float)
    return 0.0 if len(x) < 2 else stats.t.ppf(0.975, len(x) - 1) * x.std(ddof=1) / np.sqrt(len(x))


def sig2(p):
    return float(f"{p:.2g}")


def hodges_lehmann(x):
    """Median of the Walsh averages (the estimate that goes with the Wilcoxon signed-rank test), row-wise."""
    x = np.asarray(x, float)
    i, j = np.triu_indices(x.shape[-1])
    return np.median((x[..., i] + x[..., j]) / 2, axis=-1)


def boot_ci(diff, seed=0):
    """Paired bootstrap 95% CI of the Hodges-Lehmann estimate: resample matched cascades with replacement."""
    x = np.asarray(diff, float)
    idx = np.random.default_rng(seed).integers(0, len(x), (N_BOOT, len(x)))
    return np.percentile(hodges_lehmann(x[idx]), [2.5, 97.5])


def cluster_boot_r(df, x, y, cluster, seed=0):
    """Bootstrap 95% CI of the Pearson r of x and y over all rows, resampling whole clusters with replacement."""
    s = (df.assign(n=1, xy=df[x] * df[y], xx=df[x] ** 2, yy=df[y] ** 2)
         .groupby(cluster)[["n", x, y, "xy", "xx", "yy"]].sum().to_numpy(float))
    k = len(s)
    n, sx, sy, sxy, sxx, syy = (np.random.default_rng(seed).multinomial(k, np.full(k, 1 / k), size=N_BOOT) @ s).T
    with np.errstate(invalid="ignore", divide="ignore"):
        r = (n * sxy - sx * sy) / np.sqrt((n * sxx - sx ** 2) * (n * syy - sy ** 2))
    return np.nanpercentile(r, [2.5, 97.5])


def paired_tests(piv, net, pairs):
    """Matched-cascade comparisons x - y (one row of piv per cascade), Holm-adjusted across `pairs`.
    `net` holds the same measure averaged over the headlines of each network: a direction check only,
    since the cascades of one network share its agents and graph."""
    rows = []
    for x, y in pairs:
        diff = piv[x] - piv[y]
        nz = diff[diff != 0]  # Wilcoxon drops zero differences
        lo, hi = boot_ci(diff)
        nd = net[x] - net[y]
        rows.append({"comparison": f"{COND[x][0]} vs {COND[y][0].lower()}", "hl_diff_pts": round(float(hodges_lehmann(diff)), 1),
                     "ci95_boot": f"[{lo:+.1f}, {hi:+.1f}]", "lower_in": f"{int((diff < 0).sum())}/{len(diff)}",
                     "n_eff": len(nz), "wilcoxon_p": stats.wilcoxon(nz).pvalue if len(nz) else np.nan,
                     "by_network": ", ".join(f"{v:+.1f}" for v in nd), "networks_lower": f"{int((nd < 0).sum())}/{len(nd)}"})
    t = pd.DataFrame(rows)
    t["holm_p"] = np.nan
    ok = t["wilcoxon_p"].notna()
    if ok.any():
        t.loc[ok, "holm_p"] = multipletests(t.loc[ok, "wilcoxon_p"], method="holm")[1]
    for c in ("wilcoxon_p", "holm_p"):
        t[c] = t[c].map(sig2)
    return t[["comparison", "hl_diff_pts", "ci95_boot", "lower_in", "n_eff", "wilcoxon_p", "holm_p", "by_network", "networks_lower"]]


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
    fk = dec[dec.veracity == "fake"]

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
    belief = dec.groupby("veracity")["believe"].mean()

    # 2. Paired tests on false headlines (same network, seeds and headline across conditions)
    fake_final = final[final.veracity == "fake"]
    piv = fake_final.pivot_table(index=["rep", "item"], columns="condition", values="pct")
    net = fake_final.pivot_table(index="rep", columns="condition", values="pct")
    tests = paired_tests(piv, net, [(x, y) for x, y in (("random30", "control"), ("hubs30", "control"), ("hubs30_late", "control"),
                                                        ("hubs30", "random30"), ("hubs30_late", "hubs30")) if x in piv and y in piv])
    dead = [f"rep {r}, headline {i}" for r, i in piv.index[(piv == 100 * a["seeds"] / a["agents"]).all(axis=1)]]

    # 3. Indirect protection: agents who were never prebunked (and did not seed the rumor).
    # Definition A: the unprotected agents of each condition (without prebunking, every non-seed agent, hubs included).
    # Definition B, like-for-like: the same agents in every condition, those in neither the hub set nor the random set.
    herd, outside = [], {}
    for rep in sorted(int(r) for r in casc.rep.unique()):
        for item in fake_items:
            g, seeds, sets = protection_sets(rep, item, a["agents"], a["frac"], a["seeds"])
            outside[(rep, item)] = {v for v in g.nodes if v not in sets["hubs30"] and v not in seeds}
            same = [v for v in g.nodes if v not in sets["hubs30"] and v not in sets["random30"] and v not in seeds]
            for c in conds:
                dd = dec[(dec.rep == rep) & (dec["item"] == item) & (dec.condition == c)]
                ev, sh = set(dd.agent), set(dd[dd.share == 1].agent)
                unprot = [v for v in g.nodes if v not in sets[c] and v not in seeds]
                herd.append({"rep": rep, "item": item, "condition": c,
                             "exposed": 100 * np.mean([v in ev for v in unprot]),
                             "shared": 100 * np.mean([v in sh for v in unprot]),
                             "exposed_same": 100 * np.mean([v in ev for v in same]), "n_same": len(same)})
    herd = pd.DataFrame(herd)
    herd_tab = herd.groupby("condition").agg(exposed=("exposed", "mean"), exposed_ci=("exposed", ci95),
                                             shared=("shared", "mean")).reindex(conds).round(1)
    herd_tab.index = [COND[c][0] for c in herd_tab.index]
    herd_same_tab = herd.groupby("condition").agg(saw_it_pct=("exposed_same", "mean"), ci95=("exposed_same", ci95)).reindex(conds).round(1)
    herd_same_tab.index = [COND[c][0] for c in herd_same_tab.index]
    pairs_h = [(x, "control") for x in ("hubs30", "hubs30_late", "random30") if x in conds and "control" in conds]

    def herd_paired(col):
        return paired_tests(herd.pivot_table(index=["rep", "item"], columns="condition", values=col),
                            herd.pivot_table(index="rep", columns="condition", values=col), pairs_h)
    herd_tests, herd_tests_same = herd_paired("exposed"), herd_paired("exposed_same")

    # Share rate once exposed, same agents in both conditions: non-seed agents outside the 30% hub set
    lf = fk[fk.condition.isin(["control", "hubs30"])]
    lf = lf[[v in outside[(r, it)] for r, it, v in zip(lf.rep, lf["item"], lf.agent)]]
    once = lf.groupby(["condition", "rep", "item", "agent"])["share"].max().groupby("condition")
    exposed_tab = pd.DataFrame({"share_rate_pct": lf.groupby("condition")["share"].mean() * 100,
                                "decisions": lf.groupby("condition").size(),
                                "ever_shared_pct": once.mean() * 100, "exposed": once.size()})
    exposed_tab = exposed_tab.reindex([c for c in ("control", "hubs30") if c in exposed_tab.index]).round(1)
    exposed_tab.index = [COND[c][0] for c in exposed_tab.index]

    # 4. Direct effect: share rate when exposed, prebunked vs not
    direct = pd.DataFrame([
        {"agents": "Not prebunked (all conditions)", "share_rate_pct": round(100 * fk[fk.inoculated == 0].share.mean(), 1),
         "mean_belief": round(fk[fk.inoculated == 0].believe.mean(), 2), "decisions": int((fk.inoculated == 0).sum())},
        {"agents": "Prebunked (active)", "share_rate_pct": round(100 * fk[fk.inoculated == 1].share.mean(), 1),
         "mean_belief": round(fk[fk.inoculated == 1].believe.mean(), 2), "decisions": int((fk.inoculated == 1).sum())}])
    hubs_by_rep = {int(r): hub_set(build_graph(a["agents"], int(r)), a["frac"]) for r in casc.rep.unique()}
    pb = fk[fk.inoculated == 1]
    pb_hub_pct = 100 * np.mean([v in hubs_by_rep[r] for r, v in zip(pb.rep, pb.agent)])

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
    # Same comparison within agents who got every MIST-20 item right, so what they know is not in doubt
    tot = plain.groupby("agent")["correct"].sum()
    perfect = set(tot[tot == len(ITEMS)].index)
    pf = ctrl[ctrl.agent.isin(perfect)]
    levels_pf = [l for l in levels if l in set(pf.conspiracy)]
    kd_pf = pd.DataFrame({
        "agents": pf.groupby("conspiracy")["agent"].nunique(),
        "called_fake_on_MIST_pct": fake_test[fake_test.agent.isin(set(pf.agent))].groupby("conspiracy")["correct"].mean().mul(100),
        "shared_in_feed_pct": pf.groupby("conspiracy")["share"].mean().mul(100),
        "feed_decisions": pf.groupby("conspiracy").size(),
        "agents_shared_at_least_once": pf.groupby(["conspiracy", "agent"])["share"].max().groupby("conspiracy").sum()}).reindex(levels_pf).round(1)

    # 6. MIST: agents vs humans
    human = {v: np.mean([i["human_pct"] for i in ITEMS.values() if i["veracity"] == v]) for v in ("fake", "real")}
    agent_acc = plain.groupby("veracity")["correct"].mean() * 100
    pre_acc = m[m.inoculated == 1].groupby("veracity")["correct"].mean() * 100
    item_acc = plain.groupby("item")["correct"].mean() * 100
    hp = pd.Series({k: v["human_pct"] for k, v in ITEMS.items()})
    r_items, p_items = stats.pearsonr(item_acc, hp.loc[item_acc.index])

    # 7. Does the MIST score (leaving out the spreading item) predict sharing? Decisions are nested in agents,
    # so: GEE logistic regression with agent clusters, an agent-level correlation, and a cluster bootstrap.
    ic = plain.set_index(["agent", "item"])["correct"]
    pv = ctrl.copy()
    pv["mist_loo"] = [tot.get(x, np.nan) - ic.get((x, it), 0) for x, it in zip(pv.agent, pv["item"])]
    pv = pv.dropna(subset=["mist_loo"])
    gee = []
    for label, f in (("MIST score", "share ~ mist_loo"), ("MIST score + conspiracy mentality", "share ~ mist_loo + C(conspiracy)")):
        fit = smf.gee(f, groups="agent", data=pv, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
        lo, hi = np.exp(fit.conf_int().loc["mist_loo"])
        gee.append({"model": label, "odds_ratio_per_point": round(float(np.exp(fit.params["mist_loo"])), 2),
                    "ci95": f"[{lo:.2f}, {hi:.2f}]", "p": sig2(fit.pvalues["mist_loo"])})
    gee = pd.DataFrame(gee)
    ag = pv.groupby("agent").agg(share=("share", "mean"), mist=("mist_loo", "mean"))
    rho, p_rho = stats.spearmanr(ag["share"], ag["mist"])
    r_pv = stats.pointbiserialr(pv["share"], pv["mist_loo"])[0]
    r_lo, r_hi = cluster_boot_r(pv, "mist_loo", "share", "agent")
    below = per.set_index("id").loc[[x for x in ag.index if tot[x] < len(ITEMS)], "conspiracy"].value_counts()

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
    xs = np.arange(len(levels_pf))
    w = 0.36
    b1 = ax.bar(xs - w / 2 - 0.01, kd_pf["called_fake_on_MIST_pct"], width=w, color=TEST_C, edgecolor=SURFACE, linewidth=2,
                label="On the MIST test: called fakes fake")
    b2 = ax.bar(xs + w / 2 + 0.01, kd_pf["shared_in_feed_pct"], width=w, color=FEED_C, edgecolor=SURFACE, linewidth=2,
                label="In the feed: shared the false headline")
    for bars in (b1, b2):
        for r in bars:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 2, f"{r.get_height():.0f}%", ha="center", color=INK, fontsize=9)
    ax.set_xticks(xs, [f"{l.capitalize()}\n{int(kd_pf.loc[l, 'agents'])} agents" for l in levels_pf])
    ax.set_xlabel("Agent's conspiracy mentality", color=INK2, fontsize=9)
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_ylabel("%", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc="upper center", ncol=1, bbox_to_anchor=(0.45, -0.22))
    ax.set_title("C. Knowing a headline is fake is not enough", loc="left", color=INK, fontsize=11, fontweight="bold")

    h, l = fig.axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, frameon=False, fontsize=9, labelcolor=INK2, bbox_to_anchor=(0.5, 1.05))
    n_casc = len(piv)
    fig.text(0.01, -0.24, f"Pilot. {a['model']}, {a['agents']} agents, scale-free networks, {n_casc} matched cascades per condition "
             f"({a['reps']} networks x {len(fake_items)} MIST-20 false headlines). Bars and bands: 95% CI. "
             f"C: no-prebunking condition, only agents with a perfect {len(ITEMS)}/{len(ITEMS)} MIST-20 score.",
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
         f"Mean belief (1-7), all feed decisions: true headlines {belief.get('real', np.nan):.1f}, "
         f"false headlines {belief.get('fake', np.nan):.1f}", "",
         "## 2. Paired tests, false headlines (same network, seeds and headline in every condition)", "",
         f"hl_diff_pts: Hodges-Lehmann estimate of the paired difference, in percentage points. ci95_boot: paired bootstrap "
         f"95% CI ({N_BOOT:,} resamples of the {n_casc} cascades). n_eff: cascades with a nonzero difference (the Wilcoxon "
         f"test drops ties). holm_p: Holm-adjusted across the {len(tests)} tests. by_network: difference of the means over "
         f"the {len(fake_items)} headlines of each network, a direction check only.", "",
         tests.to_markdown(index=False), "",
         f"Never spread beyond its {a['seeds']} seed users in any condition, so a zero difference in every comparison: "
         f"{'; '.join(dead) if dead else 'none'}.", "",
         "## 3. Indirect protection: agents who were never prebunked and did not seed the rumor", "",
         "Definition A (README headline and figure panel B): the never-prebunked, non-seed agents of each condition. "
         "Without prebunking that is every non-seed agent, hubs included.", "",
         herd_tab.rename(columns={"exposed": "saw_it_pct", "exposed_ci": "ci95", "shared": "shared_it_pct"}).to_markdown(), "",
         f"Paired tests on saw_it_pct, definition A (columns as in section 2; Holm-adjusted across these {len(herd_tests)} tests):", "",
         herd_tests.to_markdown(index=False), "",
         "Definition B, like-for-like: the same agents in every condition, those in neither the hub set nor the random set "
         f"and not seeds ({herd.n_same.min()}-{herd.n_same.max()} agents per cascade).", "",
         herd_same_tab.to_markdown(), "",
         f"Paired tests on saw_it_pct, definition B (Holm-adjusted across these {len(herd_tests_same)} tests):", "",
         herd_tests_same.to_markdown(index=False), "",
         "Share rate once exposed, same agents in both conditions (false headlines; non-seed agents outside the "
         f"{a['frac']:.0%} hub set of their network). share_rate_pct is per decision (an agent may reconsider up to "
         f"{a['max_evals']} times); ever_shared_pct is per exposed agent and cascade.", "",
         exposed_tab.to_markdown(), "",
         "## 4. Direct effect: share rate once exposed (false headlines)", "", direct.to_markdown(index=False), "",
         f"Pooled decisions of different agents ({pb_hub_pct:.0f}% of the prebunked decisions are by hubs), so descriptive only.", "",
         "## 5. Knowing vs doing, by conspiracy mentality (no-prebunking condition)", "", kd.to_markdown(), "",
         f"All agents: {100 * ctrl.share.mean():.1f}% of {len(ctrl)} decisions shared the false headline.", "",
         f"Agents with a perfect {len(ITEMS)}/{len(ITEMS)} MIST-20 score only:", "", kd_pf.to_markdown(), "",
         "Other traits (share rate when exposed):", ""]
    for t in ("thinking", "sharing"):
        L += [traits[t].to_markdown(), ""]
    L += ["## 6. MIST-20: agents vs humans", "",
          f"Fake headlines spotted: humans {human['fake']:.1f}%, agents {agent_acc['fake']:.1f}%, agents after prebunk {pre_acc['fake']:.1f}%",
          f"Real headlines accepted: humans {human['real']:.1f}%, agents {agent_acc['real']:.1f}%, agents after prebunk {pre_acc['real']:.1f}%",
          f"Item difficulty, agents vs humans: r = {r_items:.2f} (p = {p_items:.2g})", "",
          "## 7. Does the MIST score predict sharing? (no-prebunking condition, false headlines)", "",
          f"MIST score leaves out the spreading headline. {len(pv)} decisions from {pv.agent.nunique()} agents, analysed with "
          "agents as clusters. GEE logistic regression, exchangeable working correlation; odds ratio per MIST point:", "",
          gee.to_markdown(index=False), "",
          f"Agent-level Spearman rho = {rho:.2f} (p = {p_rho:.2g}, n = {len(ag)} agents; share rate vs mean MIST score)",
          f"Decision-level point-biserial r = {r_pv:.2f}, cluster bootstrap 95% CI [{r_lo:.2f}, {r_hi:.2f}] "
          f"({N_BOOT:,} resamples of agents)",
          f"{len(perfect)} of {len(tot)} agents scored {len(ITEMS)}/{len(ITEMS)}, so the link rests on the {below.sum()} agents "
          f"in this analysis who did not ({', '.join(f'{below.get(l, 0)} {l}' for l in levels)} conspiracy mentality).", "",
          "## 8. Caveats", "",
          f"- The {n_casc} cascades are not independent: they come from {a['reps']} networks, and the {len(fake_items)} headlines "
          "on one network share its agents and graph. The cascade-level tests treat them as independent. "
          f"{a['reps']} networks are too few for a network-level test, so by_network is a direction check only.",
          "- Holm adjustment is within each family (the reach tests in section 2, each definition's indirect-protection tests "
          "in section 3), not across the whole report.",
          "- Indirect protection depends on the definition (section 3). Definition A counts the hubs in the no-prebunking "
          "baseline but not in the hub condition, so it mixes the network effect with who is counted. Definition B compares "
          "the same agents and is the stricter test.", ""]
    open(os.path.join(d, "summary.md"), "w", encoding="utf-8").write("\n".join(L))
    print("\n".join(L))
    print("figure:", fig_path)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run", default="pilot")
    main(p.parse_args().run)
