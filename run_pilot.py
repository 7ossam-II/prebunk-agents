"""Pilot: does prebunking stop misinformation spreading through a network of LLM agents?

Usage:
  python run_pilot.py --backend mock                      # free pipeline test
  set LLM_API_KEY=sk-...    (Windows)   /   export LLM_API_KEY=sk-...    (Mac/Linux)
  python run_pilot.py --backend openai --reps 3           # real run (resumable: cached calls are free)
"""
import argparse
import asyncio
import json
import os
import sys
import time

import pandas as pd

from pilot.items import CASCADE_IDS, ITEMS
from pilot.llm import LLM, FatalAPIError
from pilot.personas import make_personas
from pilot.sim import CONDITIONS, administer_mist, build_graph, run_cascade


def print_calibration(m, personas):
    """Compare agents' MIST-20 accuracy with the human benchmark (YouGov 2023)."""
    m = m.dropna(subset=["correct"])
    human = {v: sum(i["human_pct"] for i in ITEMS.values() if i["veracity"] == v) / 10 for v in ("fake", "real")}
    print("\nCALIBRATION (MIST-20, % correct)        fake     real")
    print(f"  Humans (YouGov 2023, n=1,516)        {human['fake']:5.1f}    {human['real']:5.1f}")
    for inoc, lab in ((0, "Agents, plain"), (1, "Agents, after prebunk")):
        s = m[m.inoculated == inoc].groupby("veracity")["correct"].mean() * 100
        print(f"  {lab:<36} {s.get('fake', float('nan')):5.1f}    {s.get('real', float('nan')):5.1f}")
    plain = m[m.inoculated == 0]
    tot = plain.groupby("agent")["correct"].sum()
    print(f"  Agent total score (of 20): mean {tot.mean():.1f}, SD {tot.std():.1f}, range {tot.min()}-{tot.max()}")
    trait = {p["id"]: p["conspiracy"] for p in personas}
    by = plain.assign(c=plain.agent.map(trait)).groupby("c")["correct"].mean().mul(100).round(1)
    print("  Accuracy by conspiracy mentality: " + ", ".join(f"{k} {v}" for k, v in by.items()))
    item = plain.groupby("item")["correct"].mean() * 100
    hp = pd.Series({k: v["human_pct"] for k, v in ITEMS.items()})
    if item.std() > 0:
        print(f"  Item difficulty vs humans: r = {item.corr(hp.loc[item.index]):.2f}")
    print()


async def main(a):
    out = os.path.join("results", a.run)
    os.makedirs(out, exist_ok=True)
    personas = make_personas(a.agents, seed=0)
    t0 = time.time()
    async with LLM(backend=a.backend, model=a.model, base_url=a.base_url, temperature=a.temperature,
                   concurrency=a.concurrency, cache_path=os.path.join("results", f"cache_{a.backend}.sqlite")) as llm:
        await llm.check()
        print(f"[1/2] MIST-20 for {a.agents} agents x 2 (plain, prebunked)...")
        mist = await administer_mist(llm, personas)
        pd.DataFrame(mist).to_csv(os.path.join(out, "mist.csv"), index=False)
        print_calibration(pd.DataFrame(mist), personas)
        if a.calibrate:
            json.dump({"args": vars(a), "usage": llm.usage}, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"), indent=2)
            print(json.dumps(llm.usage), f"| saved to {out}")
            return

        conds = a.conditions.split(",") if a.conditions else list(CONDITIONS)
        items = a.items.split(",") if a.items else CASCADE_IDS
        jobs = []
        for rep in range(a.reps):
            g = build_graph(a.agents, rep)
            for item in items:
                for cond in conds:
                    jobs.append(run_cascade(llm, g, personas, item, cond, rep, a.rounds, a.seeds, a.frac, a.max_evals))
        print(f"[2/2] {len(jobs)} cascades ({a.reps} reps x {len(items)} headlines x {len(conds)} conditions)...")
        res = await asyncio.gather(*jobs)
        curves = [r for c, _ in res for r in c]
        decisions = [d for _, ds in res for d in ds]
        pd.DataFrame(curves).to_csv(os.path.join(out, "cascades.csv"), index=False)
        pd.DataFrame(decisions).to_csv(os.path.join(out, "decisions.csv"), index=False)
        pd.DataFrame(personas).to_json(os.path.join(out, "personas.json"), orient="records", indent=1)
        meta = {"args": vars(a), "usage": llm.usage, "minutes": round((time.time() - t0) / 60, 1)}
        json.dump(meta, open(os.path.join(out, "meta.json"), "w", encoding="utf-8"), indent=2)
        print(json.dumps(meta["usage"]), f"| {meta['minutes']} min | saved to {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--backend", default="mock", choices=["mock", "openai"])
    p.add_argument("--model", default="deepseek-flash")
    p.add_argument("--base-url", default="https://api.deepseek.com")
    p.add_argument("--run", default="pilot")
    p.add_argument("--agents", type=int, default=100)
    p.add_argument("--reps", type=int, default=3)
    p.add_argument("--rounds", type=int, default=8)
    p.add_argument("--seeds", type=int, default=3, help="agents who post the headline first")
    p.add_argument("--frac", type=float, default=0.30, help="share of agents prebunked")
    p.add_argument("--max-evals", type=int, default=3, help="max times one agent reconsiders a headline")
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--concurrency", type=int, default=16)
    p.add_argument("--conditions", default="")
    p.add_argument("--items", default="")
    p.add_argument("--calibrate", action="store_true", help="only run the MIST-20 and compare agents with humans")
    try:
        asyncio.run(main(p.parse_args()))
    except FatalAPIError as e:
        print(f"\nSTOPPED: {e}\nNothing is lost: finished calls are cached, so rerunning the same command resumes.")
        sys.exit(1)
