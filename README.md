# Prebunking in LLM Agent Social Networks (pilot)

**Question.** In a social network of LLM agents, can psychological inoculation ("prebunking") stop a false headline from spreading, and does it matter *who* is prebunked and *when*?

**Why it matters.** LLM agent simulations (OASIS, MiroFish, POSIM) now reproduce how rumors spread online and are starting to be used to test interventions such as fact-checks, accuracy prompts and debunking. Prebunking is psychology's best-supported defense against misinformation in humans. Rule-based network models (Pilditch, Roozenbeek, Madsen & van der Linden, 2022) predict herd-immunity effects when the right users are inoculated before beliefs consolidate, and RumorSphere (Liu et al., 2025) reports that pre-bunking flattens the rumor curve in a hybrid simulation where most agents follow fixed rules. Neither tests *who* should be prebunked, *when*, and whether never-prebunked agents are protected, with agents that all read the actual message. This pilot does.

![Pilot results](figures/pilot_overview.png)

## Results (pilot, DeepSeek `deepseek-flash`, 100 agents)

Each condition was run on the same 9 cascades (3 networks x 3 false headlines, same seed users), so conditions are compared pairwise.

| Finding | Evidence |
|---|---|
| Prebunking the 30% best-connected agents before the rumor appeared cut its reach from **22% to 9%** of agents (-59%) | -12.9 points, 95% CI [-19.8, -6.0], lower in 8/9 cascades, Wilcoxon p = .008 |
| Prebunking 30% random agents cut reach to 13% (-41%) | -9.0 points, 95% CI [-16.1, -1.9], 7/9, p = .039 |
| **Timing matters:** prebunking the same hubs from round 3, after the rumor started, cut reach only to 16% | early beat late, never worse in 9/9, p = .016 |
| **Indirect protection:** agents who were never prebunked saw the rumor far less often (70% without prebunking vs 29% with hubs prebunked) | lower in 9/9 cascades, p = .004; once exposed they shared at a similar rate (20% vs 15%), so the protection came mainly from not being reached |
| Prebunked agents shared less once exposed | 10.4% vs 18.8% for non-prebunked agents; many explicitly cite "the conspiracy framing the video warned about" |
| **Knowing is not doing:** agents with high conspiracy mentality labeled 90% of MIST fakes correctly, yet shared the false headline 57% of the time when friends did (low: 3%) | MIST score still predicts sharing (point-biserial r = -0.37) |
| Hubs vs random prebunking | Suggestive only: -3.9 points, p = .06, lower in 5/9 |

Full tables: [`results/pilot/summary.md`](results/pilot/summary.md).

## What did not work, and what it means

- **Out of the box, agents almost never spread misinformation.** In a first smoke test agents shared the false headline 7% of the time and it died after the seed users. Adding three news-psychology traits to the personas (conspiracy mentality, intuitive vs analytic thinking, sharing without reading) raised sharing to 21%, with the gradient human studies predict (low 3%, moderate 20%, high 57% conspiracy mentality). The traits were added once, after that smoke test, and are reported as part of the method.
- **The MIST-20 is at ceiling for LLM agents:** 96% of fakes spotted and 100% of real headlines accepted, against 66% and 69% for 1,516 U.S. adults (YouGov, 2023). The items have been public since 2023 and are likely in training data. LLM-based social simulations therefore risk underestimating misinformation spread unless agents are calibrated against human data.
- **True headlines barely spread in any condition** (3-5% of agents, close to the 3% who seeded them), even though agents believed them more than the false ones (5.2 vs 3.4 on a 7-point scale). This mirrors the finding that false news travels farther than true news (Vosoughi, Roy & Aral, 2018), but it means this pilot cannot test whether prebunking makes agents reject true news.

## Design

| Part | Choice |
|---|---|
| Agents | 100 U.S. social media users: age, education, occupation, politics, media trust, Big Five, plus conspiracy mentality, intuitive vs analytic thinking, and sharing habit |
| Network | Scale-free network with clustering (Holme-Kim, m = 3, p = 0.3), so hubs exist; 3 different networks |
| Headlines | MIST-20 items: false A, C, F and true K, M, O; each spreads separately from 3 non-hub seed users |
| Spread rule | Each round, an agent whose friends newly shared the headline rates its accuracy (1-7) and decides whether to share; it may reconsider up to 3 times as more friends share; 8 rounds |
| Conditions | No prebunking · 30% random users prebunked · 30% hubs prebunked · 30% hubs prebunked late (from round 3) |
| Prebunk | Technique-based inoculation (conspiracy framing, fake science, us-versus-them outrage): forewarning plus a weakened example of each, none repeating a MIST claim |
| Measures | Final reach; exposure and sharing of never-prebunked agents; share rate once exposed; MIST-20 taken plain and after the prebunk, compared with YouGov human data |

## Run it

Windows: `python -m venv .venv`, `.venv\Scripts\activate`, `set LLM_API_KEY=sk-...`
Mac/Linux: `python3 -m venv .venv && source .venv/bin/activate`, `export LLM_API_KEY="sk-..."`

```
pip install -r requirements.txt
python run_pilot.py --backend mock --run mock_test        # free pipeline test, fake numbers
python run_pilot.py --backend openai --run calib --calibrate   # MIST-20 only: agents vs humans
python run_pilot.py --backend openai --run pilot          # full pilot (~3,000 calls, a few minutes)
python analyze.py --run pilot                             # figure + summary
```

The script checks the key and model before spending anything, runs DeepSeek in non-thinking mode, and caches every call so interrupted runs resume for free. Other providers: `--base-url` and `--model` (any OpenAI-compatible API).

## Limits of this pilot

One model, 100 agents, 3 networks, 3 false headlines that the model has probably seen, one prebunk text, English only. The prebunk sits in the prebunked agents' instructions, so their own lower sharing is partly instruction following; the indirect protection of never-prebunked agents is a network effect and does not have that problem. Agent behavior is simulated, so results describe LLM agent societies; how closely they track people is measured, not assumed.

## Next steps for the thesis

Move to OASIS; use Chinese Weibo rumors and fresh items the model cannot have memorized; compare several models (DeepSeek, Qwen, GLM, Llama); vary prebunk coverage from 0% to 50% to locate the threshold at which spread stops; test harm to true news with more shareable true headlines; compare the LLM-agent results with the predictions of rule-based inoculation models.

## Sources

- Maertens et al., The Misinformation Susceptibility Test (MIST), *Behavior Research Methods*.
- YouGov, Misinformation Susceptibility poll, April 3-9, 2023, 1,516 U.S. adult citizens.
- Pilditch, Roozenbeek, Madsen & van der Linden (2022), Psychological inoculation can reduce susceptibility to misinformation in large rational agent networks, *Royal Society Open Science*.
- Vosoughi, Roy & Aral (2018), The spread of true and false news online, *Science*.
- OASIS: Open Agent Social Interaction Simulations with One Million Agents (CAMEL-AI, 2024), arXiv:2411.11581.
- Liu et al. (2025), RumorSphere: A Framework for Million-scale Agent-based Dynamic Simulation of Rumor Propagation, arXiv:2509.02172.
- Liu et al. (2024), From Skepticism to Acceptance: Simulating the Attitude Dynamics Toward Fake News, IJCAI 2024 (debunking timing with LLM agents).
- Persona traits: Bruder et al. (2013) conspiracy mentality; Pennycook & Rand (2019) analytic thinking and misinformation; Gabielkov et al. (2016) sharing without reading.
