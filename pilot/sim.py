"""Network construction, MIST administration and rumor cascades with prebunking conditions."""
import asyncio
import random

import networkx as nx

from .items import ITEMS, MIST20
from .prompts import feed_prompt, mist_prompt, parse_json, system_prompt

CONDITIONS = {
    # name: (who is prebunked, round from which the prebunk is active)
    "control": (None, None),
    "random30": ("random", 0),
    "hubs30": ("hubs", 0),
    "hubs30_late": ("hubs", 3),
}


def build_graph(n, rep):
    # Scale-free degree distribution with clustering (Holme-Kim), so "hubs" exist.
    return nx.powerlaw_cluster_graph(n, 3, 0.3, seed=1000 + rep)


def hub_set(g, frac):
    k = int(round(frac * g.number_of_nodes()))
    return set(sorted(g.nodes, key=lambda v: (-g.degree[v], v))[:k])


async def administer_mist(llm, personas):
    """Every agent takes the MIST-20 twice: once plain, once after the prebunk."""
    items = [ITEMS[i[0]] for i in MIST20]
    rows = []

    async def one(p, inoc):
        rng = random.Random(p["id"] * 7 + (1 if inoc else 0))
        user, order = mist_prompt(items, rng)
        text = await llm.chat(system_prompt(p, inoc), user, tag=f"mist-{p['id']}-{int(inoc)}")
        d = parse_json(text or "") or {}
        ans = d.get("answers", {}) if isinstance(d, dict) else {}
        out = []
        for pos, iid in enumerate(order, 1):
            a = str(ans.get(str(pos), "")).strip().lower()
            label = "fake" if a.startswith("f") else "real" if a.startswith("r") else None
            out.append({"agent": p["id"], "inoculated": int(inoc), "item": iid,
                        "veracity": ITEMS[iid]["veracity"], "answer": label,
                        "correct": None if label is None else int(label == ITEMS[iid]["veracity"])})
        return out

    res = await asyncio.gather(*[one(p, inoc) for p in personas for inoc in (False, True)])
    for r in res:
        rows.extend(r)
    return rows


async def run_cascade(llm, g, personas, item_id, cond, rep, rounds, n_seeds, frac, max_evals):
    who, start = CONDITIONS[cond]
    item = ITEMS[item_id]
    hubs = hub_set(g, frac)
    rng = random.Random(f"{rep}-{item_id}")  # same seeds across conditions (common random numbers)
    non_hubs = sorted(v for v in g.nodes if v not in hubs)
    seeds = set(rng.sample(non_hubs, n_seeds))
    if who == "hubs":
        inoc = hubs - seeds
    elif who == "random":
        r2 = random.Random(f"rand-{rep}")
        inoc = set(r2.sample(sorted(v for v in g.nodes if v not in seeds), int(round(frac * g.number_of_nodes()))))
    else:
        inoc = set()

    shared_at = {s: 0 for s in seeds}
    evals = {v: 0 for v in g.nodes}
    last_k = {v: 0 for v in g.nodes}
    last_belief = {v: None for v in g.nodes}
    decisions, curve = [], [{"round": 0, "shared": len(seeds), "evaluated": 0}]

    for t in range(1, rounds + 1):
        active_inoc = inoc if (start is not None and t >= start) else set()
        cands = []
        for v in g.nodes:
            if v in shared_at or evals[v] >= max_evals:
                continue
            friends = [u for u in g.neighbors(v) if u in shared_at]
            if len(friends) > last_k[v]:
                cands.append((v, friends))

        async def decide(v, friends):
            names = [personas[u]["name"] for u in sorted(friends, key=lambda u: shared_at[u])]
            user = feed_prompt(item["text"], names, last_belief[v])
            is_inoc = v in active_inoc
            text = await llm.chat(system_prompt(personas[v], is_inoc), user,
                                  tag=f"casc-{rep}-{item_id}-{cond}-{t}-{v}")
            d = parse_json(text or "") or {}
            try:
                believe = int(d.get("believe"))
            except Exception:
                believe = None
            share = d.get("share")
            share = share if isinstance(share, bool) else str(share).lower() == "true"
            return v, friends, is_inoc, believe, share, str(d.get("reason", ""))[:200]

        res = await asyncio.gather(*[decide(v, f) for v, f in cands])
        for v, friends, is_inoc, believe, share, reason in res:
            evals[v] += 1
            last_k[v] = len(friends)
            last_belief[v] = believe
            decisions.append({"rep": rep, "item": item_id, "veracity": item["veracity"], "condition": cond,
                              "round": t, "agent": v, "degree": g.degree[v], "k_friends": len(friends),
                              "inoculated": int(is_inoc), "in_inoc_set": int(v in inoc),
                              "believe": believe, "share": int(bool(share)), "reason": reason})
            if share:
                shared_at[v] = t
        curve.append({"round": t, "shared": len(shared_at), "evaluated": len(cands)})

    for c in curve:
        c.update({"rep": rep, "item": item_id, "veracity": item["veracity"], "condition": cond,
                  "n": g.number_of_nodes(), "n_inoc": len(inoc)})
    return curve, decisions
